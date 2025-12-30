"""
LLM模块
提供大语言模型的抽象层
"""

from .provider import LLMProvider, get_llm_provider, OllamaProvider
from .chains import (
    LogAnalysisChain,
    ReportGeneratorChain,
    TestCaseGeneratorChain,
    ResultValidatorChain,
    CurlGeneratorChain
)

__all__ = [
    "LLMProvider",
    "get_llm_provider",
    "OllamaProvider",
    "LogAnalysisChain",
    "ReportGeneratorChain",
    "TestCaseGeneratorChain",
    "ResultValidatorChain",
    "CurlGeneratorChain"
]
