# 该文件内容使用AI生成，注意识别准确性
"""
Skill 工具注册体系

提供 @skill 装饰器和 SkillRegistry，将确定性操作封装为可调用的工具。
LLM 只做决策，具体操作由 Skill 执行。
"""

from .registry import SkillRegistry, skill, get_registry
from .data_skills import register_data_skills
from .knowledge_skills import register_knowledge_skills
from .analysis_skills import register_analysis_skills


def init_skills() -> SkillRegistry:
    """初始化并注册所有 Skill，返回全局注册表"""
    registry = get_registry()
    register_data_skills(registry)
    register_knowledge_skills(registry)
    register_analysis_skills(registry)
    return registry


__all__ = [
    "SkillRegistry",
    "skill",
    "get_registry",
    "init_skills",
]
