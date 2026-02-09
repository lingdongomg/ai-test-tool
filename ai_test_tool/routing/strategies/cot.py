"""
CoT 链式推理策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# CoT 高级分析策略（使用链式推理）
# ============================================================

@strategy(
    strategy_id="error_diagnosis_cot",
    name="CoT错误诊断",
    scenario_types=[ScenarioType.ERROR_ANALYSIS, ScenarioType.ROOT_CAUSE],
    description="使用CoT链式推理进行深度错误诊断",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.6,
    requires_llm=True,
    tags=["error", "cot", "advanced", "diagnosis"]
)
def analyze_errors_cot(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用CoT链式推理进行错误诊断

    推理链步骤：
    1. 错误识别 → 2. 上下文分析 → 3. 模式匹配 → 4. 影响评估 → 5. 解决建议
    """
    from ..reasoning import ErrorDiagnosisChain

    log_content = context.get("log_content", "")
    if not log_content:
        # 从请求中构建日志内容
        requests = context.get("requests", [])
        log_lines = []
        for req in requests:
            if req.get("has_error") or req.get("http_status", 0) >= 400:
                log_lines.append(
                    f"[{req.get('timestamp', '')}] {req.get('method', '')} {req.get('url', '')} "
                    f"- {req.get('http_status', '')} - {req.get('error_message', '')}"
                )
        log_content = "\n".join(log_lines[:100])

    if not log_content:
        return {
            "status": "no_data",
            "message": "无错误日志可分析"
        }

    # 执行CoT推理
    chain = ErrorDiagnosisChain()
    result = chain.diagnose(log_content)

    return {
        "status": "completed" if result.is_success else "partial",
        "chain_status": result.status.value,
        "final_output": result.final_output,
        "thinking_trace": result.thinking_trace,
        "completed_steps": result.completed_steps,
        "total_steps": len(result.steps),
        "execution_time_ms": result.total_execution_time_ms
    }


@strategy(
    strategy_id="performance_analysis_cot",
    name="CoT性能分析",
    scenario_types=[ScenarioType.PERFORMANCE_ANALYSIS],
    description="使用CoT链式推理进行深度性能分析",
    priority=StrategyPriority.HIGH,
    min_confidence=0.5,
    requires_llm=True,
    tags=["performance", "cot", "advanced"]
)
def analyze_performance_cot(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用CoT链式推理进行性能分析

    推理链步骤：
    1. 指标提取 → 2. 基线对比 → 3. 瓶颈定位 → 4. 优化建议
    """
    from ..reasoning import PerformanceAnalysisChain
    import json

    requests = context.get("requests", [])
    if not requests:
        return {
            "status": "no_data",
            "message": "无请求数据可分析"
        }

    # 执行CoT推理
    chain = PerformanceAnalysisChain()
    result = chain.analyze(requests[:100])

    return {
        "status": "completed" if result.is_success else "partial",
        "chain_status": result.status.value,
        "final_output": result.final_output,
        "thinking_trace": result.thinking_trace,
        "completed_steps": result.completed_steps,
        "total_steps": len(result.steps),
        "execution_time_ms": result.total_execution_time_ms
    }


@strategy(
    strategy_id="root_cause_cot",
    name="CoT根因分析",
    scenario_types=[ScenarioType.ROOT_CAUSE],
    description="使用CoT链式推理进行根因分析",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.7,
    requires_llm=True,
    tags=["root_cause", "cot", "advanced", "diagnosis"]
)
def analyze_root_cause_cot(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用CoT链式推理进行根因分析

    推理链步骤：
    1. 症状收集 → 2. 时序分析 → 3. 因果推理 → 4. 根因定位 → 5. 验证建议
    """
    from ..reasoning import RootCauseChain

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    # 执行CoT推理
    chain = RootCauseChain()
    result = chain.analyze(log_content=log_content, requests=requests[:50])

    return {
        "status": "completed" if result.is_success else "partial",
        "chain_status": result.status.value,
        "root_cause": result.get_step_output("root_cause"),
        "verification": result.get_step_output("verification"),
        "final_output": result.final_output,
        "thinking_trace": result.thinking_trace,
        "completed_steps": result.completed_steps,
        "total_steps": len(result.steps),
        "execution_time_ms": result.total_execution_time_ms
    }


@strategy(
    strategy_id="security_audit_cot",
    name="CoT安全审计",
    scenario_types=[ScenarioType.SECURITY_ANALYSIS],
    description="使用CoT链式推理进行安全审计",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.6,
    requires_llm=True,
    tags=["security", "cot", "advanced", "audit"]
)
def analyze_security_cot(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用CoT链式推理进行安全审计

    推理链步骤：
    1. 威胁识别 → 2. 漏洞分析 → 3. 风险评估 → 4. 修复建议
    """
    from ..reasoning import SecurityAuditChain

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    # 执行CoT推理
    chain = SecurityAuditChain()
    result = chain.audit(log_content=log_content, requests=requests[:50])

    return {
        "status": "completed" if result.is_success else "partial",
        "chain_status": result.status.value,
        "threats": result.get_step_output("threats"),
        "risk_assessment": result.get_step_output("risk_assessment"),
        "recommendations": result.get_step_output("recommendations"),
        "final_output": result.final_output,
        "thinking_trace": result.thinking_trace,
        "completed_steps": result.completed_steps,
        "total_steps": len(result.steps),
        "execution_time_ms": result.total_execution_time_ms
    }
