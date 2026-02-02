"""
智能路由器

核心路由分发器，协调场景识别和策略选择
"""

import asyncio
import logging
import time
from typing import Any

from .models import (
    AnalysisScenario,
    AnalysisStrategy,
    AnalysisContext,
    AnalysisResult,
    RouteDecision,
    ScenarioType,
    StrategyPriority,
)
from .registry import StrategyRegistry, get_registry
from .detector import ScenarioDetector

logger = logging.getLogger(__name__)


class IntelligentRouter:
    """
    智能路由分发器

    核心功能：
    1. 接收日志/请求数据
    2. 调用场景识别器检测场景
    3. 从策略注册表选择匹配策略
    4. 执行策略并返回结果
    5. 支持策略链和回退机制
    """

    def __init__(
        self,
        registry: StrategyRegistry | None = None,
        detector: ScenarioDetector | None = None,
        llm_provider: Any = None,
        max_strategies: int = 3,
        enable_fallback: bool = True,
        default_timeout: int = 60
    ):
        """
        初始化智能路由器

        Args:
            registry: 策略注册表（默认使用全局实例）
            detector: 场景识别器
            llm_provider: LLM提供者
            max_strategies: 最多执行的策略数量
            enable_fallback: 是否启用回退策略
            default_timeout: 默认超时时间（秒）
        """
        self.registry = registry or get_registry()
        self.detector = detector or ScenarioDetector(llm_provider=llm_provider)
        self.llm_provider = llm_provider
        self.max_strategies = max_strategies
        self.enable_fallback = enable_fallback
        self.default_timeout = default_timeout

        # 统计信息
        self._route_count = 0
        self._success_count = 0
        self._fallback_count = 0

    def route(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        metrics: dict[str, float] | None = None,
        user_hint: str = "",
        options: dict[str, Any] | None = None
    ) -> RouteDecision:
        """
        路由决策

        根据输入数据识别场景并选择策略

        Args:
            log_content: 日志内容
            requests: 解析后的请求列表
            metrics: 统计指标
            user_hint: 用户提示
            options: 额外选项

        Returns:
            路由决策结果
        """
        self._route_count += 1
        options = options or {}

        # 1. 场景识别
        scenarios = self.detector.detect(
            log_content=log_content,
            requests=requests,
            metrics=metrics,
            user_hint=user_hint
        )

        if not scenarios:
            logger.warning("未识别到任何分析场景")
            return RouteDecision(
                scenarios=[],
                selected_strategies=[],
                reasoning="未能识别分析场景，请提供更多上下文信息"
            )

        # 2. 策略选择
        selected_strategies: list[AnalysisStrategy] = []
        reasoning_parts: list[str] = []

        for scenario in scenarios[:self.max_strategies]:
            strategies = self.registry.find_by_scenario(scenario)

            if strategies:
                # 选择优先级最高的策略
                best_strategy = strategies[0]
                if best_strategy not in selected_strategies:
                    selected_strategies.append(best_strategy)
                    reasoning_parts.append(
                        f"场景[{scenario.scenario_type.value}](置信度{scenario.confidence:.0%}) "
                        f"→ 策略[{best_strategy.name}]"
                    )
            else:
                reasoning_parts.append(
                    f"场景[{scenario.scenario_type.value}] 无匹配策略"
                )

        # 3. 回退策略
        fallback_strategy = None
        if self.enable_fallback and not selected_strategies:
            fallback_strategy = self._get_fallback_strategy(scenarios)
            if fallback_strategy:
                selected_strategies.append(fallback_strategy)
                reasoning_parts.append(f"使用回退策略: {fallback_strategy.name}")
                self._fallback_count += 1

        # 4. 构建决策结果
        decision = RouteDecision(
            scenarios=scenarios,
            selected_strategies=selected_strategies,
            fallback_strategy=fallback_strategy,
            reasoning="; ".join(reasoning_parts)
        )

        logger.info(
            f"路由决策: {len(scenarios)} 个场景, {len(selected_strategies)} 个策略 - "
            f"{decision.reasoning[:100]}"
        )

        return decision

    def execute(
        self,
        decision: RouteDecision,
        context: AnalysisContext
    ) -> list[AnalysisResult]:
        """
        执行路由决策

        Args:
            decision: 路由决策
            context: 分析上下文

        Returns:
            执行结果列表
        """
        if not decision.has_valid_route:
            return [AnalysisResult(
                success=False,
                strategy_id="none",
                scenario_type=ScenarioType.CUSTOM,
                error_message="无有效策略可执行"
            )]

        results: list[AnalysisResult] = []

        for strategy in decision.selected_strategies:
            result = self._execute_strategy(strategy, context)
            results.append(result)

            # 如果策略执行成功，可以选择跳过后续策略
            if result.success and not context.get_option("execute_all", False):
                break

        if results:
            self._success_count += sum(1 for r in results if r.success)

        return results

    async def execute_async(
        self,
        decision: RouteDecision,
        context: AnalysisContext
    ) -> list[AnalysisResult]:
        """
        异步执行路由决策

        Args:
            decision: 路由决策
            context: 分析上下文

        Returns:
            执行结果列表
        """
        if not decision.has_valid_route:
            return [AnalysisResult(
                success=False,
                strategy_id="none",
                scenario_type=ScenarioType.CUSTOM,
                error_message="无有效策略可执行"
            )]

        # 分离同步和异步策略
        sync_strategies = [s for s in decision.selected_strategies if not s.is_async]
        async_strategies = [s for s in decision.selected_strategies if s.is_async]

        results: list[AnalysisResult] = []

        # 执行同步策略
        for strategy in sync_strategies:
            result = self._execute_strategy(strategy, context)
            results.append(result)

        # 并发执行异步策略
        if async_strategies:
            async_tasks = [
                self._execute_strategy_async(strategy, context)
                for strategy in async_strategies
            ]
            async_results = await asyncio.gather(*async_tasks, return_exceptions=True)

            for i, result in enumerate(async_results):
                if isinstance(result, Exception):
                    results.append(AnalysisResult(
                        success=False,
                        strategy_id=async_strategies[i].strategy_id,
                        scenario_type=async_strategies[i].scenario_types[0],
                        error_message=str(result)
                    ))
                else:
                    results.append(result)

        return results

    def route_and_execute(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        metrics: dict[str, float] | None = None,
        user_hint: str = "",
        options: dict[str, Any] | None = None,
        task_id: str = ""
    ) -> tuple[RouteDecision, list[AnalysisResult]]:
        """
        一站式路由和执行

        Args:
            log_content: 日志内容
            requests: 请求列表
            metrics: 指标
            user_hint: 用户提示
            options: 选项
            task_id: 任务ID

        Returns:
            (路由决策, 执行结果列表)
        """
        # 1. 路由决策
        decision = self.route(
            log_content=log_content,
            requests=requests,
            metrics=metrics,
            user_hint=user_hint,
            options=options
        )

        # 2. 构建上下文
        context = AnalysisContext(
            log_content=log_content,
            requests=requests or [],
            scenario=decision.primary_scenario,
            all_scenarios=decision.scenarios,
            options=options or {},
            task_id=task_id
        )

        # 3. 执行策略
        results = self.execute(decision, context)

        return decision, results

    async def route_and_execute_async(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        metrics: dict[str, float] | None = None,
        user_hint: str = "",
        options: dict[str, Any] | None = None,
        task_id: str = ""
    ) -> tuple[RouteDecision, list[AnalysisResult]]:
        """异步版本的一站式路由和执行"""
        decision = self.route(
            log_content=log_content,
            requests=requests,
            metrics=metrics,
            user_hint=user_hint,
            options=options
        )

        context = AnalysisContext(
            log_content=log_content,
            requests=requests or [],
            scenario=decision.primary_scenario,
            all_scenarios=decision.scenarios,
            options=options or {},
            task_id=task_id
        )

        results = await self.execute_async(decision, context)

        return decision, results

    def _execute_strategy(
        self,
        strategy: AnalysisStrategy,
        context: AnalysisContext
    ) -> AnalysisResult:
        """执行单个策略"""
        start_time = time.time()

        try:
            # 准备输入数据
            input_data = {
                "log_content": context.log_content,
                "requests": context.requests,
                "scenario": context.scenario.to_dict() if context.scenario else None,
                "options": context.options,
                "shared_data": context.shared_data,
                "task_id": context.task_id
            }

            # 执行处理函数
            if strategy.is_async:
                # 在同步上下文中执行异步函数
                loop = asyncio.new_event_loop()
                try:
                    result_data = loop.run_until_complete(
                        asyncio.wait_for(
                            strategy.handler(input_data),
                            timeout=strategy.timeout_seconds
                        )
                    )
                finally:
                    loop.close()
            else:
                result_data = strategy.handler(input_data)

            execution_time = (time.time() - start_time) * 1000

            return AnalysisResult(
                success=True,
                strategy_id=strategy.strategy_id,
                scenario_type=strategy.scenario_types[0],
                data=result_data if isinstance(result_data, dict) else {"result": result_data},
                execution_time_ms=execution_time
            )

        except asyncio.TimeoutError:
            return AnalysisResult(
                success=False,
                strategy_id=strategy.strategy_id,
                scenario_type=strategy.scenario_types[0],
                error_message=f"策略执行超时 ({strategy.timeout_seconds}s)",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.error(f"策略 {strategy.strategy_id} 执行失败: {e}")
            return AnalysisResult(
                success=False,
                strategy_id=strategy.strategy_id,
                scenario_type=strategy.scenario_types[0],
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

    async def _execute_strategy_async(
        self,
        strategy: AnalysisStrategy,
        context: AnalysisContext
    ) -> AnalysisResult:
        """异步执行单个策略"""
        start_time = time.time()

        try:
            input_data = {
                "log_content": context.log_content,
                "requests": context.requests,
                "scenario": context.scenario.to_dict() if context.scenario else None,
                "options": context.options,
                "shared_data": context.shared_data,
                "task_id": context.task_id
            }

            if strategy.is_async:
                result_data = await asyncio.wait_for(
                    strategy.handler(input_data),
                    timeout=strategy.timeout_seconds
                )
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                result_data = await loop.run_in_executor(
                    None,
                    strategy.handler,
                    input_data
                )

            execution_time = (time.time() - start_time) * 1000

            return AnalysisResult(
                success=True,
                strategy_id=strategy.strategy_id,
                scenario_type=strategy.scenario_types[0],
                data=result_data if isinstance(result_data, dict) else {"result": result_data},
                execution_time_ms=execution_time
            )

        except asyncio.TimeoutError:
            return AnalysisResult(
                success=False,
                strategy_id=strategy.strategy_id,
                scenario_type=strategy.scenario_types[0],
                error_message=f"策略执行超时 ({strategy.timeout_seconds}s)",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            logger.error(f"策略 {strategy.strategy_id} 异步执行失败: {e}")
            return AnalysisResult(
                success=False,
                strategy_id=strategy.strategy_id,
                scenario_type=strategy.scenario_types[0],
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _get_fallback_strategy(
        self,
        scenarios: list[AnalysisScenario]
    ) -> AnalysisStrategy | None:
        """获取回退策略"""
        # 尝试找一个通用策略
        for scenario in scenarios:
            strategies = self.registry.find_by_scenario_type(scenario.scenario_type)
            if strategies:
                # 返回优先级最低的策略作为回退
                return min(strategies, key=lambda s: s.priority.value)

        # 查找任何可用策略
        all_strategies = self.registry.get_all()
        if all_strategies:
            return min(all_strategies, key=lambda s: s.priority.value)

        return None

    def get_statistics(self) -> dict[str, Any]:
        """获取路由器统计信息"""
        return {
            "total_routes": self._route_count,
            "successful_executions": self._success_count,
            "fallback_uses": self._fallback_count,
            "success_rate": self._success_count / self._route_count if self._route_count > 0 else 0,
            "registry_stats": self.registry.get_statistics()
        }

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._route_count = 0
        self._success_count = 0
        self._fallback_count = 0


# 便捷函数
def create_router(
    llm_provider: Any = None,
    custom_rules: list[Any] | None = None
) -> IntelligentRouter:
    """
    创建智能路由器实例

    Args:
        llm_provider: LLM提供者
        custom_rules: 自定义检测规则

    Returns:
        IntelligentRouter 实例
    """
    detector = ScenarioDetector(
        llm_provider=llm_provider,
        custom_rules=custom_rules
    )
    return IntelligentRouter(
        detector=detector,
        llm_provider=llm_provider
    )
