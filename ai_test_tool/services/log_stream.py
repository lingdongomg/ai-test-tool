"""
实时日志流服务
管理 WebSocket 连接、日志缓冲和自动触发分析
"""

import asyncio
import logging
import time
import uuid
from typing import Any
from dataclasses import dataclass, field

from ..database.repositories.log_source import LogSourceRepository
from ..knowledge.learner import KnowledgeLearner
from ..parser.log_parser import LogParser
from .rule_detector import RuleDetector, DetectionResult

logger = logging.getLogger(__name__)

# 最大并发连接数
MAX_CONNECTIONS = 10
# 缓冲区最大行数硬限制（防止 OOM）
MAX_BUFFER_HARD_LIMIT = 1000


@dataclass
class LogBuffer:
    """日志缓冲区"""
    source_id: str
    lines: list[str] = field(default_factory=list)
    last_flush_time: float = field(default_factory=time.time)
    buffer_size_threshold: int = 100
    timeout_sec: int = 30

    @property
    def should_flush(self) -> bool:
        """是否应该刷新缓冲区"""
        if len(self.lines) >= self.buffer_size_threshold:
            return True
        if len(self.lines) > 0 and (time.time() - self.last_flush_time) >= self.timeout_sec:
            return True
        if len(self.lines) >= MAX_BUFFER_HARD_LIMIT:
            return True
        return False

    def add_line(self, line: str) -> None:
        self.lines.append(line)

    def add_lines(self, lines: list[str]) -> None:
        self.lines.extend(lines)

    def flush(self) -> list[str]:
        """刷新缓冲区并返回数据"""
        data = self.lines[:]
        self.lines.clear()
        self.last_flush_time = time.time()
        return data


