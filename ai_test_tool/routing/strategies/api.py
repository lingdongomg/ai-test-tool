"""
API 流量与覆盖率分析策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# 流量分析策略
# ============================================================

@strategy(
    strategy_id="traffic_analysis_basic",
    name="基础流量分析",
    scenario_types=[ScenarioType.TRAFFIC_ANALYSIS],
    description="分析请求流量分布和趋势",
    priority=StrategyPriority.LOW,
    min_confidence=0.3,
    tags=["traffic", "statistics"]
)
def analyze_traffic_basic(context: dict[str, Any]) -> dict[str, Any]:
    """基础流量分析策略"""
    requests = context.get("requests", [])

    if not requests:
        return {"summary": {"message": "无请求数据"}, "has_data": False}

    # 按接口统计
    endpoint_counts: dict[str, int] = defaultdict(int)
    method_counts: dict[str, int] = defaultdict(int)
    status_counts: dict[str, int] = defaultdict(int)

    for req in requests:
        endpoint = req.get("url", "").split("?")[0]
        endpoint_counts[endpoint] += 1
        method_counts[req.get("method", "UNKNOWN")] += 1

        status = req.get("http_status", 0)
        if status > 0:
            status_group = f"{status // 100}xx"
            status_counts[status_group] += 1

    # 排序
    top_endpoints = sorted(
        endpoint_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:20]

    return {
        "summary": {
            "total_requests": len(requests),
            "unique_endpoints": len(endpoint_counts),
            "method_distribution": dict(method_counts),
            "status_distribution": dict(status_counts)
        },
        "top_endpoints": [
            {"endpoint": ep, "count": cnt}
            for ep, cnt in top_endpoints
        ],
        "recommendations": []
    }


# ============================================================
# API 覆盖率分析策略
# ============================================================

@strategy(
    strategy_id="api_coverage_basic",
    name="API 覆盖率分析",
    scenario_types=[ScenarioType.API_COVERAGE],
    description="分析日志中的 API 调用覆盖情况",
    priority=StrategyPriority.LOW,
    min_confidence=0.3,
    tags=["coverage", "api"]
)
def analyze_api_coverage(context: dict[str, Any]) -> dict[str, Any]:
    """API 覆盖率分析策略"""
    requests = context.get("requests", [])

    # 提取所有被调用的接口
    called_endpoints: set[str] = set()
    method_endpoint_map: dict[str, set[str]] = defaultdict(set)

    for req in requests:
        url = req.get("url", "").split("?")[0]
        method = req.get("method", "GET")
        key = f"{method} {url}"
        called_endpoints.add(key)
        method_endpoint_map[method].add(url)

    return {
        "summary": {
            "total_unique_endpoints": len(called_endpoints),
            "by_method": {
                method: len(endpoints)
                for method, endpoints in method_endpoint_map.items()
            }
        },
        "called_endpoints": list(called_endpoints)[:100],
        "recommendations": []
    }


# ============================================================
# 健康检查策略
# ============================================================

@strategy(
    strategy_id="health_check_basic",
    name="基础健康检查",
    scenario_types=[ScenarioType.HEALTH_CHECK],
    description="评估服务整体健康状态",
    priority=StrategyPriority.MEDIUM,
    min_confidence=0.3,
    tags=["health", "monitoring"]
)
def analyze_health_basic(context: dict[str, Any]) -> dict[str, Any]:
    """基础健康检查策略"""
    requests = context.get("requests", [])

    if not requests:
        return {
            "health_status": "unknown",
            "score": 0,
            "message": "无数据可分析"
        }

    total = len(requests)
    success = sum(
        1 for r in requests
        if 200 <= r.get("http_status", 0) < 400 and not r.get("has_error")
    )
    errors = sum(1 for r in requests if r.get("has_error") or r.get("http_status", 0) >= 500)

    success_rate = success / total
    error_rate = errors / total

    # 计算健康分数 (0-100)
    score = int(success_rate * 100 - error_rate * 50)
    score = max(0, min(100, score))

    # 确定健康状态
    if score >= 90:
        health_status = "healthy"
    elif score >= 70:
        health_status = "degraded"
    else:
        health_status = "unhealthy"

    return {
        "health_status": health_status,
        "score": score,
        "metrics": {
            "total_requests": total,
            "success_count": success,
            "error_count": errors,
            "success_rate": f"{success_rate:.2%}",
            "error_rate": f"{error_rate:.2%}"
        },
        "recommendations": []
    }
