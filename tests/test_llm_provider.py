"""
LLM Provider 增强功能单元测试
"""

import time
from unittest.mock import Mock, patch, MagicMock

import pytest

from ai_test_tool.llm.provider import (
    LLMProvider,
    RateLimiter,
    generate_with_retry,
    _convert_messages,
)


# ============================================================
# 创建可实例化的 Provider 子类用于测试
# ============================================================

class MockProvider(LLMProvider):
    """可实例化的 Mock Provider"""

    def __init__(self, generate_func=None, chat_func=None, **kwargs):
        # 创建 minimal config
        config = Mock()
        config.model = "test-model"
        config.debug = False
        super().__init__(config)
        self._generate_func = generate_func
        self._chat_func = chat_func

    def get_llm(self):
        llm = Mock()
        if self._generate_func:
            llm.invoke = self._generate_func
        else:
            llm.invoke = Mock(return_value="generated text")
        return llm

    def get_chat_model(self):
        model = Mock()
        if self._chat_func:
            model.invoke = self._chat_func
        else:
            resp = Mock()
            resp.content = "chat response"
            model.invoke = Mock(return_value=resp)
        return model


# ============================================================
# estimate_tokens 测试
# ============================================================

class TestEstimateTokens:
    def test_empty_string(self):
        provider = MockProvider()
        assert provider.estimate_tokens("") == 0

    def test_non_empty(self):
        provider = MockProvider()
        tokens = provider.estimate_tokens("Hello world, this is a test")
        assert tokens > 0

    def test_chinese_text(self):
        provider = MockProvider()
        tokens = provider.estimate_tokens("你好世界")
        assert tokens > 0


# ============================================================
# generate_with_fallback 测试
# ============================================================

class TestGenerateWithFallback:
    def test_primary_succeeds(self):
        primary = MockProvider(generate_func=lambda p: "primary result")
        fallback = MockProvider(generate_func=lambda p: "fallback result")

        result = primary.generate_with_fallback("test", fallback)
        assert result == "primary result"

    def test_fallback_on_primary_failure(self):
        def fail(p):
            raise RuntimeError("primary down")

        primary = MockProvider(generate_func=fail)
        fallback = MockProvider(generate_func=lambda p: "fallback result")

        result = primary.generate_with_fallback("test", fallback)
        assert result == "fallback result"

    def test_both_fail(self):
        def fail(p):
            raise RuntimeError("down")

        primary = MockProvider(generate_func=fail)
        fallback = MockProvider(generate_func=fail)

        with pytest.raises(RuntimeError):
            primary.generate_with_fallback("test", fallback)


# ============================================================
# chat_with_fallback 测试
# ============================================================

class TestChatWithFallback:
    def test_primary_succeeds(self):
        resp = Mock()
        resp.content = "primary chat"
        primary = MockProvider(chat_func=lambda m: resp)
        fallback = MockProvider()

        result = primary.chat_with_fallback([{"role": "user", "content": "hi"}], fallback)
        assert result == "primary chat"

    def test_fallback_on_failure(self):
        def fail(m):
            raise RuntimeError("down")

        resp = Mock()
        resp.content = "fallback chat"
        primary = MockProvider(chat_func=fail)
        fallback = MockProvider(chat_func=lambda m: resp)

        result = primary.chat_with_fallback([{"role": "user", "content": "hi"}], fallback)
        assert result == "fallback chat"


# ============================================================
# RateLimiter 测试
# ============================================================

class TestRateLimiter:
    def test_acquire_within_limit(self):
        limiter = RateLimiter(max_calls_per_minute=1000)
        # Should not block
        start = time.monotonic()
        for _ in range(10):
            limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # should be nearly instant

    def test_set_rate_limit_on_provider(self):
        provider = MockProvider()
        provider.set_rate_limit(120)
        assert provider._rate_limiter is not None
        assert provider._rate_limiter.max_calls == 120


# ============================================================
# generate_with_retry 测试
# ============================================================

class TestGenerateWithRetry:
    def test_succeeds_first_try(self):
        provider = MockProvider(generate_func=lambda p: "ok")
        result = generate_with_retry(provider, "test", max_retries=3, base_delay=0.01)
        assert result == "ok"

    def test_succeeds_after_retries(self):
        call_count = [0]

        def flaky(p):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("temporary failure")
            return "finally ok"

        provider = MockProvider(generate_func=flaky)
        result = generate_with_retry(provider, "test", max_retries=3, base_delay=0.01)
        assert result == "finally ok"
        assert call_count[0] == 3

    def test_all_retries_fail(self):
        def always_fail(p):
            raise RuntimeError("permanent failure")

        provider = MockProvider(generate_func=always_fail)
        with pytest.raises(RuntimeError, match="permanent failure"):
            generate_with_retry(provider, "test", max_retries=2, base_delay=0.01)

    def test_exponential_backoff(self):
        call_count = [0]
        timestamps: list[float] = []

        def fail_twice(p):
            call_count[0] += 1
            timestamps.append(time.monotonic())
            if call_count[0] < 3:
                raise RuntimeError("fail")
            return "ok"

        provider = MockProvider(generate_func=fail_twice)
        generate_with_retry(provider, "test", max_retries=3, base_delay=0.05)

        # Second retry should wait longer than first
        if len(timestamps) >= 3:
            gap1 = timestamps[1] - timestamps[0]
            gap2 = timestamps[2] - timestamps[1]
            assert gap2 > gap1


# ============================================================
# _convert_messages 测试
# ============================================================

class TestConvertMessages:
    def test_all_roles(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
            {"role": "assistant", "content": "ast"},
        ]
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        result = _convert_messages(messages)
        assert len(result) == 3
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], AIMessage)

    def test_default_role(self):
        messages = [{"content": "hello"}]
        from langchain_core.messages import HumanMessage
        result = _convert_messages(messages)
        assert isinstance(result[0], HumanMessage)
