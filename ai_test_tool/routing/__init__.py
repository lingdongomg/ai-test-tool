"""
智能路由分发器模块

根据日志类型/分析场景，自动选择合适的分析策略

核心组件：
- ScenarioDetector: 场景识别器 - 基于关键词/模式/阈值/LLM识别分析场景
- StrategyRegistry: 策略注册表 - 管理所有分析策略
- IntelligentRouter: 智能路由器 - 协调场景识别和策略执行

使用示例：
```python
from ai_test_tool.routing import IntelligentRouter, create_router

# 方式1: 使用便捷函数创建路由器
router = create_router()

# 方式2: 一站式路由和执行
decision, results = router.route_and_execute(
    log_content="ERROR: Connection refused...",
    user_hint="分析错误"
)

# 方式3: 分步执行
decision = router.route(log_content=log_content)
results = router.execute(decision, context)

# 注册自定义策略
from ai_test_tool.routing import strategy, ScenarioType, StrategyPriority

@strategy(
    strategy_id="my_custom_strategy",
    name="自定义策略",
    scenario_types=[ScenarioType.ERROR_ANALYSIS],
    priority=StrategyPriority.HIGH
)
def my_handler(context: dict) -> dict:
    return {"result": "..."}
```
"""

from .models import (
    AnalysisScenario,
    AnalysisStrategy,
    AnalysisContext,
    AnalysisResult,
    RouteDecision,
    ScenarioType,
    StrategyPriority,
    MatchMethod,
    ScenarioIndicator,
)
from .registry import (
    StrategyRegistry,
    strategy,
    get_registry,
    register_strategy,
    unregister_strategy,
)
from .detector import ScenarioDetector, DetectionRule
from .router import IntelligentRouter, create_router

# 导入内置策略（触发自动注册）
from . import strategies  # noqa: F401

__all__ = [
    # 数据模型
    "AnalysisScenario",
    "AnalysisStrategy",
    "AnalysisContext",
    "AnalysisResult",
    "RouteDecision",
    "ScenarioType",
    "StrategyPriority",
    "MatchMethod",
    "ScenarioIndicator",
    # 场景识别
    "ScenarioDetector",
    "DetectionRule",
    # 策略注册
    "StrategyRegistry",
    "strategy",
    "get_registry",
    "register_strategy",
    "unregister_strategy",
    # 路由器
    "IntelligentRouter",
    "create_router",
]

