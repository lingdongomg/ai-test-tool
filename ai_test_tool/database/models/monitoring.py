"""
监控相关数据模型
该文件内容使用AI生成，注意识别准确性
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .base import BaseModel


class InsightSeverity(str, Enum):
    """洞察严重程度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HealthCheckStatus(str, Enum):
    """健康检查状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RequestSource(str, Enum):
    """请求来源"""
    LOG_PARSE = "log_parse"
    MANUAL = "manual"
    IMPORT = "import"


@dataclass
class AIInsight(BaseModel):
    """AI洞察模型"""
    insight_id: str
    insight_type: str
    title: str
    description: str | None = None
    severity: InsightSeverity = InsightSeverity.MEDIUM
    confidence: float = 0.8
    details: str | None = None
    recommendations: str | None = None
    is_resolved: bool = False
    resolved_at: str | None = None
    created_at: datetime | None = None
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'insight_id': self.insight_id,
            'insight_type': self.insight_type,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value if isinstance(self.severity, InsightSeverity) else self.severity,
            'confidence': self.confidence,
            'details': self.details,
            'recommendations': self.recommendations,
            'is_resolved': 1 if self.is_resolved else 0,
            'resolved_at': self.resolved_at,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AIInsight":
        severity = data.get('severity', 'medium')
        if isinstance(severity, str):
            try:
                severity = InsightSeverity(severity)
            except ValueError:
                severity = InsightSeverity.MEDIUM

        return cls(
            id=data.get('id'),
            insight_id=data['insight_id'],
            insight_type=data['insight_type'],
            title=data['title'],
            description=data.get('description'),
            severity=severity,
            confidence=float(data.get('confidence', 0.8)),
            details=data.get('details'),
            recommendations=data.get('recommendations'),
            is_resolved=bool(data.get('is_resolved', 0)),
            resolved_at=data.get('resolved_at'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') and isinstance(data['created_at'], str) else data.get('created_at'),
        )


@dataclass
class ProductionRequest(BaseModel):
    """生产请求监控模型"""
    request_id: str
    method: str
    url: str
    headers: str | None = None
    body: str | None = None
    query_params: str | None = None
    expected_status_code: int = 200
    expected_response_pattern: str | None = None
    source: RequestSource = RequestSource.MANUAL
    source_task_id: str | None = None
    tags: str | None = None
    is_enabled: bool = True
    last_check_at: str | None = None
    last_check_status: str | None = None
    consecutive_failures: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'request_id': self.request_id,
            'method': self.method,
            'url': self.url,
            'headers': self.headers,
            'body': self.body,
            'query_params': self.query_params,
            'expected_status_code': self.expected_status_code,
            'expected_response_pattern': self.expected_response_pattern,
            'source': self.source.value if isinstance(self.source, RequestSource) else self.source,
            'source_task_id': self.source_task_id,
            'tags': self.tags,
            'is_enabled': 1 if self.is_enabled else 0,
            'last_check_at': self.last_check_at,
            'last_check_status': self.last_check_status,
            'consecutive_failures': self.consecutive_failures,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductionRequest":
        source = data.get('source', 'manual')
        if isinstance(source, str):
            try:
                source = RequestSource(source)
            except ValueError:
                source = RequestSource.MANUAL

        return cls(
            id=data.get('id'),
            request_id=data['request_id'],
            method=data['method'],
            url=data['url'],
            headers=data.get('headers'),
            body=data.get('body'),
            query_params=data.get('query_params'),
            expected_status_code=data.get('expected_status_code', 200),
            expected_response_pattern=data.get('expected_response_pattern'),
            source=source,
            source_task_id=data.get('source_task_id'),
            tags=data.get('tags'),
            is_enabled=bool(data.get('is_enabled', 1)),
            last_check_at=data.get('last_check_at'),
            last_check_status=data.get('last_check_status'),
            consecutive_failures=data.get('consecutive_failures', 0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') and isinstance(data['created_at'], str) else data.get('created_at'),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') and isinstance(data['updated_at'], str) else data.get('updated_at'),
        )


@dataclass
class HealthCheckExecution(BaseModel):
    """健康检查执行记录模型"""
    execution_id: str
    base_url: str | None = None
    total_requests: int = 0
    healthy_count: int = 0
    unhealthy_count: int = 0
    status: HealthCheckStatus = HealthCheckStatus.PENDING
    trigger_type: str = "manual"
    started_at: str | None = None
    completed_at: str | None = None
    created_at: datetime | None = None
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'base_url': self.base_url,
            'total_requests': self.total_requests,
            'healthy_count': self.healthy_count,
            'unhealthy_count': self.unhealthy_count,
            'status': self.status.value if isinstance(self.status, HealthCheckStatus) else self.status,
            'trigger_type': self.trigger_type,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthCheckExecution":
        status = data.get('status', 'pending')
        if isinstance(status, str):
            try:
                status = HealthCheckStatus(status)
            except ValueError:
                status = HealthCheckStatus.PENDING

        return cls(
            id=data.get('id'),
            execution_id=data['execution_id'],
            base_url=data.get('base_url'),
            total_requests=data.get('total_requests', 0),
            healthy_count=data.get('healthy_count', 0),
            unhealthy_count=data.get('unhealthy_count', 0),
            status=status,
            trigger_type=data.get('trigger_type', 'manual'),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') and isinstance(data['created_at'], str) else data.get('created_at'),
        )


@dataclass
class HealthCheckResult(BaseModel):
    """健康检查结果模型"""
    execution_id: str
    request_id: str
    success: bool
    status_code: int | None = None
    response_time_ms: float | None = None
    response_body: str | None = None
    error_message: str | None = None
    ai_analysis: str | None = None
    checked_at: datetime | None = None
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'request_id': self.request_id,
            'success': 1 if self.success else 0,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'response_body': self.response_body,
            'error_message': self.error_message,
            'ai_analysis': self.ai_analysis,
            'checked_at': self.checked_at.isoformat() if isinstance(self.checked_at, datetime) else self.checked_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthCheckResult":
        return cls(
            id=data.get('id'),
            execution_id=data['execution_id'],
            request_id=data['request_id'],
            success=bool(data.get('success', 0)),
            status_code=data.get('status_code'),
            response_time_ms=float(data['response_time_ms']) if data.get('response_time_ms') else None,
            response_body=data.get('response_body'),
            error_message=data.get('error_message'),
            ai_analysis=data.get('ai_analysis'),
            checked_at=datetime.fromisoformat(data['checked_at']) if data.get('checked_at') and isinstance(data['checked_at'], str) else data.get('checked_at'),
        )
