"""
内置分析策略

提供常用的分析策略实现
"""

from typing import Any
from collections import defaultdict

from .models import ScenarioType, StrategyPriority
from .registry import strategy, register_strategy, AnalysisStrategy


# ============================================================
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


# ============================================================
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


# ============================================================
# 安全分析策略
# ============================================================

@strategy(
    strategy_id="security_analysis_basic",
    name="基础安全分析",
    scenario_types=[ScenarioType.SECURITY_ANALYSIS],
    description="检测潜在的安全威胁和异常访问模式",
    priority=StrategyPriority.CRITICAL,
    min_confidence=0.4,
    tags=["security", "threat"]
)
def analyze_security_basic(context: dict[str, Any]) -> dict[str, Any]:
    """基础安全分析策略"""
    import re
    requests = context.get("requests", [])
    log_content = context.get("log_content", "")

    threats: list[dict[str, Any]] = []
    threat_types: dict[str, int] = defaultdict(int)

    # 安全威胁模式
    security_patterns = [
        (r"(?i)(sql\s*injection|union\s+select|or\s+1\s*=\s*1)", "sql_injection", "high"),
        (r"<script[^>]*>", "xss", "high"),
        (r"(?i)(\.\.\/|\.\.\\)", "path_traversal", "medium"),
        (r"(?i)(unauthorized|forbidden|access\s*denied)", "auth_failure", "low"),
        (r"(?i)(brute\s*force|too\s*many\s*attempts)", "brute_force", "high"),
        (r"(?i)(invalid|expired)\s*token", "token_issue", "medium"),
    ]

    # 检查请求中的安全问题
    for req in requests:
        url = req.get("url", "")
        body = str(req.get("body", ""))
        status = req.get("http_status", 0)

        # 检查 URL 和 body 中的威胁模式
        content = f"{url} {body}"
        for pattern, threat_type, severity in security_patterns:
            if re.search(pattern, content):
                threats.append({
                    "type": threat_type,
                    "severity": severity,
                    "url": url,
                    "method": req.get("method", ""),
                    "evidence": re.search(pattern, content).group(0)[:100]
                })
                threat_types[threat_type] += 1
                break

        # 检查认证失败
        if status in [401, 403]:
            threats.append({
                "type": "auth_failure",
                "severity": "low",
                "url": url,
                "method": req.get("method", ""),
                "status_code": status
            })
            threat_types["auth_failure"] += 1

    # 检查日志内容
    for pattern, threat_type, severity in security_patterns:
        matches = re.findall(pattern, log_content)
        if matches:
            threat_types[f"log_{threat_type}"] += len(matches)

    # 统计分析
    high_threats = sum(1 for t in threats if t.get("severity") == "high")
    medium_threats = sum(1 for t in threats if t.get("severity") == "medium")

    return {
        "summary": {
            "total_threats": len(threats),
            "high_severity": high_threats,
            "medium_severity": medium_threats,
            "threat_types": dict(threat_types)
        },
        "threats": threats[:50],
        "risk_level": "high" if high_threats > 0 else "medium" if medium_threats > 0 else "low",
        "recommendations": _generate_security_recommendations(threat_types)
    }


def _generate_security_recommendations(threat_types: dict[str, int]) -> list[str]:
    """生成安全建议"""
    recommendations: list[str] = []

    if threat_types.get("sql_injection", 0) > 0:
        recommendations.append("检测到 SQL 注入尝试，请检查参数过滤和 PreparedStatement 使用")

    if threat_types.get("xss", 0) > 0:
        recommendations.append("检测到 XSS 攻击尝试，请检查输出编码和 CSP 策略")

    if threat_types.get("brute_force", 0) > 0:
        recommendations.append("检测到暴力破解尝试，建议启用速率限制和账户锁定")

    if threat_types.get("auth_failure", 0) > 10:
        recommendations.append("认证失败次数较多，检查是否存在攻击行为")

    if not recommendations:
        recommendations.append("未发现明显安全威胁")

    return recommendations


# ============================================================
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


# ============================================================
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


# ============================================================
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


# ============================================================
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


# ============================================================
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


# ============================================================
# 告警智能过滤策略
# ============================================================

