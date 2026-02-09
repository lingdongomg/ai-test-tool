"""
性能分析策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# 性能分析策略
# ============================================================

@strategy(
    strategy_id="performance_analysis_basic",
    name="基础性能分析",
    scenario_types=[ScenarioType.PERFORMANCE_ANALYSIS],
    description="分析请求响应时间，识别性能瓶颈",
    priority=StrategyPriority.MEDIUM,
    min_confidence=0.3,
    tags=["performance", "latency"]
)
def analyze_performance_basic(context: dict[str, Any]) -> dict[str, Any]:
    """基础性能分析策略"""
    requests = context.get("requests", [])

    # 提取响应时间
    response_times: list[float] = []
    endpoint_times: dict[str, list[float]] = defaultdict(list)

    for req in requests:
        rt = req.get("response_time_ms", 0)
        if rt > 0:
            response_times.append(rt)
            endpoint = f"{req.get('method', '')} {req.get('url', '').split('?')[0]}"
            endpoint_times[endpoint].append(rt)

    if not response_times:
        return {
            "summary": {"message": "无响应时间数据"},
            "has_data": False
        }

    # 计算统计指标
    response_times.sort()
    n = len(response_times)

    stats = {
        "count": n,
        "avg_ms": round(sum(response_times) / n, 2),
        "min_ms": round(min(response_times), 2),
        "max_ms": round(max(response_times), 2),
        "p50_ms": round(response_times[n // 2], 2),
        "p90_ms": round(response_times[int(n * 0.9)], 2),
        "p99_ms": round(response_times[int(n * 0.99)], 2) if n >= 100 else None,
    }

    # 识别慢请求
    slow_threshold = max(stats["p90_ms"], 3000)
    slow_requests = [
        {
            "url": req.get("url", ""),
            "method": req.get("method", ""),
            "response_time_ms": req.get("response_time_ms", 0)
        }
        for req in requests
        if req.get("response_time_ms", 0) > slow_threshold
    ]

    # 接口性能排名
    endpoint_stats: list[dict[str, Any]] = []
    for endpoint, times in endpoint_times.items():
        times.sort()
        en = len(times)
        endpoint_stats.append({
            "endpoint": endpoint,
            "count": en,
            "avg_ms": round(sum(times) / en, 2),
            "p90_ms": round(times[int(en * 0.9)], 2) if en > 1 else times[0],
            "max_ms": round(max(times), 2)
        })

    # 按平均响应时间排序
    endpoint_stats.sort(key=lambda x: x["avg_ms"], reverse=True)

    return {
        "summary": stats,
        "slow_requests": slow_requests[:20],
        "slow_threshold_ms": slow_threshold,
        "endpoint_ranking": endpoint_stats[:20],
        "recommendations": _generate_performance_recommendations(stats, endpoint_stats)
    }


def _generate_performance_recommendations(
    stats: dict[str, Any],
    endpoint_stats: list[dict[str, Any]]
) -> list[str]:
    """生成性能优化建议"""
    recommendations: list[str] = []

    avg = stats.get("avg_ms", 0)
    p90 = stats.get("p90_ms", 0)
    p99 = stats.get("p99_ms", 0)

    if avg > 1000:
        recommendations.append(f"平均响应时间 {avg}ms 较高，建议全面优化")

    if p90 > 3000:
        recommendations.append(f"P90 延迟 {p90}ms，存在性能长尾问题")

    if p99 and p99 > p90 * 3:
        recommendations.append("P99 远高于 P90，存在严重的性能抖动")

    if endpoint_stats:
        slowest = endpoint_stats[0]
        if slowest["avg_ms"] > 2000:
            recommendations.append(
                f"最慢接口: {slowest['endpoint']} (平均 {slowest['avg_ms']}ms)"
            )

    if not recommendations:
        recommendations.append("整体性能表现良好")

    return recommendations
