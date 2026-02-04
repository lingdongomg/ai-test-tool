"""
健康度评分模块

提供系统和组件的健康度评估功能

核心功能：
- 健康度评分：基于多维指标计算健康度评分（0-100）
- 健康检查：支持HTTP、TCP、自定义检查
- 趋势分析：分析健康度变化趋势
- 健康报告：生成综合健康评估报告

使用示例：

1. 基本使用：
```python
from ai_test_tool.health import HealthScoreEngine, create_availability_metric

# 创建引擎
engine = HealthScoreEngine()

# 注册组件
engine.register_component(
    component_id="api-service",
    name="API服务",
    component_type="service",
)

# 添加指标
engine.add_metric("api-service", create_availability_metric(value=99.5))
engine.add_metric("api-service", create_error_rate_metric(value=0.5))

# 获取健康状态
print(engine.get_summary())
```

2. 使用构建器：
```python
from ai_test_tool.health import ComponentHealthBuilder, HealthScoreEngine

# 使用构建器创建组件
component = (
    ComponentHealthBuilder("db", "数据库")
    .set_type("database")
    .add_availability_metric(value=99.9)
    .add_latency_metric(value=50)
    .add_error_rate_metric(value=0.1)
    .build()
)

engine = HealthScoreEngine()
engine.system.add_component(component)
```

3. 健康检查：
```python
from ai_test_tool.health import HealthChecker, create_http_check

checker = HealthChecker()
checker.register(
    check_id="api_health",
    component_id="api-service",
    check_func=create_http_check("http://localhost:8080/health"),
)

result = checker.run("api_health")
print(result.status, result.message)
```

4. 生成报告：
```python
report = engine.generate_report()
print(report.summary)
print(report.recommendations)
```
"""

from .models import (
    HealthMetric,
    ComponentHealth,
    SystemHealth,
    HealthCheckResult,
    HealthConfig,
    HealthReport,
    HealthStatus,
    MetricType,
    TrendDirection,
)
from .engine import (
    HealthScoreEngine,
    create_health_engine,
    create_availability_metric,
    create_latency_metric,
    create_error_rate_metric,
    create_throughput_metric,
    create_saturation_metric,
)
from .checker import (
    HealthChecker,
    ComponentHealthBuilder,
    create_http_check,
    create_tcp_check,
    create_threshold_check,
    create_custom_check,
)

__all__ = [
    # 数据模型
    "HealthMetric",
    "ComponentHealth",
    "SystemHealth",
    "HealthCheckResult",
    "HealthConfig",
    "HealthReport",
    # 枚举
    "HealthStatus",
    "MetricType",
    "TrendDirection",
    # 引擎
    "HealthScoreEngine",
    "create_health_engine",
    # 指标工厂
    "create_availability_metric",
    "create_latency_metric",
    "create_error_rate_metric",
    "create_throughput_metric",
    "create_saturation_metric",
    # 检查器
    "HealthChecker",
    "ComponentHealthBuilder",
    "create_http_check",
    "create_tcp_check",
    "create_threshold_check",
    "create_custom_check",
]
