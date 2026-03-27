# 该文件内容使用AI生成，注意识别准确性
"""
每日摘要服务

每日 09:00 自动生成 WARN 级别日志摘要报告（Markdown 模板，不用 LLM）。
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class DailyDigestScheduler:
    """每日摘要调度器"""

    def __init__(self, digest_hour: int = 9, digest_minute: int = 0):
        self._digest_hour = digest_hour
        self._digest_minute = digest_minute
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._schedule_next()
        logger.info(f"每日摘要调度器已启动 (每天 {self._digest_hour:02d}:{self._digest_minute:02d})")

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self) -> None:
        """计算并设置下次执行时间"""
        if not self._running:
            return

        now = datetime.now()
        target = now.replace(hour=self._digest_hour, minute=self._digest_minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        delay = (target - now).total_seconds()
        self._timer = threading.Timer(delay, self._run_digest)
        self._timer.daemon = True
        self._timer.start()
        logger.debug(f"下次摘要生成时间: {target.isoformat()} ({delay:.0f}s 后)")

    def _run_digest(self) -> None:
        """执行摘要生成"""
        try:
            self.generate_daily_digest()
        except Exception as e:
            logger.error(f"每日摘要生成失败: {e}")
        finally:
            # 调度下一次
            self._schedule_next()

    def generate_daily_digest(self, target_date: str | None = None) -> str | None:
        """
        生成某一天的 WARN 摘要报告

        Args:
            target_date: 目标日期 (YYYY-MM-DD)，默认昨天

        Returns:
            生成的报告内容（Markdown），如果无数据则返回 None
        """
        if not target_date:
            target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        logger.info(f"生成每日摘要: {target_date}")

        try:
            from ..database import get_db_manager
            db = get_db_manager()

            # 查询当天的统计数据
            rows = db.fetch_all(
                "SELECT * FROM log_daily_stats WHERE date = ?",
                (target_date,)
            )

            if not rows:
                logger.info(f"日期 {target_date} 无统计数据，跳过摘要生成")
                return None

            # 汇总统计
            total_error = sum(r.get('error_count', 0) for r in rows)
            total_warn = sum(r.get('warn_count', 0) for r in rows)
            total_critical = sum(r.get('critical_count', 0) for r in rows)
            total_security = sum(r.get('security_count', 0) for r in rows)

            # 查询前一天的数据做趋势对比
            prev_date = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            prev_rows = db.fetch_all(
                "SELECT * FROM log_daily_stats WHERE date = ?",
                (prev_date,)
            )
            prev_warn = sum(r.get('warn_count', 0) for r in prev_rows) if prev_rows else 0
            prev_error = sum(r.get('error_count', 0) for r in prev_rows) if prev_rows else 0

            # 生成 Markdown 报告
            content = self._render_digest(
                date=target_date,
                stats_by_source=rows,
                total_error=total_error,
                total_warn=total_warn,
                total_critical=total_critical,
                total_security=total_security,
                prev_warn=prev_warn,
                prev_error=prev_error,
            )

            # 存入 analysis_reports
            db.execute(
                """INSERT INTO analysis_reports
                   (task_id, report_type, title, content, format, severity, created_at)
                   VALUES (?, 'daily_digest', ?, ?, 'markdown', ?, datetime('now'))""",
                (
                    f"digest_{target_date}",
                    f"每日日志摘要 - {target_date}",
                    content,
                    "high" if total_critical > 0 else "medium" if total_error > 0 else "low",
                )
            )

            logger.info(
                f"每日摘要已生成: {target_date} "
                f"(ERROR: {total_error}, WARN: {total_warn}, CRITICAL: {total_critical})"
            )

            # 发送 webhook（遍历有 webhook_url 的日志源）
            self._send_digest_webhooks(content, target_date)

            return content

        except Exception as e:
            logger.error(f"生成每日摘要失败: {e}")
            return None

    def _render_digest(
        self,
        date: str,
        stats_by_source: list,
        total_error: int,
        total_warn: int,
        total_critical: int,
        total_security: int,
        prev_warn: int,
        prev_error: int,
    ) -> str:
        """使用 Markdown 模板渲染摘要（不调用 LLM）"""
        # 趋势计算
        def trend(current: int, previous: int) -> str:
            if previous == 0:
                return "新增" if current > 0 else "无变化"
            change = ((current - previous) / previous) * 100
            if change > 10:
                return f"↑ {change:.0f}%"
            elif change < -10:
                return f"↓ {abs(change):.0f}%"
            return "→ 持平"

        sections = [
            f"# 每日日志摘要 — {date}\n",
            "## 总览\n",
            f"| 级别 | 数量 | 趋势(vs前日) |",
            f"|------|------|-------------|",
            f"| CRITICAL | {total_critical} | - |",
            f"| ERROR | {total_error} | {trend(total_error, prev_error)} |",
            f"| WARN | {total_warn} | {trend(total_warn, prev_warn)} |",
            f"| SECURITY | {total_security} | - |",
            "",
        ]

        # 按日志源分组
        if len(stats_by_source) > 1:
            sections.append("## 按日志源分布\n")
            sections.append("| 日志源 | ERROR | WARN | CRITICAL |")
            sections.append("|--------|-------|------|----------|")
            for row in stats_by_source:
                sections.append(
                    f"| {row.get('source_id', '?')} "
                    f"| {row.get('error_count', 0)} "
                    f"| {row.get('warn_count', 0)} "
                    f"| {row.get('critical_count', 0)} |"
                )
            sections.append("")

        # 需关注项
        attention_items = []
        if total_critical > 0:
            attention_items.append(f"- **CRITICAL 告警 {total_critical} 条**，请立即排查")
        if total_error > prev_error * 1.5 and prev_error > 0:
            attention_items.append(f"- ERROR 数量较前日增长 {((total_error-prev_error)/prev_error*100):.0f}%，需关注")
        if total_warn > prev_warn * 2 and prev_warn > 0:
            attention_items.append(f"- WARN 数量较前日翻倍增长，可能存在潜在问题")

        if attention_items:
            sections.append("## 需关注项\n")
            sections.extend(attention_items)
            sections.append("")

        return "\n".join(sections)

    def _send_digest_webhooks(self, content: str, date: str) -> None:
        """向配置了 webhook 的日志源发送摘要"""
        try:
            from ..database.repositories.log_source import LogSourceRepository
            from .notification import NotificationService

            repo = LogSourceRepository()
            sources = repo.list_all()
            notifier = NotificationService()

            for source in sources:
                webhook_url = getattr(source, 'webhook_url', None)
                if webhook_url and getattr(source, 'alert_enabled', True):
                    notifier.send_webhook(
                        url=webhook_url,
                        payload={
                            "event_type": "daily_digest",
                            "date": date,
                            "title": f"每日日志摘要 - {date}",
                            "summary": content[:500],
                        },
                    )
        except Exception as e:
            logger.debug(f"摘要 webhook 发送失败: {e}")
