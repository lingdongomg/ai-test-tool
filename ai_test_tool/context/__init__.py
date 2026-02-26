"""
Context Engineering 模块

提供统一的上下文管理能力，包括：
- TokenCounter: Token 计数（估算 / tiktoken 精确计数）
- ContextWindow: 滑动窗口管理
- MessageBuilder: Messages 列表构建器
- ContextCompressor: 上下文压缩
- FileContextStore: 文件系统上下文持久化
"""

from .token_counter import TokenCounter
from .context_window import ContextWindow
from .message_builder import MessageBuilder, Message, MessageRole
from .compressor import ContextCompressor
from .file_store import FileContextStore

__all__ = [
    "TokenCounter",
    "ContextWindow",
    "MessageBuilder",
    "Message",
    "MessageRole",
    "ContextCompressor",
    "FileContextStore",
]
