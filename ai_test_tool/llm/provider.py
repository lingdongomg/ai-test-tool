# 该文件内容使用AI生成，注意识别准确性
"""
LLM提供商抽象层
支持多种LLM后端：Ollama、OpenAI、Azure、Anthropic等
Python 3.13+ 兼容
"""

import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Any
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from ..config import LLMConfig, get_config

import re as _re

class TokenCounter:
    """简化版 Token 计数器（内联，原 context/token_counter.py）"""
    _CHINESE_RATIO = 1.5
    _ASCII_RATIO = 0.25

    def __init__(self, model: str = ""):
        self.model = model

    def count(self, text: str) -> int:
        if not text:
            return 0
        chinese = len(_re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text))
        ascii_c = len(text) - chinese
        return int(chinese * self._CHINESE_RATIO + ascii_c * self._ASCII_RATIO)

logger = logging.getLogger(__name__)


def _setup_langchain_debug(debug: bool) -> None:
    """设置LangChain调试模式"""
    try:
        from langchain.globals import set_debug, set_verbose
        set_debug(debug)
        set_verbose(debug)
        if debug:
            logging.getLogger("langchain").setLevel(logging.DEBUG)
    except ImportError:
        try:
            import langchain
            langchain.debug = debug
            langchain.verbose = debug
        except Exception:
            pass


def _convert_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    """将字典格式消息转换为LangChain消息对象"""
    result: list[BaseMessage] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            result.append(SystemMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        else:
            result.append(HumanMessage(content=content))
    return result


class RateLimiter:
    """
    令牌桶速率限制器

    控制 LLM 调用频率，避免触发 API 限制
    """

    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self._tokens = float(max_calls_per_minute)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """获取一个调用令牌，必要时阻塞等待"""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
            time.sleep(0.1)

    def _refill(self) -> None:
        """补充令牌"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * (self.max_calls / 60.0)
        self._tokens = min(float(self.max_calls), self._tokens + new_tokens)
        self._last_refill = now


class LLMProvider(ABC):
    """LLM提供商抽象基类"""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._llm: Any = None
        self._chat_model: Any = None
        self._token_counter = TokenCounter(model=config.model)
        self._rate_limiter: RateLimiter | None = None
        _setup_langchain_debug(config.debug)

    @abstractmethod
    def get_llm(self) -> BaseLLM:
        """获取LLM实例"""
        ...

    @abstractmethod
    def get_chat_model(self) -> Any:
        """获取Chat模型"""
        ...

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数

        Args:
            text: 输入文本

        Returns:
            估算的 token 数
        """
        return self._token_counter.count(text)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """生成文本"""
        if self._rate_limiter:
            self._rate_limiter.acquire()
        llm = self.get_llm()
        return llm.invoke(prompt)

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """聊天对话（所有Provider通用）"""
        if self._rate_limiter:
            self._rate_limiter.acquire()
        chat_model = self.get_chat_model()
        response = chat_model.invoke(_convert_messages(messages))
        return response.content

    def generate_with_fallback(
        self,
        prompt: str,
        fallback_provider: "LLMProvider",
        **kwargs: Any,
    ) -> str:
        """
        带降级的生成：主 Provider 失败时自动切换备用 Provider

        Args:
            prompt: 提示文本
            fallback_provider: 备用 Provider
            **kwargs: 额外参数

        Returns:
            生成的文本
        """
        try:
            return self.generate(prompt, **kwargs)
        except Exception as e:
            logger.warning(f"主 Provider 失败 ({e}), 切换到备用 Provider")
            return fallback_provider.generate(prompt, **kwargs)

    def chat_with_fallback(
        self,
        messages: list[dict[str, str]],
        fallback_provider: "LLMProvider",
        **kwargs: Any,
    ) -> str:
        """带降级的 chat"""
        try:
            return self.chat(messages, **kwargs)
        except Exception as e:
            logger.warning(f"主 Provider chat 失败 ({e}), 切换到备用 Provider")
            return fallback_provider.chat(messages, **kwargs)

    def set_rate_limit(self, max_calls_per_minute: int) -> None:
        """设置速率限制"""
        self._rate_limiter = RateLimiter(max_calls_per_minute)


def generate_with_retry(
    provider: LLMProvider,
    prompt: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs: Any,
) -> str:
    """
    指数退避重试调用

    Args:
        provider: LLM Provider
        prompt: 提示文本
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）

    Returns:
        生成的文本
    """
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return provider.generate(prompt, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries}), "
                    f"{delay:.1f}s 后重试: {e}"
                )
                time.sleep(delay)
    raise last_error  # type: ignore[misc]


class OllamaProvider(LLMProvider):
    """Ollama本地模型提供商"""

    def get_llm(self) -> Any:
        if self._llm is None:
            try:
                from langchain_ollama import OllamaLLM
                self._llm = OllamaLLM(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    num_predict=self.config.max_tokens,
                    base_url=self.config.api_base or "http://localhost:11434"
                )
            except ImportError as e:
                raise ImportError("请安装 langchain-ollama: pip install langchain-ollama") from e
        return self._llm

    def get_chat_model(self) -> Any:
        if self._chat_model is None:
            try:
                from langchain_ollama import ChatOllama
                self._chat_model = ChatOllama(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    num_predict=self.config.max_tokens,
                    base_url=self.config.api_base or "http://localhost:11434"
                )
            except ImportError as e:
                raise ImportError("请安装 langchain-ollama: pip install langchain-ollama") from e
        return self._chat_model


class OpenAIProvider(LLMProvider):
    """OpenAI API提供商"""

    def get_llm(self) -> Any:
        if self._llm is None:
            try:
                from langchain_openai import OpenAI
                self._llm = OpenAI(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
            except ImportError as e:
                raise ImportError("请安装 langchain-openai: pip install langchain-openai") from e
        return self._llm

    def get_chat_model(self) -> Any:
        if self._chat_model is None:
            try:
                from langchain_openai import ChatOpenAI
                self._chat_model = ChatOpenAI(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
            except ImportError as e:
                raise ImportError("请安装 langchain-openai: pip install langchain-openai") from e
        return self._chat_model


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API提供商"""

    def get_llm(self) -> Any:
        """Claude主要使用Chat接口"""
        return self.get_chat_model()

    def get_chat_model(self) -> Any:
        if self._chat_model is None:
            try:
                from langchain_anthropic import ChatAnthropic
                self._chat_model = ChatAnthropic(
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    api_key=self.config.api_key
                )
            except ImportError as e:
                raise ImportError("请安装 langchain-anthropic: pip install langchain-anthropic") from e
        return self._chat_model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Claude使用chat接口生成"""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)


# 提供商注册表
_PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    """获取LLM提供商实例"""
    if config is None:
        config = get_config().llm

    provider_class = _PROVIDERS.get(config.provider)
    if provider_class is None:
        raise ValueError(f"不支持的LLM提供商: {config.provider}")

    return provider_class(config)


def register_provider(name: str, provider_class: type[LLMProvider]) -> None:
    """注册自定义LLM提供商"""
    _PROVIDERS[name] = provider_class
