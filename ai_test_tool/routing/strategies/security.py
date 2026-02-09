"""
安全分析策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


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
