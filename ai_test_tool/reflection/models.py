"""
Reflection 数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ReflectionConfig:
    """Reflection 配置"""
    max_rounds: int = 3           # 最大反思轮数
    pass_threshold: float = 0.7   # 通过阈值（0-1）
    enabled: bool = False         # 是否启用（默认关闭）


@dataclass
class ReflectionResult:
    """
    反思评估结果

    LLM 对输出的评估，包含评分和改进建议
    """
    score: float                  # 评分 (0-1)
    passed: bool                  # 是否通过
    feedback: str                 # 评估反馈
    issues: list[str] = field(default_factory=list)  # 发现的问题
    suggestions: list[str] = field(default_factory=list)  # 改进建议
    round_number: int = 0         # 反思轮次
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "feedback": self.feedback,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "round_number": self.round_number,
        }


@dataclass
class RefinedOutput:
    """
    修正后的输出

    基于反思结果对原始输出的修正
    """
    original: str                 # 原始输出
    refined: str                  # 修正后输出
    reflections: list[ReflectionResult] = field(default_factory=list)  # 反思历史
    total_rounds: int = 0         # 总轮数
    final_passed: bool = False    # 最终是否通过

    @property
    def improved(self) -> bool:
        """输出是否有改进"""
        return self.refined != self.original

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original[:500],
            "refined": self.refined[:500],
            "total_rounds": self.total_rounds,
            "final_passed": self.final_passed,
            "improved": self.improved,
            "reflections": [r.to_dict() for r in self.reflections],
        }
