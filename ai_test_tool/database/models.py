"""
数据模型定义
该文件内容使用AI生成，注意识别准确性
重构版本：添加 BaseModel 基类，移除冗余模型
"""

import json
from typing import Any, Self, TypeVar, get_type_hints, Type
from dataclasses import dataclass, field, asdict, fields
from datetime import datetime
from enum import Enum

T = TypeVar('T', bound='BaseModel')


# =====================================================
# 枚举定义
# =====================================================

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(Enum):
    """任务类型"""
    LOG_ANALYSIS = "log_analysis"
    TEST_GENERATION = "test_generation"
    REPORT = "report"


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
    INSIGHT = "insight"


class TriggerType(Enum):
    """触发类型"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    PIPELINE = "pipeline"
    API = "api"


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ExecutionType(Enum):
    """执行类型"""
    TEST = "test"
    HEALTH_CHECK = "health_check"
    SCENARIO = "scenario"


class ResultType(Enum):
    """结果类型"""
    TEST = "test"
    HEALTH_CHECK = "health_check"
    SCENARIO_STEP = "scenario_step"


class EndpointSourceType(Enum):
    """端点来源类型"""
    SWAGGER = "swagger"
    POSTMAN = "postman"
    MANUAL = "manual"


class StepType(Enum):
    """步骤类型"""
    REQUEST = "request"
    WAIT = "wait"
    CONDITION = "condition"
    LOOP = "loop"
    EXTRACT = "extract"
    ASSERT = "assert"


class ScenarioStatus(Enum):
    """场景执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    ENABLE = "enable"
    DISABLE = "disable"
    ARCHIVE = "archive"


class KnowledgeType(Enum):
    """知识类型"""
    PROJECT_CONFIG = "project_config"      # 项目配置知识
    BUSINESS_RULE = "business_rule"        # 业务规则知识
    MODULE_CONTEXT = "module_context"      # 模块上下文知识
    TEST_EXPERIENCE = "test_experience"    # 测试经验知识


class KnowledgeStatus(Enum):
    """知识状态"""
    ACTIVE = "active"      # 活跃
    PENDING = "pending"    # 待审核
    ARCHIVED = "archived"  # 已归档


class KnowledgeSource(Enum):
    """知识来源"""
    MANUAL = "manual"              # 手动创建
    LOG_LEARNING = "log_learning"  # 日志学习
    TEST_LEARNING = "test_learning"  # 测试学习


# =====================================================
# 基类定义
# =====================================================

