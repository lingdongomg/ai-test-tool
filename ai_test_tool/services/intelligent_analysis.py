"""
智能路由分析服务
该文件内容使用AI生成，注意识别准确性

将路由分发器封装为服务层，便于API调用
"""

import json
from typing import Any

from ..routing import (
    IntelligentRouter,
    ScenarioDetector,
    StrategyRegistry,
    AnalysisContext,
    ScenarioType,
    create_router,
    get_registry,
)
from ..llm.provider import get_llm_provider
from ..utils.logger import get_logger


class IntelligentAnalysisService:
    """
    智能分析服务

    提供基于路由的智能日志分析能力，自动识别场景并选择合适的分析策略
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = get_logger(verbose)
        self._router: IntelligentRouter | None = None
        self._llm_provider = None

    @property
    def router(self) -> IntelligentRouter:
        """懒加载路由器"""
        if self._router is None:
            try:
                self._llm_provider = get_llm_provider()
            except Exception:
                self._llm_provider = None
            self._router = create_router(llm_provider=self._llm_provider)
        return self._router

    def _enrich_with_knowledge(
        self,
        requests: list[dict[str, Any]] | None,
        user_hint: str
    ) -> str:
        """
        从知识库检索相关上下文，用于增强分析

        Returns:
            知识上下文字符串，可拼接到 user_hint 中
        """
        try:
            from ..api.dependencies import get_knowledge_retriever, get_rag_context_builder
            retriever = get_knowledge_retriever()
            rag_builder = get_rag_context_builder()

            # 从请求中提取 URL 和错误信息
            urls: list[str] = []
            errors: list[str] = []
            if requests:
                for r in requests[:10]:
                    url = r.get("url") or r.get("path") or ""
                    if url:
                        urls.append(url)
                    err = r.get("error_message") or r.get("error") or ""
                    if err:
                        errors.append(str(err)[:200])

            if not urls and not user_hint:
                return ""

            results = retriever.retrieve_for_log_analysis(urls, errors if errors else None)

            if not results:
                return ""

            rag_context = rag_builder.build(results)
            return rag_context.context_text if not rag_context.is_empty else ""
        except Exception as e:
            self.logger.warn(f"知识库检索失败（不影响主流程）: {e}")
            return ""

    def _save_analysis_to_knowledge(
        self,
        response: dict[str, Any],
        task_id: str
    ) -> None:
        """
        将分析结果中的关键发现写回知识库
        """
        try:
            from ..api.dependencies import get_knowledge_store
            store = get_knowledge_store()

            analysis = response.get("analysis", {})
            scenario = response.get("scenario_type", "unknown")

            # 提取摘要作为知识条目
            summary_parts = []
            if isinstance(analysis, dict):
                for key in ("summary", "conclusion", "findings", "description"):
                    val = analysis.get(key)
                    if val:
                        summary_parts.append(str(val)[:500])
                        break

            if not summary_parts:
                return

            title = f"[分析结论] {scenario} - {task_id[:20]}"
            content = "\n".join(summary_parts)

            # 查重
            existing = store.search(scope=task_id, keyword=scenario, limit=1)
            if existing:
                return

            store.create(
                title=title,
                content=content,
                type="test_experience",
                category="analysis_result",
                scope=task_id,
                tags=[scenario],
                source="auto_analysis",
                source_ref=task_id,
                status="active",
                created_by="intelligent_analysis"
            )
        except Exception as e:
            self.logger.warn(f"分析结果回写知识库失败（不影响主流程）: {e}")

    def analyze(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        metrics: dict[str, float] | None = None,
        user_hint: str = "",
        task_id: str = "",
        options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        智能分析入口

        自动识别分析场景并执行相应策略

        Args:
            log_content: 日志内容
            requests: 解析后的请求列表
            metrics: 统计指标（如错误率、响应时间等）
            user_hint: 用户提示（如"分析错误"、"查看性能"）
            task_id: 任务ID
            options: 额外选项
                - execute_all: 是否执行所有匹配策略（默认False，只执行第一个成功的）
                - max_strategies: 最多执行策略数量

        Returns:
            分析结果，包含场景识别、策略执行结果等
        """
        self.logger.start_step("智能路由分析")

        # 从知识库检索相关上下文，增强分析
        knowledge_context = self._enrich_with_knowledge(requests, user_hint)
        enriched_hint = user_hint
        if knowledge_context:
            enriched_hint = f"{user_hint}\n\n--- 知识库上下文 ---\n{knowledge_context}" if user_hint else knowledge_context

        # 执行路由和分析
        decision, results = self.router.route_and_execute(
            log_content=log_content,
            requests=requests,
            metrics=metrics,
            user_hint=enriched_hint,
            options=options or {},
            task_id=task_id
        )

        # 整理结果
        response = {
            "success": any(r.success for r in results),
            "routing": {
                "detected_scenarios": [
                    {
                        "type": s.scenario_type.value,
                        "confidence": s.confidence,
                        "description": s.description
                    }
                    for s in decision.scenarios
                ],
                "primary_scenario": decision.primary_scenario.scenario_type.value if decision.primary_scenario else None,
                "selected_strategies": [
                    {
                        "id": s.strategy_id,
                        "name": s.name,
                        "priority": s.priority.name
                    }
                    for s in decision.selected_strategies
                ],
                "reasoning": decision.reasoning
            },
            "results": [
                {
                    "strategy_id": r.strategy_id,
                    "scenario_type": r.scenario_type.value,
                    "success": r.success,
                    "execution_time_ms": r.execution_time_ms,
                    "data": r.data,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }

        # 如果有成功结果，提取主要数据
        successful_results = [r for r in results if r.success]
        if successful_results:
            primary_result = successful_results[0]
            response["analysis"] = primary_result.data
            response["scenario_type"] = primary_result.scenario_type.value

        self.logger.end_step(
            f"完成: {len(decision.scenarios)} 场景, "
            f"{len(results)} 策略执行, "
            f"{len(successful_results)} 成功"
        )

        # 将分析结果写回知识库
        if successful_results and task_id:
            self._save_analysis_to_knowledge(response, task_id)

        return response

    def detect_scenarios(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        metrics: dict[str, float] | None = None,
        user_hint: str = ""
    ) -> list[dict[str, Any]]:
        """
        仅检测场景，不执行策略

        Args:
            log_content: 日志内容
            requests: 请求列表
            metrics: 指标
            user_hint: 用户提示

        Returns:
            检测到的场景列表
        """
        scenarios = self.router.detector.detect(
            log_content=log_content,
            requests=requests,
            metrics=metrics,
            user_hint=user_hint
        )

        return [s.to_dict() for s in scenarios]

    def get_available_strategies(
        self,
        scenario_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        获取可用策略列表

        Args:
            scenario_type: 按场景类型过滤

        Returns:
            策略列表
        """
        registry = get_registry()

        if scenario_type:
            try:
                st = ScenarioType(scenario_type)
                strategies = registry.find_by_scenario_type(st)
            except ValueError:
                strategies = []
        else:
            strategies = registry.get_all()

        return [s.to_dict() for s in strategies]

    def get_statistics(self) -> dict[str, Any]:
        """获取路由统计信息"""
        return {
            "router_stats": self.router.get_statistics(),
            "registry_stats": get_registry().get_statistics()
        }

    def analyze_errors(
        self,
        requests: list[dict[str, Any]],
        log_content: str = ""
    ) -> dict[str, Any]:
        """
        专门的错误分析

        Args:
            requests: 请求列表
            log_content: 日志内容

        Returns:
            错误分析结果
        """
        return self.analyze(
            log_content=log_content,
            requests=requests,
            user_hint="error analysis 错误分析"
        )

    def analyze_performance(
        self,
        requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        专门的性能分析

        Args:
            requests: 请求列表

        Returns:
            性能分析结果
        """
        # 计算性能指标
        response_times = [
            r.get("response_time_ms", 0)
            for r in requests
            if r.get("response_time_ms")
        ]

        metrics = {}
        if response_times:
            response_times.sort()
            n = len(response_times)
            metrics = {
                "avg_latency_ms": sum(response_times) / n,
                "p90_latency_ms": response_times[int(n * 0.9)],
                "p99_latency_ms": response_times[int(n * 0.99)] if n >= 100 else response_times[-1],
                "slow_request_rate": sum(1 for t in response_times if t > 3000) / n
            }

        return self.analyze(
            requests=requests,
            metrics=metrics,
            user_hint="performance analysis 性能分析"
        )

    def analyze_security(
        self,
        requests: list[dict[str, Any]],
        log_content: str = ""
    ) -> dict[str, Any]:
        """
        专门的安全分析

        Args:
            requests: 请求列表
            log_content: 日志内容

        Returns:
            安全分析结果
        """
        return self.analyze(
            log_content=log_content,
            requests=requests,
            user_hint="security analysis 安全分析"
        )

    def health_check(
        self,
        requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        健康检查分析

        Args:
            requests: 请求列表

        Returns:
            健康状态分析结果
        """
        return self.analyze(
            requests=requests,
            user_hint="health check 健康检查"
        )
