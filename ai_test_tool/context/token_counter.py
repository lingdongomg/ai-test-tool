"""
Token 计数器

支持两种模式：
1. 字符估算（默认）: 中文 ~1.5 token/字, 英文 ~0.25 token/字
2. tiktoken 精确计数（可选依赖）
"""

import logging
import re

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token 计数器"""

    # 默认字符/token 比率（适用于大多数模型）
    _CHINESE_RATIO = 1.5  # 中文字符约 1.5 token
    _ASCII_RATIO = 0.25   # ASCII 字符约 0.25 token
    _SAFETY_MARGIN = 0.1  # 预留 10% 安全余量

    def __init__(self, model: str = "", use_tiktoken: bool = False):
        """
        初始化

        Args:
            model: 模型名称（用于 tiktoken 选择编码器）
            use_tiktoken: 是否使用 tiktoken 精确计数
        """
        self.model = model
        self._encoder = None

        if use_tiktoken:
            self._encoder = self._load_tiktoken(model)

    @staticmethod
    def _load_tiktoken(model: str):
        """尝试加载 tiktoken"""
        try:
            import tiktoken
            try:
                return tiktoken.encoding_for_model(model)
            except KeyError:
                return tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.debug("tiktoken 未安装，使用字符估算")
            return None

    def count(self, text: str) -> int:
        """
        计算文本的 token 数

        Args:
            text: 输入文本

        Returns:
            估算的 token 数
        """
        if not text:
            return 0

        if self._encoder is not None:
            return len(self._encoder.encode(text))

        return self._estimate(text)

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        """
        计算 messages 列表的 token 数

        每条消息额外 4 token（role + formatting overhead）

        Args:
            messages: 消息列表

        Returns:
            估算的 token 数
        """
        total = 0
        for msg in messages:
            total += 4  # message overhead
            total += self.count(msg.get("role", ""))
            total += self.count(msg.get("content", ""))
        total += 2  # reply priming
        return total

    def fits_in_window(self, text: str, max_tokens: int) -> bool:
        """检查文本是否在 token 窗口内"""
        return self.count(text) <= self._safe_limit(max_tokens)

    def _safe_limit(self, max_tokens: int) -> int:
        """计算含安全余量的限制"""
        return int(max_tokens * (1 - self._SAFETY_MARGIN))

    def _estimate(self, text: str) -> int:
        """字符估算 token 数"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text))
        ascii_chars = len(text) - chinese_chars
        return int(chinese_chars * self._CHINESE_RATIO + ascii_chars * self._ASCII_RATIO)

    def truncate_to_fit(self, text: str, max_tokens: int) -> str:
        """
        截断文本使其适合 token 窗口

        Args:
            text: 输入文本
            max_tokens: 最大 token 数

        Returns:
            截断后的文本
        """
        safe_limit = self._safe_limit(max_tokens)
        if self.count(text) <= safe_limit:
            return text

        # 二分查找合适的截断点
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if self.count(text[:mid]) <= safe_limit:
                low = mid
            else:
                high = mid - 1

        return text[:low]
