"""
CoT链式推理引擎

核心推理引擎，负责执行推理链、管理步骤间依赖、处理中间结果
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Any

from .models import (
    ThinkingStep,
    StepResult,
    ChainConfig,
    ChainResult,
    ChainContext,
    StepStatus,
    ChainStatus,
)
from ..llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class ChainOfThoughtEngine:
    """
    CoT链式推理引擎

    功能：
    1. 按顺序执行推理步骤
    2. 管理步骤间的依赖关系
    3. 处理和传递中间结果
    4. 支持条件执行和跳过
    5. 提取思考过程（<think>标签）
    6. 支持重试和错误处理
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        config: ChainConfig | None = None
    ):
        """
        初始化推理引擎

        Args:
            llm_provider: LLM提供者
            config: 链配置（如果不提供则使用默认配置）
        """
        self._llm_provider = llm_provider
        self.config = config or ChainConfig(
            chain_id="default",
            name="Default Chain"
        )

        # 步骤注册表
        self._steps: list[ThinkingStep] = []

        # 缓存
        self._cache: dict[str, Any] = {}

    @property
    def llm_provider(self) -> LLMProvider:
        """懒加载LLM提供者"""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    def add_step(self, step: ThinkingStep) -> "ChainOfThoughtEngine":
        """
        添加推理步骤

        Args:
            step: 推理步骤

        Returns:
            self（支持链式调用）
        """
        # 自动设置顺序
        if step.order == 0:
            step.order = len(self._steps) + 1

        self._steps.append(step)
        # 按顺序排序
        self._steps.sort(key=lambda s: s.order)
        return self

    def add_steps(self, steps: list[ThinkingStep]) -> "ChainOfThoughtEngine":
        """批量添加步骤"""
        for step in steps:
            self.add_step(step)
        return self

    def clear_steps(self) -> None:
        """清除所有步骤"""
        self._steps.clear()

    def execute(
        self,
        input_data: dict[str, Any],
        output_key: str | None = None
    ) -> ChainResult:
        """
        执行推理链

        Args:
            input_data: 输入数据
            output_key: 指定最终输出的键（默认使用最后一个步骤的输出）

        Returns:
            推理链执行结果
        """
        if not self._steps:
            return ChainResult(
                chain_id=self.config.chain_id,
                status=ChainStatus.FAILED,
                steps=[],
                step_results=[],
                error_message="没有定义推理步骤"
            )

        # 初始化上下文
        context = ChainContext(original_input=input_data)
        step_results: list[StepResult] = []

        # 记录开始时间
        start_time = time.time()
        started_at = datetime.now()

        # 检查超时
        total_timeout = self.config.total_timeout_seconds

        logger.info(f"开始执行推理链: {self.config.name} ({len(self._steps)} 步)")

        try:
            for i, step in enumerate(self._steps):
                # 检查总超时
                elapsed = time.time() - start_time
                if elapsed > total_timeout:
                    logger.warning(f"推理链超时: {elapsed:.1f}s > {total_timeout}s")
                    step_results.append(StepResult(
                        step_id=step.step_id,
                        status=StepStatus.SKIPPED,
                        error_message="总超时"
                    ))
                    continue

                # 检查依赖
                if not self._check_dependencies(step, step_results):
                    logger.warning(f"步骤 {step.name} 依赖未满足，跳过")
                    step_results.append(StepResult(
                        step_id=step.step_id,
                        status=StepStatus.SKIPPED,
                        error_message="依赖步骤未完成"
                    ))
                    continue

                # 检查执行条件
                if not step.should_execute(context.to_dict()):
                    logger.info(f"步骤 {step.name} 条件不满足，跳过")
                    step_results.append(StepResult(
                        step_id=step.step_id,
                        status=StepStatus.SKIPPED,
                        error_message="执行条件不满足"
                    ))
                    continue

                # 执行步骤
                logger.info(f"执行步骤 {i+1}/{len(self._steps)}: {step.name}")
                result = self._execute_step(step, context)
                step_results.append(result)

                # 更新上下文
                if result.is_success and result.output is not None:
                    if step.output_key:
                        context.set_step_output(step.output_key, result.output)
                    context.set_step_output(step.step_id, result.output)

                # 检查是否需要停止
                if result.status == StepStatus.FAILED and self.config.stop_on_error:
                    logger.error(f"步骤 {step.name} 失败，停止执行")
                    break

        except Exception as e:
            logger.error(f"推理链执行异常: {e}")
            return ChainResult(
                chain_id=self.config.chain_id,
                status=ChainStatus.FAILED,
                steps=self._steps,
                step_results=step_results,
                context=context.to_dict(),
                error_message=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
                total_execution_time_ms=(time.time() - start_time) * 1000
            )

        # 计算最终状态
        completed = sum(1 for r in step_results if r.status == StepStatus.COMPLETED)
        failed = sum(1 for r in step_results if r.status == StepStatus.FAILED)

        if failed == 0 and completed == len(self._steps):
            status = ChainStatus.COMPLETED
        elif completed > 0:
            status = ChainStatus.PARTIAL
        else:
            status = ChainStatus.FAILED

        # 获取最终输出
        final_output = None
        if output_key and output_key in context:
            final_output = context.get(output_key)
        elif step_results and step_results[-1].is_success:
            final_output = step_results[-1].output

        # 汇总token使用
        total_tokens: dict[str, int] = {}
        for result in step_results:
            for key, value in result.token_usage.items():
                total_tokens[key] = total_tokens.get(key, 0) + value

        completed_at = datetime.now()

        return ChainResult(
            chain_id=self.config.chain_id,
            status=status,
            steps=self._steps,
            step_results=step_results,
            final_output=final_output,
            context=context.to_dict(),
            total_execution_time_ms=(time.time() - start_time) * 1000,
            total_token_usage=total_tokens,
            started_at=started_at,
            completed_at=completed_at
        )

    async def execute_async(
        self,
        input_data: dict[str, Any],
        output_key: str | None = None
    ) -> ChainResult:
        """异步执行推理链"""
        # 当前实现中异步版本与同步版本相同
        # 未来可以优化为真正的异步LLM调用
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.execute,
            input_data,
            output_key
        )

    def _execute_step(
        self,
        step: ThinkingStep,
        context: ChainContext
    ) -> StepResult:
        """执行单个步骤"""
        step_start = time.time()
        started_at = datetime.now()

        # 尝试从缓存获取
        cache_key = self._get_cache_key(step, context)
        if self.config.enable_cache and cache_key in self._cache:
            logger.debug(f"步骤 {step.name} 命中缓存")
            cached = self._cache[cache_key]
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                output=cached["output"],
                raw_response=cached.get("raw_response", ""),
                thinking=cached.get("thinking", ""),
                execution_time_ms=0,
                started_at=started_at,
                completed_at=datetime.now(),
                metadata={"from_cache": True}
            )

        # 生成prompt
        prompt = step.get_prompt(context.to_dict())

        # 重试逻辑
        last_error = ""
        for attempt in range(step.retry_count):
            try:
                # 调用LLM
                raw_response = self.llm_provider.generate(prompt)

                # 提取思考过程
                thinking = ""
                clean_response = raw_response
                if self.config.enable_thinking_extraction:
                    thinking, clean_response = self._extract_thinking(raw_response)

                # 解析输出
                output = self._parse_response(clean_response)

                # 后处理
                if step.post_processor:
                    output = step.post_processor(context.to_dict(), output)

                # 缓存结果
                if self.config.enable_cache:
                    self._cache[cache_key] = {
                        "output": output,
                        "raw_response": raw_response,
                        "thinking": thinking
                    }

                return StepResult(
                    step_id=step.step_id,
                    status=StepStatus.COMPLETED,
                    output=output,
                    raw_response=raw_response,
                    thinking=thinking,
                    execution_time_ms=(time.time() - step_start) * 1000,
                    retry_count=attempt,
                    started_at=started_at,
                    completed_at=datetime.now()
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(f"步骤 {step.name} 第 {attempt + 1} 次尝试失败: {e}")
                if attempt < step.retry_count - 1:
                    time.sleep(1)  # 重试前等待

        # 所有重试都失败
        return StepResult(
            step_id=step.step_id,
            status=StepStatus.FAILED,
            error_message=last_error,
            execution_time_ms=(time.time() - step_start) * 1000,
            retry_count=step.retry_count,
            started_at=started_at,
            completed_at=datetime.now()
        )

    def _check_dependencies(
        self,
        step: ThinkingStep,
        completed_results: list[StepResult]
    ) -> bool:
        """检查步骤依赖是否满足"""
        if not step.depends_on:
            return True

        completed_ids = {
            r.step_id
            for r in completed_results
            if r.status == StepStatus.COMPLETED
        }

        return all(dep in completed_ids for dep in step.depends_on)

    def _extract_thinking(self, response: str) -> tuple[str, str]:
        """
        提取思考过程

        支持多种格式：
        - <think>...</think>
        - <thinking>...</thinking>
        - **思考过程**：...

        Returns:
            (thinking, clean_response)
        """
        thinking = ""
        clean_response = response

        # 提取 <think> 标签
        think_match = re.search(r"<think(?:ing)?>([\s\S]*?)</think(?:ing)?>", response, re.IGNORECASE)
        if think_match:
            thinking = think_match.group(1).strip()
            clean_response = re.sub(r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>\s*", "", response, flags=re.IGNORECASE).strip()

        # 提取 **思考过程** 格式
        if not thinking:
            thought_match = re.search(r"\*\*(?:思考过程|Thinking|Analysis)\*\*[:：]?\s*([\s\S]*?)(?=\n\n|\*\*|```|$)", response, re.IGNORECASE)
            if thought_match:
                thinking = thought_match.group(1).strip()

        return thinking, clean_response

    def _parse_response(self, response: str) -> Any:
        """解析LLM响应"""
        response = response.strip()

        # 尝试解析JSON
        # 1. 直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 2. 从代码块提取
        code_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. 从花括号提取
        brace_start = response.find("{")
        brace_end = response.rfind("}") + 1
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(response[brace_start:brace_end])
            except json.JSONDecodeError:
                pass

        # 4. 从方括号提取
        bracket_start = response.find("[")
        bracket_end = response.rfind("]") + 1
        if bracket_start >= 0 and bracket_end > bracket_start:
            try:
                return json.loads(response[bracket_start:bracket_end])
            except json.JSONDecodeError:
                pass

        # 解析失败，返回原始文本
        return response

    def _get_cache_key(self, step: ThinkingStep, context: ChainContext) -> str:
        """生成缓存键"""
        import hashlib
        prompt = step.get_prompt(context.to_dict())
        return hashlib.md5(f"{step.step_id}:{prompt}".encode()).hexdigest()

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()

    @property
    def steps(self) -> list[ThinkingStep]:
        """获取所有步骤"""
        return list(self._steps)

    @property
    def step_count(self) -> int:
        """步骤数量"""
        return len(self._steps)


def create_engine(
    chain_id: str = "default",
    name: str = "Default Chain",
    llm_provider: LLMProvider | None = None,
    **config_kwargs: Any
) -> ChainOfThoughtEngine:
    """
    创建推理引擎的便捷函数

    Args:
        chain_id: 链ID
        name: 链名称
        llm_provider: LLM提供者
        **config_kwargs: ChainConfig的其他参数

    Returns:
        ChainOfThoughtEngine实例
    """
    config = ChainConfig(
        chain_id=chain_id,
        name=name,
        **config_kwargs
    )
    return ChainOfThoughtEngine(
        llm_provider=llm_provider,
        config=config
    )
