"""
知识库相关模型
该文件内容使用AI生成，注意识别准确性
"""

from typing import Any, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import BaseModel, KnowledgeType, KnowledgeStatus, KnowledgeSource, ChangeType


@dataclass
class KnowledgeEntry(BaseModel):
    """知识条目模型"""
    knowledge_id: str
    title: str
    content: str
    type: KnowledgeType = KnowledgeType.PROJECT_CONFIG
    category: str = ""
    scope: str = ""
    priority: int = 0
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    source: KnowledgeSource = KnowledgeSource.MANUAL
    source_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str = ""
    version: int = 1
    id: int | None = None

    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {
            'type': KnowledgeType,
            'status': KnowledgeStatus,
            'source': KnowledgeSource
        }

    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['metadata']

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        # tags 不存储到主表，通过关联表管理
        result.pop('tags', None)
        return result


@dataclass
class KnowledgeHistory(BaseModel):
    """知识版本历史模型"""
    knowledge_id: str
    version: int
    content: str
    title: str
    change_type: ChangeType
    changed_by: str = ""
    changed_at: datetime | None = None
    id: int | None = None

    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'change_type': ChangeType}


@dataclass
class KnowledgeUsage(BaseModel):
    """知识使用记录模型"""
    usage_id: str
    knowledge_id: str
    used_in: str
    context: str = ""
    helpful: int = 0  # 1有帮助, 0未评价, -1无帮助
    used_at: datetime | None = None
    id: int | None = None
