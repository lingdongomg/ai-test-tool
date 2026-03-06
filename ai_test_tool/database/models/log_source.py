"""
日志源模型
"""

from typing import Any, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import BaseModel


class LogSourceStatus(str, Enum):
    """日志源连接状态"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


@dataclass
class LogSource(BaseModel):
    """日志源配置模型"""
    source_id: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    buffer_size: int = 100
    buffer_timeout_sec: int = 30
    auto_learn: bool = True
    auto_approve_threshold: float = 0.8
    is_enabled: bool = True
    status: str = "disconnected"
    total_lines_received: int = 0
    total_analyses_triggered: int = 0
    last_active_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None

    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['tags']

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        # 确保 tags 是列表格式返回
        if isinstance(result.get('tags'), str):
            import json
            try:
                result['tags'] = json.loads(result['tags'])
            except (json.JSONDecodeError, TypeError):
                result['tags'] = []
        return result
