"""
CoT链式推理 - 数据模型

定义推理步骤、链配置、执行结果等核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class StepStatus(str, Enum):
    """步骤执行状态"""
    PENDING = "pending"         # 待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    SKIPPED = "skipped"         # 跳过


class ChainStatus(str, Enum):
    """推理链执行状态"""
    PENDING = "pending"         # 待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 全部完成
    PARTIAL = "partial"         # 部分完成
    FAILED = "failed"           # 失败
    ABORTED = "aborted"         # 中止


class ReasoningStepType(str, Enum):
    """推理步骤类型"""
    ANALYSIS = "analysis"       # 分析步骤
    EXTRACTION = "extraction"   # 信息提取
    INFERENCE = "inference"     # 推理判断
    VALIDATION = "validation"   # 验证确认
    SYNTHESIS = "synthesis"     # 综合总结
    ACTION = "action"           # 执行动作


@dataclass
class ThinkingStep:
    """
    推理步骤定义

    描述推理链中的一个步骤，包含输入输出定义、prompt模板等
    """
    step_id: str                            # 步骤唯一标识
    name: str                               # 步骤名称
    description: str                        # 步骤描述
    prompt_template: str                    # Prompt模板（支持变量替换）
    step_type: ReasoningStepType = ReasoningStepType.ANALYSIS # 步骤类型
    order: int = 0                          # 执行顺序
    depends_on: list[str] = field(default_factory=list)  # 依赖的前置步骤
    input_keys: list[str] = field(default_factory=list)  # 需要的输入键
    output_key: str = ""                    # 输出键（存储到上下文）
    required: bool = True                   # 是否必须执行
    timeout_seconds: int = 60               # 超时时间
    retry_count: int = 1                    # 重试次数
    condition: Callable[[dict], bool] | None = None  # 执行条件（可选）
    post_processor: Callable[[dict, str], Any] | None = None  # 后处理函数
    metadata: dict[str, Any] = field(default_factory=dict)

    def should_execute(self, context: dict[str, Any]) -> bool:
        """判断是否应该执行该步骤"""
        if self.condition is not None:
            return self.condition(context)
        return True

    def get_prompt(self, context: dict[str, Any]) -> str:
        """根据上下文生成实际prompt"""
        prompt = self.prompt_template
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in prompt:
                if isinstance(value, (dict, list)):
                    import json
                    value = json.dumps(value, ensure_ascii=False, indent=2)
                prompt = prompt.replace(placeholder, str(value))
        return prompt

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "step_type": self.step_type.value,
            "order": self.order,
            "depends_on": self.depends_on,
            "input_keys": self.input_keys,
            "output_key": self.output_key,
            "required": self.required,
        }


@dataclass
class StepResult:
    """
    步骤执行结果

    记录单个步骤的执行结果，包括输出、耗时、状态等
    """
    step_id: str                            # 步骤ID
    status: StepStatus                      # 执行状态
    output: Any = None                      # 步骤输出
    raw_response: str = ""                  # LLM原始响应
    thinking: str = ""                      # 思考过程（如果有）
    error_message: str = ""                 # 错误信息
    execution_time_ms: float = 0            # 执行时间（毫秒）
    token_usage: dict[str, int] = field(default_factory=dict)  # Token使用情况
    retry_count: int = 0                    # 实际重试次数
    started_at: datetime | None = None      # 开始时间
    completed_at: datetime | None = None    # 完成时间
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == StepStatus.COMPLETED

    @property
    def duration_seconds(self) -> float:
        return self.execution_time_ms / 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "output": self.output,
            "thinking": self.thinking,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "retry_count": self.retry_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ChainConfig:
    """
    推理链配置

    定义推理链的全局配置，如最大步骤数、超时、是否启用缓存等
    """
    chain_id: str                           # 链唯一标识
    name: str                               # 链名称
    description: str = ""                   # 链描述
    max_steps: int = 10                     # 最大步骤数
    total_timeout_seconds: int = 300        # 总超时时间
    stop_on_error: bool = False             # 遇错停止
    enable_cache: bool = True               # 启用缓存
    enable_thinking_extraction: bool = True # 提取思考过程
    parallel_independent_steps: bool = False # 并行执行独立步骤
    verbose: bool = False                   # 详细日志
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "max_steps": self.max_steps,
            "total_timeout_seconds": self.total_timeout_seconds,
            "stop_on_error": self.stop_on_error,
        }


@dataclass
class ChainResult:
    """
    推理链执行结果

    包含整个推理链的执行结果，所有步骤的结果，最终结论等
    """
    chain_id: str                           # 链ID
    status: ChainStatus                     # 执行状态
    steps: list[ThinkingStep]               # 步骤定义
    step_results: list[StepResult]          # 步骤执行结果
    final_output: Any = None                # 最终输出
    context: dict[str, Any] = field(default_factory=dict)  # 最终上下文
    total_execution_time_ms: float = 0      # 总执行时间
    total_token_usage: dict[str, int] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == ChainStatus.COMPLETED

    @property
    def completed_steps(self) -> int:
        return sum(1 for r in self.step_results if r.status == StepStatus.COMPLETED)

    @property
    def failed_steps(self) -> int:
        return sum(1 for r in self.step_results if r.status == StepStatus.FAILED)

    @property
    def thinking_trace(self) -> list[dict[str, Any]]:
        """获取思考追溯链"""
        trace = []
        for i, result in enumerate(self.step_results):
            if result.status in [StepStatus.COMPLETED, StepStatus.FAILED]:
                step = self.steps[i] if i < len(self.steps) else None
                trace.append({
                    "step": i + 1,
                    "name": step.name if step else result.step_id,
                    "status": result.status.value,
                    "thinking": result.thinking,
                    "output": result.output,
                    "duration_ms": result.execution_time_ms
                })
        return trace

    def get_step_output(self, step_id: str) -> Any:
        """获取指定步骤的输出"""
        for result in self.step_results:
            if result.step_id == step_id:
                return result.output
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "status": self.status.value,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "total_steps": len(self.steps),
            "final_output": self.final_output,
            "total_execution_time_ms": self.total_execution_time_ms,
            "thinking_trace": self.thinking_trace,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class ChainContext:
    """
    推理链上下文

    在步骤间传递的上下文信息
    """
    # 原始输入
    original_input: dict[str, Any] = field(default_factory=dict)

    # 步骤输出（按step_id存储）
    step_outputs: dict[str, Any] = field(default_factory=dict)

    # 累积的中间数据
    intermediate_data: dict[str, Any] = field(default_factory=dict)

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值（优先级：step_outputs > intermediate_data > original_input）"""
        if key in self.step_outputs:
            return self.step_outputs[key]
        if key in self.intermediate_data:
            return self.intermediate_data[key]
        if key in self.original_input:
            return self.original_input[key]
        return default

    def set(self, key: str, value: Any) -> None:
        """设置中间数据"""
        self.intermediate_data[key] = value

    def set_step_output(self, step_id: str, output: Any) -> None:
        """设置步骤输出"""
        self.step_outputs[step_id] = output

    def to_dict(self) -> dict[str, Any]:
        """合并所有数据为字典（用于prompt模板）"""
        result = dict(self.original_input)
        result.update(self.intermediate_data)
        result.update(self.step_outputs)
        return result

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return (
            key in self.step_outputs
            or key in self.intermediate_data
            or key in self.original_input
        )
