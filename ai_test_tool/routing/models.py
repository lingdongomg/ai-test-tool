"""
智能路由分发器 - 数据模型

定义分析场景、策略、路由决策等核心数据结构
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine


class ScenarioType(str, Enum):
    """分析场景类型"""
    ERROR_ANALYSIS = "error_analysis"           # 错误分析
    PERFORMANCE_ANALYSIS = "performance"        # 性能分析
    BUSINESS_ANALYSIS = "business"              # 业务分析
    SECURITY_ANALYSIS = "security"              # 安全分析
    ANOMALY_DETECTION = "anomaly"               # 异常检测
    API_COVERAGE = "api_coverage"               # API覆盖率分析
    TRAFFIC_ANALYSIS = "traffic"                # 流量分析
    ROOT_CAUSE = "root_cause"                   # 根因分析
    HEALTH_CHECK = "health_check"               # 健康检查
    CUSTOM = "custom"                           # 自定义场景


class StrategyPriority(int, Enum):
    """策略优先级"""
    CRITICAL = 100      # 关键（安全、严重错误）
    HIGH = 80           # 高（错误分析）
    MEDIUM = 50         # 中（性能、业务）
    LOW = 30            # 低（统计、覆盖率）
    BACKGROUND = 10     # 后台（缓存预热等）


class MatchMethod(str, Enum):
    """场景匹配方法"""
    KEYWORD = "keyword"         # 关键词匹配
    PATTERN = "pattern"         # 正则模式匹配
    THRESHOLD = "threshold"     # 阈值匹配
    LLM = "llm"                 # LLM智能分类
    COMPOSITE = "composite"     # 组合匹配


@dataclass
class ScenarioIndicator:
    """场景指标 - 用于场景识别的信号"""
    name: str                               # 指标名称
    value: float                            # 指标值 (0-1 归一化)
    weight: float = 1.0                     # 权重
    source: str = ""                        # 来源描述

    @property
    def weighted_value(self) -> float:
        return self.value * self.weight


@dataclass
class AnalysisScenario:
    """
    分析场景

    描述一个具体的分析场景，包含场景类型、置信度、相关指标等
    """
    scenario_type: ScenarioType             # 场景类型
    confidence: float                        # 置信度 (0-1)
    indicators: list[ScenarioIndicator] = field(default_factory=list)  # 支持指标
    match_method: MatchMethod = MatchMethod.KEYWORD  # 匹配方法
    description: str = ""                   # 场景描述
    metadata: dict[str, Any] = field(default_factory=dict)  # 额外元数据

    def __post_init__(self):
        # 确保置信度在有效范围
        self.confidence = max(0.0, min(1.0, self.confidence))

    @property
    def is_high_confidence(self) -> bool:
        """是否高置信度（>0.7）"""
        return self.confidence >= 0.7

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "confidence": self.confidence,
            "match_method": self.match_method.value,
            "description": self.description,
            "indicators": [
                {"name": i.name, "value": i.value, "weight": i.weight}
                for i in self.indicators
            ],
            "metadata": self.metadata
        }


# 策略处理函数类型
StrategyHandler = Callable[[dict[str, Any]], dict[str, Any]]
AsyncStrategyHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


@dataclass
class AnalysisStrategy:
    """
    分析策略

    定义如何处理特定场景的策略，包含处理函数、适用条件等
    """
    strategy_id: str                        # 策略唯一标识
    name: str                               # 策略名称
    description: str                        # 策略描述
    scenario_types: list[ScenarioType]      # 适用的场景类型
    handler: StrategyHandler | AsyncStrategyHandler  # 处理函数
    priority: StrategyPriority = StrategyPriority.MEDIUM  # 优先级
    min_confidence: float = 0.3             # 最低置信度要求
    is_async: bool = False                  # 是否异步处理
    requires_llm: bool = False              # 是否需要LLM
    timeout_seconds: int = 60               # 超时时间
    tags: list[str] = field(default_factory=list)  # 标签
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches_scenario(self, scenario: AnalysisScenario) -> bool:
        """检查策略是否匹配场景"""
        return (
            scenario.scenario_type in self.scenario_types
            and scenario.confidence >= self.min_confidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "scenario_types": [s.value for s in self.scenario_types],
            "priority": self.priority.value,
            "min_confidence": self.min_confidence,
            "is_async": self.is_async,
            "requires_llm": self.requires_llm,
            "tags": self.tags
        }


@dataclass
class RouteDecision:
    """
    路由决策结果

    包含识别的场景、选择的策略、决策理由等
    """
    scenarios: list[AnalysisScenario]       # 识别的场景（按置信度排序）
    selected_strategies: list[AnalysisStrategy]  # 选择的策略（按优先级排序）
    primary_scenario: AnalysisScenario | None = None  # 主场景
    primary_strategy: AnalysisStrategy | None = None  # 主策略
    reasoning: str = ""                     # 决策理由
    fallback_strategy: AnalysisStrategy | None = None  # 备用策略
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 自动设置主场景和主策略
        if self.scenarios and not self.primary_scenario:
            self.primary_scenario = self.scenarios[0]
        if self.selected_strategies and not self.primary_strategy:
            self.primary_strategy = self.selected_strategies[0]

    @property
    def has_valid_route(self) -> bool:
        """是否有有效路由"""
        return self.primary_strategy is not None

    @property
    def strategy_count(self) -> int:
        """策略数量"""
        return len(self.selected_strategies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "selected_strategies": [s.to_dict() for s in self.selected_strategies],
            "primary_scenario": self.primary_scenario.to_dict() if self.primary_scenario else None,
            "primary_strategy": self.primary_strategy.to_dict() if self.primary_strategy else None,
            "reasoning": self.reasoning,
            "has_valid_route": self.has_valid_route,
            "strategy_count": self.strategy_count
        }


@dataclass
class AnalysisContext:
    """
    分析上下文

    传递给策略处理函数的上下文信息
    """
    # 原始输入
    log_content: str = ""                   # 日志内容
    log_file_path: str = ""                 # 日志文件路径
    requests: list[dict[str, Any]] = field(default_factory=list)  # 解析的请求

    # 场景信息
    scenario: AnalysisScenario | None = None
    all_scenarios: list[AnalysisScenario] = field(default_factory=list)

    # 配置
    options: dict[str, Any] = field(default_factory=dict)

    # 上下文数据（可在策略间传递）
    shared_data: dict[str, Any] = field(default_factory=dict)

    # 元数据
    task_id: str = ""
    source: str = ""

    def get_option(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.options.get(key, default)

    def set_shared(self, key: str, value: Any) -> None:
        """设置共享数据"""
        self.shared_data[key] = value

    def get_shared(self, key: str, default: Any = None) -> Any:
        """获取共享数据"""
        return self.shared_data.get(key, default)


@dataclass
class AnalysisResult:
    """
    分析结果

    策略执行后的结果
    """
    success: bool                           # 是否成功
    strategy_id: str                        # 执行的策略ID
    scenario_type: ScenarioType             # 场景类型
    data: dict[str, Any] = field(default_factory=dict)  # 结果数据
    error_message: str = ""                 # 错误信息
    execution_time_ms: float = 0            # 执行时间
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "strategy_id": self.strategy_id,
            "scenario_type": self.scenario_type.value,
            "data": self.data,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata
        }
