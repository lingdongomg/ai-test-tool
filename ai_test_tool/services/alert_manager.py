# 该文件内容使用AI生成，注意识别准确性
"""
告警管理器

- 告警去重（内存滑动窗口 5 分钟）
- ERROR 聚合窗口（2 分钟）
- 告警写入 DB
- 聚合窗口结束后自动根因报告
- 告警频率限制（每小时最多 20 条）
"""

import hashlib
import json
import logging
import time
import threading
import uuid
from typing import Any
from collections import defaultdict

from .rule_detector import DetectionResult

logger = logging.getLogger(__name__)

# 去重窗口（秒）
DEDUP_WINDOW = 300  # 5 分钟
# 聚合窗口（秒）
AGGREGATE_WINDOW = 120  # 2 分钟
# 每小时最大告警数
MAX_ALERTS_PER_HOUR = 20


class AlertManager:
    """告警管理器"""

    def __init__(self):
        # 去重窗口：{source_id:pattern_name -> (last_alert_time, hit_count)}
        self._dedup_cache: dict[str, tuple[float, int]] = {}
        # 聚合窗口：{source_id -> [DetectionResult, ...]}
        self._aggregate_buffers: dict[str, list[DetectionResult]] = defaultdict(list)
        self._aggregate_timers: dict[str, threading.Timer] = {}
        # 频率限制：{source_id -> [alert_timestamp, ...]}
        self._rate_limit: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def on_error_detected(self, source_id: str, detection: DetectionResult) -> None:
        """
        ERROR 检测到时调用

        1. 去重检查
        2. 频率限制
        3. 写入 DB
        4. 加入聚合窗口
        5. 触发 webhook（如果配置）
        """
        with self._lock:
            # 去重检查
            dedup_key = f"{source_id}:{detection.pattern_name}"
            now = time.time()

            if dedup_key in self._dedup_cache:
                last_time, hit_count = self._dedup_cache[dedup_key]
                if now - last_time < DEDUP_WINDOW:
                    # 去重窗口内，只增加计数
                    self._dedup_cache[dedup_key] = (last_time, hit_count + 1)
                    logger.debug(f"告警去重: {dedup_key} (已命中 {hit_count + 1} 次)")
                    return

            # 频率限制
            self._rate_limit[source_id] = [
                t for t in self._rate_limit[source_id] if now - t < 3600
            ]
            if len(self._rate_limit[source_id]) >= MAX_ALERTS_PER_HOUR:
                logger.warning(f"告警频率限制: {source_id} 已达每小时上限 {MAX_ALERTS_PER_HOUR}")
                return

            # 更新去重缓存
            self._dedup_cache[dedup_key] = (now, 1)
            self._rate_limit[source_id].append(now)

        # 写入 DB
        alert_id = self._save_alert(source_id, detection)

        # 加入聚合窗口
        self._add_to_aggregate(source_id, detection)

        # 触发 webhook（异步）
        self._try_send_webhook(source_id, detection, alert_id)

        logger.info(
            f"告警生成: [{detection.severity}] {source_id} - "
            f"{detection.pattern_name}: {detection.line[:100]}"
        )

    def _save_alert(self, source_id: str, detection: DetectionResult) -> str:
        """保存告警到数据库"""
        alert_id = str(uuid.uuid4())[:12]
        try:
            from ..database import get_db_manager
            db = get_db_manager()
            diagnosis_json = json.dumps(detection.diagnosis, ensure_ascii=False) if detection.diagnosis else None

            db.execute(
                """INSERT INTO log_alerts
                   (alert_id, source_id, severity, pattern_name, log_line, diagnosis, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                (alert_id, source_id, detection.severity, detection.pattern_name,
                 detection.line[:2000], diagnosis_json)
            )
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
        return alert_id

    def _add_to_aggregate(self, source_id: str, detection: DetectionResult) -> None:
        """加入聚合窗口"""
        self._aggregate_buffers[source_id].append(detection)

        # 如果还没有定时器，启动一个
        if source_id not in self._aggregate_timers:
            timer = threading.Timer(AGGREGATE_WINDOW, self._flush_aggregate, args=[source_id])
            timer.daemon = True
            timer.start()
            self._aggregate_timers[source_id] = timer

    def _flush_aggregate(self, source_id: str) -> None:
        """聚合窗口结束，生成根因报告"""
        detections = self._aggregate_buffers.pop(source_id, [])
        self._aggregate_timers.pop(source_id, None)

        if not detections:
            return

        logger.info(f"聚合窗口结束: {source_id}, {len(detections)} 条 ERROR，生成根因报告")

        try:
            from ..skills.analysis_skills import diagnose_with_knowledge, generate_report_from_template

            error_messages = [d.line[:200] for d in detections]
            urls = []  # 实时日志中可能没有 URL 信息

            diagnosis = diagnose_with_knowledge(
                error_messages=error_messages,
                urls=urls,
                use_llm_fallback=True,
            )

            anomalies = [
                {
                    "type": d.pattern_name,
                    "severity": d.severity,
                    "title": f"{d.pattern_name}: {d.matched_text}",
                    "description": d.line[:300],
                }
                for d in detections
            ]

            report = generate_report_from_template(
                title=f"实时告警根因报告 - {source_id}",
                anomalies=anomalies,
                diagnosis=diagnosis,
            )

            # 存入 analysis_reports
            self._save_report(source_id, report.get("content", ""), len(detections))

        except Exception as e:
            logger.error(f"生成聚合报告失败: {e}")

    def _save_report(self, source_id: str, content: str, anomaly_count: int) -> None:
        """保存根因报告到数据库"""
        try:
            from ..database import get_db_manager
            db = get_db_manager()
            report_id = str(uuid.uuid4())[:12]

            db.execute(
                """INSERT INTO analysis_reports
                   (task_id, report_type, title, content, format, severity, created_at)
                   VALUES (?, 'anomaly', ?, ?, 'markdown', 'high', datetime('now'))""",
                (source_id, f"实时告警报告 ({anomaly_count} 条错误)", content)
            )
            logger.info(f"根因报告已保存: {source_id}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")

    def _try_send_webhook(self, source_id: str, detection: DetectionResult, alert_id: str) -> None:
        """尝试通过 webhook 发送告警"""
        try:
            from ..database.repositories.log_source import LogSourceRepository
            repo = LogSourceRepository()
            source = repo.get_by_id(source_id)

            if not source:
                return

            webhook_url = getattr(source, 'webhook_url', None)
            alert_enabled = getattr(source, 'alert_enabled', True)

            if not webhook_url or not alert_enabled:
                return

            from .notification import NotificationService
            notifier = NotificationService()
            notifier.send_webhook(
                url=webhook_url,
                payload={
                    "event_type": "alert",
                    "alert_id": alert_id,
                    "severity": detection.severity,
                    "title": f"[{detection.severity.upper()}] {detection.pattern_name}",
                    "summary": detection.line[:300],
                    "diagnosis": detection.diagnosis,
                    "source_id": source_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        except Exception as e:
            logger.debug(f"Webhook 发送失败（不影响告警）: {e}")

    def get_recent_alerts(self, source_id: str = "", hours: int = 24, limit: int = 50) -> list[dict]:
        """查询最近告警"""
        try:
            from ..database import get_db_manager
            db = get_db_manager()

            if source_id:
                rows = db.fetch_all(
                    "SELECT * FROM log_alerts WHERE source_id = ? "
                    "AND created_at >= datetime('now', ?) ORDER BY created_at DESC LIMIT ?",
                    (source_id, f"-{hours} hours", limit)
                )
            else:
                rows = db.fetch_all(
                    "SELECT * FROM log_alerts "
                    "WHERE created_at >= datetime('now', ?) ORDER BY created_at DESC LIMIT ?",
                    (f"-{hours} hours", limit)
                )
            return [dict(r) for r in rows] if rows else []
        except Exception as e:
            logger.error(f"查询告警失败: {e}")
            return []

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        try:
            from ..database import get_db_manager
            db = get_db_manager()
            db.execute(
                "UPDATE log_alerts SET is_acknowledged = 1, acknowledged_at = datetime('now') WHERE alert_id = ?",
                (alert_id,)
            )
            return True
        except Exception as e:
            logger.error(f"确认告警失败: {e}")
            return False
