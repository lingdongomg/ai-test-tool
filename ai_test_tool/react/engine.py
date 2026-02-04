"""
ReAct推理引擎

实现思考-行动-观察的循环推理流程
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Any

from .models import (
    Thought,
    Action,
    Observation,
    ReActStep,
    ReActResult,
    ReActConfig,
    AgentContext,
    ActionType,
    StopReason,
    Tool,
)
from .tools import ToolRegistry, get_tool_registry
from ..llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


# ReAct Prompt模板
REACT_SYSTEM_PROMPT = """你是一个智能分析助手，使用ReAct（Reasoning + Acting）方法来解决问题。

## 工作流程
你需要交替进行"思考"和"行动"来完成任务：
1. **Thought**: 分析当前状态，决定下一步做什么
2. **Action**: 选择并执行一个工具，或者给出最终答案
3. **Observation**: 观察工具返回的结果
4. 重复以上步骤直到任务完成

## 输出格式
每一步必须严格按照以下格式输出：

```
Thought: [你的思考过程，分析当前情况和下一步计划]
Action: [工具名称]
Action Input: [工具参数，JSON格式]
```

当你认为已经收集了足够的信息可以回答问题时，使用以下格式：

```
Thought: [总结分析过程和得出的结论]
Action: finish
Action Input: {"answer": "你的最终答案"}
```

## 重要规则
1. 每次只执行一个Action
2. Action Input必须是有效的JSON格式
3. 思考时要考虑已有的信息和还需要的信息
4. 如果工具返回错误，分析原因并尝试其他方法
5. 避免重复执行相同的操作
6. 最终答案要结构化、有条理

{tools_prompt}
"""

REACT_USER_PROMPT = """## 任务
{task}

## 可用数据
- 日志内容: {has_log_content}
- 请求数据: {request_count} 条记录

{history}

