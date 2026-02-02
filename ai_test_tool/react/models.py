"""
ReAct数据模型

定义思考、行动、观察等核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class StopReason(str, Enum):
    """停止原因"""
    TASK_COMPLETED = "task_completed"       # 任务完成
    MAX_ITERATIONS = "max_iterations"       # 达到最大迭代次数
    MAX_TOKENS = "max_tokens"               # 达到token限制
    TIMEOUT = "timeout"                     # 超时
    ERROR = "error"                         # 发生错误
    NO_ACTION = "no_action"                 # LLM未返回有效action
    USER_ABORT = "user_abort"               # 用户中止


class ActionType(str, Enum):
    """行动类型"""
    TOOL_CALL = "tool_call"                 # 调用工具
    FINISH = "finish"                       # 结束任务
    ASK_USER = "ask_user"                   # 询问用户
    DELEGATE = "delegate"                   # 委托给其他agent


@dataclass
class Thought:
    """
    思考 - LLM的推理过程

    ReAct循环中的"Reasoning"部分
    """
    content: str                            # 思考内容
    step_number: int                        # 步骤编号
    timestamp: datetime = field(default_factory=datetime.now)

    # 可选：结构化的思考
    current_state: str = ""                 # 当前状态分析
    goal_progress: str = ""                 # 目标进度
    next_action_reason: str = ""            # 下一步行动的理由

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "step_number": self.step_number,
            "timestamp": self.timestamp.isoformat(),
            "current_state": self.current_state,
            "goal_progress": self.goal_progress,
            "next_action_reason": self.next_action_reason,
        }


@dataclass
class Action:
    """
    行动 - 要执行的操作

    ReAct循环中的"Acting"部分
    """
    action_type: ActionType                 # 行动类型
    tool_name: str = ""                     # 工具名称（如果是工具调用）
    tool_input: dict[str, Any] = field(default_factory=dict)  # 工具输入参数
    step_number: int = 0                    # 步骤编号
    timestamp: datetime = field(default_factory=datetime.now)

    # 结束时的最终答案
    final_answer: str = ""

    # 询问用户时的问题
    user_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "step_number": self.step_number,
            "timestamp": self.timestamp.isoformat(),
            "final_answer": self.final_answer,
            "user_question": self.user_question,
        }


@dataclass
class Observation:
    """
    观察 - 行动的结果

    ReAct循环中获取的反馈信息
    """
    content: str                            # 观察内容（工具返回值等）
    step_number: int                        # 步骤编号
    source: str = "tool"                    # 来源（tool/environment/user）
    is_error: bool = False                  # 是否为错误
    error_message: str = ""                 # 错误信息
    timestamp: datetime = field(default_factory=datetime.now)

    # 元数据
    execution_time_ms: float = 0            # 执行时间
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content[:500] if len(self.content) > 500 else self.content,
            "step_number": self.step_number,
            "source": self.source,
            "is_error": self.is_error,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class ReActStep:
    """
    ReAct单步 - 包含思考、行动、观察的完整步骤
    """
    step_number: int
    thought: Thought
    action: Action
    observation: Observation | None = None  # 如果action是finish则没有observation

    @property
    def is_terminal(self) -> bool:
        """是否为终止步骤"""
        return self.action.action_type == ActionType.FINISH

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "thought": self.thought.to_dict(),
            "action": self.action.to_dict(),
            "observation": self.observation.to_dict() if self.observation else None,
            "is_terminal": self.is_terminal,
        }


@dataclass
class Tool:
    """
    工具定义

    可被ReAct Agent调用的外部工具
    """
    name: str                               # 工具名称（唯一标识）
    description: str                        # 工具描述（用于LLM理解）
    func: Callable[..., Any]                # 工具函数
    parameters: dict[str, Any] = field(default_factory=dict)  # 参数schema
    required_params: list[str] = field(default_factory=list)  # 必需参数
    return_type: str = "string"             # 返回类型描述
    examples: list[dict[str, Any]] = field(default_factory=list)  # 使用示例
    is_async: bool = False                  # 是否异步
    timeout_seconds: int = 30               # 超时时间
    tags: list[str] = field(default_factory=list)  # 标签

    def to_prompt_description(self) -> str:
        """生成用于prompt的工具描述"""
        params_desc = ""
        if self.parameters:
            params_list = []
            for name, schema in self.parameters.items():
                required = "(必需)" if name in self.required_params else "(可选)"
                param_type = schema.get("type", "any")
                desc = schema.get("description", "")
                params_list.append(f"    - {name} ({param_type}) {required}: {desc}")
            params_desc = "\n".join(params_list)

        return f"""- {self.name}: {self.description}
  参数:
{params_desc if params_desc else "    无参数"}
  返回: {self.return_type}"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "return_type": self.return_type,
            "is_async": self.is_async,
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    output: Any = None
    error: str = ""
    execution_time_ms: float = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_observation(self, step_number: int) -> Observation:
        """转换为Observation"""
        if self.success:
            content = str(self.output) if self.output is not None else "执行成功（无输出）"
        else:
            content = f"错误: {self.error}"

        return Observation(
            content=content,
            step_number=step_number,
            source=f"tool:{self.tool_name}",
            is_error=not self.success,
            error_message=self.error if not self.success else "",
            execution_time_ms=self.execution_time_ms,
            metadata=self.metadata
        )