class BaseModel:
    """
    数据模型基类（混入类）
    提供通用的序列化和反序列化方法
    注意：这不是一个 dataclass，不能被继承为 dataclass 的基类
    """
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典，自动处理枚举和 JSON 字段"""
        result = asdict(self)  # type: ignore
        
        # 处理枚举字段
        for field_name, enum_type in self._get_enum_fields_class().items():
            if field_name in result:
                value = result[field_name]
                if isinstance(value, Enum):
                    result[field_name] = value.value
        
        # 处理 JSON 字段
        for field_name in self._get_json_fields_class():
            if field_name in result:
                value = result[field_name]
                if value is not None:
                    if isinstance(value, (dict, list)):
                        result[field_name] = json.dumps(value, ensure_ascii=False)
                    elif not isinstance(value, str):
                        result[field_name] = json.dumps(value, ensure_ascii=False)
        
        return result
    
    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """从字典创建实例，自动处理枚举和 JSON 字段"""
        # 获取有效字段
        valid_fields = {f.name for f in fields(cls)}  # type: ignore
        
        # 过滤数据
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        
        # 获取枚举和 JSON 字段配置
        enum_fields = cls._get_enum_fields_class()
        json_fields = cls._get_json_fields_class()
        
        # 处理枚举字段
        for field_name, enum_type in enum_fields.items():
            if field_name in filtered and isinstance(filtered[field_name], str):
                try:
                    filtered[field_name] = enum_type(filtered[field_name])
                except ValueError:
                    pass  # 保持原值
        
        # 处理 JSON 字段
        for field_name in json_fields:
            if field_name in filtered and isinstance(filtered[field_name], str):
                try:
                    filtered[field_name] = json.loads(filtered[field_name]) if filtered[field_name] else cls._get_json_default(field_name)
                except json.JSONDecodeError:
                    pass  # 保持原值
        
        return cls(**filtered)  # type: ignore
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        """获取枚举字段（子类需覆盖）"""
        return {}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        """获取 JSON 字段（子类需覆盖）"""
        return []
    
    @classmethod
    def _get_json_default(cls, field_name: str) -> Any:
        """获取 JSON 字段的默认值"""
        return {} if 'dict' in field_name or field_name in ['headers', 'body', 'query_params', 'metadata', 'variables'] else []


# =====================================================
# 核心业务模型
# =====================================================

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


# =====================================================
# 接口管理模型
# =====================================================

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


# =====================================================
# 测试用例模型
# =====================================================

@dataclass
class TestCaseRecord(BaseModel):
    """测试用例记录模型"""
    case_id: str
    endpoint_id: str
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
    assertions: list[dict[str, Any]] = field(default_factory=list)
    max_response_time_ms: int = 3000
    tags: list[str] = field(default_factory=list)
    is_enabled: bool = True
    is_ai_generated: bool = False
    source_task_id: str = ""
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'category': TestCaseCategory, 'priority': TestCasePriority}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['headers', 'body', 'query_params', 'expected_response', 'assertions', 'tags']


@dataclass
class TestCaseHistory(BaseModel):
    """测试用例历史记录模型（合并版本和变更日志）"""
    case_id: str
    version: int
    change_type: ChangeType
    snapshot: dict[str, Any]
    change_summary: str = ""
    changed_fields: list[str] = field(default_factory=list)
    changed_by: str = ""
    created_at: datetime | None = None
    id: int | None = None
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'change_type': ChangeType}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['snapshot', 'changed_fields']
    
    @classmethod
    def from_test_case(
        cls,
        test_case: TestCaseRecord,
        change_type: ChangeType,
        change_summary: str = "",
        changed_fields: list[str] | None = None,
        changed_by: str = ""
    ) -> Self:
        """从测试用例创建历史记录"""
        return cls(
            case_id=test_case.case_id,
            version=test_case.version,
            change_type=change_type,
            snapshot=test_case.to_dict(),
            change_summary=change_summary,
            changed_fields=changed_fields or [],
            changed_by=changed_by
        )


# =====================================================
# 测试执行模型
# =====================================================

@dataclass
class TestExecution(BaseModel):
    """测试执行批次模型"""
    execution_id: str
    name: str = ""
    description: str = ""
    execution_type: ExecutionType = ExecutionType.TEST
    trigger_type: TriggerType = TriggerType.MANUAL
    status: ExecutionStatus = ExecutionStatus.PENDING
    base_url: str = ""
    environment: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0
    skipped_cases: int = 0
    duration_ms: int = 0
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    id: int | None = None
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {
            'execution_type': ExecutionType,
            'trigger_type': TriggerType,
            'status': ExecutionStatus
        }
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['variables', 'headers']


@dataclass
class TestResultRecord(BaseModel):
    """测试结果记录模型"""
    case_id: str
    execution_id: str
    status: TestResultStatus
    result_type: ResultType = ResultType.TEST
    actual_status_code: int = 0
    actual_response_time_ms: float = 0
    actual_response_body: str = ""
    actual_headers: dict[str, str] = field(default_factory=dict)
    error_message: str = ""
    assertion_results: list[dict[str, Any]] = field(default_factory=list)
    ai_analysis: str = ""
    executed_at: datetime | None = None
    created_at: datetime | None = None
    id: int | None = None
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'status': TestResultStatus, 'result_type': ResultType}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['actual_headers', 'assertion_results']


# =====================================================
# 分析报告模型
# =====================================================

@dataclass
class AnalysisReport(BaseModel):
    """分析报告模型"""
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
        return {'report_type': ReportType}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['statistics', 'issues', 'recommendations', 'metadata']


# =====================================================
# 测试场景模型
# =====================================================

@dataclass
class TestScenario(BaseModel):
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
    steps: list["ScenarioStep"] = field(default_factory=list)
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['tags', 'variables', 'setup_hooks', 'teardown_hooks']
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.pop('steps', None)  # 步骤单独存储
        return result


@dataclass
class ScenarioStep(BaseModel):
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
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'step_type': StepType}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['headers', 'body', 'query_params', 'extractions', 'assertions', 'condition', 'loop_config']


@dataclass
class ScenarioExecution(BaseModel):
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
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'trigger_type': TriggerType, 'status': ScenarioStatus}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['variables']


@dataclass
class StepResult(BaseModel):
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
    
    @classmethod
    def _get_enum_fields_class(cls) -> dict[str, Type[Enum]]:
        return {'status': TestResultStatus}
    
    @classmethod
    def _get_json_fields_class(cls) -> list[str]:
        return ['request_headers', 'response_headers', 'extracted_variables', 'assertion_results']


# =====================================================
# 知识库模型
# 该文件内容使用AI生成，注意识别准确性
# =====================================================

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


# =====================================================
# 兼容性别名（保持向后兼容）
# =====================================================

# 已移除的模型，保留空类以防止导入错误
# 实际使用时应该迁移到新模型

class ScheduledTask:
    """已废弃：定时任务模型（功能已移除）"""
    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("ScheduledTask 已废弃，请使用外部调度系统")


class TestCaseVersion:
    """已废弃：测试用例版本模型（已合并到 TestCaseHistory）"""
    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("TestCaseVersion 已废弃，请使用 TestCaseHistory")


class TestCaseChangeLog:
    """已废弃：测试用例变更日志模型（已合并到 TestCaseHistory）"""
    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("TestCaseChangeLog 已废弃，请使用 TestCaseHistory")
