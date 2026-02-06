"""
接口管理相关模型
该文件内容使用AI生成，注意识别准确性
"""

from typing import Any, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import BaseModel, EndpointSourceType


@dataclass
class ApiTag(BaseModel):
    """接口标签模型"""
    name: str
    description: str = ""
    color: str = "#1890ff"
    parent_id: int | None = None
    sort_order: int = 0
    is_system: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None


@dataclass
class ApiEndpoint(BaseModel):
    """接口端点模型"""
    endpoint_id: str
    name: str
    method: str
    path: str
    description: str = ""
    summary: str = ""
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body: dict[str, Any] = field(default_factory=dict)
    responses: dict[str, Any] = field(default_factory=dict)
    security: list[dict[str, Any]] = field(default_factory=list)
    source_type: EndpointSourceType = EndpointSourceType.MANUAL
    source_file: str = ""
    is_deprecated: bool = False
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None

    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'source_type': EndpointSourceType}

    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['parameters', 'request_body', 'responses', 'security']

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        # tags 不存储到数据库，通过关联表管理
        result.pop('tags', None)
        return result