请开始分析，按照 Thought -> Action -> Action Input 的格式输出。"""


class ReActEngine:
    """
    ReAct推理引擎

    核心功能：
    1. 管理思考-行动-观察循环
    2. 解析LLM输出，提取action
    3. 执行工具调用
    4. 维护对话历史
    5. 控制循环终止条件
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        tool_registry: ToolRegistry | None = None,
        config: ReActConfig | None = None
    ):
        """
        初始化引擎

        Args:
            llm_provider: LLM提供者
            tool_registry: 工具注册表
            config: 配置
        """
        self._llm_provider = llm_provider
        self._tool_registry = tool_registry
        self.config = config or ReActConfig()

        # 额外注册的工具
        self._extra_tools: list[Tool] = []

    @property
    def llm_provider(self) -> LLMProvider:
        """懒加载LLM提供者"""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    @property
    def tool_registry(self) -> ToolRegistry:
        """懒加载工具注册表"""
        if self._tool_registry is None:
            self._tool_registry = get_tool_registry()
        return self._tool_registry

    def register_tool(self, tool: Tool) -> "ReActEngine":
        """
        注册额外工具

        Args:
            tool: 工具定义

        Returns:
            self（支持链式调用）
        """
        self._extra_tools.append(tool)
        self.tool_registry.register(tool)
        return self

    def run(
        self,
        task: str,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        **kwargs: Any
    ) -> ReActResult:
        """
        执行ReAct循环

        Args:
            task: 任务描述
            log_content: 日志内容
            requests: 请求数据
            **kwargs: 其他上下文数据

        Returns:
            ReAct执行结果
        """
        start_time = time.time()
        started_at = datetime.now()

        # 初始化上下文
        context = AgentContext(
            task=task,
            task_context=kwargs,
            log_content=log_content,
            requests=requests or [],
            config=self.config
        )

        # 初始化结果
        result = ReActResult(
            task=task,
            started_at=started_at
        )

        logger.info(f"开始ReAct任务: {task[:100]}...")

        try:
            iteration = 0
            while iteration < self.config.max_iterations:
                iteration += 1
                logger.debug(f"ReAct 迭代 {iteration}/{self.config.max_iterations}")

                # 检查超时
                elapsed = time.time() - start_time
                if elapsed > self.config.total_timeout_seconds:
                    logger.warning(f"ReAct超时: {elapsed:.1f}s")
                    result.stop_reason = StopReason.TIMEOUT
                    break

                # 执行一步
                step = self._execute_step(context, iteration)
                context.add_step(step)
                result.steps.append(step)

                # 检查是否结束
                if step.is_terminal:
                    result.final_answer = step.action.final_answer
                    result.stop_reason = StopReason.TASK_COMPLETED
                    logger.info("ReAct任务完成")
                    break

                # 更新工具调用计数
                if step.action.action_type == ActionType.TOOL_CALL:
                    result.total_tool_calls += 1

            else:
                # 达到最大迭代
                result.stop_reason = StopReason.MAX_ITERATIONS
                logger.warning(f"达到最大迭代次数: {self.config.max_iterations}")

        except Exception as e:
            logger.error(f"ReAct执行异常: {e}")
            result.stop_reason = StopReason.ERROR
            result.error_message = str(e)

        # 完成统计
        result.completed_at = datetime.now()
        result.total_iterations = len(result.steps)
        result.total_execution_time_ms = (time.time() - start_time) * 1000

        return result

    def _execute_step(
        self,
        context: AgentContext,
        step_number: int
    ) -> ReActStep:
        """执行单步ReAct"""
        # 1. 生成prompt并调用LLM获取思考和行动
        prompt = self._build_prompt(context)
        llm_response = self._call_llm(prompt)

        # 2. 解析LLM输出
        thought, action = self._parse_response(llm_response, step_number)

        # 3. 如果是结束动作，直接返回
        if action.action_type == ActionType.FINISH:
            return ReActStep(
                step_number=step_number,
                thought=thought,
                action=action,
                observation=None
            )

        # 4. 执行工具调用
        observation = self._execute_action(action, context, step_number)

        return ReActStep(
            step_number=step_number,
            thought=thought,
            action=action,
            observation=observation
        )

    def _build_prompt(self, context: AgentContext) -> str:
        """构建LLM prompt"""
        # 获取工具描述
        tools_prompt = self.tool_registry.get_tools_prompt()

        system_prompt = REACT_SYSTEM_PROMPT.format(tools_prompt=tools_prompt)

        # 构建用户prompt
        history = context.get_history_prompt()

        user_prompt = REACT_USER_PROMPT.format(
            task=context.task,
            has_log_content="有" if context.log_content else "无",
            request_count=len(context.requests),
            history=f"## 历史记录\n{history}" if history else ""
        )

        return f"{system_prompt}\n\n{user_prompt}"

    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        for attempt in range(self.config.llm_retry_count):
            try:
                response = self.llm_provider.generate(prompt)
                return response
            except Exception as e:
                logger.warning(f"LLM调用失败 (尝试 {attempt + 1}): {e}")
                if attempt == self.config.llm_retry_count - 1:
                    raise

        return ""

    def _parse_response(
        self,
        response: str,
        step_number: int
    ) -> tuple[Thought, Action]:
        """
        解析LLM响应

        提取Thought、Action、Action Input
        """
        # 提取Thought
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\nAction:|\Z)",
            response,
            re.DOTALL | re.IGNORECASE
        )
        thought_content = thought_match.group(1).strip() if thought_match else response[:500]

        thought = Thought(
            content=thought_content,
            step_number=step_number
        )

        # 提取Action
        action_match = re.search(
            r"Action:\s*(\w+)",
            response,
            re.IGNORECASE
        )
        action_name = action_match.group(1).strip() if action_match else ""

        # 提取Action Input
        action_input: dict[str, Any] = {}
        input_match = re.search(
            r"Action Input:\s*({.+?}|\{[\s\S]+?\})",
            response,
            re.DOTALL | re.IGNORECASE
        )
        if input_match:
            try:
                action_input = json.loads(input_match.group(1).strip())
            except json.JSONDecodeError:
                # 尝试修复常见的JSON问题
                raw_input = input_match.group(1).strip()
                # 替换单引号为双引号
                raw_input = raw_input.replace("'", '"')
                try:
                    action_input = json.loads(raw_input)
                except json.JSONDecodeError:
                    logger.warning(f"无法解析Action Input: {raw_input[:200]}")

        # 判断action类型
        if action_name.lower() == "finish":
            action = Action(
                action_type=ActionType.FINISH,
                step_number=step_number,
                final_answer=action_input.get("answer", str(action_input))
            )
        elif action_name:
            action = Action(
                action_type=ActionType.TOOL_CALL,
                tool_name=action_name,
                tool_input=action_input,
                step_number=step_number
            )
        else:
            # 无法解析action，尝试从response中提取有用信息
            action = Action(
                action_type=ActionType.FINISH,
                step_number=step_number,
                final_answer=f"分析结果: {thought_content}"
            )

        return thought, action

    def _execute_action(
        self,
        action: Action,
        context: AgentContext,
        step_number: int
    ) -> Observation:
        """执行action并返回observation"""
        if action.action_type != ActionType.TOOL_CALL:
            return Observation(
                content="无需执行工具",
                step_number=step_number,
                source="system"
            )

        start_time = time.time()

        # 准备工具参数（注入上下文数据）
        tool_input = dict(action.tool_input)
        tool_input["_context"] = {
            "log_content": context.log_content,
            "requests": context.requests,
            "task": context.task,
            "working_memory": context.working_memory,
        }

        # 某些工具需要直接传入数据
        if "log_content" not in tool_input and context.log_content:
            tool_input["log_content"] = context.log_content
        if "requests" not in tool_input and context.requests:
            tool_input["requests"] = context.requests

        # 执行工具
        result = self.tool_registry.execute(action.tool_name, **tool_input)

        # 转换为Observation
        observation = result.to_observation(step_number)
        observation.execution_time_ms = (time.time() - start_time) * 1000

        # 压缩长结果
        if self.config.compress_observations:
            if len(observation.content) > self.config.max_observation_length:
                observation.content = (
                    observation.content[:self.config.max_observation_length] +
                    f"\n...(结果已截断，原长度: {len(observation.content)})"
                )

        return observation


def create_react_engine(
    config: ReActConfig | None = None,
    llm_provider: LLMProvider | None = None,
    **config_kwargs: Any
) -> ReActEngine:
    """
    创建ReAct引擎的便捷函数

    Args:
        config: 配置对象
        llm_provider: LLM提供者
        **config_kwargs: 配置参数

    Returns:
        ReActEngine实例
    """
    if config is None:
        config = ReActConfig(**config_kwargs)

    return ReActEngine(
        llm_provider=llm_provider,
        config=config
    )
