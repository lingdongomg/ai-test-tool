"""
智能路由模块单元测试

覆盖: IntelligentRouter, StrategyRegistry, ScenarioDetector (mocked)
"""

from unittest.mock import Mock, patch, MagicMock

import pytest

from ai_test_tool.routing.router import IntelligentRouter
from ai_test_tool.routing.registry import StrategyRegistry
from ai_test_tool.routing.models import (
    AnalysisScenario,
    AnalysisStrategy,
    AnalysisContext,
    AnalysisResult,
    RouteDecision,
    ScenarioType,
    StrategyPriority,
    ScenarioIndicator,
    MatchMethod,
)


# ============================================================
# Helpers
# ============================================================

def _make_router(registry: StrategyRegistry, detector) -> IntelligentRouter:
    """Create an IntelligentRouter that uses the given registry.

    StrategyRegistry defines __len__, so an empty registry is falsy.
    IntelligentRouter.__init__ uses ``registry or get_registry()`` which
    would fall through to the global singleton when the registry is empty.
    We work around this by assigning the registry attribute directly after
    construction.
    """
    router = IntelligentRouter(registry=registry, detector=detector)
    router.registry = registry
    return router


def make_scenario(
    scenario_type: ScenarioType = ScenarioType.ERROR_ANALYSIS,
    confidence: float = 0.8,
    description: str = "test scenario",
) -> AnalysisScenario:
    """Create a test AnalysisScenario."""
    return AnalysisScenario(
        scenario_type=scenario_type,
        confidence=confidence,
        description=description,
    )


def make_strategy(
    strategy_id: str = "test_strategy",
    name: str = "Test Strategy",
    scenario_types: list[ScenarioType] | None = None,
    handler=None,
    priority: StrategyPriority = StrategyPriority.MEDIUM,
    min_confidence: float = 0.3,
    is_async: bool = False,
    timeout_seconds: int = 60,
    tags: list[str] | None = None,
    requires_llm: bool = False,
) -> AnalysisStrategy:
    """Create a test AnalysisStrategy with a mock handler."""
    if scenario_types is None:
        scenario_types = [ScenarioType.ERROR_ANALYSIS]
    if handler is None:
        handler = Mock(return_value={"result": "ok"})
    return AnalysisStrategy(
        strategy_id=strategy_id,
        name=name,
        description="test description",
        scenario_types=scenario_types,
        handler=handler,
        priority=priority,
        min_confidence=min_confidence,
        is_async=is_async,
        timeout_seconds=timeout_seconds,
        tags=tags or [],
        requires_llm=requires_llm,
    )


def make_context(**kwargs) -> AnalysisContext:
    """Create a test AnalysisContext."""
    defaults = dict(
        log_content="some log content",
        requests=[],
        scenario=None,
        all_scenarios=[],
        options={},
        task_id="test-task-001",
    )
    defaults.update(kwargs)
    return AnalysisContext(**defaults)


# ============================================================
# Model basic tests
# ============================================================

class TestAnalysisScenario:
    def test_confidence_clamped_to_0_1(self):
        s = AnalysisScenario(
            scenario_type=ScenarioType.ERROR_ANALYSIS, confidence=1.5
        )
        assert s.confidence == 1.0

        s2 = AnalysisScenario(
            scenario_type=ScenarioType.ERROR_ANALYSIS, confidence=-0.5
        )
        assert s2.confidence == 0.0

    def test_is_high_confidence(self):
        high = make_scenario(confidence=0.8)
        low = make_scenario(confidence=0.5)
        assert high.is_high_confidence is True
        assert low.is_high_confidence is False

    def test_to_dict(self):
        s = make_scenario()
        d = s.to_dict()
        assert d["scenario_type"] == ScenarioType.ERROR_ANALYSIS.value
        assert d["confidence"] == 0.8
        assert "indicators" in d


class TestAnalysisStrategy:
    def test_matches_scenario_pass(self):
        strategy = make_strategy(min_confidence=0.5)
        scenario = make_scenario(confidence=0.8)
        assert strategy.matches_scenario(scenario) is True

    def test_matches_scenario_low_confidence(self):
        strategy = make_strategy(min_confidence=0.9)
        scenario = make_scenario(confidence=0.5)
        assert strategy.matches_scenario(scenario) is False

    def test_matches_scenario_wrong_type(self):
        strategy = make_strategy(
            scenario_types=[ScenarioType.SECURITY_ANALYSIS]
        )
        scenario = make_scenario(
            scenario_type=ScenarioType.ERROR_ANALYSIS, confidence=0.9
        )
        assert strategy.matches_scenario(scenario) is False

    def test_to_dict(self):
        strategy = make_strategy(tags=["fast", "basic"])
        d = strategy.to_dict()
        assert d["strategy_id"] == "test_strategy"
        assert d["tags"] == ["fast", "basic"]


