"""
告警数据模型

定义告警、告警组、规则等核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable
import hashlib


class AlertSeverity(str, Enum):
    """告警严重程度"""
    CRITICAL = "critical"       # 严重
    HIGH = "high"               # 高
    WARNING = "warning"         # 警告
    LOW = "low"                 # 低
    INFO = "info"               # 信息


class AlertStatus(str, Enum):
    """告警状态"""
    FIRING = "firing"           # 触发中
    RESOLVED = "resolved"       # 已恢复
    SUPPRESSED = "suppressed"   # 已抑制
    ACKNOWLEDGED = "acknowledged"  # 已确认


@dataclass
class Alert:
    """
    告警

    表示一条告警信息
    """
    alert_id: str                               # 告警ID
    title: str                                  # 告警标题
    description: str = ""                       # 告警描述
    severity: AlertSeverity = AlertSeverity.WARNING  # 严重程度
    status: AlertStatus = AlertStatus.FIRING    # 状态

    # 来源信息
    source: str = ""                            # 告警来源（服务/组件）
    host: str = ""                              # 主机
    service: str = ""                           # 服务名
    component: str = ""                         # 组件

    # 时间信息
    fired_at: datetime = field(default_factory=datetime.now)  # 触发时间
    resolved_at: datetime | None = None         # 恢复时间
    last_fired_at: datetime | None = None       # 最后触发时间

    # 统计
    fire_count: int = 1                         # 触发次数
    duration_seconds: float = 0                 # 持续时间

    # 标签和注解
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    # 元数据
    fingerprint: str = ""                       # 指纹（用于去重）
    group_key: str = ""                         # 分组键
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.fingerprint:
            self.fingerprint = self._generate_fingerprint()
        if not self.group_key:
            self.group_key = self._generate_group_key()
        if isinstance(self.severity, str):
            self.severity = AlertSeverity(self.severity)
        if isinstance(self.status, str):
            self.status = AlertStatus(self.status)

    def _generate_fingerprint(self) -> str:
        """生成告警指纹"""
        content = f"{self.title}:{self.source}:{self.host}:{self.service}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _generate_group_key(self) -> str:
        """生成分组键"""
        return f"{self.source}:{self.service}:{self.severity.value}"

    @property
    def severity_score(self) -> int:
        """严重程度分数"""
        scores = {
            AlertSeverity.CRITICAL: 5,
            AlertSeverity.HIGH: 4,
            AlertSeverity.WARNING: 3,
            AlertSeverity.LOW: 2,
            AlertSeverity.INFO: 1,
        }
        return scores.get(self.severity, 0)

    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self.status == AlertStatus.FIRING

    def matches(self, other: "Alert", threshold: float = 0.8) -> bool:
        """
        检查与另一条告警是否匹配（用于去重）

        Args:
            other: 另一条告警
            threshold: 相似度阈值

        Returns:
            是否匹配
        """
        # 指纹相同则匹配
        if self.fingerprint == other.fingerprint:
            return True

        # 计算相似度
        score = 0
        total = 4

        if self.title == other.title:
            score += 1
        if self.source == other.source:
            score += 1
        if self.service == other.service:
            score += 1
        if self.severity == other.severity:
            score += 1

        return score / total >= threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "source": self.source,
            "host": self.host,
            "service": self.service,
            "component": self.component,
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
            "fire_count": self.fire_count,
            "fingerprint": self.fingerprint,
            "labels": self.labels,
        }


@dataclass
class AlertGroup:
    """
    告警组

    聚合相关的告警
    """
    group_id: str                               # 组ID
    group_key: str                              # 分组键
    alerts: list[Alert] = field(default_factory=list)  # 组内告警
    representative: Alert | None = None          # 代表告警

    # 聚合统计
    total_count: int = 0                        # 总告警数
    active_count: int = 0                       # 活跃告警数
    first_fired_at: datetime | None = None      # 首次触发
    last_fired_at: datetime | None = None       # 最后触发

    # 元数据
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_alert(self, alert: Alert) -> None:
        """添加告警到组"""
        self.alerts.append(alert)
        self.total_count = len(self.alerts)
        self.active_count = sum(1 for a in self.alerts if a.is_active)

        # 更新时间
        if self.first_fired_at is None or alert.fired_at < self.first_fired_at:
            self.first_fired_at = alert.fired_at
        if self.last_fired_at is None or alert.fired_at > self.last_fired_at:
            self.last_fired_at = alert.fired_at

        # 更新代表告警（选择最高严重程度的）
        if self.representative is None or alert.severity_score > self.representative.severity_score:
            self.representative = alert

    @property
    def severity(self) -> AlertSeverity:
        """组的严重程度（取最高）"""
        if self.representative:
            return self.representative.severity
        if self.alerts:
            return max(self.alerts, key=lambda a: a.severity_score).severity
        return AlertSeverity.INFO

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "group_key": self.group_key,
            "severity": self.severity.value,
            "total_count": self.total_count,
            "active_count": self.active_count,
            "first_fired_at": self.first_fired_at.isoformat() if self.first_fired_at else None,
            "last_fired_at": self.last_fired_at.isoformat() if self.last_fired_at else None,
            "representative": self.representative.to_dict() if self.representative else None,
            "alert_ids": [a.alert_id for a in self.alerts],
        }


@dataclass
class AlertRule:
    """告警规则基类"""
    rule_id: str                                # 规则ID
    name: str                                   # 规则名称
    description: str = ""                       # 描述
    enabled: bool = True                        # 是否启用
    priority: int = 0                           # 优先级（越高越先执行）

    def match(self, alert: Alert) -> bool:
        """检查告警是否匹配规则"""
        raise NotImplementedError

    def apply(self, alert: Alert) -> Alert | None:
        """应用规则，返回处理后的告警或None（表示过滤掉）"""
        raise NotImplementedError


@dataclass
class SuppressRule(AlertRule):
    """
    抑制规则

    用于抑制特定条件的告警
    """
    condition: Callable[[Alert], bool] | None = None  # 匹配条件
    matchers: dict[str, str] = field(default_factory=dict)  # 标签匹配器
    time_window: timedelta | None = None         # 时间窗口
    max_fires: int = 0                           # 最大触发次数（0表示不限制）

    def match(self, alert: Alert) -> bool:
        """检查是否匹配抑制条件"""
        if not self.enabled:
            return False

        # 自定义条件
        if self.condition and self.condition(alert):
            return True

        # 标签匹配
        if self.matchers:
            for key, value in self.matchers.items():
                if alert.labels.get(key) != value:
                    return False
            return True

        return False

    def apply(self, alert: Alert) -> Alert | None:
        """应用抑制规则"""
        if self.match(alert):
            alert.status = AlertStatus.SUPPRESSED
            alert.metadata["suppressed_by"] = self.rule_id
            return None  # 抑制
        return alert


@dataclass
class AggregateRule(AlertRule):
    """
    聚合规则

    用于将相关告警聚合到一起
    """
    group_by: list[str] = field(default_factory=list)  # 分组字段
    time_window: timedelta = field(default_factory=lambda: timedelta(minutes=5))

    def get_group_key(self, alert: Alert) -> str:
        """获取告警的分组键"""
        parts = []
        for field_name in self.group_by:
            if field_name == "severity":
                parts.append(alert.severity.value)
            elif field_name == "source":
                parts.append(alert.source)
            elif field_name == "service":
                parts.append(alert.service)
            elif field_name == "host":
                parts.append(alert.host)
            elif field_name == "component":
                parts.append(alert.component)
            elif field_name in alert.labels:
                parts.append(alert.labels[field_name])
        return ":".join(parts) if parts else "default"

    def match(self, alert: Alert) -> bool:
        return self.enabled

    def apply(self, alert: Alert) -> Alert | None:
        alert.group_key = self.get_group_key(alert)
        return alert


@dataclass
class DedupeRule(AlertRule):
    """
    去重规则

    用于去除重复告警
    """
    dedupe_by: list[str] = field(default_factory=lambda: ["fingerprint"])
    time_window: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    merge_count: bool = True                    # 是否合并计数

    def get_dedupe_key(self, alert: Alert) -> str:
        """获取去重键"""
        parts = []
        for field_name in self.dedupe_by:
            if field_name == "fingerprint":
                parts.append(alert.fingerprint)
            elif field_name == "title":
                parts.append(alert.title)
            elif field_name == "source":
                parts.append(alert.source)
            elif field_name == "service":
                parts.append(alert.service)
        return ":".join(parts) if parts else alert.fingerprint

    def match(self, alert: Alert) -> bool:
        return self.enabled

    def apply(self, alert: Alert) -> Alert | None:
        return alert


@dataclass
class AlertConfig:
    """告警过滤配置"""
    # 去重
    enable_dedupe: bool = True
    dedupe_window_minutes: int = 10
    dedupe_similarity_threshold: float = 0.8

    # 聚合
    enable_aggregate: bool = True
    aggregate_by: list[str] = field(default_factory=lambda: ["service", "severity"])
    aggregate_window_minutes: int = 5

    # 抑制
    enable_suppress: bool = True
    suppress_low_severity: bool = False         # 抑制低优先级告警
    suppress_resolved: bool = True              # 抑制已恢复的告警

    # 降噪
    enable_noise_reduction: bool = True
    noise_threshold: int = 10                   # 短时间内超过此数量视为噪音
    noise_window_minutes: int = 5

    # 排序
    sort_by_severity: bool = True
    sort_by_time: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "enable_dedupe": self.enable_dedupe,
            "enable_aggregate": self.enable_aggregate,
            "enable_suppress": self.enable_suppress,
            "enable_noise_reduction": self.enable_noise_reduction,
        }


@dataclass
class AlertFilterResult:
    """
    告警过滤结果
    """
    # 输入统计
    total_input: int = 0                        # 输入告警数

    # 输出
    filtered_alerts: list[Alert] = field(default_factory=list)  # 过滤后的告警
    alert_groups: list[AlertGroup] = field(default_factory=list)  # 告警组

    # 过滤统计
    dedupe_count: int = 0                       # 去重数量
    suppressed_count: int = 0                   # 抑制数量
    noise_filtered_count: int = 0               # 噪音过滤数量
    total_filtered: int = 0                     # 总过滤数量

    # 按严重程度统计
    severity_counts: dict[str, int] = field(default_factory=dict)

    # 处理时间
    processing_time_ms: float = 0

    @property
    def output_count(self) -> int:
        """输出告警数"""
        return len(self.filtered_alerts)

    @property
    def filter_rate(self) -> float:
        """过滤率"""
        if self.total_input == 0:
            return 0
        return self.total_filtered / self.total_input

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_input": self.total_input,
            "output_count": self.output_count,
            "filter_rate": f"{self.filter_rate:.1%}",
            "dedupe_count": self.dedupe_count,
            "suppressed_count": self.suppressed_count,
            "noise_filtered_count": self.noise_filtered_count,
            "group_count": len(self.alert_groups),
            "severity_counts": self.severity_counts,
            "processing_time_ms": self.processing_time_ms,
        }
