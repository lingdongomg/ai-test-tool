"""
测试场景相关模型
该文件内容使用AI生成，注意识别准确性
"""

from typing import Any, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import BaseModel, ScenarioStepType, ScenarioStatus, TriggerType, TestResultStatus


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
    step_type: ScenarioStepType = ScenarioStepType.REQUEST
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
        return {'step_type': ScenarioStepType}

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
