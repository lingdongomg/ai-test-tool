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


# =====================================================
# 接口标签和端点模型
# =====================================================

@dataclass
class ApiTag:
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
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class EndpointSourceType(Enum):
    """端点来源类型"""
    SWAGGER = "swagger"
    POSTMAN = "postman"
    MANUAL = "manual"


@dataclass
class ApiEndpoint:
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
    tags: list[str] = field(default_factory=list)  # 标签名称列表
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['source_type'] = self.source_type.value if isinstance(self.source_type, EndpointSourceType) else self.source_type
        result['parameters'] = json.dumps(self.parameters, ensure_ascii=False) if self.parameters else '[]'
        result['request_body'] = json.dumps(self.request_body, ensure_ascii=False) if self.request_body else '{}'
        result['responses'] = json.dumps(self.responses, ensure_ascii=False) if self.responses else '{}'
        result['security'] = json.dumps(self.security, ensure_ascii=False) if self.security else '[]'
        # tags不存储到数据库，通过关联表管理
        del result['tags']
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'source_type' in data and isinstance(data['source_type'], str):
            data['source_type'] = EndpointSourceType(data['source_type'])
        if 'parameters' in data and isinstance(data['parameters'], str):
            data['parameters'] = json.loads(data['parameters']) if data['parameters'] else []
        if 'request_body' in data and isinstance(data['request_body'], str):
            data['request_body'] = json.loads(data['request_body']) if data['request_body'] else {}
        if 'responses' in data and isinstance(data['responses'], str):
            data['responses'] = json.loads(data['responses']) if data['responses'] else {}
        if 'security' in data and isinstance(data['security'], str):
            data['security'] = json.loads(data['security']) if data['security'] else []
        if 'tags' not in data:
            data['tags'] = []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =====================================================
# 测试场景模型
# =====================================================

class StepType(Enum):
    """步骤类型"""
    REQUEST = "request"
    WAIT = "wait"
    CONDITION = "condition"
    LOOP = "loop"
    EXTRACT = "extract"
    ASSERT = "assert"


