"""
告警过滤器

提供高级告警过滤功能，支持多种过滤策略
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from .models import (
    Alert,
    AlertGroup,
    AlertConfig,
    AlertFilterResult,
    AlertSeverity,
    AlertStatus,
    SuppressRule,
    AggregateRule,
    DedupeRule,
)
from .engine import AlertFilterEngine

logger = logging.getLogger(__name__)


class AlertFilter:
    """
    告警过滤器

    提供便捷的告警过滤接口，支持：
    1. 基础过滤（去重、聚合、抑制）
    2. 自定义规则过滤
    3. 时间范围过滤
    4. 严重程度过滤
    5. 标签匹配过滤
    """

    def __init__(self, config: AlertConfig | None = None):
        """
        初始化过滤器

        Args:
            config: 告警配置
        """
        self.config = config or AlertConfig()
        self.engine = AlertFilterEngine(config=self.config)

        # 自定义过滤器
        self._custom_filters: list[Callable[[Alert], bool]] = []

        # 规则
        self._suppress_rules: list[SuppressRule] = []
        self._aggregate_rules: list[AggregateRule] = []
        self._dedupe_rules: list[DedupeRule] = []

    def filter(
        self,
        alerts: list[Alert],
        severity_filter: list[AlertSeverity] | None = None,
        time_range: tuple[datetime, datetime] | None = None,
        label_matchers: dict[str, str] | None = None,
        source_filter: list[str] | None = None,
        service_filter: list[str] | None = None,
    ) -> AlertFilterResult:
        """
        过滤告警

        Args:
            alerts: 原始告警列表
            severity_filter: 严重程度过滤（只保留指定级别）
            time_range: 时间范围过滤 (start, end)
            label_matchers: 标签匹配过滤
            source_filter: 来源过滤
            service_filter: 服务过滤

        Returns:
            过滤结果
        """
        # 预过滤
        filtered = self._pre_filter(
            alerts,
            severity_filter=severity_filter,
            time_range=time_range,
            label_matchers=label_matchers,
            source_filter=source_filter,
            service_filter=service_filter,
        )

        # 应用自定义规则
        filtered = self._apply_custom_rules(filtered)

        # 使用引擎进行核心过滤
        result = self.engine.filter(filtered)

        return result

    def _pre_filter(
        self,
        alerts: list[Alert],
        severity_filter: list[AlertSeverity] | None = None,
        time_range: tuple[datetime, datetime] | None = None,
        label_matchers: dict[str, str] | None = None,
        source_filter: list[str] | None = None,
        service_filter: list[str] | None = None,
    ) -> list[Alert]:
        """预过滤"""
        result = alerts

        # 严重程度过滤
        if severity_filter:
            result = [a for a in result if a.severity in severity_filter]

        # 时间范围过滤
        if time_range:
            start, end = time_range
            result = [a for a in result if start <= a.fired_at <= end]

        # 标签匹配
        if label_matchers:
            result = [
                a for a in result
                if all(a.labels.get(k) == v for k, v in label_matchers.items())
            ]

        # 来源过滤
        if source_filter:
            result = [a for a in result if a.source in source_filter]

        # 服务过滤
        if service_filter:
            result = [a for a in result if a.service in service_filter]

        # 自定义过滤器
        for custom_filter in self._custom_filters:
            result = [a for a in result if custom_filter(a)]

        return result

    def _apply_custom_rules(self, alerts: list[Alert]) -> list[Alert]:
        """应用自定义规则"""
        result = alerts

        # 应用抑制规则
        for rule in sorted(self._suppress_rules, key=lambda r: -r.priority):
            if rule.enabled:
                result = [
                    a for a in result
                    if rule.apply(a) is not None
                ]

        # 应用聚合规则
        for rule in sorted(self._aggregate_rules, key=lambda r: -r.priority):
            if rule.enabled:
                for alert in result:
                    rule.apply(alert)

        # 应用去重规则
        for rule in sorted(self._dedupe_rules, key=lambda r: -r.priority):
            if rule.enabled:
                for alert in result:
                    rule.apply(alert)

        return result

    def add_filter(self, filter_func: Callable[[Alert], bool]) -> None:
        """
        添加自定义过滤器

        Args:
            filter_func: 过滤函数，返回True保留，False过滤
        """
        self._custom_filters.append(filter_func)

    def add_suppress_rule(self, rule: SuppressRule) -> None:
        """添加抑制规则"""
        self._suppress_rules.append(rule)

    def add_aggregate_rule(self, rule: AggregateRule) -> None:
        """添加聚合规则"""
        self._aggregate_rules.append(rule)

    def add_dedupe_rule(self, rule: DedupeRule) -> None:
        """添加去重规则"""
        self._dedupe_rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """
        移除规则

        Args:
            rule_id: 规则ID

        Returns:
            是否成功移除
        """
        for rule_list in [self._suppress_rules, self._aggregate_rules, self._dedupe_rules]:
            for i, rule in enumerate(rule_list):
                if rule.rule_id == rule_id:
                    rule_list.pop(i)
                    return True
        return False

    def clear_rules(self) -> None:
        """清除所有规则"""
        self._suppress_rules.clear()
        self._aggregate_rules.clear()
        self._dedupe_rules.clear()
        self._custom_filters.clear()

    # 便捷方法

    def filter_by_severity(
        self,
        alerts: list[Alert],
        min_severity: AlertSeverity = AlertSeverity.WARNING
    ) -> list[Alert]:
        """
        按严重程度过滤

        Args:
            alerts: 告警列表
            min_severity: 最低严重程度

        Returns:
            过滤后的告警
        """
        severity_order = {
            AlertSeverity.CRITICAL: 5,
            AlertSeverity.HIGH: 4,
            AlertSeverity.WARNING: 3,
            AlertSeverity.LOW: 2,
            AlertSeverity.INFO: 1,
        }
        min_level = severity_order.get(min_severity, 0)
        return [
            a for a in alerts
            if severity_order.get(a.severity, 0) >= min_level
        ]

    def filter_active(self, alerts: list[Alert]) -> list[Alert]:
        """只保留活跃告警"""
        return [a for a in alerts if a.is_active]

    def filter_by_time(
        self,
        alerts: list[Alert],
        hours: int = 24
    ) -> list[Alert]:
        """
        过滤最近N小时的告警

        Args:
            alerts: 告警列表
            hours: 小时数

        Returns:
            过滤后的告警
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in alerts if a.fired_at >= cutoff]

    def filter_by_service(
        self,
        alerts: list[Alert],
        services: list[str]
    ) -> list[Alert]:
        """按服务过滤"""
        return [a for a in alerts if a.service in services]

    def filter_by_labels(
        self,
        alerts: list[Alert],
        labels: dict[str, str],
        match_all: bool = True
    ) -> list[Alert]:
        """
        按标签过滤

        Args:
            alerts: 告警列表
            labels: 标签字典
            match_all: 是否需要匹配所有标签

        Returns:
            过滤后的告警
        """
        result = []
        for alert in alerts:
            if match_all:
                if all(alert.labels.get(k) == v for k, v in labels.items()):
                    result.append(alert)
            else:
                if any(alert.labels.get(k) == v for k, v in labels.items()):
                    result.append(alert)
        return result

    def group_by_service(self, alerts: list[Alert]) -> dict[str, list[Alert]]:
        """按服务分组"""
        groups: dict[str, list[Alert]] = {}
        for alert in alerts:
            service = alert.service or "unknown"
            if service not in groups:
                groups[service] = []
            groups[service].append(alert)
        return groups

    def group_by_severity(self, alerts: list[Alert]) -> dict[str, list[Alert]]:
        """按严重程度分组"""
        groups: dict[str, list[Alert]] = {}
        for alert in alerts:
            severity = alert.severity.value
            if severity not in groups:
                groups[severity] = []
            groups[severity].append(alert)
        return groups

    def get_summary(self, alerts: list[Alert]) -> dict[str, Any]:
        """
        获取告警摘要

        Args:
            alerts: 告警列表

        Returns:
            摘要信息
        """
        if not alerts:
            return {
                "total": 0,
                "by_severity": {},
                "by_status": {},
                "by_service": {},
                "active_count": 0,
            }

        by_severity: dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_service: dict[str, int] = {}
        active_count = 0

        for alert in alerts:
            # 严重程度统计
            sev = alert.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1

            # 状态统计
            status = alert.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # 服务统计
            service = alert.service or "unknown"
            by_service[service] = by_service.get(service, 0) + 1

            # 活跃计数
            if alert.is_active:
                active_count += 1

        return {
            "total": len(alerts),
            "by_severity": by_severity,
            "by_status": by_status,
            "by_service": by_service,
            "active_count": active_count,
            "critical_count": by_severity.get("critical", 0),
            "high_count": by_severity.get("high", 0),
        }


def create_alert_filter(
    enable_dedupe: bool = True,
    enable_aggregate: bool = True,
    enable_suppress: bool = True,
    enable_noise_reduction: bool = True,
    **config_kwargs
) -> AlertFilter:
    """
    创建告警过滤器的便捷函数

    Args:
        enable_dedupe: 启用去重
        enable_aggregate: 启用聚合
        enable_suppress: 启用抑制
        enable_noise_reduction: 启用降噪
        **config_kwargs: 其他配置参数

    Returns:
        AlertFilter实例
    """
    config = AlertConfig(
        enable_dedupe=enable_dedupe,
        enable_aggregate=enable_aggregate,
        enable_suppress=enable_suppress,
        enable_noise_reduction=enable_noise_reduction,
        **config_kwargs
    )
    return AlertFilter(config=config)
