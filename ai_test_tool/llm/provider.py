# 该文件内容使用AI生成，注意识别准确性
"""
LLM提供商抽象层
支持多种LLM后端：Ollama、OpenAI、Azure、Anthropic等
Python 3.13+ 兼容
"""

from abc import ABC, abstractmethod
from typing import Any
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from ..config import LLMConfig, get_config


def _setup_langchain_debug(debug: bool) -> None:
    """设置LangChain调试模式"""
    try:
        from langchain.globals import set_debug, set_verbose
        set_debug(debug)
        set_verbose(debug)
        if debug:
            import logging
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


class LLMProvider(ABC):
    """LLM提供商抽象基类"""
    
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._llm: Any = None
        self._chat_model: Any = None
        _setup_langchain_debug(config.debug)
    
    @abstractmethod
    def get_llm(self) -> BaseLLM:
        """获取LLM实例"""
        ...
    
    @abstractmethod
    def get_chat_model(self) -> Any:
        """获取Chat模型"""
        ...
    
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """生成文本"""
        llm = self.get_llm()
        return llm.invoke(prompt)
    
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """聊天对话（所有Provider通用）"""
        chat_model = self.get_chat_model()
        response = chat_model.invoke(_convert_messages(messages))
        return response.content


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
