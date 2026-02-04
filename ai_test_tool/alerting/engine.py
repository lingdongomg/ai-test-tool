"""
告警过滤引擎

实现告警的去重、聚合、抑制、降噪等核心功能
"""

import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .models import (
    Alert,
    AlertGroup,
    AlertConfig,
    AlertFilterResult,
    AlertSeverity,
    AlertStatus,
)

logger = logging.getLogger(__name__)


class AlertFilterEngine:
    """
    告警过滤引擎

    核心功能：
    1. 去重：基于指纹和相似度去除重复告警
    2. 聚合：将相关告警合并为告警组
    3. 抑制：基于规则抑制低优先级告警
    4. 降噪：识别并过滤噪音告警
    5. 排序：按严重程度和时间排序
    """

    def __init__(self, config: AlertConfig | None = None):
        """
        初始化引擎

        Args:
            config: 告警过滤配置
        """
        self.config = config or AlertConfig()

        # 告警缓存（用于去重）
        self._alert_cache: dict[str, Alert] = {}
        self._cache_expiry: dict[str, datetime] = {}

        # 告警组缓存
        self._group_cache: dict[str, AlertGroup] = {}

        # 噪音检测窗口
        self._noise_window: list[tuple[datetime, str]] = []

    def filter(self, alerts: list[Alert]) -> AlertFilterResult:
        """
        过滤告警

        Args:
            alerts: 原始告警列表

        Returns:
            过滤结果
        """
        start_time = time.time()

        result = AlertFilterResult(total_input=len(alerts))

        if not alerts:
            return result

        # 清理过期缓存
        self._cleanup_cache()

        # 过滤流程
        current_alerts = alerts.copy()

        # 1. 去重
        if self.config.enable_dedupe:
            current_alerts, dedupe_count = self._deduplicate(current_alerts)
            result.dedupe_count = dedupe_count

        # 2. 抑制
        if self.config.enable_suppress:
            current_alerts, suppressed_count = self._suppress(current_alerts)
            result.suppressed_count = suppressed_count

        # 3. 降噪
        if self.config.enable_noise_reduction:
            current_alerts, noise_count = self._reduce_noise(current_alerts)
            result.noise_filtered_count = noise_count

        # 4. 聚合
        if self.config.enable_aggregate:
            groups = self._aggregate(current_alerts)
            result.alert_groups = groups

        # 5. 排序
        current_alerts = self._sort_alerts(current_alerts)

        # 统计严重程度
        severity_counts: dict[str, int] = defaultdict(int)
        for alert in current_alerts:
            severity_counts[alert.severity.value] += 1
        result.severity_counts = dict(severity_counts)

        result.filtered_alerts = current_alerts
        result.total_filtered = result.dedupe_count + result.suppressed_count + result.noise_filtered_count
        result.processing_time_ms = (time.time() - start_time) * 1000

        return result

    def _deduplicate(self, alerts: list[Alert]) -> tuple[list[Alert], int]:
        """
        去重

        基于指纹和相似度去除重复告警

        Args:
            alerts: 告警列表

        Returns:
            (去重后的告警, 去重数量)
        """
        dedupe_count = 0
        unique_alerts: list[Alert] = []
        seen_fingerprints: dict[str, Alert] = {}

        window = timedelta(minutes=self.config.dedupe_window_minutes)
        threshold = self.config.dedupe_similarity_threshold

        for alert in alerts:
            # 检查指纹是否已存在
            if alert.fingerprint in seen_fingerprints:
                existing = seen_fingerprints[alert.fingerprint]
                # 合并计数
                existing.fire_count += alert.fire_count
                existing.last_fired_at = alert.fired_at
                dedupe_count += 1
                continue

            # 检查缓存中的相似告警
            cache_key = self._get_cache_key(alert)
            if cache_key in self._alert_cache:
                cached = self._alert_cache[cache_key]
                expiry = self._cache_expiry.get(cache_key, datetime.min)

                if datetime.now() < expiry and cached.matches(alert, threshold):
                    # 更新缓存中的告警
                    cached.fire_count += alert.fire_count
                    cached.last_fired_at = alert.fired_at
                    dedupe_count += 1
                    continue

            # 检查当前批次中的相似告警
            is_duplicate = False
            for existing in unique_alerts:
                if existing.matches(alert, threshold):
                    existing.fire_count += alert.fire_count
                    existing.last_fired_at = alert.fired_at
                    is_duplicate = True
                    dedupe_count += 1
                    break

            if not is_duplicate:
                unique_alerts.append(alert)
                seen_fingerprints[alert.fingerprint] = alert

                # 更新缓存
                self._alert_cache[cache_key] = alert
                self._cache_expiry[cache_key] = datetime.now() + window

        return unique_alerts, dedupe_count

    def _suppress(self, alerts: list[Alert]) -> tuple[list[Alert], int]:
        """
        抑制

        基于规则抑制告警

        Args:
            alerts: 告警列表

        Returns:
            (抑制后的告警, 抑制数量)
        """
        suppressed_count = 0
        remaining_alerts: list[Alert] = []

        for alert in alerts:
            should_suppress = False

            # 规则1: 抑制低优先级告警
            if self.config.suppress_low_severity:
                if alert.severity in (AlertSeverity.LOW, AlertSeverity.INFO):
                    should_suppress = True

            # 规则2: 抑制已恢复的告警
            if self.config.suppress_resolved:
                if alert.status == AlertStatus.RESOLVED:
                    should_suppress = True

            # 规则3: 抑制已确认的告警
            if alert.status == AlertStatus.ACKNOWLEDGED:
                should_suppress = True

            if should_suppress:
                alert.status = AlertStatus.SUPPRESSED
                suppressed_count += 1
            else:
                remaining_alerts.append(alert)

        return remaining_alerts, suppressed_count

    def _reduce_noise(self, alerts: list[Alert]) -> tuple[list[Alert], int]:
        """
        降噪

        识别并过滤噪音告警

        Args:
            alerts: 告警列表

        Returns:
            (降噪后的告警, 过滤数量)
        """
        noise_count = 0
        clean_alerts: list[Alert] = []

        noise_threshold = self.config.noise_threshold
        noise_window = timedelta(minutes=self.config.noise_window_minutes)
        now = datetime.now()

        # 清理过期的噪音窗口记录
        self._noise_window = [
            (ts, fp) for ts, fp in self._noise_window
            if now - ts < noise_window
        ]

        # 统计每个指纹的出现频率
        fingerprint_counts: dict[str, int] = defaultdict(int)
        for ts, fp in self._noise_window:
            fingerprint_counts[fp] += 1

        for alert in alerts:
            # 更新噪音窗口
            self._noise_window.append((alert.fired_at, alert.fingerprint))
            fingerprint_counts[alert.fingerprint] += 1

            # 检查是否为噪音
            if fingerprint_counts[alert.fingerprint] > noise_threshold:
                # 标记为噪音但保留一条
                if fingerprint_counts[alert.fingerprint] == noise_threshold + 1:
                    alert.metadata["noise_alert"] = True
                    alert.metadata["noise_count"] = fingerprint_counts[alert.fingerprint]
                    clean_alerts.append(alert)
                else:
                    noise_count += 1
            else:
                clean_alerts.append(alert)

        return clean_alerts, noise_count

    def _aggregate(self, alerts: list[Alert]) -> list[AlertGroup]:
        """
        聚合

        将相关告警合并为告警组

        Args:
            alerts: 告警列表

        Returns:
            告警组列表
        """
        groups: dict[str, AlertGroup] = {}

        for alert in alerts:
            # 生成分组键
            group_key = self._get_group_key(alert)

            if group_key not in groups:
                # 检查缓存中是否有现有组
                if group_key in self._group_cache:
                    groups[group_key] = self._group_cache[group_key]
                else:
                    groups[group_key] = AlertGroup(
                        group_id=str(uuid.uuid4())[:8],
                        group_key=group_key
                    )

            groups[group_key].add_alert(alert)

        # 更新缓存
        self._group_cache.update(groups)

        # 按严重程度排序组
        sorted_groups = sorted(
            groups.values(),
            key=lambda g: (
                -g.severity.value if hasattr(g.severity, 'value') else 0,
                -g.active_count,
                g.first_fired_at or datetime.min
            )
        )

        return sorted_groups

    def _sort_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """
        排序告警

        Args:
            alerts: 告警列表

        Returns:
            排序后的告警
        """
        def sort_key(alert: Alert) -> tuple:
            keys = []

            if self.config.sort_by_severity:
                keys.append(-alert.severity_score)

            if self.config.sort_by_time:
                keys.append(alert.fired_at)

            return tuple(keys)

        return sorted(alerts, key=sort_key)

    def _get_cache_key(self, alert: Alert) -> str:
        """获取缓存键"""
        return f"{alert.source}:{alert.service}:{alert.fingerprint}"

    def _get_group_key(self, alert: Alert) -> str:
        """获取分组键"""
        parts = []
        for field in self.config.aggregate_by:
            if field == "service":
                parts.append(alert.service)
            elif field == "severity":
                parts.append(alert.severity.value)
            elif field == "source":
                parts.append(alert.source)
            elif field == "host":
                parts.append(alert.host)
            elif field == "component":
                parts.append(alert.component)
        return ":".join(parts) if parts else "default"

    def _cleanup_cache(self) -> None:
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, expiry in self._cache_expiry.items()
            if now > expiry
        ]
        for key in expired_keys:
            self._alert_cache.pop(key, None)
            self._cache_expiry.pop(key, None)

    def clear_cache(self) -> None:
        """清除所有缓存"""
        self._alert_cache.clear()
        self._cache_expiry.clear()
        self._group_cache.clear()
        self._noise_window.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取引擎统计信息"""
        return {
            "cache_size": len(self._alert_cache),
            "group_count": len(self._group_cache),
            "noise_window_size": len(self._noise_window),
            "config": self.config.to_dict(),
        }
