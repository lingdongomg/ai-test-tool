"""
根因分析策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


# 根因分析策略（需要 LLM）
# ============================================================

@strategy(
    strategy_id="root_cause_basic",
    name="基础根因分析",
    scenario_types=[ScenarioType.ROOT_CAUSE],
    description="基于规则的根因分析",
    priority=StrategyPriority.HIGH,
    min_confidence=0.5,
    requires_llm=False,
    tags=["root_cause", "diagnosis"]
)
def analyze_root_cause_basic(context: dict[str, Any]) -> dict[str, Any]:
    """基础根因分析策略"""
    requests = context.get("requests", [])
    scenario = context.get("scenario", {})

    # 收集错误信息
    errors = [r for r in requests if r.get("has_error") or r.get("http_status", 0) >= 400]

    if not errors:
        return {
            "root_cause": "未发现明显错误",
            "confidence": 0.5,
            "evidence": []
        }

    # 分析错误模式
    error_patterns: dict[str, list[dict]] = defaultdict(list)

    for err in errors:
        status = err.get("http_status", 0)
        msg = err.get("error_message", "")

        if status >= 500:
            error_patterns["server_error"].append(err)
        elif status == 401 or status == 403:
            error_patterns["auth_error"].append(err)
        elif status == 404:
            error_patterns["not_found"].append(err)
        elif status >= 400:
            error_patterns["client_error"].append(err)

        if "timeout" in msg.lower():
            error_patterns["timeout"].append(err)
        if "connection" in msg.lower():
            error_patterns["connection_error"].append(err)

    # 确定最可能的根因
    if error_patterns["timeout"]:
        root_cause = "服务响应超时，可能是下游服务慢或资源不足"
        evidence = error_patterns["timeout"][:5]
    elif error_patterns["connection_error"]:
        root_cause = "连接错误，可能是网络问题或服务不可用"
        evidence = error_patterns["connection_error"][:5]
    elif error_patterns["server_error"]:
        root_cause = "服务器内部错误，需要检查服务端日志"
        evidence = error_patterns["server_error"][:5]
    elif error_patterns["auth_error"]:
        root_cause = "认证/授权问题，检查 token 或权限配置"
        evidence = error_patterns["auth_error"][:5]
    else:
        root_cause = "多种错误混合，需要进一步分析"
        evidence = errors[:5]

    return {
        "root_cause": root_cause,
        "confidence": 0.7,
        "error_distribution": {k: len(v) for k, v in error_patterns.items()},
        "evidence": [
            {"url": e.get("url"), "status": e.get("http_status"), "message": e.get("error_message", "")[:100]}
            for e in evidence
        ],
        "recommendations": [
            "检查服务端日志获取详细错误信息",
            "确认依赖服务状态",
            "检查近期是否有配置变更"
        ]
    }