@strategy(
    strategy_id="alert_filter_basic",
    name="基础告警过滤",
    scenario_types=[ScenarioType.ANOMALY_DETECTION, ScenarioType.HEALTH_CHECK],
    description="对告警进行去重、聚合和抑制处理",
    priority=StrategyPriority.MEDIUM,
    min_confidence=0.5,
    requires_llm=False,
    tags=["alert", "filter", "dedupe"]
)
def filter_alerts_basic(context: dict[str, Any]) -> dict[str, Any]:
    """
    基础告警过滤策略

    功能：
    1. 告警去重
    2. 告警聚合
    3. 告警抑制
    4. 降噪处理
    """
    from ..alerting import AlertFilter, Alert, AlertSeverity

    requests = context.get("requests", [])
    log_content = context.get("log_content", "")

    # 从请求中提取告警
    alerts: list[Alert] = []
    alert_id = 0

    for req in requests:
        if req.get("has_error") or req.get("http_status", 0) >= 400:
            status = req.get("http_status", 0)

            # 确定严重程度
            if status >= 500:
                severity = AlertSeverity.HIGH
            elif status == 401 or status == 403:
                severity = AlertSeverity.MEDIUM
            else:
                severity = AlertSeverity.WARNING

            alert = Alert(
                alert_id=f"alert_{alert_id}",
                title=f"请求错误: {req.get('method', '')} {req.get('url', '').split('?')[0][:50]}",
                description=req.get("error_message", "")[:200],
                severity=severity,
                source="request_log",
                service=_extract_service_from_url(req.get("url", "")),
                host=req.get("host", ""),
            )
            alerts.append(alert)
            alert_id += 1

    # 从日志中提取告警
    import re
    error_patterns = [
        (r"(?i)error[:\s]+(.+?)(?:\n|$)", AlertSeverity.HIGH),
        (r"(?i)exception[:\s]+(.+?)(?:\n|$)", AlertSeverity.HIGH),
        (r"(?i)warning[:\s]+(.+?)(?:\n|$)", AlertSeverity.WARNING),
        (r"(?i)failed[:\s]+(.+?)(?:\n|$)", AlertSeverity.MEDIUM),
    ]

    for pattern, severity in error_patterns:
        matches = re.findall(pattern, log_content)
        for match in matches[:20]:
            alert = Alert(
                alert_id=f"alert_{alert_id}",
                title=f"日志告警: {match[:50]}",
                description=match[:200],
                severity=severity,
                source="log",
            )
            alerts.append(alert)
            alert_id += 1

    if not alerts:
        return {
            "status": "no_alerts",
            "message": "未检测到告警",
            "total_input": 0
        }

    # 执行过滤
    filter_engine = AlertFilter()
    result = filter_engine.filter(alerts)

    return {
        "status": "completed",
        "filter_result": result.to_dict(),
        "filtered_alerts": [a.to_dict() for a in result.filtered_alerts[:50]],
        "alert_groups": [g.to_dict() for g in result.alert_groups[:20]],
        "summary": filter_engine.get_summary(result.filtered_alerts),
        "recommendations": _generate_alert_recommendations(result)
    }


def _extract_service_from_url(url: str) -> str:
    """从URL中提取服务名"""
    import re
    # 尝试提取服务路径
    match = re.search(r"/api/v?\d*/(\w+)", url)
    if match:
        return match.group(1)
    match = re.search(r"/(\w+)/", url)
    if match:
        return match.group(1)
    return "unknown"


def _generate_alert_recommendations(result) -> list[str]:
    """生成告警处理建议"""
    recommendations: list[str] = []

    summary = result.to_dict()

    if summary.get("dedupe_count", 0) > 10:
        recommendations.append(f"去重 {summary['dedupe_count']} 条重复告警，建议检查告警源配置")

    if summary.get("noise_filtered_count", 0) > 5:
        recommendations.append(f"过滤 {summary['noise_filtered_count']} 条噪音告警，建议调整告警阈值")

    severity_counts = summary.get("severity_counts", {})
    if severity_counts.get("critical", 0) > 0:
        recommendations.append("存在严重告警，需要立即处理")

    if severity_counts.get("high", 0) > 5:
        recommendations.append("高级别告警较多，建议优先排查")

    group_count = len(result.alert_groups)
    if group_count > 5:
        recommendations.append(f"告警分为 {group_count} 组，建议按组处理")

    if not recommendations:
        recommendations.append("告警数量正常，系统运行稳定")

    return recommendations


@strategy(
    strategy_id="alert_rule_engine",
    name="规则引擎告警处理",
    scenario_types=[ScenarioType.ANOMALY_DETECTION],
    description="使用规则引擎处理告警，支持自定义规则",
    priority=StrategyPriority.HIGH,
    min_confidence=0.6,
    requires_llm=False,
    tags=["alert", "rules", "engine"]
)
def process_alerts_with_rules(context: dict[str, Any]) -> dict[str, Any]:
    """
    使用规则引擎处理告警

    支持：
    1. 抑制规则
    2. 聚合规则
    3. 升级规则
    4. 路由规则
    """
    from ..alerting import (
        AlertRuleEngine,
        Alert,
        AlertSeverity,
        SeverityEscalationRule,
        BusinessHoursRule,
        create_rule_engine,
    )

    requests = context.get("requests", [])
    custom_rules = context.get("rules", [])

    # 创建规则引擎
    engine = create_rule_engine()

    # 添加自定义规则
    # 例如：工作时间规则
    engine.add_rule(BusinessHoursRule(
        rule_id="business_hours",
        name="工作时间规则",
        work_start_hour=9,
        work_end_hour=18,
    ))

    # 添加升级规则
    engine.add_rule(SeverityEscalationRule(
        rule_id="escalation",
        name="频繁告警升级",
        threshold=5,
        time_window_minutes=10,
    ))

    # 从请求中创建告警
    alerts: list[Alert] = []
    for i, req in enumerate(requests):
        if req.get("has_error") or req.get("http_status", 0) >= 400:
            alert = Alert(
                alert_id=f"alert_{i}",
                title=f"请求错误: {req.get('url', '')[:50]}",
                severity=AlertSeverity.WARNING,
            )
            alerts.append(alert)

    if not alerts:
        return {
            "status": "no_alerts",
            "message": "无告警需要处理"
        }

    # 处理告警
    processed = engine.process_batch(alerts)

    return {
        "status": "completed",
        "input_count": len(alerts),
        "output_count": len(processed),
        "filtered_count": len(alerts) - len(processed),
        "processed_alerts": [a.to_dict() for a in processed[:30]],
        "engine_stats": engine.get_stats(),
        "rules_applied": [r.name for r in engine.list_rules()]
    }


# ============================================================
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
