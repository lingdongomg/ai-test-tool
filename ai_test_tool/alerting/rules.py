"""
告警规则引擎

管理和执行告警处理规则
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from .models import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    SuppressRule,
    AggregateRule,
    DedupeRule,
)

logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """
    告警规则引擎

    管理和执行各类告警规则：
    1. 抑制规则：基于条件抑制告警
    2. 聚合规则：将相关告警分组
    3. 去重规则：识别和合并重复告警
    4. 转换规则：修改告警属性
    5. 路由规则：决定告警发送目标
    """

    def __init__(self):
        """初始化规则引擎"""
        self._rules: dict[str, AlertRule] = {}
        self._rule_order: list[str] = []

        # 规则执行统计
        self._stats: dict[str, dict[str, int]] = {}

    def add_rule(self, rule: AlertRule) -> None:
        """
        添加规则

        Args:
            rule: 告警规则
        """
        self._rules[rule.rule_id] = rule
        if rule.rule_id not in self._rule_order:
            self._rule_order.append(rule.rule_id)
            # 按优先级重排序
            self._rule_order.sort(
                key=lambda rid: -self._rules[rid].priority
            )
        self._stats[rule.rule_id] = {"matched": 0, "applied": 0}

    def remove_rule(self, rule_id: str) -> bool:
        """
        移除规则

        Args:
            rule_id: 规则ID

        Returns:
            是否成功移除
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._rule_order.remove(rule_id)
            self._stats.pop(rule_id, None)
            return True
        return False

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """获取规则"""
        return self._rules.get(rule_id)

    def list_rules(self) -> list[AlertRule]:
        """列出所有规则"""
        return [self._rules[rid] for rid in self._rule_order]

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def process(self, alert: Alert) -> Alert | None:
        """
        处理单条告警

        Args:
            alert: 告警

        Returns:
            处理后的告警，None表示被过滤
        """
        current_alert: Alert | None = alert

        for rule_id in self._rule_order:
            if current_alert is None:
                break

            rule = self._rules[rule_id]
            if not rule.enabled:
                continue

            if rule.match(current_alert):
                self._stats[rule_id]["matched"] += 1
                result = rule.apply(current_alert)
                self._stats[rule_id]["applied"] += 1
                current_alert = result

        return current_alert

    def process_batch(self, alerts: list[Alert]) -> list[Alert]:
        """
        批量处理告警

        Args:
            alerts: 告警列表

        Returns:
            处理后的告警列表
        """
        result = []
        for alert in alerts:
            processed = self.process(alert)
            if processed is not None:
                result.append(processed)
        return result

    def get_stats(self) -> dict[str, Any]:
        """获取规则执行统计"""
        return {
            "rule_count": len(self._rules),
            "enabled_count": sum(1 for r in self._rules.values() if r.enabled),
            "rule_stats": self._stats.copy(),
        }

    def clear_stats(self) -> None:
        """清除统计"""
        for rule_id in self._stats:
            self._stats[rule_id] = {"matched": 0, "applied": 0}

    # 便捷方法：创建常用规则

    def add_suppress_by_label(
        self,
        rule_id: str,
        name: str,
        labels: dict[str, str],
        priority: int = 0
    ) -> SuppressRule:
        """
        添加基于标签的抑制规则

        Args:
            rule_id: 规则ID
            name: 规则名称
            labels: 匹配标签
            priority: 优先级

        Returns:
            创建的规则
        """
        rule = SuppressRule(
            rule_id=rule_id,
            name=name,
            matchers=labels,
            priority=priority
        )
        self.add_rule(rule)
        return rule

    def add_suppress_by_condition(
        self,
        rule_id: str,
        name: str,
        condition: Callable[[Alert], bool],
        priority: int = 0
    ) -> SuppressRule:
        """
        添加基于条件的抑制规则

        Args:
            rule_id: 规则ID
            name: 规则名称
            condition: 匹配条件
            priority: 优先级

        Returns:
            创建的规则
        """
        rule = SuppressRule(
            rule_id=rule_id,
            name=name,
            condition=condition,
            priority=priority
        )
        self.add_rule(rule)
        return rule

    def add_aggregate_by_fields(
        self,
        rule_id: str,
        name: str,
        group_by: list[str],
        time_window_minutes: int = 5,
        priority: int = 0
    ) -> AggregateRule:
        """
        添加基于字段的聚合规则

        Args:
            rule_id: 规则ID
            name: 规则名称
            group_by: 分组字段
            time_window_minutes: 时间窗口
            priority: 优先级

        Returns:
            创建的规则
        """
        rule = AggregateRule(
            rule_id=rule_id,
            name=name,
            group_by=group_by,
            time_window=timedelta(minutes=time_window_minutes),
            priority=priority
        )
        self.add_rule(rule)
        return rule

    def add_dedupe_by_fields(
        self,
        rule_id: str,
        name: str,
        dedupe_by: list[str],
        time_window_minutes: int = 10,
        priority: int = 0
    ) -> DedupeRule:
        """
        添加基于字段的去重规则

        Args:
            rule_id: 规则ID
            name: 规则名称
            dedupe_by: 去重字段
            time_window_minutes: 时间窗口
            priority: 优先级

        Returns:
            创建的规则
        """
        rule = DedupeRule(
            rule_id=rule_id,
            name=name,
            dedupe_by=dedupe_by,
            time_window=timedelta(minutes=time_window_minutes),
            priority=priority
        )
        self.add_rule(rule)
        return rule