@dataclass
class ReActConfig:
    """
    ReAct配置
    """
    # 迭代限制
    max_iterations: int = 10                # 最大迭代次数
    max_tokens: int = 8000                  # 最大token数（用于控制历史长度）

    # 超时
    total_timeout_seconds: int = 300        # 总超时
    step_timeout_seconds: int = 60          # 单步超时

    # 行为控制
    allow_ask_user: bool = True             # 允许询问用户
    stop_on_tool_error: bool = False        # 工具错误时停止
    verbose: bool = False                   # 详细日志

    # 历史管理
    keep_full_history: bool = True          # 保留完整历史
    compress_observations: bool = True      # 压缩长观察结果
    max_observation_length: int = 2000      # 观察结果最大长度

    # 重试
    llm_retry_count: int = 2                # LLM调用重试次数
    tool_retry_count: int = 1               # 工具调用重试次数

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "max_tokens": self.max_tokens,
            "total_timeout_seconds": self.total_timeout_seconds,
            "step_timeout_seconds": self.step_timeout_seconds,
            "allow_ask_user": self.allow_ask_user,
            "stop_on_tool_error": self.stop_on_tool_error,
        }


@dataclass
class ReActResult:
    """
    ReAct执行结果

    包含完整的推理轨迹和最终答案
    """
    task: str                               # 原始任务
    final_answer: str = ""                  # 最终答案
    stop_reason: StopReason = StopReason.TASK_COMPLETED
    steps: list[ReActStep] = field(default_factory=list)  # 所有步骤

    # 统计
    total_iterations: int = 0               # 总迭代次数
    total_execution_time_ms: float = 0      # 总执行时间
    total_tool_calls: int = 0               # 工具调用次数
    total_tokens_used: int = 0              # 使用的token数（估算）

    # 时间
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # 错误信息
    error_message: str = ""

    @property
    def is_success(self) -> bool:
        """是否成功完成"""
        return self.stop_reason == StopReason.TASK_COMPLETED

    @property
    def trajectory(self) -> list[dict[str, Any]]:
        """
        获取推理轨迹

        返回格式化的思考-行动-观察序列
        """
        trajectory = []
        for step in self.steps:
            trajectory.append({
                "step": step.step_number,
                "thought": step.thought.content,
                "action": {
                    "type": step.action.action_type.value,
                    "tool": step.action.tool_name,
                    "input": step.action.tool_input,
                } if step.action.action_type == ActionType.TOOL_CALL else {
                    "type": step.action.action_type.value,
                    "final_answer": step.action.final_answer,
                },
                "observation": step.observation.content if step.observation else None,
            })
        return trajectory

    @property
    def tool_calls_summary(self) -> list[dict[str, Any]]:
        """获取工具调用摘要"""
        calls = []
        for step in self.steps:
            if step.action.action_type == ActionType.TOOL_CALL:
                calls.append({
                    "step": step.step_number,
                    "tool": step.action.tool_name,
                    "input": step.action.tool_input,
                    "success": not step.observation.is_error if step.observation else None,
                })
        return calls

    def get_thoughts(self) -> list[str]:
        """获取所有思考内容"""
        return [step.thought.content for step in self.steps]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "final_answer": self.final_answer,
            "stop_reason": self.stop_reason.value,
            "is_success": self.is_success,
            "total_iterations": self.total_iterations,
            "total_execution_time_ms": self.total_execution_time_ms,
            "total_tool_calls": self.total_tool_calls,
            "trajectory": self.trajectory,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class AgentContext:
    """
    Agent上下文

    在ReAct循环中传递的上下文信息
    """
    # 任务信息
    task: str
    task_context: dict[str, Any] = field(default_factory=dict)

    # 数据
    log_content: str = ""
    requests: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    # 历史
    steps: list[ReActStep] = field(default_factory=list)

    # 工作记忆（用于跨步骤记录信息）
    working_memory: dict[str, Any] = field(default_factory=dict)

    # 配置
    config: ReActConfig = field(default_factory=ReActConfig)

    def add_step(self, step: ReActStep) -> None:
        """添加步骤"""
        self.steps.append(step)

    def get_history_prompt(self) -> str:
        """生成历史记录prompt"""
        if not self.steps:
            return ""

        lines = []
        for step in self.steps:
            lines.append(f"[Step {step.step_number}]")
            lines.append(f"Thought: {step.thought.content}")
            lines.append(f"Action: {step.action.tool_name}({step.action.tool_input})")
            if step.observation:
                obs_content = step.observation.content
                if self.config.compress_observations and len(obs_content) > self.config.max_observation_length:
                    obs_content = obs_content[:self.config.max_observation_length] + "...(truncated)"
                lines.append(f"Observation: {obs_content}")
            lines.append("")

        return "\n".join(lines)

    def remember(self, key: str, value: Any) -> None:
        """在工作记忆中存储信息"""
        self.working_memory[key] = value

    def recall(self, key: str, default: Any = None) -> Any:
        """从工作记忆中读取信息"""
        return self.working_memory.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "task_context": self.task_context,
            "step_count": len(self.steps),
            "working_memory_keys": list(self.working_memory.keys()),
        }
