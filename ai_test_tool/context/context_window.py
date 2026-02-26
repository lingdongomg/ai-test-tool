"""
上下文窗口管理器

管理消息列表的 token 预算，支持滑动窗口、自动截断
"""

import logging
from typing import Any

from .token_counter import TokenCounter
from .message_builder import MessageBuilder, MessageRole

logger = logging.getLogger(__name__)


class ContextWindow:
    """
    上下文窗口管理器

    功能：
    1. 维护 token 预算，自动丢弃旧消息
    2. 保护 system 消息不被丢弃
    3. 跟踪 token 使用统计
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        reserved_for_output: int = 2000,
        token_counter: TokenCounter | None = None,
    ):
        """
        Args:
            max_tokens: 模型的最大上下文长度
            reserved_for_output: 为输出预留的 token 数
            token_counter: Token 计数器
        """
        self.max_tokens = max_tokens
        self.reserved_for_output = reserved_for_output
        self.token_counter = token_counter or TokenCounter()

        # 统计
        self._total_tokens_processed = 0
        self._messages_dropped = 0

    @property
    def available_tokens(self) -> int:
        """可用于输入的 token 数"""
        return self.max_tokens - self.reserved_for_output

    def fit_messages(self, builder: MessageBuilder) -> MessageBuilder:
        """
        将消息列表调整到窗口大小内

        策略：保留 system 消息，从最早的非 system 消息开始丢弃

        Args:
            builder: 消息构建器

        Returns:
            调整后的消息构建器
        """
        messages = builder.build()
        current_tokens = self.token_counter.count_messages(messages)
        self._total_tokens_processed += current_tokens

        while current_tokens > self.available_tokens and builder.size > 1:
            builder.pop_oldest_non_system()
            messages = builder.build()
            current_tokens = self.token_counter.count_messages(messages)
            self._messages_dropped += 1

        return builder

    def get_token_usage(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """
        获取 token 使用详情

        Args:
            messages: 消息列表

        Returns:
            token 使用统计
        """
        used = self.token_counter.count_messages(messages)
        return {
            "used": used,
            "available": self.available_tokens,
            "max": self.max_tokens,
            "reserved_for_output": self.reserved_for_output,
            "utilization": round(used / self.available_tokens, 4) if self.available_tokens > 0 else 0,
        }

    def get_statistics(self) -> dict[str, int]:
        """获取累计统计"""
        return {
            "total_tokens_processed": self._total_tokens_processed,
            "messages_dropped": self._messages_dropped,
        }
