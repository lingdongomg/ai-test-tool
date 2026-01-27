"""
告警智能过滤模块

提供告警去重、聚合、抑制、智能降噪等功能

核心功能：
- 告警去重：基于内容相似度去除重复告警
- 告警聚合：将相关告警合并为告警组
- 告警抑制：基于规则抑制低优先级告警
- 智能降噪：基于历史和模式识别过滤噪音告警
- 优先级排序：根据严重程度和影响范围排序

使用示例：

1. 使用AlertFilter过滤告警：
```python
from ai_test_tool.alerting import AlertFilter, Alert

filter = AlertFilter()
alerts = [
    Alert(alert_id="1", title="CPU高", severity="warning"),
    Alert(alert_id="2", title="CPU高", severity="warning"),  # 重复
    Alert(alert_id="3", title="内存不足", severity="critical"),
]
result = filter.filter(alerts)
print(result.filtered_alerts)  # 去重后的告警
print(result.alert_groups)     # 聚合后的告警组
```

2. 使用规则引擎：
```python
from ai_test_tool.alerting import AlertRuleEngine, SuppressRule

engine = AlertRuleEngine()
engine.add_rule(SuppressRule(
    rule_id="suppress_maintenance",
    name="抑制维护期告警",
    condition=lambda a: a.source == "maintenance_host"
))
```

3. 使用预定义规则：
```python
from ai_test_tool.alerting import (
    AlertRuleEngine,
    MaintenanceWindowRule,
    BusinessHoursRule,
)

engine = AlertRuleEngine()

# 添加维护窗口规则
engine.add_rule(MaintenanceWindowRule(
    rule_id="maint_window",
    name="维护窗口",
    hosts=["server1", "server2"],
    start_time=datetime(2024, 1, 1, 0, 0),
    end_time=datetime(2024, 1, 1, 6, 0),
))

# 添加工作时间规则
engine.add_rule(BusinessHoursRule(
    rule_id="business_hours",
    name="工作时间规则",
    work_start_hour=9,
    work_end_hour=18,
))
```
"""

from .models import (
    Alert,
    AlertGroup,
    AlertRule,
    AlertFilterResult,
    AlertConfig,
    AlertSeverity,
    AlertStatus,
    SuppressRule,
    AggregateRule,
    DedupeRule,
)
from .engine import AlertFilterEngine
from .filter import AlertFilter, create_alert_filter
from .rules import (
    AlertRuleEngine,
    MaintenanceWindowRule,
    SeverityEscalationRule,
    LabelRoutingRule,
    BusinessHoursRule,
    create_rule_engine,
)

__all__ = [
    # 数据模型
    "Alert",
    "AlertGroup",
    "AlertRule",
    "AlertFilterResult",
    "AlertConfig",
    "AlertSeverity",
    "AlertStatus",
    # 规则类型
    "SuppressRule",
    "AggregateRule",
    "DedupeRule",
    # 预定义规则
    "MaintenanceWindowRule",
    "SeverityEscalationRule",
    "LabelRoutingRule",
    "BusinessHoursRule",
    # 引擎
    "AlertFilterEngine",
    "AlertFilter",
    "AlertRuleEngine",
    # 工厂函数
    "create_alert_filter",
    "create_rule_engine",
]