class TestRouteDecision:
    def test_auto_set_primary(self):
        scenario = make_scenario()
        strategy = make_strategy()
        decision = RouteDecision(
            scenarios=[scenario],
            selected_strategies=[strategy],
        )
        assert decision.primary_scenario is scenario
        assert decision.primary_strategy is strategy

    def test_has_valid_route_true(self):
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[make_strategy()],
        )
        assert decision.has_valid_route is True

    def test_has_valid_route_false_empty(self):
        decision = RouteDecision(scenarios=[], selected_strategies=[])
        assert decision.has_valid_route is False

    def test_strategy_count(self):
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[make_strategy("a"), make_strategy("b")],
        )
        assert decision.strategy_count == 2


class TestAnalysisContext:
    def test_get_option(self):
        ctx = make_context(options={"verbose": True})
        assert ctx.get_option("verbose") is True
        assert ctx.get_option("missing", "default") == "default"

    def test_shared_data(self):
        ctx = make_context()
        ctx.set_shared("key1", "value1")
        assert ctx.get_shared("key1") == "value1"
        assert ctx.get_shared("missing") is None


class TestAnalysisResult:
    def test_to_dict(self):
        r = AnalysisResult(
            success=True,
            strategy_id="s1",
            scenario_type=ScenarioType.ERROR_ANALYSIS,
            data={"count": 5},
            execution_time_ms=123.4,
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["strategy_id"] == "s1"
        assert d["scenario_type"] == "error_analysis"
        assert d["data"] == {"count": 5}


class TestScenarioIndicator:
    def test_weighted_value(self):
        ind = ScenarioIndicator(name="err", value=0.8, weight=0.5)
        assert ind.weighted_value == pytest.approx(0.4)


# ============================================================
# StrategyRegistry tests
# ============================================================

class TestStrategyRegistry:
    @pytest.fixture(autouse=True)
    def fresh_registry(self):
        """Each test gets its own isolated registry instance."""
        self.registry = StrategyRegistry()

    def test_register_and_get(self):
        s = make_strategy(strategy_id="s1")
        self.registry.register(s)
        assert self.registry.get("s1") is s

    def test_register_overwrites_duplicate(self):
        s1 = make_strategy(strategy_id="dup", name="first")
        s2 = make_strategy(strategy_id="dup", name="second")
        self.registry.register(s1)
        self.registry.register(s2)
        assert self.registry.get("dup").name == "second"
        assert self.registry.size == 1

    def test_unregister(self):
        s = make_strategy(strategy_id="s1")
        self.registry.register(s)
        assert self.registry.unregister("s1") is True
        assert self.registry.get("s1") is None
        assert self.registry.size == 0

    def test_unregister_nonexistent(self):
        assert self.registry.unregister("nope") is False

    def test_get_all(self):
        self.registry.register(make_strategy(strategy_id="a"))
        self.registry.register(make_strategy(strategy_id="b"))
        all_strategies = self.registry.get_all()
        assert len(all_strategies) == 2
        ids = {s.strategy_id for s in all_strategies}
        assert ids == {"a", "b"}

    def test_contains_and_len(self):
        self.registry.register(make_strategy(strategy_id="x"))
        assert "x" in self.registry
        assert "y" not in self.registry
        assert len(self.registry) == 1

    def test_find_by_scenario_matches(self):
        s_high = make_strategy(
            strategy_id="high",
            priority=StrategyPriority.HIGH,
            min_confidence=0.3,
        )
        s_low = make_strategy(
            strategy_id="low",
            priority=StrategyPriority.LOW,
            min_confidence=0.3,
        )
        self.registry.register(s_high)
        self.registry.register(s_low)

        scenario = make_scenario(confidence=0.8)
        matched = self.registry.find_by_scenario(scenario)
        assert len(matched) == 2
        # Sorted by priority descending: HIGH first
        assert matched[0].strategy_id == "high"
        assert matched[1].strategy_id == "low"

    def test_find_by_scenario_filters_low_confidence(self):
        s = make_strategy(strategy_id="strict", min_confidence=0.9)
        self.registry.register(s)

        scenario = make_scenario(confidence=0.5)
        matched = self.registry.find_by_scenario(scenario)
        assert len(matched) == 0

    def test_find_by_scenario_filters_wrong_type(self):
        s = make_strategy(
            strategy_id="sec",
            scenario_types=[ScenarioType.SECURITY_ANALYSIS],
        )
        self.registry.register(s)

        scenario = make_scenario(scenario_type=ScenarioType.ERROR_ANALYSIS)
        matched = self.registry.find_by_scenario(scenario)
        assert len(matched) == 0

    def test_find_by_scenario_require_llm_filter(self):
        s_llm = make_strategy(strategy_id="llm_s", requires_llm=True)
        s_no = make_strategy(strategy_id="no_llm", requires_llm=False)
        self.registry.register(s_llm)
        self.registry.register(s_no)

        scenario = make_scenario(confidence=0.8)

        only_llm = self.registry.find_by_scenario(scenario, require_llm=True)
        assert len(only_llm) == 1
        assert only_llm[0].strategy_id == "llm_s"

        no_llm = self.registry.find_by_scenario(scenario, require_llm=False)
        assert len(no_llm) == 1
        assert no_llm[0].strategy_id == "no_llm"

    def test_find_by_scenario_type(self):
        s1 = make_strategy(
            strategy_id="err1",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            priority=StrategyPriority.HIGH,
        )
        s2 = make_strategy(
            strategy_id="err2",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            priority=StrategyPriority.LOW,
        )
        s3 = make_strategy(
            strategy_id="sec1",
            scenario_types=[ScenarioType.SECURITY_ANALYSIS],
        )
        self.registry.register(s1)
        self.registry.register(s2)
        self.registry.register(s3)

        result = self.registry.find_by_scenario_type(ScenarioType.ERROR_ANALYSIS)
        assert len(result) == 2
        assert result[0].strategy_id == "err1"  # HIGH first

        result_sec = self.registry.find_by_scenario_type(
            ScenarioType.SECURITY_ANALYSIS
        )
        assert len(result_sec) == 1

    def test_find_by_scenario_type_empty(self):
        result = self.registry.find_by_scenario_type(ScenarioType.HEALTH_CHECK)
        assert result == []

    def test_find_by_tags(self):
        s1 = make_strategy(strategy_id="t1", tags=["fast", "basic"])
        s2 = make_strategy(strategy_id="t2", tags=["slow", "advanced"])
        s3 = make_strategy(strategy_id="t3", tags=["fast", "advanced"])
        self.registry.register(s1)
        self.registry.register(s2)
        self.registry.register(s3)

        result = self.registry.find_by_tags(["fast"])
        assert len(result) == 2
        ids = {s.strategy_id for s in result}
        assert ids == {"t1", "t3"}

    def test_find_by_tags_no_match(self):
        s = make_strategy(strategy_id="t1", tags=["a"])
        self.registry.register(s)
        assert self.registry.find_by_tags(["nonexistent"]) == []

    def test_get_statistics(self):
        s1 = make_strategy(
            strategy_id="s1",
            priority=StrategyPriority.HIGH,
            is_async=True,
            requires_llm=True,
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
        )
        s2 = make_strategy(
            strategy_id="s2",
            priority=StrategyPriority.LOW,
            scenario_types=[ScenarioType.ERROR_ANALYSIS, ScenarioType.SECURITY_ANALYSIS],
        )
        self.registry.register(s1)
        self.registry.register(s2)

        stats = self.registry.get_statistics()
        assert stats["total_strategies"] == 2
        assert stats["llm_required_count"] == 1
        assert stats["async_count"] == 1
        assert ScenarioType.ERROR_ANALYSIS.value in stats["scenario_coverage"]
        assert stats["scenario_coverage"][ScenarioType.ERROR_ANALYSIS.value] == 2
        assert "HIGH" in stats["priority_distribution"]
        assert "LOW" in stats["priority_distribution"]

    def test_unregister_cleans_scenario_index(self):
        s = make_strategy(
            strategy_id="s1",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
        )
        self.registry.register(s)
        self.registry.unregister("s1")

        result = self.registry.find_by_scenario_type(ScenarioType.ERROR_ANALYSIS)
        assert result == []

    def test_strategy_with_multiple_scenario_types(self):
        s = make_strategy(
            strategy_id="multi",
            scenario_types=[
                ScenarioType.ERROR_ANALYSIS,
                ScenarioType.ROOT_CAUSE,
            ],
        )
        self.registry.register(s)

        err = self.registry.find_by_scenario_type(ScenarioType.ERROR_ANALYSIS)
        root = self.registry.find_by_scenario_type(ScenarioType.ROOT_CAUSE)
        assert len(err) == 1
        assert len(root) == 1
        assert err[0] is root[0]


# ============================================================
# IntelligentRouter tests
# ============================================================

class TestIntelligentRouterRoute:
    """Tests for IntelligentRouter.route()."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry = StrategyRegistry()
        self.detector = Mock()
        self.router = _make_router(self.registry, self.detector)

    def test_route_with_matched_scenarios_and_strategies(self):
        """Detector returns scenarios, registry has matching strategies."""
        scenario = make_scenario(
            scenario_type=ScenarioType.ERROR_ANALYSIS, confidence=0.9
        )
        self.detector.detect.return_value = [scenario]

        strategy = make_strategy(
            strategy_id="err_basic",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            priority=StrategyPriority.HIGH,
        )
        self.registry.register(strategy)

        decision = self.router.route(log_content="ERROR: something broke")

        assert isinstance(decision, RouteDecision)
        assert len(decision.scenarios) == 1
        assert decision.scenarios[0].scenario_type == ScenarioType.ERROR_ANALYSIS
        assert len(decision.selected_strategies) == 1
        assert decision.selected_strategies[0].strategy_id == "err_basic"
        assert decision.has_valid_route is True
        assert decision.primary_scenario is scenario
        assert "err_basic" not in (decision.fallback_strategy or "")

    def test_route_no_scenarios_detected(self):
        """Detector returns empty list -> no valid route."""
        self.detector.detect.return_value = []

        decision = self.router.route(log_content="nothing interesting")

        assert decision.scenarios == []
        assert decision.selected_strategies == []
        assert decision.has_valid_route is False
        assert "未能识别" in decision.reasoning

    def test_route_scenarios_but_no_matching_strategies(self):
        """Detector returns scenarios but registry has no match -> fallback."""
        scenario = make_scenario(
            scenario_type=ScenarioType.SECURITY_ANALYSIS, confidence=0.8
        )
        self.detector.detect.return_value = [scenario]
        # Registry is empty for SECURITY_ANALYSIS, but add an unrelated strategy
        # so fallback can find it
        fallback_s = make_strategy(
            strategy_id="generic",
            scenario_types=[ScenarioType.HEALTH_CHECK],
            priority=StrategyPriority.LOW,
        )
        self.registry.register(fallback_s)

        decision = self.router.route(log_content="sql injection attempt")

        # Fallback should kick in since no strategy matches SECURITY_ANALYSIS
        assert decision.has_valid_route is True
        assert decision.fallback_strategy is not None
        assert decision.fallback_strategy.strategy_id == "generic"

    def test_route_no_strategies_no_fallback_available(self):
        """Detector returns scenarios, no matching strategies, empty registry -> no valid route."""
        scenario = make_scenario(
            scenario_type=ScenarioType.SECURITY_ANALYSIS, confidence=0.8
        )
        self.detector.detect.return_value = [scenario]
        # Registry is completely empty

        decision = self.router.route(log_content="attack")

        assert decision.has_valid_route is False
        assert decision.fallback_strategy is None

    def test_route_fallback_disabled(self):
        """With enable_fallback=False, no fallback is attempted."""
        self.router.enable_fallback = False
        scenario = make_scenario(
            scenario_type=ScenarioType.SECURITY_ANALYSIS, confidence=0.8
        )
        self.detector.detect.return_value = [scenario]

        unrelated = make_strategy(
            strategy_id="unrelated",
            scenario_types=[ScenarioType.HEALTH_CHECK],
        )
        self.registry.register(unrelated)

        decision = self.router.route(log_content="attack")

        assert decision.has_valid_route is False
        assert decision.fallback_strategy is None

    def test_route_multiple_scenarios_picks_best_strategies(self):
        """Multiple scenarios each get their best strategy (up to max_strategies)."""
        s1 = make_scenario(ScenarioType.ERROR_ANALYSIS, confidence=0.9)
        s2 = make_scenario(ScenarioType.PERFORMANCE_ANALYSIS, confidence=0.7)
        self.detector.detect.return_value = [s1, s2]

        err_strat = make_strategy(
            strategy_id="err",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            priority=StrategyPriority.HIGH,
        )
        perf_strat = make_strategy(
            strategy_id="perf",
            scenario_types=[ScenarioType.PERFORMANCE_ANALYSIS],
            priority=StrategyPriority.MEDIUM,
        )
        self.registry.register(err_strat)
        self.registry.register(perf_strat)

        decision = self.router.route(log_content="error and slow")

        assert len(decision.selected_strategies) == 2
        ids = {s.strategy_id for s in decision.selected_strategies}
        assert ids == {"err", "perf"}

    def test_route_respects_max_strategies(self):
        """Only the first max_strategies scenarios are considered."""
        self.router.max_strategies = 1
        s1 = make_scenario(ScenarioType.ERROR_ANALYSIS, confidence=0.9)
        s2 = make_scenario(ScenarioType.PERFORMANCE_ANALYSIS, confidence=0.7)
        self.detector.detect.return_value = [s1, s2]

        err_strat = make_strategy(
            strategy_id="err",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
        )
        perf_strat = make_strategy(
            strategy_id="perf",
            scenario_types=[ScenarioType.PERFORMANCE_ANALYSIS],
        )
        self.registry.register(err_strat)
        self.registry.register(perf_strat)

        decision = self.router.route(log_content="error")

        # Only the first scenario considered -> only err strategy
        assert len(decision.selected_strategies) == 1
        assert decision.selected_strategies[0].strategy_id == "err"

    def test_route_deduplicates_strategies(self):
        """Same strategy is not added twice if it matches multiple scenarios."""
        s1 = make_scenario(ScenarioType.ERROR_ANALYSIS, confidence=0.9)
        s2 = make_scenario(ScenarioType.ROOT_CAUSE, confidence=0.7)
        self.detector.detect.return_value = [s1, s2]

        # One strategy handles both scenario types
        shared = make_strategy(
            strategy_id="shared",
            scenario_types=[ScenarioType.ERROR_ANALYSIS, ScenarioType.ROOT_CAUSE],
            priority=StrategyPriority.HIGH,
        )
        self.registry.register(shared)

        decision = self.router.route(log_content="error root cause")

        assert len(decision.selected_strategies) == 1
        assert decision.selected_strategies[0].strategy_id == "shared"

    def test_route_increments_route_count(self):
        self.detector.detect.return_value = []
        self.router.route(log_content="a")
        self.router.route(log_content="b")
        stats = self.router.get_statistics()
        assert stats["total_routes"] == 2

    def test_route_passes_arguments_to_detector(self):
        self.detector.detect.return_value = []
        self.router.route(
            log_content="logs",
            requests=[{"url": "/api"}],
            metrics={"error_rate": 0.5},
            user_hint="check errors",
        )
        self.detector.detect.assert_called_once_with(
            log_content="logs",
            requests=[{"url": "/api"}],
            metrics={"error_rate": 0.5},
            user_hint="check errors",
        )


# ============================================================
# IntelligentRouter._get_fallback_strategy tests
# ============================================================

class TestFallbackStrategy:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry = StrategyRegistry()
        self.detector = Mock()
        self.router = _make_router(self.registry, self.detector)

    def test_fallback_returns_lowest_priority_for_scenario_type(self):
        high = make_strategy(
            strategy_id="high",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            priority=StrategyPriority.HIGH,
        )
        low = make_strategy(
            strategy_id="low",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            priority=StrategyPriority.LOW,
        )
        self.registry.register(high)
        self.registry.register(low)

        scenario = make_scenario(ScenarioType.ERROR_ANALYSIS)
        result = self.router._get_fallback_strategy([scenario])
        # Fallback should return the lowest-priority strategy
        assert result.strategy_id == "low"

    def test_fallback_tries_all_scenarios(self):
        """If first scenario has no strategies, tries the next."""
        strat = make_strategy(
            strategy_id="perf_fallback",
            scenario_types=[ScenarioType.PERFORMANCE_ANALYSIS],
            priority=StrategyPriority.LOW,
        )
        self.registry.register(strat)

        scenarios = [
            make_scenario(ScenarioType.SECURITY_ANALYSIS),
            make_scenario(ScenarioType.PERFORMANCE_ANALYSIS),
        ]
        result = self.router._get_fallback_strategy(scenarios)
        assert result.strategy_id == "perf_fallback"

    def test_fallback_uses_any_available_when_no_type_match(self):
        """When no scenario-type match, picks the lowest priority from all."""
        strat = make_strategy(
            strategy_id="generic",
            scenario_types=[ScenarioType.HEALTH_CHECK],
            priority=StrategyPriority.BACKGROUND,
        )
        self.registry.register(strat)

        scenarios = [make_scenario(ScenarioType.SECURITY_ANALYSIS)]
        result = self.router._get_fallback_strategy(scenarios)
        assert result.strategy_id == "generic"

    def test_fallback_returns_none_when_registry_empty(self):
        scenarios = [make_scenario(ScenarioType.ERROR_ANALYSIS)]
        result = self.router._get_fallback_strategy(scenarios)
        assert result is None


# ============================================================
# IntelligentRouter.execute tests
# ============================================================

class TestIntelligentRouterExecute:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry = StrategyRegistry()
        self.detector = Mock()
        self.router = _make_router(self.registry, self.detector)

    def test_execute_no_valid_route(self):
        decision = RouteDecision(scenarios=[], selected_strategies=[])
        context = make_context()

        results = self.router.execute(decision, context)

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].strategy_id == "none"
        assert "无有效策略" in results[0].error_message

    def test_execute_successful_strategy(self):
        handler = Mock(return_value={"errors": ["e1"]})
        strategy = make_strategy(strategy_id="s1", handler=handler)
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[strategy],
        )
        context = make_context(scenario=make_scenario())

        results = self.router.execute(decision, context)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].strategy_id == "s1"
        assert results[0].data == {"errors": ["e1"]}
        assert results[0].execution_time_ms > 0
        handler.assert_called_once()

    def test_execute_handler_receives_correct_input(self):
        handler = Mock(return_value={})
        strategy = make_strategy(strategy_id="s1", handler=handler)
        scenario = make_scenario()
        decision = RouteDecision(
            scenarios=[scenario],
            selected_strategies=[strategy],
        )
        context = make_context(
            log_content="test logs",
            task_id="task-42",
            scenario=scenario,
        )

        self.router.execute(decision, context)

        call_args = handler.call_args[0][0]
        assert call_args["log_content"] == "test logs"
        assert call_args["task_id"] == "task-42"
        assert call_args["scenario"] is not None

    def test_execute_failing_strategy(self):
        handler = Mock(side_effect=RuntimeError("boom"))
        strategy = make_strategy(strategy_id="fail", handler=handler)
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[strategy],
        )
        context = make_context()

        results = self.router.execute(decision, context)

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].strategy_id == "fail"
        assert "boom" in results[0].error_message
        assert results[0].execution_time_ms >= 0

    def test_execute_stops_after_first_success_by_default(self):
        h1 = Mock(return_value={"v": 1})
        h2 = Mock(return_value={"v": 2})
        s1 = make_strategy(strategy_id="s1", handler=h1)
        s2 = make_strategy(strategy_id="s2", handler=h2)
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[s1, s2],
        )
        context = make_context()

        results = self.router.execute(decision, context)

        # Default behaviour: stop after first success
        assert len(results) == 1
        assert results[0].strategy_id == "s1"
        h2.assert_not_called()

    def test_execute_all_when_option_set(self):
        h1 = Mock(return_value={"v": 1})
        h2 = Mock(return_value={"v": 2})
        s1 = make_strategy(strategy_id="s1", handler=h1)
        s2 = make_strategy(strategy_id="s2", handler=h2)
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[s1, s2],
        )
        context = make_context(options={"execute_all": True})

        results = self.router.execute(decision, context)

        assert len(results) == 2
        h1.assert_called_once()
        h2.assert_called_once()

    def test_execute_continues_on_failure(self):
        """When first strategy fails, the next one is tried."""
        h1 = Mock(side_effect=RuntimeError("fail"))
        h2 = Mock(return_value={"ok": True})
        s1 = make_strategy(strategy_id="s1", handler=h1)
        s2 = make_strategy(strategy_id="s2", handler=h2)
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[s1, s2],
        )
        context = make_context()

        results = self.router.execute(decision, context)

        # First fails, second succeeds and then execution stops
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True

    def test_execute_non_dict_handler_result_wrapped(self):
        handler = Mock(return_value="plain string")
        strategy = make_strategy(strategy_id="s1", handler=handler)
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[strategy],
        )
        context = make_context()

        results = self.router.execute(decision, context)

        assert results[0].success is True
        assert results[0].data == {"result": "plain string"}


# ============================================================
# IntelligentRouter.route_and_execute tests
# ============================================================

class TestRouteAndExecute:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry = StrategyRegistry()
        self.detector = Mock()
        self.router = _make_router(self.registry, self.detector)

    def test_route_and_execute_success(self):
        scenario = make_scenario(ScenarioType.ERROR_ANALYSIS, confidence=0.9)
        self.detector.detect.return_value = [scenario]

        handler = Mock(return_value={"found": 3})
        strategy = make_strategy(
            strategy_id="err",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            handler=handler,
        )
        self.registry.register(strategy)

        decision, results = self.router.route_and_execute(
            log_content="ERROR: crash",
            task_id="t-001",
        )

        assert decision.has_valid_route is True
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].data == {"found": 3}

    def test_route_and_execute_no_scenarios(self):
        self.detector.detect.return_value = []

        decision, results = self.router.route_and_execute(
            log_content="nothing"
        )

        assert decision.has_valid_route is False
        assert len(results) == 1
        assert results[0].success is False

    def test_route_and_execute_context_has_correct_fields(self):
        """Verify the AnalysisContext passed to execute is built properly."""
        scenario = make_scenario(ScenarioType.ERROR_ANALYSIS)
        self.detector.detect.return_value = [scenario]

        captured_input = {}

        def capture_handler(input_data):
            captured_input.update(input_data)
            return {}

        strategy = make_strategy(
            strategy_id="cap",
            scenario_types=[ScenarioType.ERROR_ANALYSIS],
            handler=capture_handler,
        )
        self.registry.register(strategy)

        self.router.route_and_execute(
            log_content="test content",
            requests=[{"url": "/api"}],
            options={"verbose": True},
            task_id="task-99",
        )

        assert captured_input["log_content"] == "test content"
        assert captured_input["requests"] == [{"url": "/api"}]
        assert captured_input["task_id"] == "task-99"
        assert captured_input["options"] == {"verbose": True}


# ============================================================
# Statistics tracking tests
# ============================================================

class TestStatistics:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry = StrategyRegistry()
        self.detector = Mock()
        self.router = _make_router(self.registry, self.detector)

    def test_initial_statistics(self):
        stats = self.router.get_statistics()
        assert stats["total_routes"] == 0
        assert stats["successful_executions"] == 0
        assert stats["fallback_uses"] == 0
        assert stats["success_rate"] == 0

    def test_statistics_after_route_and_execute(self):
        scenario = make_scenario()
        self.detector.detect.return_value = [scenario]

        handler = Mock(return_value={"ok": True})
        strategy = make_strategy(
            strategy_id="s1",
            handler=handler,
        )
        self.registry.register(strategy)

        self.router.route_and_execute(log_content="test")

        stats = self.router.get_statistics()
        assert stats["total_routes"] == 1
        assert stats["successful_executions"] == 1
        assert stats["success_rate"] == 1.0
        assert stats["fallback_uses"] == 0

    def test_statistics_with_failure(self):
        scenario = make_scenario()
        self.detector.detect.return_value = [scenario]

        handler = Mock(side_effect=RuntimeError("fail"))
        strategy = make_strategy(strategy_id="fail_s", handler=handler)
        self.registry.register(strategy)

        self.router.route_and_execute(log_content="test")

        stats = self.router.get_statistics()
        assert stats["total_routes"] == 1
        assert stats["successful_executions"] == 0
        assert stats["success_rate"] == 0.0

    def test_statistics_fallback_count(self):
        """Fallback count increments when no strategy matches but fallback is used."""
        scenario = make_scenario(ScenarioType.SECURITY_ANALYSIS)
        self.detector.detect.return_value = [scenario]

        # Only register for a different type so fallback triggers
        fallback_s = make_strategy(
            strategy_id="fb",
            scenario_types=[ScenarioType.HEALTH_CHECK],
            priority=StrategyPriority.LOW,
        )
        self.registry.register(fallback_s)

        self.router.route(log_content="attack")

        stats = self.router.get_statistics()
        assert stats["fallback_uses"] == 1

    def test_reset_statistics(self):
        self.detector.detect.return_value = []
        self.router.route(log_content="a")
        self.router.route(log_content="b")

        self.router.reset_statistics()

        stats = self.router.get_statistics()
        assert stats["total_routes"] == 0
        assert stats["successful_executions"] == 0
        assert stats["fallback_uses"] == 0

    def test_statistics_includes_registry_stats(self):
        strategy = make_strategy(strategy_id="s1")
        self.registry.register(strategy)

        stats = self.router.get_statistics()
        assert "registry_stats" in stats
        assert stats["registry_stats"]["total_strategies"] == 1

    def test_success_rate_across_multiple_executions(self):
        scenario = make_scenario()
        self.detector.detect.return_value = [scenario]

        ok_handler = Mock(return_value={})
        fail_handler = Mock(side_effect=RuntimeError("x"))
        ok_strategy = make_strategy(strategy_id="ok", handler=ok_handler)
        fail_strategy = make_strategy(strategy_id="fail", handler=fail_handler)

        # First: register ok strategy, route+execute
        self.registry.register(ok_strategy)
        self.router.route_and_execute(log_content="a")

        # Second: replace with fail strategy, route+execute
        self.registry.unregister("ok")
        self.registry.register(fail_strategy)
        self.router.route_and_execute(log_content="b")

        stats = self.router.get_statistics()
        assert stats["total_routes"] == 2
        assert stats["successful_executions"] == 1
        assert stats["success_rate"] == pytest.approx(0.5)


# ============================================================
# ScenarioDetector (mocked) integration with router
# ============================================================

class TestDetectorIntegration:
    """Tests verifying how the router interacts with the detector Mock."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry = StrategyRegistry()
        self.detector = Mock()
        self.router = _make_router(self.registry, self.detector)

    def test_detector_called_with_all_params(self):
        self.detector.detect.return_value = []
        self.router.route(
            log_content="c",
            requests=[{"a": 1}],
            metrics={"x": 0.5},
            user_hint="hint",
        )
        self.detector.detect.assert_called_once_with(
            log_content="c",
            requests=[{"a": 1}],
            metrics={"x": 0.5},
            user_hint="hint",
        )

    def test_detector_returning_multiple_types(self):
        scenarios = [
            make_scenario(ScenarioType.ERROR_ANALYSIS, confidence=0.9),
            make_scenario(ScenarioType.PERFORMANCE_ANALYSIS, confidence=0.7),
            make_scenario(ScenarioType.SECURITY_ANALYSIS, confidence=0.6),
        ]
        self.detector.detect.return_value = scenarios

        err = make_strategy(
            strategy_id="err", scenario_types=[ScenarioType.ERROR_ANALYSIS]
        )
        perf = make_strategy(
            strategy_id="perf",
            scenario_types=[ScenarioType.PERFORMANCE_ANALYSIS],
        )
        sec = make_strategy(
            strategy_id="sec",
            scenario_types=[ScenarioType.SECURITY_ANALYSIS],
        )
        self.registry.register(err)
        self.registry.register(perf)
        self.registry.register(sec)

        decision = self.router.route(log_content="test")
        assert len(decision.scenarios) == 3
        assert len(decision.selected_strategies) == 3

    def test_detector_exception_propagates(self):
        """If the detector raises, the router does not swallow it."""
        self.detector.detect.side_effect = ValueError("bad input")
        with pytest.raises(ValueError, match="bad input"):
            self.router.route(log_content="x")


# ============================================================
# StrategyRegistry singleton tests
# ============================================================

class TestRegistrySingleton:
    def test_get_instance_returns_same_object(self):
        StrategyRegistry.reset_instance()
        a = StrategyRegistry.get_instance()
        b = StrategyRegistry.get_instance()
        assert a is b

    def test_reset_instance(self):
        StrategyRegistry.reset_instance()
        a = StrategyRegistry.get_instance()
        StrategyRegistry.reset_instance()
        b = StrategyRegistry.get_instance()
        assert a is not b

    def teardown_method(self):
        StrategyRegistry.reset_instance()


# ============================================================
# Edge cases
# ============================================================

class TestEdgeCases:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.registry = StrategyRegistry()
        self.detector = Mock()
        self.router = _make_router(self.registry, self.detector)

    def test_route_with_none_requests_and_metrics(self):
        self.detector.detect.return_value = []
        decision = self.router.route(log_content="x", requests=None, metrics=None)
        assert isinstance(decision, RouteDecision)

    def test_execute_with_empty_strategies_in_decision(self):
        """RouteDecision has scenarios but no strategies -> no valid route."""
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[],
        )
        context = make_context()
        results = self.router.execute(decision, context)
        assert len(results) == 1
        assert results[0].success is False

    def test_handler_returning_none(self):
        handler = Mock(return_value=None)
        strategy = make_strategy(strategy_id="s1", handler=handler)
        decision = RouteDecision(
            scenarios=[make_scenario()],
            selected_strategies=[strategy],
        )
        context = make_context()

        results = self.router.execute(decision, context)
        assert results[0].success is True
        # None is not a dict, so it gets wrapped
        assert results[0].data == {"result": None}

    def test_route_decision_to_dict(self):
        scenario = make_scenario()
        strategy = make_strategy()
        decision = RouteDecision(
            scenarios=[scenario],
            selected_strategies=[strategy],
            reasoning="test reason",
        )
        d = decision.to_dict()
        assert d["has_valid_route"] is True
        assert d["strategy_count"] == 1
        assert d["reasoning"] == "test reason"
        assert len(d["scenarios"]) == 1
        assert len(d["selected_strategies"]) == 1