class TriggerType(Enum):
    """触发类型"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    PIPELINE = "pipeline"
    API = "api"


class ScenarioStatus(Enum):
    """场景执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TestScenario:
    """测试场景模型"""
    scenario_id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    setup_hooks: list[dict[str, Any]] = field(default_factory=list)
    teardown_hooks: list[dict[str, Any]] = field(default_factory=list)
    retry_on_failure: bool = False
    max_retries: int = 3
    is_enabled: bool = True
    created_by: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
    steps: list["ScenarioStep"] = field(default_factory=list)  # 关联步骤
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['tags'] = json.dumps(self.tags, ensure_ascii=False) if self.tags else '[]'
        result['variables'] = json.dumps(self.variables, ensure_ascii=False) if self.variables else '{}'
        result['setup_hooks'] = json.dumps(self.setup_hooks, ensure_ascii=False) if self.setup_hooks else '[]'
        result['teardown_hooks'] = json.dumps(self.teardown_hooks, ensure_ascii=False) if self.teardown_hooks else '[]'
        del result['steps']  # 步骤单独存储
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags']) if data['tags'] else []
        if 'variables' in data and isinstance(data['variables'], str):
            data['variables'] = json.loads(data['variables']) if data['variables'] else {}
        if 'setup_hooks' in data and isinstance(data['setup_hooks'], str):
            data['setup_hooks'] = json.loads(data['setup_hooks']) if data['setup_hooks'] else []
        if 'teardown_hooks' in data and isinstance(data['teardown_hooks'], str):
            data['teardown_hooks'] = json.loads(data['teardown_hooks']) if data['teardown_hooks'] else []
        if 'steps' not in data:
            data['steps'] = []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScenarioStep:
    """场景步骤模型"""
    scenario_id: str
    step_id: str
    step_order: int
    name: str
    description: str = ""
    step_type: StepType = StepType.REQUEST
    method: str = ""
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    query_params: dict[str, str] = field(default_factory=dict)
    extractions: list[dict[str, Any]] = field(default_factory=list)
    assertions: list[dict[str, Any]] = field(default_factory=list)
    wait_time_ms: int = 0
    condition: dict[str, Any] = field(default_factory=dict)
    loop_config: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int = 30000
    continue_on_failure: bool = False
    is_enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['step_type'] = self.step_type.value if isinstance(self.step_type, StepType) else self.step_type
        result['headers'] = json.dumps(self.headers, ensure_ascii=False) if self.headers else '{}'
        result['body'] = json.dumps(self.body, ensure_ascii=False) if self.body else None
        result['query_params'] = json.dumps(self.query_params, ensure_ascii=False) if self.query_params else '{}'
        result['extractions'] = json.dumps(self.extractions, ensure_ascii=False) if self.extractions else '[]'
        result['assertions'] = json.dumps(self.assertions, ensure_ascii=False) if self.assertions else '[]'
        result['condition'] = json.dumps(self.condition, ensure_ascii=False) if self.condition else '{}'
        result['loop_config'] = json.dumps(self.loop_config, ensure_ascii=False) if self.loop_config else '{}'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'step_type' in data and isinstance(data['step_type'], str):
            data['step_type'] = StepType(data['step_type'])
        if 'headers' in data and isinstance(data['headers'], str):
            data['headers'] = json.loads(data['headers']) if data['headers'] else {}
        if 'body' in data and isinstance(data['body'], str):
            data['body'] = json.loads(data['body']) if data['body'] else None
        if 'query_params' in data and isinstance(data['query_params'], str):
            data['query_params'] = json.loads(data['query_params']) if data['query_params'] else {}
        if 'extractions' in data and isinstance(data['extractions'], str):
            data['extractions'] = json.loads(data['extractions']) if data['extractions'] else []
        if 'assertions' in data and isinstance(data['assertions'], str):
            data['assertions'] = json.loads(data['assertions']) if data['assertions'] else []
        if 'condition' in data and isinstance(data['condition'], str):
            data['condition'] = json.loads(data['condition']) if data['condition'] else {}
        if 'loop_config' in data and isinstance(data['loop_config'], str):
            data['loop_config'] = json.loads(data['loop_config']) if data['loop_config'] else {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScenarioExecution:
    """场景执行记录模型"""
    execution_id: str
    scenario_id: str
    trigger_type: TriggerType = TriggerType.MANUAL
    status: ScenarioStatus = ScenarioStatus.PENDING
    base_url: str = ""
    environment: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    duration_ms: int = 0
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['trigger_type'] = self.trigger_type.value if isinstance(self.trigger_type, TriggerType) else self.trigger_type
        result['status'] = self.status.value if isinstance(self.status, ScenarioStatus) else self.status
        result['variables'] = json.dumps(self.variables, ensure_ascii=False) if self.variables else '{}'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'trigger_type' in data and isinstance(data['trigger_type'], str):
            data['trigger_type'] = TriggerType(data['trigger_type'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ScenarioStatus(data['status'])
        if 'variables' in data and isinstance(data['variables'], str):
            data['variables'] = json.loads(data['variables']) if data['variables'] else {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StepResult:
    """步骤执行结果模型"""
    execution_id: str
    step_id: str
    step_order: int
    status: TestResultStatus
    request_url: str = ""
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str = ""
    response_status_code: int = 0
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    response_time_ms: float = 0
    extracted_variables: dict[str, Any] = field(default_factory=dict)
    assertion_results: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    executed_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value if isinstance(self.status, TestResultStatus) else self.status
        result['request_headers'] = json.dumps(self.request_headers, ensure_ascii=False) if self.request_headers else '{}'
        result['response_headers'] = json.dumps(self.response_headers, ensure_ascii=False) if self.response_headers else '{}'
        result['extracted_variables'] = json.dumps(self.extracted_variables, ensure_ascii=False) if self.extracted_variables else '{}'
        result['assertion_results'] = json.dumps(self.assertion_results, ensure_ascii=False) if self.assertion_results else '[]'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TestResultStatus(data['status'])
        if 'request_headers' in data and isinstance(data['request_headers'], str):
            data['request_headers'] = json.loads(data['request_headers']) if data['request_headers'] else {}
        if 'response_headers' in data and isinstance(data['response_headers'], str):
            data['response_headers'] = json.loads(data['response_headers']) if data['response_headers'] else {}
        if 'extracted_variables' in data and isinstance(data['extracted_variables'], str):
            data['extracted_variables'] = json.loads(data['extracted_variables']) if data['extracted_variables'] else {}
        if 'assertion_results' in data and isinstance(data['assertion_results'], str):
            data['assertion_results'] = json.loads(data['assertion_results']) if data['assertion_results'] else []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScheduledTask:
    """定时任务模型"""
    task_id: str
    name: str
    scenario_ids: list[str]
    cron_expression: str
    description: str = ""
    base_url: str = ""
    environment: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    is_enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['scenario_ids'] = json.dumps(self.scenario_ids, ensure_ascii=False) if self.scenario_ids else '[]'
        result['variables'] = json.dumps(self.variables, ensure_ascii=False) if self.variables else '{}'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'scenario_ids' in data and isinstance(data['scenario_ids'], str):
            data['scenario_ids'] = json.loads(data['scenario_ids']) if data['scenario_ids'] else []
        if 'variables' in data and isinstance(data['variables'], str):
            data['variables'] = json.loads(data['variables']) if data['variables'] else {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =====================================================
# 测试用例版本管理模型
# =====================================================

class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    ENABLE = "enable"
    DISABLE = "disable"


@dataclass
class TestCaseVersion:
    """测试用例版本模型"""
    version_id: str
    task_id: str
    case_id: str
    version_number: int
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
    change_type: ChangeType = ChangeType.CREATE
    change_summary: str = ""
    changed_fields: list[str] = field(default_factory=list)
    changed_by: str = ""
    created_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['category'] = self.category.value if isinstance(self.category, TestCaseCategory) else self.category
        result['priority'] = self.priority.value if isinstance(self.priority, TestCasePriority) else self.priority
        result['change_type'] = self.change_type.value if isinstance(self.change_type, ChangeType) else self.change_type
        # JSON字段序列化
        result['headers'] = json.dumps(self.headers, ensure_ascii=False) if self.headers else '{}'
        result['body'] = json.dumps(self.body, ensure_ascii=False) if self.body else None
        result['query_params'] = json.dumps(self.query_params, ensure_ascii=False) if self.query_params else '{}'
        result['expected_response'] = json.dumps(self.expected_response, ensure_ascii=False) if self.expected_response else '{}'
        result['tags'] = json.dumps(self.tags, ensure_ascii=False) if self.tags else '[]'
        result['dependencies'] = json.dumps(self.dependencies, ensure_ascii=False) if self.dependencies else '[]'
        result['changed_fields'] = json.dumps(self.changed_fields, ensure_ascii=False) if self.changed_fields else '[]'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        # 枚举字段转换
        if 'category' in data and isinstance(data['category'], str):
            data['category'] = TestCaseCategory(data['category'])
        if 'priority' in data and isinstance(data['priority'], str):
            data['priority'] = TestCasePriority(data['priority'])
        if 'change_type' in data and isinstance(data['change_type'], str):
            data['change_type'] = ChangeType(data['change_type'])
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
        if 'changed_fields' in data and isinstance(data['changed_fields'], str):
            data['changed_fields'] = json.loads(data['changed_fields']) if data['changed_fields'] else []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_test_case(
        cls,
        test_case: TestCaseRecord,
        version_id: str,
        version_number: int,
        change_type: ChangeType,
        change_summary: str = "",
        changed_fields: list[str] | None = None,
        changed_by: str = ""
    ) -> Self:
        """从测试用例创建版本"""
        return cls(
            version_id=version_id,
            task_id=test_case.task_id,
            case_id=test_case.case_id,
            version_number=version_number,
            name=test_case.name,
            description=test_case.description,
            category=test_case.category,
            priority=test_case.priority,
            method=test_case.method,
            url=test_case.url,
            headers=test_case.headers,
            body=test_case.body,
            query_params=test_case.query_params,
            expected_status_code=test_case.expected_status_code,
            expected_response=test_case.expected_response,
            max_response_time_ms=test_case.max_response_time_ms,
            tags=test_case.tags,
            group_name=test_case.group_name,
            dependencies=test_case.dependencies,
            change_type=change_type,
            change_summary=change_summary,
            changed_fields=changed_fields or [],
            changed_by=changed_by
        )


@dataclass
class TestCaseChangeLog:
    """测试用例变更日志模型"""
    task_id: str
    case_id: str
    version_id: str
    change_type: ChangeType
    change_summary: str = ""
    old_value: dict[str, Any] = field(default_factory=dict)
    new_value: dict[str, Any] = field(default_factory=dict)
    changed_by: str = ""
    ip_address: str = ""
    user_agent: str = ""
    created_at: datetime | None = None
    id: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['change_type'] = self.change_type.value if isinstance(self.change_type, ChangeType) else self.change_type
        result['old_value'] = json.dumps(self.old_value, ensure_ascii=False) if self.old_value else '{}'
        result['new_value'] = json.dumps(self.new_value, ensure_ascii=False) if self.new_value else '{}'
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        if 'change_type' in data and isinstance(data['change_type'], str):
            data['change_type'] = ChangeType(data['change_type'])
        if 'old_value' in data and isinstance(data['old_value'], str):
            data['old_value'] = json.loads(data['old_value']) if data['old_value'] else {}
        if 'new_value' in data and isinstance(data['new_value'], str):
            data['new_value'] = json.loads(data['new_value']) if data['new_value'] else {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
