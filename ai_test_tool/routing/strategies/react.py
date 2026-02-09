"""
ReAct 代理策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# ReAct 交互式分析策略（使用Agent）
# ============================================================

@strategy(
    strategy_id="log_analysis_react",
    name="ReAct日志分析",
    scenario_types=[ScenarioType.ERROR_ANALYSIS, ScenarioType.ROOT_CAUSE, ScenarioType.ANOMALY_DETECTION],
    description="使用ReAct Agent进行交互式日志分析，自主决定分析步骤",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.7,
    requires_llm=True,
    tags=["log", "react", "agent", "interactive"]
)
def analyze_logs_react(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用ReAct Agent进行日志分析

    Agent会自主决定：
    1. 搜索哪些关键词
    2. 过滤哪些请求
    3. 提取哪些模式
    4. 如何关联分析
    """
    from ..react import LogAnalysisAgent

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])
    user_query = context.get("user_query", "分析日志中的错误和异常")

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    # 构建任务描述
    task = f"""请分析提供的日志和请求数据：

用户问题: {user_query}

数据概览:
- 日志内容长度: {len(log_content)} 字符
- 请求记录数: {len(requests)} 条

请：
1. 搜索关键的错误信息
2. 过滤异常请求
3. 识别问题模式
4. 给出分析结论和建议"""

    # 执行ReAct分析
    agent = LogAnalysisAgent()
    result = agent.run(task=task, log_content=log_content, requests=requests[:100])

    return {
        "status": "completed" if result.is_success else "partial",
        "stop_reason": result.stop_reason.value,
        "final_answer": result.final_answer,
        "trajectory": result.trajectory,
        "tool_calls": result.tool_calls_summary,
        "total_iterations": result.total_iterations,
        "total_tool_calls": result.total_tool_calls,
        "execution_time_ms": result.total_execution_time_ms
    }


@strategy(
    strategy_id="performance_debug_react",
    name="ReAct性能调试",
    scenario_types=[ScenarioType.PERFORMANCE_ANALYSIS],
    description="使用ReAct Agent进行交互式性能调试，自主定位瓶颈",
    priority=StrategyPriority.HIGH,
    min_confidence=0.6,
    requires_llm=True,
    tags=["performance", "react", "agent", "debug"]
)
def debug_performance_react(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用ReAct Agent进行性能调试

    Agent会自主：
    1. 计算性能统计
    2. 识别慢请求
    3. 检测性能异常
    4. 定位瓶颈
    """
    from ..react import PerformanceDebugAgent

    requests = context.get("requests", [])
    log_content = context.get("log_content", "")

    if not requests:
        return {
            "status": "no_data",
            "message": "无请求数据可分析"
        }

    task = f"""请分析性能问题：

数据概览:
- 请求记录数: {len(requests)} 条

请：
1. 计算整体性能统计
2. 识别最慢的请求和接口
3. 检测性能异常和波动
4. 定位性能瓶颈
5. 给出优化建议"""

    agent = PerformanceDebugAgent()
    result = agent.run(task=task, log_content=log_content, requests=requests[:200])

    return {
        "status": "completed" if result.is_success else "partial",
        "stop_reason": result.stop_reason.value,
        "final_answer": result.final_answer,
        "trajectory": result.trajectory,
        "tool_calls": result.tool_calls_summary,
        "total_iterations": result.total_iterations,
        "execution_time_ms": result.total_execution_time_ms
    }


@strategy(
    strategy_id="security_investigation_react",
    name="ReAct安全调查",
    scenario_types=[ScenarioType.SECURITY_ANALYSIS],
    description="使用ReAct Agent进行安全事件调查",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.7,
    requires_llm=True,
    tags=["security", "react", "agent", "investigation"]
)
def investigate_security_react(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用ReAct Agent进行安全调查

    Agent会自主：
    1. 检测攻击模式
    2. 分析可疑IP
    3. 追踪安全事件
    4. 评估风险
    """
    from ..react import SecurityInvestigationAgent

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    task = f"""请进行安全调查：

数据概览:
- 日志内容长度: {len(log_content)} 字符
- 请求记录数: {len(requests)} 条

请：
1. 检测常见攻击模式（SQL注入、XSS等）
2. 识别可疑的IP地址和行为
3. 分析认证和授权问题
4. 评估安全风险等级
5. 给出安全建议"""

    agent = SecurityInvestigationAgent()
    result = agent.run(task=task, log_content=log_content, requests=requests[:100])

    return {
        "status": "completed" if result.is_success else "partial",
        "stop_reason": result.stop_reason.value,
        "final_answer": result.final_answer,
        "trajectory": result.trajectory,
        "tool_calls": result.tool_calls_summary,
        "total_iterations": result.total_iterations,
        "execution_time_ms": result.total_execution_time_ms
    }


@strategy(
    strategy_id="anomaly_hunting_react",
    name="ReAct异常猎手",
    scenario_types=[ScenarioType.ANOMALY_DETECTION, ScenarioType.HEALTH_CHECK],
    description="使用ReAct Agent主动搜索和识别各类异常",
    priority=StrategyPriority.HIGH,
    min_confidence=0.5,
    requires_llm=True,
    tags=["anomaly", "react", "agent", "hunting"]
)
def hunt_anomalies_react(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用ReAct Agent进行异常猎取

    Agent会主动：
    1. 全面扫描数据
    2. 检测各类异常
    3. 关联分析事件
    4. 发现隐藏问题
    """
    from ..react import AnomalyHuntingAgent

    log_content = context.get("log_content", "")
    requests = context.get("requests", [])

    if not log_content and not requests:
        return {
            "status": "no_data",
            "message": "无数据可分析"
        }

    task = f"""请主动搜索和识别异常：

数据概览:
- 日志内容长度: {len(log_content)} 字符
- 请求记录数: {len(requests)} 条

请：
1. 全面扫描数据，检测各类异常
2. 分析错误、性能、安全等各维度
3. 关联分析不同事件，找出联系
4. 识别潜在的系统问题
5. 给出发现和建议"""

    agent = AnomalyHuntingAgent()
    result = agent.run(task=task, log_content=log_content, requests=requests[:150])

    return {
        "status": "completed" if result.is_success else "partial",
        "stop_reason": result.stop_reason.value,
        "final_answer": result.final_answer,
        "trajectory": result.trajectory,
        "tool_calls": result.tool_calls_summary,
        "total_iterations": result.total_iterations,
        "execution_time_ms": result.total_execution_time_ms
    }
