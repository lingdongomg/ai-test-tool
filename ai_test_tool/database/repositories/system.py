"""
系统相关 Repository：会话、消息、配置
"""

from datetime import datetime
from typing import Any

from ..connection import DatabaseManager, get_db_manager


class ChatSessionRepository:
    """对话会话仓库"""

    table_name = "chat_sessions"

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db or get_db_manager()

    def create(self, session_id: str, title: str = "", context: dict | None = None) -> str:
        """创建会话"""
        import json
        sql = """
            INSERT INTO chat_sessions (session_id, title, context)
            VALUES (%s, %s, %s)
        """
        context_str = json.dumps(context or {}, ensure_ascii=False)
        self.db.execute(sql, (session_id, title, context_str))
        return session_id

    def get_by_id(self, session_id: str) -> dict | None:
        """根据ID获取会话"""
        sql = "SELECT * FROM chat_sessions WHERE session_id = %s"
        return self.db.fetch_one(sql, (session_id,))

    def update_title(self, session_id: str, title: str) -> int:
        """更新会话标题"""
        sql = """
            UPDATE chat_sessions
            SET title = %s, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = %s
        """
        return self.db.execute(sql, (title, session_id))

    def increment_message_count(self, session_id: str) -> int:
        """增加消息计数"""
        sql = """
            UPDATE chat_sessions
            SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = %s
        """
        return self.db.execute(sql, (session_id,))

    def list_recent(self, limit: int = 20) -> list[dict]:
        """获取最近的会话列表"""
        sql = """
            SELECT * FROM chat_sessions
            ORDER BY updated_at DESC
            LIMIT %s
        """
        return self.db.fetch_all(sql, (limit,))

    def delete(self, session_id: str) -> int:
        """删除会话"""
        sql = "DELETE FROM chat_sessions WHERE session_id = %s"
        return self.db.execute(sql, (session_id,))


class ChatMessageRepository:
    """对话消息仓库"""

    table_name = "chat_messages"

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db or get_db_manager()

    def create(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> str:
        """创建消息"""
        import json
        sql = """
            INSERT INTO chat_messages (message_id, session_id, role, content, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """
        metadata_str = json.dumps(metadata or {}, ensure_ascii=False)
        self.db.execute(sql, (message_id, session_id, role, content, metadata_str))
        return message_id

    def get_by_session(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict]:
        """获取会话的所有消息"""
        sql = """
            SELECT * FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s OFFSET %s
        """
        return self.db.fetch_all(sql, (session_id, limit, offset))

    def get_recent_by_session(self, session_id: str, limit: int = 10) -> list[dict]:
        """获取会话最近的N条消息（用于构建上下文）"""
        sql = """
            SELECT * FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        messages = self.db.fetch_all(sql, (session_id, limit))
        # 反转顺序使其按时间正序排列
        return list(reversed(messages))

    def count_by_session(self, session_id: str) -> int:
        """统计会话消息数量"""
        sql = "SELECT COUNT(*) as count FROM chat_messages WHERE session_id = %s"
        result = self.db.fetch_one(sql, (session_id,))
        return result['count'] if result else 0

    def delete_by_session(self, session_id: str) -> int:
        """删除会话的所有消息"""
        sql = "DELETE FROM chat_messages WHERE session_id = %s"
        return self.db.execute(sql, (session_id,))


# =====================================================
# 系统配置仓库
# 该文件内容使用AI生成，注意识别准确性
# =====================================================

class SystemConfigRepository:
    """系统配置仓库"""

    table_name = "system_configs"

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db or get_db_manager()

    def get(self, key: str, default: dict | None = None) -> dict:
        """获取配置"""
        import json
        sql = "SELECT config_value FROM system_configs WHERE config_key = %s"
        result = self.db.fetch_one(sql, (key,))
        if result:
            try:
                return json.loads(result['config_value'])
            except json.JSONDecodeError:
                return default or {}
        return default or {}

    def set(self, key: str, value: dict, description: str = "") -> bool:
        """设置配置"""
        import json
        value_str = json.dumps(value, ensure_ascii=False)

        # 使用 UPSERT
        sql = """
            INSERT INTO system_configs (config_key, config_value, description, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT(config_key) DO UPDATE SET
                config_value = excluded.config_value,
                description = CASE WHEN excluded.description != '' THEN excluded.description ELSE system_configs.description END,
                updated_at = CURRENT_TIMESTAMP
        """
        self.db.execute(sql, (key, value_str, description))
        return True

    def delete(self, key: str) -> bool:
        """删除配置"""
        sql = "DELETE FROM system_configs WHERE config_key = %s"
        return self.db.execute(sql, (key,)) > 0

    def list_all(self) -> list[dict]:
        """列出所有配置"""
        sql = "SELECT * FROM system_configs ORDER BY config_key"
        return self.db.fetch_all(sql)