class LogStreamService:
    """
    实时日志流服务

    管理 WebSocket 连接、日志缓冲区和自动触发分析
    """

    def __init__(self) -> None:
        self._source_repo = LogSourceRepository()
        self._buffers: dict[str, LogBuffer] = {}
        self._active_connections: dict[str, Any] = {}  # source_id -> websocket
        self._processing_lock = asyncio.Lock()
        self._rule_detector = RuleDetector()
        self._alert_manager = None  # 延迟初始化

    @property
    def active_connection_count(self) -> int:
        return len(self._active_connections)

    def can_accept_connection(self) -> bool:
        return self.active_connection_count < MAX_CONNECTIONS

    def register_connection(self, source_id: str, websocket: Any) -> None:
        """注册新的 WebSocket 连接"""
        source = self._source_repo.get_by_id(source_id)
        if not source:
            raise ValueError(f"日志源不存在: {source_id}")
        if not source.is_enabled:
            raise ValueError(f"日志源未启用: {source_id}")

        self._active_connections[source_id] = websocket
        self._buffers[source_id] = LogBuffer(
            source_id=source_id,
            buffer_size_threshold=source.buffer_size,
            timeout_sec=source.buffer_timeout_sec,
        )
        self._source_repo.set_status(source_id, "connected")
        logger.info(f"日志源已连接: {source_id} ({source.name})")

    def unregister_connection(self, source_id: str) -> None:
        """注销 WebSocket 连接"""
        self._active_connections.pop(source_id, None)
        # 刷新剩余缓冲
        buffer = self._buffers.pop(source_id, None)
        if buffer and buffer.lines:
            logger.info(f"日志源断开，丢弃 {len(buffer.lines)} 行未处理缓冲数据: {source_id}")
        self._source_repo.set_status(source_id, "disconnected")
        logger.info(f"日志源已断开: {source_id}")

    async def on_message(self, source_id: str, message: dict) -> dict | None:
        """
        处理收到的消息

        Returns:
            需要发送给客户端的响应消息（可为 None）
        """
        msg_type = message.get("type", "")

        if msg_type == "ping":
            return {"type": "pong"}

        if msg_type == "log":
            line = message.get("line", "")
            if line:
                return await self._add_lines(source_id, [line])

        elif msg_type == "batch":
            lines = message.get("lines", [])
            if lines:
                return await self._add_lines(source_id, lines)

        return None

    async def _add_lines(self, source_id: str, lines: list[str]) -> dict | None:
        """添加日志行到缓冲区，先执行规则检测再入缓冲区"""
        buffer = self._buffers.get(source_id)
        if not buffer:
            return {"type": "error", "message": "缓冲区不存在"}

        # 逐行规则检测（微秒级，不阻塞）
        alert_events = []
        for line in lines:
            result = self._rule_detector.check(line)
            if result and self._rule_detector.is_error_or_critical(result):
                alert_events.append(result)
            # WARN 暂只记日志，Phase 7 会接入 daily_stats
            elif result and self._rule_detector.is_warning(result):
                logger.debug(f"WARN 检测: [{source_id}] {result.pattern_name}: {line[:100]}")

        # 触发告警（如果有 AlertManager）
        if alert_events:
            try:
                if self._alert_manager is None:
                    from .alert_manager import AlertManager
                    self._alert_manager = AlertManager()
                for event in alert_events:
                    self._alert_manager.on_error_detected(source_id, event)
            except Exception as e:
                logger.warning(f"告警处理失败: {e}")

        # 日志行照常入缓冲区
        buffer.add_lines(lines)
        self._source_repo.update_stats(source_id, lines_added=len(lines))

        response = None
        if buffer.should_flush:
            response = await self._flush_and_analyze(source_id, buffer)

        # 如果有告警，附加告警信息到响应
        if alert_events and not response:
            response = {
                "type": "alerts_detected",
                "count": len(alert_events),
                "severities": [e.severity for e in alert_events],
            }

        return response

    async def _flush_and_analyze(self, source_id: str, buffer: LogBuffer) -> dict | None:
        """刷新缓冲区并在后台触发分析"""
        data = buffer.flush()
        if not data:
            return None

        task_id = str(uuid.uuid4())[:8]
        self._source_repo.update_stats(source_id, analyses_added=1)

        # 在后台线程执行分析
        asyncio.get_event_loop().run_in_executor(
            None,
            self._analyze_and_learn,
            source_id,
            data,
            task_id,
        )

        return {
            "type": "analysis_triggered",
            "buffer_size": len(data),
            "task_id": task_id,
        }

    def _analyze_and_learn(self, source_id: str, lines: list[str], task_id: str) -> None:
        """同步执行分析和知识提取（在线程池中运行）"""
        try:
            # 使用 LogParser 解析
            parser = LogParser(verbose=False)
            all_requests: list[dict] = []

            for batch in parser._process_batch(lines):
                if isinstance(batch, list):
                    all_requests.extend([r.to_dict() for r in batch])

            if not all_requests:
                logger.info(f"日志源 {source_id} 分析无请求数据，跳过知识学习")
                return

            # 触发知识学习
            source = self._source_repo.get_by_id(source_id)
            if not source or not source.auto_learn:
                return

            from ..api.dependencies import get_knowledge_learner
            learner = get_knowledge_learner()
            suggestions = learner.extract_from_log_analysis(all_requests, f"realtime:{source_id}:{task_id}")

            created_count = 0
            for s in suggestions:
                if s.confidence < 0.5:
                    continue
                item = learner.store.create_from_suggestion(s, "realtime_log")
                created_count += 1
                if s.confidence >= source.auto_approve_threshold:
                    learner.store.approve([item.knowledge_id])

            if created_count > 0:
                logger.info(f"实时日志源 {source_id} 知识学习完成，创建 {created_count} 条知识")

        except Exception as e:
            logger.error(f"实时日志分析失败 (source={source_id}): {e}")

    def get_source_stats(self, source_id: str) -> dict[str, Any]:
        """获取日志源详细统计"""
        source = self._source_repo.get_by_id(source_id)
        if not source:
            raise ValueError(f"日志源不存在: {source_id}")

        buffer = self._buffers.get(source_id)
        buffer_current = len(buffer.lines) if buffer else 0

        is_connected = source_id in self._active_connections
        uptime = 0
        if is_connected and source.last_active_at:
            uptime = int(time.time() - source.last_active_at.timestamp()) if hasattr(source.last_active_at, 'timestamp') else 0

        return {
            "source_id": source.source_id,
            "name": source.name,
            "status": "connected" if is_connected else "disconnected",
            "total_lines_received": source.total_lines_received,
            "total_analyses_triggered": source.total_analyses_triggered,
            "buffer_current_size": buffer_current,
            "last_active_at": source.last_active_at.isoformat() if source.last_active_at else None,
            "uptime_seconds": uptime,
        }

    async def check_timeouts(self) -> None:
        """检查所有缓冲区是否超时，超时则触发分析"""
        for source_id, buffer in list(self._buffers.items()):
            if buffer.should_flush:
                ws = self._active_connections.get(source_id)
                response = await self._flush_and_analyze(source_id, buffer)
                if response and ws:
                    try:
                        import json
                        await ws.send_text(json.dumps(response))
                    except Exception:
                        pass