# 预定义规则模板

class MaintenanceWindowRule(SuppressRule):
    """
    维护窗口规则

    在维护时间段内抑制指定主机/服务的告警
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        hosts: list[str] | None = None,
        services: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            description="维护窗口期间抑制告警"
        )
        self.hosts = hosts or []
        self.services = services or []
        self.start_time = start_time
        self.end_time = end_time

    def match(self, alert: Alert) -> bool:
        if not self.enabled:
            return False

        # 检查时间窗口
        now = datetime.now()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False

        # 检查主机
        if self.hosts and alert.host not in self.hosts:
            return False

        # 检查服务
        if self.services and alert.service not in self.services:
            return False

        return True


class SeverityEscalationRule(AlertRule):
    """
    严重程度升级规则

    当告警频繁触发时自动升级严重程度
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        threshold: int = 5,
        time_window_minutes: int = 10,
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            description="频繁触发时升级严重程度"
        )
        self.threshold = threshold
        self.time_window = timedelta(minutes=time_window_minutes)
        self._trigger_history: dict[str, list[datetime]] = {}

    def match(self, alert: Alert) -> bool:
        if not self.enabled:
            return False

        # 检查触发历史
        fingerprint = alert.fingerprint
        now = datetime.now()

        # 清理过期记录
        if fingerprint in self._trigger_history:
            self._trigger_history[fingerprint] = [
                t for t in self._trigger_history[fingerprint]
                if now - t < self.time_window
            ]
        else:
            self._trigger_history[fingerprint] = []

        # 记录本次触发
        self._trigger_history[fingerprint].append(now)

        # 检查是否达到阈值
        return len(self._trigger_history[fingerprint]) >= self.threshold

    def apply(self, alert: Alert) -> Alert:
        # 升级严重程度
        severity_order = [
            AlertSeverity.INFO,
            AlertSeverity.LOW,
            AlertSeverity.WARNING,
            AlertSeverity.HIGH,
            AlertSeverity.CRITICAL,
        ]

        current_index = severity_order.index(alert.severity)
        if current_index < len(severity_order) - 1:
            alert.severity = severity_order[current_index + 1]
            alert.metadata["escalated"] = True
            alert.metadata["escalation_reason"] = f"触发次数达到{self.threshold}次"

        return alert


class LabelRoutingRule(AlertRule):
    """
    标签路由规则

    根据标签设置告警的路由目标
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        label_routes: dict[str, str],  # label_value -> route_target
        label_key: str = "team",
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            description="基于标签路由告警"
        )
        self.label_routes = label_routes
        self.label_key = label_key

    def match(self, alert: Alert) -> bool:
        if not self.enabled:
            return False
        return self.label_key in alert.labels

    def apply(self, alert: Alert) -> Alert:
        label_value = alert.labels.get(self.label_key, "")
        if label_value in self.label_routes:
            alert.metadata["route_target"] = self.label_routes[label_value]
        return alert


class BusinessHoursRule(SuppressRule):
    """
    工作时间规则

    在非工作时间抑制低优先级告警
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        work_start_hour: int = 9,
        work_end_hour: int = 18,
        work_days: list[int] | None = None,  # 0=Monday, 6=Sunday
        suppress_severities: list[AlertSeverity] | None = None,
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            description="非工作时间抑制低优先级告警"
        )
        self.work_start_hour = work_start_hour
        self.work_end_hour = work_end_hour
        self.work_days = work_days or [0, 1, 2, 3, 4]  # Mon-Fri
        self.suppress_severities = suppress_severities or [
            AlertSeverity.LOW,
            AlertSeverity.INFO
        ]

    def match(self, alert: Alert) -> bool:
        if not self.enabled:
            return False

        # 检查告警严重程度
        if alert.severity not in self.suppress_severities:
            return False

        # 检查是否为非工作时间
        now = datetime.now()

        # 检查星期
        if now.weekday() not in self.work_days:
            return True

        # 检查小时
        if now.hour < self.work_start_hour or now.hour >= self.work_end_hour:
            return True

        return False


def create_rule_engine() -> AlertRuleEngine:
    """
    创建规则引擎并加载默认规则

    Returns:
        AlertRuleEngine实例
    """
    engine = AlertRuleEngine()

    # 添加默认规则
    engine.add_dedupe_by_fields(
        rule_id="default_dedupe",
        name="默认去重规则",
        dedupe_by=["fingerprint"],
        time_window_minutes=10,
        priority=100
    )

    engine.add_aggregate_by_fields(
        rule_id="default_aggregate",
        name="默认聚合规则",
        group_by=["service", "severity"],
        time_window_minutes=5,
        priority=90
    )

    return engine
