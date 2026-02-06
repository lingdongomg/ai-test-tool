"""
任务相关模型
该文件内容使用AI生成，注意识别准确性
"""

import json
from typing import Any, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import BaseModel, TaskStatus, TaskType


@dataclass
class AnalysisTask(BaseModel):
    """分析任务模型"""
    task_id: str
    name: str
    log_file_path: str = ""
    description: str = ""
    task_type: TaskType = TaskType.LOG_ANALYSIS
    log_file_size: int = 0
    status: TaskStatus = TaskStatus.PENDING
    total_lines: int = 0
    processed_lines: int = 0
    total_requests: int = 0
    total_test_cases: int = 0
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None

    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'status': TaskStatus, 'task_type': TaskType}

    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['metadata']


@dataclass
class ParsedRequestRecord(BaseModel):
    """解析请求记录模型"""
    task_id: str
    request_id: str
    method: str
    url: str
    category: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: str | dict | None = None
    query_params: dict[str, str] = field(default_factory=dict)
    http_status: int = 0
    response_time_ms: float = 0
    response_body: str | None = None
    has_error: bool = False
    error_message: str = ""
    has_warning: bool = False
    warning_message: str = ""
    curl_command: str = ""
    timestamp: str = ""
    raw_logs: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    id: int | None = None

    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['headers', 'query_params', 'metadata']

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        # body 特殊处理：可能是字典或字符串
        if isinstance(result.get('body'), dict):
            result['body'] = json.dumps(result['body'], ensure_ascii=False)
        return result


@dataclass
class AnalysisReport(BaseModel):
    """分析报告模型"""
    from .base import ReportType

    task_id: str
    title: str
    content: str
    report_type: ReportType = ReportType.ANALYSIS
    format: str = "markdown"
    statistics: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    severity: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    id: int | None = None

    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        from .base import ReportType
        return {'report_type': ReportType}

    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['statistics', 'issues', 'recommendations', 'metadata']
