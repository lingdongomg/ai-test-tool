"""
健康度评分数据模型

定义健康度评分相关的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"           # 健康
    DEGRADED = "degraded"         # 降级
    UNHEALTHY = "unhealthy"       # 不健康
    CRITICAL = "critical"         # 严重
    UNKNOWN = "unknown"           # 未知


class MetricType(str, Enum):
    """指标类型"""
    AVAILABILITY = "availability"     # 可用性
    LATENCY = "latency"               # 延迟
    ERROR_RATE = "error_rate"         # 错误率
    THROUGHPUT = "throughput"         # 吞吐量
    SATURATION = "saturation"         # 饱和度
    CUSTOM = "custom"                 # 自定义


class TrendDirection(str, Enum):
    """趋势方向"""
    IMPROVING = "improving"       # 改善
    STABLE = "stable"             # 稳定
    DEGRADING = "degrading"       # 恶化
    UNKNOWN = "unknown"           # 未知


@dataclass
class HealthMetric:
    """
    健康指标

    表示单个健康度量指标
    """
    name: str                                   # 指标名称
    value: float                                # 当前值
    metric_type: MetricType = MetricType.CUSTOM # 指标类型

    # 阈值
    threshold_warning: float | None = None      # 警告阈值
    threshold_critical: float | None = None     # 严重阈值

    # 权重
    weight: float = 1.0                         # 权重（用于计算总分）

    # 元数据
    unit: str = ""                              # 单位
    description: str = ""                       # 描述
    timestamp: datetime = field(default_factory=datetime.now)

    # 历史数据（用于趋势分析）
    history: list[tuple[datetime, float]] = field(default_factory=list)

    @property
    def score(self) -> float:
        """
        计算指标得分（0-100）

        根据指标类型和阈值计算
        """
        if self.threshold_critical is None:
            return 100.0

        # 对于不同类型的指标，评分逻辑不同
        if self.metric_type == MetricType.AVAILABILITY:
            # 可用性：值越高越好
            return min(100.0, self.value)

        elif self.metric_type == MetricType.ERROR_RATE:
            # 错误率：值越低越好
            if self.value >= self.threshold_critical:
                return 0.0
            elif self.threshold_warning and self.value >= self.threshold_warning:
                # 线性插值
                ratio = (self.threshold_critical - self.value) / (
                    self.threshold_critical - self.threshold_warning
                )
                return ratio * 50  # 50-0分
            else:
                if self.threshold_warning:
                    ratio = (self.threshold_warning - self.value) / self.threshold_warning
                    return 50 + ratio * 50  # 100-50分
                return 100.0

        elif self.metric_type == MetricType.LATENCY:
            # 延迟：值越低越好
            if self.value >= self.threshold_critical:
                return 0.0
            elif self.threshold_warning and self.value >= self.threshold_warning:
                ratio = (self.threshold_critical - self.value) / (
                    self.threshold_critical - self.threshold_warning
                )
                return ratio * 50
            else:
                return 100.0

        elif self.metric_type == MetricType.THROUGHPUT:
            # 吞吐量：值越高越好
            if self.threshold_critical and self.value <= self.threshold_critical:
                return 0.0
            return 100.0

        elif self.metric_type == MetricType.SATURATION:
            # 饱和度：值越低越好（类似错误率）
            if self.value >= self.threshold_critical:
                return 0.0
            elif self.threshold_warning and self.value >= self.threshold_warning:
                ratio = (self.threshold_critical - self.value) / (
                    self.threshold_critical - self.threshold_warning
                )
                return ratio * 50
            else:
                return 100.0

        # 默认：线性评分
        return max(0.0, min(100.0, 100 - self.value))

    @property
    def status(self) -> HealthStatus:
        """获取指标状态"""
        score = self.score
        if score >= 90:
            return HealthStatus.HEALTHY
        elif score >= 70:
            return HealthStatus.DEGRADED
        elif score >= 50:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.CRITICAL

    @property
    def trend(self) -> TrendDirection:
        """计算趋势方向"""
        if len(self.history) < 3:
            return TrendDirection.UNKNOWN

        # 取最近几个值计算趋势
        recent = [v for _, v in self.history[-5:]]
        if len(recent) < 2:
            return TrendDirection.UNKNOWN

        # 计算平均变化
        changes = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        avg_change = sum(changes) / len(changes)

        # 根据指标类型判断趋势
        threshold = 0.05  # 5%变化视为显著

        if self.metric_type in (MetricType.ERROR_RATE, MetricType.LATENCY, MetricType.SATURATION):
            # 值越低越好
            if avg_change < -threshold:
                return TrendDirection.IMPROVING
            elif avg_change > threshold:
                return TrendDirection.DEGRADING
        else:
            # 值越高越好
            if avg_change > threshold:
                return TrendDirection.IMPROVING
            elif avg_change < -threshold:
                return TrendDirection.DEGRADING

        return TrendDirection.STABLE

    def add_history(self, value: float, timestamp: datetime | None = None) -> None:
        """添加历史数据点"""
        ts = timestamp or datetime.now()
        self.history.append((ts, value))
        # 保留最近100个点
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "score": self.score,
            "status": self.status.value,
            "trend": self.trend.value,
            "weight": self.weight,
            "unit": self.unit,
            "threshold_warning": self.threshold_warning,
            "threshold_critical": self.threshold_critical,
        }


@dataclass
class ComponentHealth:
    """
    组件健康度

    表示单个组件的健康状态
    """
    component_id: str                           # 组件ID
    name: str                                   # 组件名称
    component_type: str = ""                    # 组件类型（service, database, cache等）

    # 指标
    metrics: list[HealthMetric] = field(default_factory=list)

    # 状态
    status: HealthStatus = HealthStatus.UNKNOWN
    score: float = 0.0                          # 综合得分

    # 依赖
    dependencies: list[str] = field(default_factory=list)  # 依赖的组件ID

    # 元数据
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)

    def add_metric(self, metric: HealthMetric) -> None:
        """添加指标"""
        self.metrics.append(metric)
        self._recalculate()

    def update_metric(self, name: str, value: float) -> bool:
        """更新指标值"""
        for metric in self.metrics:
            if metric.name == name:
                metric.add_history(metric.value)
                metric.value = value
                metric.timestamp = datetime.now()
                self._recalculate()
                return True
        return False

    def get_metric(self, name: str) -> HealthMetric | None:
        """获取指标"""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def _recalculate(self) -> None:
        """重新计算综合得分和状态"""
        if not self.metrics:
            self.score = 0
            self.status = HealthStatus.UNKNOWN
            return

        # 加权平均
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            self.score = 0
        else:
            self.score = sum(m.score * m.weight for m in self.metrics) / total_weight

        # 状态取决于最差的指标
        worst_status = HealthStatus.HEALTHY
        status_order = [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
            HealthStatus.CRITICAL,
        ]

        for metric in self.metrics:
            if status_order.index(metric.status) > status_order.index(worst_status):
                worst_status = metric.status

        self.status = worst_status
        self.last_check = datetime.now()

    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == HealthStatus.HEALTHY

    @property
    def issues(self) -> list[str]:
        """获取问题列表"""
        issues = []
        for metric in self.metrics:
            if metric.status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                issues.append(f"{metric.name}: {metric.value}{metric.unit} ({metric.status.value})")
        return issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "type": self.component_type,
            "status": self.status.value,
            "score": round(self.score, 2),
            "is_healthy": self.is_healthy,
            "metrics": [m.to_dict() for m in self.metrics],
            "dependencies": self.dependencies,
            "issues": self.issues,
            "last_check": self.last_check.isoformat(),
        }


@dataclass
class SystemHealth:
    """
    系统健康度

    表示整个系统的健康状态
    """
    system_id: str = "default"                  # 系统ID
    name: str = "System"                        # 系统名称

    # 组件
    components: dict[str, ComponentHealth] = field(default_factory=dict)

    # 综合状态
    status: HealthStatus = HealthStatus.UNKNOWN
    score: float = 0.0

    # 统计
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    critical_count: int = 0

    # 元数据
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_component(self, component: ComponentHealth) -> None:
        """添加组件"""
        self.components[component.component_id] = component
        self._recalculate()

    def remove_component(self, component_id: str) -> bool:
        """移除组件"""
        if component_id in self.components:
            del self.components[component_id]
            self._recalculate()
            return True
        return False

    def get_component(self, component_id: str) -> ComponentHealth | None:
        """获取组件"""
        return self.components.get(component_id)

    def update_component_metric(
        self,
        component_id: str,
        metric_name: str,
        value: float
    ) -> bool:
        """更新组件指标"""
        component = self.components.get(component_id)
        if component:
            result = component.update_metric(metric_name, value)
            if result:
                self._recalculate()
            return result
        return False

    def _recalculate(self) -> None:
        """重新计算系统健康度"""
        if not self.components:
            self.score = 0
            self.status = HealthStatus.UNKNOWN
            return

        # 统计各状态组件数
        self.healthy_count = 0
        self.degraded_count = 0
        self.unhealthy_count = 0
        self.critical_count = 0

        for component in self.components.values():
            if component.status == HealthStatus.HEALTHY:
                self.healthy_count += 1
            elif component.status == HealthStatus.DEGRADED:
                self.degraded_count += 1
            elif component.status == HealthStatus.UNHEALTHY:
                self.unhealthy_count += 1
            elif component.status == HealthStatus.CRITICAL:
                self.critical_count += 1

        # 计算综合得分（简单平均）
        self.score = sum(c.score for c in self.components.values()) / len(self.components)

        # 确定系统状态
        if self.critical_count > 0:
            self.status = HealthStatus.CRITICAL
        elif self.unhealthy_count > 0:
            self.status = HealthStatus.UNHEALTHY
        elif self.degraded_count > 0:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.HEALTHY

        self.last_updated = datetime.now()

    @property
    def total_components(self) -> int:
        """组件总数"""
        return len(self.components)

    @property
    def is_healthy(self) -> bool:
        """系统是否健康"""
        return self.status == HealthStatus.HEALTHY

    @property
    def critical_components(self) -> list[ComponentHealth]:
        """获取严重问题组件"""
        return [
            c for c in self.components.values()
            if c.status == HealthStatus.CRITICAL
        ]

    @property
    def unhealthy_components(self) -> list[ComponentHealth]:
        """获取不健康组件"""
        return [
            c for c in self.components.values()
            if c.status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL)
        ]

    def get_summary(self) -> dict[str, Any]:
        """获取健康摘要"""
        return {
            "system_id": self.system_id,
            "name": self.name,
            "status": self.status.value,
            "score": round(self.score, 2),
            "is_healthy": self.is_healthy,
            "total_components": self.total_components,
            "by_status": {
                "healthy": self.healthy_count,
                "degraded": self.degraded_count,
                "unhealthy": self.unhealthy_count,
                "critical": self.critical_count,
            },
            "critical_issues": [
                c.name for c in self.critical_components
            ],
            "last_updated": self.last_updated.isoformat(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.get_summary(),
            "components": {
                cid: c.to_dict()
                for cid, c in self.components.items()
            },
        }


@dataclass
class HealthCheckResult:
    """
    健康检查结果

    单次健康检查的结果
    """
    check_id: str                               # 检查ID
    component_id: str                           # 组件ID
    check_type: str = "basic"                   # 检查类型

    # 结果
    success: bool = True                        # 是否成功
    status: HealthStatus = HealthStatus.HEALTHY
    message: str = ""                           # 结果消息
    details: dict[str, Any] = field(default_factory=dict)

    # 性能
    duration_ms: float = 0                      # 检查耗时
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "component_id": self.component_id,
            "check_type": self.check_type,
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class HealthConfig:
    """健康度评分配置"""
    # 阈值
    healthy_threshold: float = 90               # 健康阈值
    degraded_threshold: float = 70              # 降级阈值
    unhealthy_threshold: float = 50             # 不健康阈值

    # 默认权重
    default_metric_weight: float = 1.0

    # 检查配置
    check_interval_seconds: int = 60            # 检查间隔
    check_timeout_ms: int = 5000                # 检查超时

    # 历史保留
    history_retention_hours: int = 24           # 历史数据保留时间

    # 聚合配置
    aggregate_by_type: bool = True              # 按类型聚合
    include_dependencies: bool = True           # 计算时考虑依赖

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy_threshold": self.healthy_threshold,
            "degraded_threshold": self.degraded_threshold,
            "unhealthy_threshold": self.unhealthy_threshold,
            "check_interval_seconds": self.check_interval_seconds,
            "check_timeout_ms": self.check_timeout_ms,
        }


@dataclass
class HealthReport:
    """
    健康报告

    综合健康评估报告
    """
    report_id: str                              # 报告ID
    system_health: SystemHealth                 # 系统健康度
    generated_at: datetime = field(default_factory=datetime.now)

    # 摘要
    overall_score: float = 0.0
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    summary: str = ""

    # 问题和建议
    issues: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # 趋势
    trend: TrendDirection = TrendDirection.UNKNOWN
    score_history: list[tuple[datetime, float]] = field(default_factory=list)

    def add_issue(
        self,
        component: str,
        severity: str,
        description: str,
        suggestion: str = ""
    ) -> None:
        """添加问题"""
        self.issues.append({
            "component": component,
            "severity": severity,
            "description": description,
            "suggestion": suggestion,
        })

    def add_recommendation(self, recommendation: str) -> None:
        """添加建议"""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "overall_score": round(self.overall_score, 2),
            "overall_status": self.overall_status.value,
            "trend": self.trend.value,
            "summary": self.summary,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "system_health": self.system_health.to_dict(),
        }
