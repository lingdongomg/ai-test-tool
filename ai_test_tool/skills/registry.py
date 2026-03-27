# 该文件内容使用AI生成，注意识别准确性
"""
Skill 注册表

提供 @skill 装饰器和 SkillRegistry 类。
每个 Skill 是一个普通 Python 函数，带有 name/description/parameters 元数据。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str
    description: str
    category: str  # data_query / knowledge / analysis
    parameters: dict[str, str] = field(default_factory=dict)  # {param_name: description}
    returns: str = ""
    func: Callable[..., dict[str, Any]] | None = None


class SkillRegistry:
    """Skill 工具注册表"""

    def __init__(self):
        self._skills: dict[str, SkillMetadata] = {}

    def register(self, metadata: SkillMetadata) -> None:
        """注册一个 Skill"""
        self._skills[metadata.name] = metadata
        logger.debug(f"Skill 注册: {metadata.name} ({metadata.category})")

    def get(self, name: str) -> SkillMetadata | None:
        """获取 Skill 元数据"""
        return self._skills.get(name)

    def execute(self, name: str, **kwargs) -> dict[str, Any]:
        """执行 Skill"""
        meta = self._skills.get(name)
        if not meta or not meta.func:
            return {"error": f"Skill '{name}' 未注册或无可执行函数"}
        try:
            return meta.func(**kwargs)
        except Exception as e:
            logger.error(f"Skill '{name}' 执行失败: {e}")
            return {"error": str(e)}

    def list_skills(self, category: str | None = None) -> list[SkillMetadata]:
        """列出所有 Skill（可按分类过滤）"""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    def get_descriptions(self, category: str | None = None) -> list[dict[str, Any]]:
        """获取 Skill 描述（用于传给 LLM 做决策）"""
        return [
            {
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
            }
            for s in self.list_skills(category)
        ]

    @property
    def count(self) -> int:
        return len(self._skills)


# 全局单例
_global_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    """获取全局 Skill 注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry


def skill(
    name: str,
    description: str,
    category: str = "data_query",
    parameters: dict[str, str] | None = None,
    returns: str = "",
):
    """
    @skill 装饰器，自动注册函数为 Skill

    用法:
        @skill("get_error_stats", "统计错误数量", category="data_query",
               parameters={"task_id": "任务ID", "hours": "统计时间范围(小时)"})
        def get_error_stats(task_id: str = "", hours: int = 24) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        metadata = SkillMetadata(
            name=name,
            description=description,
            category=category,
            parameters=parameters or {},
            returns=returns,
            func=func,
        )
        get_registry().register(metadata)
        return func
    return decorator
