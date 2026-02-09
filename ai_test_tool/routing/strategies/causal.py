"""
因果分析策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# 因果分析策略（使用因果图推理）
# ============================================================

@strategy(
    strategy_id="causal_root_cause",
    name="因果根因分析",
    scenario_types=[ScenarioType.ROOT_CAUSE],
    description="使用因果图分析找出问题的根本原因",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.6,
    requires_llm=True,
    tags=["causal", "root_cause", "graph"]
)
def analyze_causal_root_cause(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用因果图进行根因分析

    流程：
    1. 从日志/请求构建因果图
    2. 识别根因节点
    3. 分析因果链
    4. 使用LLM增强推理
    """
    from ..causal import RootCauseAnalyzer

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])
    symptoms = context.get("symptoms", [])

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    analyzer = RootCauseAnalyzer()
    result = analyzer.find_root_causes(
        log_content=log_content,
        requests=requests[:100],
        symptoms=symptoms
    )

    return {
        "status": "completed" if result.get("primary_root_cause") else "partial",
        "primary_root_cause": result.get("primary_root_cause"),
        "all_root_causes": result.get("all_root_causes", []),
        "confidence": result.get("confidence", 0),
        "reasoning": result.get("reasoning", ""),
        "causal_chains": result.get("causal_chains", []),
        "recommendations": result.get("recommendations", [])
    }


@strategy(
    strategy_id="causal_impact_assessment",
    name="因果影响评估",
    scenario_types=[ScenarioType.ROOT_CAUSE, ScenarioType.HEALTH_CHECK],
    description="评估问题的影响范围和传播路径",
    priority=StrategyPriority.HIGH,
    min_confidence=0.5,
    requires_llm=False,
    tags=["causal", "impact", "assessment"]
)
def assess_causal_impact(context: dict[str, Any]) -> dict[str, Any]:
    """
    评估问题影响范围

    基于因果图分析故障传播和影响范围
    """
    from ..causal import ImpactAnalyzer

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])
    root_cause = context.get("root_cause", "")

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    analyzer = ImpactAnalyzer()

    if root_cause:
        # 如果已知根因，直接评估影响
        result = analyzer.assess_impact(
            root_cause=root_cause,
            log_content=log_content,
            requests=requests[:100]
        )
    else:
        # 否则预测潜在影响
        # 尝试从请求中识别主要问题组件
        error_count = sum(1 for r in requests if r.get("has_error") or r.get("http_status", 0) >= 400)
        if error_count > len(requests) * 0.1:
            result = analyzer.predict_impact(
                potential_issue="高错误率",
                component="api",
                severity="high" if error_count > len(requests) * 0.3 else "medium"
            )
        else:
            result = {"message": "未检测到明显问题"}

    return {
        "status": "completed",
        **result
    }


@strategy(
    strategy_id="causal_propagation_trace",
    name="因果传播追踪",
    scenario_types=[ScenarioType.ROOT_CAUSE, ScenarioType.ERROR_ANALYSIS],
    description="追踪故障在系统中的传播路径",
    priority=StrategyPriority.HIGH,
    min_confidence=0.5,
    requires_llm=False,
    tags=["causal", "propagation", "trace"]
)
def trace_causal_propagation(context: dict[str, Any]) -> dict[str, Any]:
    """
    追踪故障传播

    分析故障如何从源头传播到各个组件
    """
    from ..causal import PropagationAnalyzer

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])
    start_event = context.get("start_event", "")

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    analyzer = PropagationAnalyzer()

    if start_event:
        # 从指定事件开始追踪
        result = analyzer.trace_propagation(
            start_event=start_event,
            log_content=log_content,
            requests=requests[:100]
        )
    else:
        # 找出关键传播路径
        critical_paths = analyzer.find_critical_paths(
            log_content=log_content,
            requests=requests[:100]
        )
        result = {
            "critical_paths": critical_paths,
            "path_count": len(critical_paths)
        }

    return {
        "status": "completed",
        **result
    }


@strategy(
    strategy_id="causal_full_analysis",
    name="完整因果分析",
    scenario_types=[ScenarioType.ROOT_CAUSE, ScenarioType.ERROR_ANALYSIS, ScenarioType.ANOMALY_DETECTION],
    description="执行完整的因果分析，包括根因定位、影响评估和传播追踪",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.7,
    requires_llm=True,
    tags=["causal", "comprehensive", "analysis"]
)
def analyze_causal_full(context: dict[str, Any]) -> dict[str, Any]:
    """
    完整因果分析

    综合运用因果图构建、根因定位、影响评估和传播分析
    """
    from ..causal import CausalAnalyzer

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])
    focus = context.get("focus", context.get("user_query", ""))

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    analyzer = CausalAnalyzer()
    result = analyzer.analyze(
        log_content=log_content,
        requests=requests[:100],
        focus=focus
    )

    return {
        "status": "completed" if result.has_root_cause else "partial",
        "has_root_cause": result.has_root_cause,
        "primary_root_cause": result.primary_root_cause,
        "root_causes": result.root_causes,
        "causal_chains": [c.to_dict() for c in result.causal_chains[:5]],
        "critical_path": result.critical_path.to_dict() if result.critical_path else None,
        "impact_assessment": result.impact_assessment,
        "affected_components": result.affected_components,
        "confidence": result.overall_confidence,
        "reasoning": result.reasoning,
        "recommendations": result.recommendations,
        "graph_summary": {
            "node_count": result.graph.node_count if result.graph else 0,
            "edge_count": result.graph.edge_count if result.graph else 0,
        },
        "analysis_time_ms": result.analysis_time_ms
    }
