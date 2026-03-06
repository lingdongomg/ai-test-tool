"""
日志源 Repository
"""

import json
import uuid
from typing import Any

from .base import BaseRepository
from ..models.log_source import LogSource


class LogSourceRepository(BaseRepository[LogSource]):
    """日志源仓库"""

    table_name = "log_sources"
    model_class = LogSource
    id_field = "source_id"
    allowed_fields = frozenset({
        "id", "source_id", "name", "description", "tags",
        "buffer_size", "buffer_timeout_sec", "auto_learn",
        "auto_approve_threshold", "is_enabled", "status",
        "total_lines_received", "total_analyses_triggered",
        "last_active_at", "created_at", "updated_at",
    })
    allowed_sort_fields = frozenset({"id", "created_at", "name", "last_active_at"})

    def get_by_id(self, source_id: str) -> LogSource | None:
        return self._get_by_field("source_id", source_id)

    def create(self, source: LogSource) -> LogSource:
        """创建日志源"""
        if not source.source_id:
            source.source_id = str(uuid.uuid4())[:8]

        sql = """
            INSERT INTO log_sources
            (source_id, name, description, tags, buffer_size, buffer_timeout_sec,
             auto_learn, auto_approve_threshold, is_enabled, status,
             total_lines_received, total_analyses_triggered)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(sql, (
            source.source_id,
            source.name,
            json.dumps(source.tags, ensure_ascii=False) if source.tags else '[]',
            source.description or '',
            source.buffer_size,
            source.buffer_timeout_sec,
            source.auto_learn,
            source.auto_approve_threshold,
            source.is_enabled,
            source.status or 'disconnected',
            0,
            0,
        ))
        return source

    def update(self, source_id: str, updates: dict[str, Any]) -> int:
        """更新日志源"""
        if 'tags' in updates and isinstance(updates['tags'], list):
            updates['tags'] = json.dumps(updates['tags'], ensure_ascii=False)
        return self._update_by_field("source_id", source_id, updates)

    def delete(self, source_id: str) -> int:
        """删除日志源"""
        return self._delete_by_field("source_id", source_id)

    def list_all(
        self,
        is_enabled: bool | None = None,
        status: str | None = None,
    ) -> list[LogSource]:
        """获取日志源列表"""
        conditions = []
        params: list[Any] = []

        if is_enabled is not None:
            conditions.append("is_enabled = %s")
            params.append(is_enabled)
        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM log_sources {where_clause} ORDER BY created_at DESC"
        rows = self.db.fetch_all(sql, tuple(params) if params else None)
        return [LogSource.from_dict(dict(r)) for r in rows]

    def update_stats(self, source_id: str, lines_added: int = 0, analyses_added: int = 0) -> None:
        """更新统计信息"""
        sql = """
            UPDATE log_sources SET
                total_lines_received = total_lines_received + %s,
                total_analyses_triggered = total_analyses_triggered + %s,
                last_active_at = datetime('now'),
                updated_at = datetime('now')
            WHERE source_id = %s
        """
        self.db.execute(sql, (lines_added, analyses_added, source_id))

    def set_status(self, source_id: str, status: str) -> None:
        """更新连接状态"""
        sql = "UPDATE log_sources SET status = %s, updated_at = datetime('now') WHERE source_id = %s"
        self.db.execute(sql, (status, source_id))
