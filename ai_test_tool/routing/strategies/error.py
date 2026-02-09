"""
错误分析策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# 错误分析策略
# ============================================================

@strategy(
    strategy_id="error_analysis_basic",
    name="基础错误分析",
    scenario_types=[ScenarioType.ERROR_ANALYSIS],
    description="分析日志中的错误信息，统计错误类型和频率",
    priority=StrategyPriority.HIGH,
    min_confidence=0.3,
    tags=["error", "basic"]
)
def analyze_errors_basic(context: dict[str, Any]) -> dict[str, Any]:
    """基础错误分析策略"""
    requests = context.get("requests", [])
    log_content = context.get("log_content", "")

    errors: list[dict[str, Any]] = []
    error_types: dict[str, int] = defaultdict(int)
    affected_endpoints: dict[str, int] = defaultdict(int)

    # 从请求中提取错误
    for req in requests:
        if req.get("has_error") or req.get("http_status", 0) >= 400:
            error_info = {
                "url": req.get("url", ""),
                "method": req.get("method", ""),
                "status_code": req.get("http_status", 0),
                "error_message": req.get("error_message", ""),
                "timestamp": req.get("timestamp", "")
            }
            errors.append(error_info)

            # 分类错误
            status = req.get("http_status", 0)
            if status >= 500:
                error_types["5xx_server_error"] += 1
            elif status >= 400:
                error_types["4xx_client_error"] += 1
            if req.get("has_error"):
                error_types["application_error"] += 1

            # 统计受影响接口
            endpoint = f"{req.get('method', '')} {req.get('url', '').split('?')[0]}"
            affected_endpoints[endpoint] += 1

    # 从日志内容中提取额外错误信息
    import re
    error_patterns = [
        (r"(?i)(exception|error):\s*(.+?)(?:\n|$)", "exception"),
        (r"(?i)(failed|failure)\s+to\s+(.+?)(?:\n|$)", "failure"),
        (r"Traceback \(most recent call last\):", "traceback"),
    ]

    log_errors: list[dict[str, str]] = []
    for pattern, error_type in error_patterns:
        matches = re.findall(pattern, log_content)
        for match in matches[:10]:  # 限制数量
            log_errors.append({
                "type": error_type,
                "message": match[1] if isinstance(match, tuple) else str(match)
            })
            error_types[error_type] += 1

    # 计算统计
    total_requests = len(requests)
    error_count = len(errors)
    error_rate = error_count / total_requests if total_requests > 0 else 0

    return {
        "summary": {
            "total_errors": error_count,
            "error_rate": f"{error_rate:.2%}",
            "error_types": dict(error_types),
            "top_affected_endpoints": dict(
                sorted(affected_endpoints.items(), key=lambda x: x[1], reverse=True)[:10]
            )
        },
        "errors": errors[:50],  # 限制返回数量
        "log_errors": log_errors,
        "recommendations": _generate_error_recommendations(error_types, error_rate)
    }


def _generate_error_recommendations(
    error_types: dict[str, int],
    error_rate: float
) -> list[str]:
    """生成错误处理建议"""
    recommendations: list[str] = []

    if error_rate > 0.1:
        recommendations.append("错误率较高，建议优先排查高频错误接口")

    if error_types.get("5xx_server_error", 0) > 0:
        recommendations.append("存在服务器错误，检查服务端日志和资源状态")

    if error_types.get("4xx_client_error", 0) > 0:
        recommendations.append("存在客户端错误，检查请求参数和认证状态")

    if error_types.get("traceback", 0) > 0:
        recommendations.append("发现异常堆栈，建议定位具体代码位置")

    if not recommendations:
        recommendations.append("错误数量较少，系统整体运行正常")

    return recommendations
