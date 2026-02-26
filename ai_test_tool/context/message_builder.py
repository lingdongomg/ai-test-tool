"""
消息构建器

构建 system/user/assistant 消息列表，替代字符串拼接
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """单条消息"""
    role: MessageRole
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}

    @property
    def token_estimate(self) -> int:
        """粗略估算 token 数（不依赖 TokenCounter）"""
        return len(self.content) // 4 + 4


class MessageBuilder:
    """
    Messages 列表构建器

    提供链式 API 构建 system/user/assistant 消息序列
    """

    def __init__(self):
        self._messages: list[Message] = []

    def system(self, content: str, **metadata: Any) -> "MessageBuilder":
        """添加 system 消息"""
        self._messages.append(Message(
            role=MessageRole.SYSTEM,
            content=content,
            metadata=metadata,
        ))
        return self

    def user(self, content: str, **metadata: Any) -> "MessageBuilder":
        """添加 user 消息"""
        self._messages.append(Message(
            role=MessageRole.USER,
            content=content,
            metadata=metadata,
        ))
        return self

    def assistant(self, content: str, **metadata: Any) -> "MessageBuilder":
        """添加 assistant 消息"""
        self._messages.append(Message(
            role=MessageRole.ASSISTANT,
            content=content,
            metadata=metadata,
        ))
        return self

    def add(self, role: MessageRole, content: str, **metadata: Any) -> "MessageBuilder":
        """添加任意角色消息"""
        self._messages.append(Message(
            role=role,
            content=content,
            metadata=metadata,
        ))
        return self

    def build(self) -> list[dict[str, str]]:
        """构建最终的 messages 列表"""
        return [m.to_dict() for m in self._messages]

    @property
    def messages(self) -> list[Message]:
        """获取原始消息列表"""
        return list(self._messages)

    @property
    def size(self) -> int:
        """消息数量"""
        return len(self._messages)

    def clear(self) -> "MessageBuilder":
        """清空消息"""
        self._messages.clear()
        return self

    def pop_oldest_non_system(self) -> "MessageBuilder":
        """
        移除最早的非 system 消息

        用于上下文窗口滑动时丢弃旧消息
        """
        for i, msg in enumerate(self._messages):
            if msg.role != MessageRole.SYSTEM:
                self._messages.pop(i)
                return self
        return self
