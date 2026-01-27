"""
策略注册表

管理所有分析策略的注册、查询、匹配
"""

import logging
from typing import Any, Callable
from functools import wraps

from .models import (
    AnalysisStrategy,
    AnalysisScenario,
    ScenarioType,
    StrategyPriority,
    StrategyHandler,
    AsyncStrategyHandler,
)

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    策略注册表

    功能：
    1. 注册/注销分析策略
    2. 按场景类型查询匹配策略
    3. 支持装饰器方式注册
    4. 策略优先级排序
    """

    # 全局单例实例
    _instance: "StrategyRegistry | None" = None

    def __init__(self):
        self._strategies: dict[str, AnalysisStrategy] = {}
        self._scenario_index: dict[ScenarioType, list[str]] = {}

    @classmethod
    def get_instance(cls) -> "StrategyRegistry":
        """获取全局单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（测试用）"""
        cls._instance = None

    def register(self, strategy: AnalysisStrategy) -> None:
        """
        注册策略

        Args:
            strategy: 分析策略实例
        """
        if strategy.strategy_id in self._strategies:
            logger.warning(f"策略 {strategy.strategy_id} 已存在，将被覆盖")

        self._strategies[strategy.strategy_id] = strategy

        # 更新场景索引
        for scenario_type in strategy.scenario_types:
            if scenario_type not in self._scenario_index:
                self._scenario_index[scenario_type] = []
            if strategy.strategy_id not in self._scenario_index[scenario_type]:
                self._scenario_index[scenario_type].append(strategy.strategy_id)

        logger.debug(f"注册策略: {strategy.strategy_id} -> {[s.value for s in strategy.scenario_types]}")

    def unregister(self, strategy_id: str) -> bool:
        """
        注销策略

        Args:
            strategy_id: 策略ID

        Returns:
            是否成功注销
        """
        if strategy_id not in self._strategies:
            return False

        strategy = self._strategies.pop(strategy_id)

        # 更新场景索引
        for scenario_type in strategy.scenario_types:
            if scenario_type in self._scenario_index:
                if strategy_id in self._scenario_index[scenario_type]:
                    self._scenario_index[scenario_type].remove(strategy_id)

        logger.debug(f"注销策略: {strategy_id}")
        return True

    def get(self, strategy_id: str) -> AnalysisStrategy | None:
        """获取策略"""
        return self._strategies.get(strategy_id)

    def get_all(self) -> list[AnalysisStrategy]:
        """获取所有策略"""
        return list(self._strategies.values())

    def find_by_scenario(
        self,
        scenario: AnalysisScenario,
        require_llm: bool | None = None
    ) -> list[AnalysisStrategy]:
        """
        根据场景查找匹配的策略

        Args:
            scenario: 分析场景
            require_llm: 是否必须使用LLM（None表示不限制）

        Returns:
            匹配的策略列表（按优先级排序）
        """
        strategy_ids = self._scenario_index.get(scenario.scenario_type, [])
        matched: list[AnalysisStrategy] = []

        for strategy_id in strategy_ids:
            strategy = self._strategies.get(strategy_id)
            if not strategy:
                continue

            # 检查置信度要求
            if scenario.confidence < strategy.min_confidence:
                continue

            # 检查LLM要求
            if require_llm is not None and strategy.requires_llm != require_llm:
                continue

            matched.append(strategy)

        # 按优先级排序（高优先级在前）
        matched.sort(key=lambda s: s.priority.value, reverse=True)

        return matched

    def find_by_scenario_type(
        self,
        scenario_type: ScenarioType
    ) -> list[AnalysisStrategy]:
        """
        根据场景类型查找策略

        Args:
            scenario_type: 场景类型

        Returns:
            匹配的策略列表
        """
        strategy_ids = self._scenario_index.get(scenario_type, [])
        strategies = [
            self._strategies[sid]
            for sid in strategy_ids
            if sid in self._strategies
        ]
        strategies.sort(key=lambda s: s.priority.value, reverse=True)
        return strategies

    def find_by_tags(self, tags: list[str]) -> list[AnalysisStrategy]:
        """
        根据标签查找策略

        Args:
            tags: 标签列表

        Returns:
            包含任意标签的策略列表
        """
        tag_set = set(tags)
        matched = [
            s for s in self._strategies.values()
            if tag_set & set(s.tags)
        ]
        matched.sort(key=lambda s: s.priority.value, reverse=True)
        return matched

    def get_statistics(self) -> dict[str, Any]:
        """获取注册表统计信息"""
        scenario_counts: dict[str, int] = {}
        for scenario_type, strategy_ids in self._scenario_index.items():
            scenario_counts[scenario_type.value] = len(strategy_ids)

        priority_counts: dict[str, int] = {}
        for strategy in self._strategies.values():
            priority_name = strategy.priority.name
            priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1

        return {
            "total_strategies": len(self._strategies),
            "scenario_coverage": scenario_counts,
            "priority_distribution": priority_counts,
            "llm_required_count": sum(1 for s in self._strategies.values() if s.requires_llm),
            "async_count": sum(1 for s in self._strategies.values() if s.is_async)
        }

    @property
    def size(self) -> int:
        """策略数量"""
        return len(self._strategies)

    def __contains__(self, strategy_id: str) -> bool:
        return strategy_id in self._strategies

    def __len__(self) -> int:
        return len(self._strategies)


def strategy(
    strategy_id: str,
    name: str,
    scenario_types: list[ScenarioType],
    description: str = "",
    priority: StrategyPriority = StrategyPriority.MEDIUM,
    min_confidence: float = 0.3,
    requires_llm: bool = False,
    is_async: bool = False,
    tags: list[str] | None = None,
    auto_register: bool = True
) -> Callable[[StrategyHandler | AsyncStrategyHandler], StrategyHandler | AsyncStrategyHandler]:
    """
    策略注册装饰器

    使用方式：
    ```python
    @strategy(
        strategy_id="error_analysis_basic",
        name="基础错误分析",
        scenario_types=[ScenarioType.ERROR_ANALYSIS],
        priority=StrategyPriority.HIGH
    )
    def analyze_errors(context: dict) -> dict:
        # 分析逻辑
        return {"errors": [...]}
    ```

    Args:
        strategy_id: 策略唯一标识
        name: 策略名称
        scenario_types: 适用场景类型列表
        description: 策略描述
        priority: 优先级
        min_confidence: 最低置信度要求
        requires_llm: 是否需要LLM
        is_async: 是否异步
        tags: 标签列表
        auto_register: 是否自动注册到全局注册表
    """
    def decorator(func: StrategyHandler | AsyncStrategyHandler) -> StrategyHandler | AsyncStrategyHandler:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 创建策略对象
        strategy_obj = AnalysisStrategy(
            strategy_id=strategy_id,
            name=name,
            description=description or func.__doc__ or "",
            scenario_types=scenario_types,
            handler=func,
            priority=priority,
            min_confidence=min_confidence,
            is_async=is_async,
            requires_llm=requires_llm,
            tags=tags or []
        )

        # 将策略对象附加到函数上
        wrapper._strategy = strategy_obj  # type: ignore

        # 自动注册
        if auto_register:
            registry = StrategyRegistry.get_instance()
            registry.register(strategy_obj)

        return wrapper

    return decorator


# 便捷函数
def get_registry() -> StrategyRegistry:
    """获取全局策略注册表"""
    return StrategyRegistry.get_instance()


def register_strategy(strategy: AnalysisStrategy) -> None:
    """注册策略到全局注册表"""
    get_registry().register(strategy)


def unregister_strategy(strategy_id: str) -> bool:
    """从全局注册表注销策略"""
    return get_registry().unregister(strategy_id)
