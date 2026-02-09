"""
测试相关模型
该文件内容使用AI生成，注意识别准确性
"""

from typing import Any, Self, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import (
    BaseModel, TestCaseCategory, TestCasePriority, TestResultStatus,
    ResultType, ExecutionStatus, ExecutionType, TriggerType, ChangeType
)


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
