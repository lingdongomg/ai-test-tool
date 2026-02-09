"""
健康度评分策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# 健康度评分策略
# ============================================================

@strategy(
    strategy_id="health_score_basic",
    name="基础健康度评分",
    scenario_types=[ScenarioType.HEALTH_CHECK],
    description="计算系统/组件的健康度评分",
    priority=StrategyPriority.MEDIUM,
    min_confidence=0.5,
    requires_llm=False,
    tags=["health", "score", "metrics"]
)
def calculate_health_score(context: dict[str, Any]) -> dict[str, Any]:
    """
    计算健康度评分

    基于多维指标：
    1. 可用性
    2. 错误率
    3. 延迟
    4. 吞吐量
    """
    from ..health import (
        HealthScoreEngine,
        create_availability_metric,
        create_error_rate_metric,
        create_latency_metric,
    )

    requests = context.get("requests", [])

    if not requests:
        return {
            "status": "no_data",
            "message": "无请求数据可分析"
        }

    # 计算指标
    total = len(requests)
    success = sum(
        1 for r in requests
        if 200 <= r.get("http_status", 0) < 400 and not r.get("has_error")
    )
    errors = sum(
        1 for r in requests
        if r.get("has_error") or r.get("http_status", 0) >= 500
    )

    # 计算响应时间
    response_times = [
        r.get("response_time_ms", 0)
        for r in requests
        if r.get("response_time_ms", 0) > 0
    ]

    availability = (success / total * 100) if total > 0 else 0
    error_rate = (errors / total * 100) if total > 0 else 0
    avg_latency = sum(response_times) / len(response_times) if response_times else 0

    # 创建健康度引擎
    engine = HealthScoreEngine()

    # 注册组件
    engine.register_component(
        component_id="api_service",
        name="API服务",
        component_type="service",
    )

    # 添加指标
    engine.add_metric("api_service", create_availability_metric(value=availability))
    engine.add_metric("api_service", create_error_rate_metric(value=error_rate))
    engine.add_metric("api_service", create_latency_metric(value=avg_latency))

    # 获取健康状态
    summary = engine.get_summary()
    component_health = engine.get_component_health("api_service")

    return {
        "status": "completed",
        "system_summary": summary,
        "component_health": component_health,
        "metrics": {
            "availability": f"{availability:.2f}%",
            "error_rate": f"{error_rate:.2f}%",
            "avg_latency_ms": round(avg_latency, 2),
            "total_requests": total,
        },
        "recommendations": _generate_health_recommendations(
            availability, error_rate, avg_latency
        )
    }


def _generate_health_recommendations(
    availability: float,
    error_rate: float,
    avg_latency: float
) -> list[str]:
    """生成健康建议"""
    recommendations: list[str] = []

    if availability < 95:
        recommendations.append(f"可用性 {availability:.1f}% 低于阈值，需要排查服务问题")

    if error_rate > 5:
        recommendations.append(f"错误率 {error_rate:.1f}% 过高，检查错误日志")

    if avg_latency > 1000:
        recommendations.append(f"平均延迟 {avg_latency:.0f}ms 过高，优化性能")

    if not recommendations:
        recommendations.append("系统健康状态良好")

    return recommendations


@strategy(
    strategy_id="health_report_full",
    name="完整健康报告",
    scenario_types=[ScenarioType.HEALTH_CHECK],
    description="生成完整的系统健康报告",
    priority=StrategyPriority.HIGH,
    min_confidence=0.6,
    requires_llm=False,
    tags=["health", "report", "comprehensive"]
)
def generate_health_report(context: dict[str, Any]) -> dict[str, Any]:
    """
    生成完整健康报告

    包含：
    1. 各组件健康状态
    2. 趋势分析
    3. 问题列表
    4. 改进建议
    """
    from ..health import (
        HealthScoreEngine,
        ComponentHealthBuilder,
        HealthStatus,
    )

    requests = context.get("requests", [])

    if not requests:
        return {
            "status": "no_data",
            "message": "无请求数据"
        }

    # 按服务分组请求
    service_requests: dict[str, list] = defaultdict(list)
    for req in requests:
        service = _extract_service_from_url(req.get("url", ""))
        service_requests[service].append(req)

    # 创建引擎
    engine = HealthScoreEngine()

    # 为每个服务创建组件
    for service, reqs in service_requests.items():
        total = len(reqs)
        success = sum(
            1 for r in reqs
            if 200 <= r.get("http_status", 0) < 400
        )
        errors = sum(1 for r in reqs if r.get("http_status", 0) >= 500)
        response_times = [r.get("response_time_ms", 0) for r in reqs if r.get("response_time_ms")]

        availability = (success / total * 100) if total > 0 else 0
        error_rate = (errors / total * 100) if total > 0 else 0
        avg_latency = sum(response_times) / len(response_times) if response_times else 0

        # 使用构建器创建组件
        component = (
            ComponentHealthBuilder(service, f"{service}服务")
            .set_type("service")
            .add_availability_metric(value=availability)
            .add_error_rate_metric(value=error_rate)
            .add_latency_metric(value=avg_latency)
            .build()
        )

        engine.system.add_component(component)

    # 生成报告
    report = engine.generate_report()

    return {
        "status": "completed",
        "report": report.to_dict(),
        "summary": report.summary,
        "overall_score": round(report.overall_score, 2),
        "overall_status": report.overall_status.value,
        "issues": report.issues[:20],
        "recommendations": report.recommendations[:10],
        "components_count": engine.system.total_components,
        "unhealthy_components": [
            c.name for c in engine.system.unhealthy_components
        ]
    }


@strategy(
    strategy_id="health_trend_analysis",
    name="健康趋势分析",
    scenario_types=[ScenarioType.HEALTH_CHECK, ScenarioType.ANOMALY_DETECTION],
    description="分析系统健康度变化趋势",
    priority=StrategyPriority.MEDIUM,
    min_confidence=0.5,
    requires_llm=False,
    tags=["health", "trend", "analysis"]
)
def analyze_health_trend(context: dict[str, Any]) -> dict[str, Any]:
    """
    分析健康趋势

    检测健康度是否在改善、稳定还是恶化
    """
    from ..health import (
        HealthScoreEngine,
        TrendDirection,
        create_error_rate_metric,
    )
    from datetime import datetime, timedelta

    requests = context.get("requests", [])

    if not requests:
        return {
            "status": "no_data",
            "message": "无请求数据"
        }

    # 按时间段分组
    time_buckets: dict[str, list] = defaultdict(list)

    for req in requests:
        ts = req.get("timestamp", "")
        if ts:
            # 简化：按小时分组
            hour = ts[:13] if len(ts) >= 13 else ts[:10]
            time_buckets[hour].append(req)

    if len(time_buckets) < 2:
        return {
            "status": "insufficient_data",
            "message": "时间跨度不足，无法分析趋势"
        }

    # 计算每个时间段的错误率
    trend_data: list[dict] = []
    for time_key in sorted(time_buckets.keys()):
        reqs = time_buckets[time_key]
        total = len(reqs)
        errors = sum(1 for r in reqs if r.get("has_error") or r.get("http_status", 0) >= 400)
        error_rate = (errors / total * 100) if total > 0 else 0

        trend_data.append({
            "time": time_key,
            "total_requests": total,
            "error_count": errors,
            "error_rate": round(error_rate, 2),
            "health_score": round(100 - error_rate * 2, 2)  # 简单计算
        })

    # 分析趋势
    if len(trend_data) >= 3:
        recent_scores = [d["health_score"] for d in trend_data[-3:]]
        changes = [recent_scores[i] - recent_scores[i-1] for i in range(1, len(recent_scores))]
        avg_change = sum(changes) / len(changes)

        if avg_change > 5:
            trend = "improving"
            trend_message = "健康度正在改善"
        elif avg_change < -5:
            trend = "degrading"
            trend_message = "健康度正在恶化，需要关注"
        else:
            trend = "stable"
            trend_message = "健康度保持稳定"
    else:
        trend = "unknown"
        trend_message = "数据不足，无法判断趋势"

    return {
        "status": "completed",
        "trend": trend,
        "trend_message": trend_message,
        "trend_data": trend_data,
        "latest_health_score": trend_data[-1]["health_score"] if trend_data else 0,
        "recommendations": [
            "持续监控健康度变化",
            "设置健康度告警阈值",
            "定期检查问题组件"
        ] if trend == "degrading" else ["系统运行正常"]
    }
