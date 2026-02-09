"""
数据模型基类和枚举定义
该文件内容使用AI生成，注意识别准确性
"""

import json
from typing import Any, TypeVar, Type
from dataclasses import asdict, fields
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


class ScenarioStepType(Enum):
    """场景步骤类型"""
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
    PROJECT_CONFIG = "project_config"
    BUSINESS_RULE = "business_rule"
    MODULE_CONTEXT = "module_context"
    TEST_EXPERIENCE = "test_experience"


class KnowledgeStatus(Enum):
    """知识状态"""
    ACTIVE = "active"
    PENDING = "pending"
    ARCHIVED = "archived"


class KnowledgeSource(Enum):
    """知识来源"""
    MANUAL = "manual"
    LOG_LEARNING = "log_learning"
    TEST_LEARNING = "test_learning"


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
