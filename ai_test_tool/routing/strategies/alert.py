"""
告警处理策略
"""

from typing import Any
from collections import defaultdict

from ..models import ScenarioType, StrategyPriority
from ..registry import strategy, register_strategy, AnalysisStrategy


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
