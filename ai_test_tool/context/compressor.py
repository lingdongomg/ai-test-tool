"""
上下文压缩器

长上下文压缩策略：截断、摘要
"""

import logging

from .token_counter import TokenCounter

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    上下文压缩器

    当上下文超过限制时，提供多种压缩策略
    """

    def __init__(self, token_counter: TokenCounter | None = None):
        self.token_counter = token_counter or TokenCounter()

    def truncate(self, text: str, max_tokens: int, keep_end: bool = False) -> str:
        """
        截断文本

        Args:
            text: 输入文本
            max_tokens: 最大 token 数
            keep_end: True 保留末尾（截断开头），False 保留开头（截断末尾）

        Returns:
            截断后的文本
        """
        if self.token_counter.count(text) <= max_tokens:
            return text

        if keep_end:
            # 保留末尾：从后往前找合适的截断点
            lines = text.split("\n")
            result_lines: list[str] = []
            for line in reversed(lines):
                candidate = "\n".join([line] + result_lines)
                if self.token_counter.count(candidate) > max_tokens:
                    break
                result_lines.insert(0, line)
            if result_lines:
                return "...(truncated)\n" + "\n".join(result_lines)
            return self.token_counter.truncate_to_fit(text, max_tokens)
        else:
            return self.token_counter.truncate_to_fit(text, max_tokens) + "\n...(truncated)"

    def compress_history(
        self,
        steps: list[dict],
        max_tokens: int,
        keep_recent: int = 3,
    ) -> list[dict]:
        """
        压缩历史步骤

        策略：保留最近 N 步完整内容，更早的步骤只保留摘要

        Args:
            steps: 历史步骤列表（每步包含 thought/action/observation）
            max_tokens: 最大 token 数
            keep_recent: 保留最近的完整步骤数

        Returns:
            压缩后的步骤列表
        """
        if not steps:
            return []

        total = len(steps)
        if total <= keep_recent:
            return steps

        # 最近 N 步保持不变
        recent = steps[-keep_recent:]

        # 更早的步骤压缩为摘要
        older = steps[:-keep_recent]
        compressed_older = []
        for step in older:
            compressed = {
                "step_number": step.get("step_number", "?"),
                "thought": self._summarize_text(step.get("thought", ""), max_chars=100),
                "action": step.get("action", ""),
                "observation": self._summarize_text(step.get("observation", ""), max_chars=80),
            }
            compressed_older.append(compressed)

        result = compressed_older + recent

        # 如果仍然超限，进一步截断旧步骤
        result_text = str(result)
        while self.token_counter.count(result_text) > max_tokens and compressed_older:
            compressed_older.pop(0)
            result = compressed_older + recent
            result_text = str(result)

        return result

    @staticmethod
    def _summarize_text(text: str, max_chars: int = 100) -> str:
        """简单截断摘要"""
        if not text or len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
