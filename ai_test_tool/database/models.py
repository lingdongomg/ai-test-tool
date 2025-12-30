"""
数据模型定义
Python 3.13+ 兼容
"""

import json
from typing import Any, Self
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TestCaseCategory(Enum):
    """测试用例类别"""
    NORMAL = "normal"
    BOUNDARY = "boundary"
    EXCEPTION = "exception"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestCasePriority(Enum):
    """测试用例优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TestResultStatus(Enum):
    """测试结果状态"""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class ReportType(Enum):
    """报告类型"""
    ANALYSIS = "analysis"
    TEST = "test"
    SUMMARY = "summary"


@dataclass
class AnalysisTask:
    """分析任务模型"""
    task_id: str
    name: str
    log_file_path: str
    description: str = ""
    log_file_size: int = 0
    status: TaskStatus = TaskStatus.PENDING
    total_lines: int = 0
    processed_lines: int = 0
    total_requests: int = 0
    total_test_cases: int = 0
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value if isinstance(self.status, TaskStatus) else self.status
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ParsedRequestRecord:
    """解析请求记录模型"""
    task_id: str
    request_id: str
    method: str
    url: str
    category: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
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
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        # JSON字段序列化
        result['headers'] = json.dumps(self.headers, ensure_ascii=False) if self.headers else '{}'
        result['query_params'] = json.dumps(self.query_params, ensure_ascii=False) if self.query_params else '{}'
        result['metadata'] = json.dumps(self.metadata, ensure_ascii=False) if self.metadata else '{}'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        # JSON字段反序列化
        if 'headers' in data and isinstance(data['headers'], str):
            data['headers'] = json.loads(data['headers']) if data['headers'] else {}
        if 'query_params' in data and isinstance(data['query_params'], str):
            data['query_params'] = json.loads(data['query_params']) if data['query_params'] else {}
        if 'metadata' in data and isinstance(data['metadata'], str):
            data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TestCaseRecord:
    """测试用例记录模型"""
    task_id: str
    case_id: str
    name: str
    method: str
    url: str
    description: str = ""
    category: TestCaseCategory = TestCaseCategory.NORMAL
    priority: TestCasePriority = TestCasePriority.MEDIUM
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    query_params: dict[str, str] = field(default_factory=dict)
    expected_status_code: int = 200
    expected_response: dict[str, Any] = field(default_factory=dict)
    max_response_time_ms: int = 3000
    tags: list[str] = field(default_factory=list)
    group_name: str = ""
    dependencies: list[str] = field(default_factory=list)
    is_enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['category'] = self.category.value if isinstance(self.category, TestCaseCategory) else self.category
        result['priority'] = self.priority.value if isinstance(self.priority, TestCasePriority) else self.priority
        # JSON字段序列化
        result['headers'] = json.dumps(self.headers, ensure_ascii=False) if self.headers else '{}'
        result['body'] = json.dumps(self.body, ensure_ascii=False) if self.body else None
        result['query_params'] = json.dumps(self.query_params, ensure_ascii=False) if self.query_params else '{}'
        result['expected_response'] = json.dumps(self.expected_response, ensure_ascii=False) if self.expected_response else '{}'
        result['tags'] = json.dumps(self.tags, ensure_ascii=False) if self.tags else '[]'
        result['dependencies'] = json.dumps(self.dependencies, ensure_ascii=False) if self.dependencies else '[]'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        # 枚举字段转换
        if 'category' in data and isinstance(data['category'], str):
            data['category'] = TestCaseCategory(data['category'])
        if 'priority' in data and isinstance(data['priority'], str):
            data['priority'] = TestCasePriority(data['priority'])
        # JSON字段反序列化
        if 'headers' in data and isinstance(data['headers'], str):
            data['headers'] = json.loads(data['headers']) if data['headers'] else {}
        if 'body' in data and isinstance(data['body'], str):
            data['body'] = json.loads(data['body']) if data['body'] else None
        if 'query_params' in data and isinstance(data['query_params'], str):
            data['query_params'] = json.loads(data['query_params']) if data['query_params'] else {}
        if 'expected_response' in data and isinstance(data['expected_response'], str):
            data['expected_response'] = json.loads(data['expected_response']) if data['expected_response'] else {}
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags']) if data['tags'] else []
        if 'dependencies' in data and isinstance(data['dependencies'], str):
            data['dependencies'] = json.loads(data['dependencies']) if data['dependencies'] else []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TestResultRecord:
    """测试结果记录模型"""
    task_id: str
    case_id: str
    execution_id: str
    status: TestResultStatus
    actual_status_code: int = 0
    actual_response_time_ms: float = 0
    actual_response_body: str = ""
    actual_headers: dict[str, str] = field(default_factory=dict)
    error_message: str = ""
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    executed_at: datetime | None = None
    created_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value if isinstance(self.status, TestResultStatus) else self.status
        result['actual_headers'] = json.dumps(self.actual_headers, ensure_ascii=False) if self.actual_headers else '{}'
        result['validation_results'] = json.dumps(self.validation_results, ensure_ascii=False) if self.validation_results else '[]'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TestResultStatus(data['status'])
        if 'actual_headers' in data and isinstance(data['actual_headers'], str):
            data['actual_headers'] = json.loads(data['actual_headers']) if data['actual_headers'] else {}
        if 'validation_results' in data and isinstance(data['validation_results'], str):
            data['validation_results'] = json.loads(data['validation_results']) if data['validation_results'] else []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AnalysisReport:
    """分析报告模型"""
    task_id: str
    title: str
    content: str
    report_type: ReportType = ReportType.ANALYSIS
    format: str = "markdown"
    statistics: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['report_type'] = self.report_type.value if isinstance(self.report_type, ReportType) else self.report_type
        result['statistics'] = json.dumps(self.statistics, ensure_ascii=False) if self.statistics else '{}'
        result['issues'] = json.dumps(self.issues, ensure_ascii=False) if self.issues else '[]'
        result['recommendations'] = json.dumps(self.recommendations, ensure_ascii=False) if self.recommendations else '[]'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'report_type' in data and isinstance(data['report_type'], str):
            data['report_type'] = ReportType(data['report_type'])
        if 'statistics' in data and isinstance(data['statistics'], str):
            data['statistics'] = json.loads(data['statistics']) if data['statistics'] else {}
        if 'issues' in data and isinstance(data['issues'], str):
            data['issues'] = json.loads(data['issues']) if data['issues'] else []
        if 'recommendations' in data and isinstance(data['recommendations'], str):
            data['recommendations'] = json.loads(data['recommendations']) if data['recommendations'] else []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
