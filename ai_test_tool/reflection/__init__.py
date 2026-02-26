"""
Reflection 引擎模块

提供输出验证→自我修正循环能力，可组合到任何推理流程中

核心组件：
- ReflectionResult / RefinedOutput: 数据模型
- ReflectionEngine: 反思-修正引擎
"""

from .models import ReflectionResult, RefinedOutput, ReflectionConfig
from .engine import ReflectionEngine

__all__ = [
    "ReflectionResult",
    "RefinedOutput",
    "ReflectionConfig",
    "ReflectionEngine",
]
