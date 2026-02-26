"""
Context Engineering 模块单元测试
"""

import json
import os
import tempfile

import pytest

from ai_test_tool.context.token_counter import TokenCounter
from ai_test_tool.context.context_window import ContextWindow
from ai_test_tool.context.message_builder import MessageBuilder, MessageRole, Message
from ai_test_tool.context.compressor import ContextCompressor
from ai_test_tool.context.file_store import FileContextStore


# ============================================================
# TokenCounter 测试
# ============================================================

class TestTokenCounter:
    def test_empty_string(self):
        counter = TokenCounter()
        assert counter.count("") == 0

    def test_ascii_estimate(self):
        counter = TokenCounter()
        # 100 ASCII chars -> ~25 tokens
        text = "a" * 100
        tokens = counter.count(text)
        assert 20 <= tokens <= 30

    def test_chinese_estimate(self):
        counter = TokenCounter()
        # 10 Chinese chars -> ~15 tokens
        text = "你好世界测试一下中文"
        tokens = counter.count(text)
        assert 10 <= tokens <= 20

    def test_mixed_text(self):
        counter = TokenCounter()
        text = "Hello 你好 World 世界"
        tokens = counter.count(text)
        assert tokens > 0

    def test_count_messages(self):
        counter = TokenCounter()
        messages = [
            {"role": "system", "content": "You are a helper."},
            {"role": "user", "content": "Hello"},
        ]
        tokens = counter.count_messages(messages)
        # 2 messages * 4 overhead + content tokens + 2 priming
        assert tokens > 10

    def test_fits_in_window(self):
        counter = TokenCounter()
        short_text = "Hello"
        assert counter.fits_in_window(short_text, 100) is True

        long_text = "x" * 10000
        assert counter.fits_in_window(long_text, 10) is False

    def test_truncate_to_fit(self):
        counter = TokenCounter()
        text = "abcdefghijklmnopqrstuvwxyz" * 100  # 2600 ASCII chars
        truncated = counter.truncate_to_fit(text, 100)
        assert counter.count(truncated) <= 100
        assert len(truncated) < len(text)

    def test_truncate_short_text_unchanged(self):
        counter = TokenCounter()
        text = "short"
        result = counter.truncate_to_fit(text, 1000)
        assert result == text


# ============================================================
# MessageBuilder 测试
# ============================================================

class TestMessageBuilder:
    def test_build_empty(self):
        builder = MessageBuilder()
        assert builder.build() == []
        assert builder.size == 0

    def test_build_chain(self):
        messages = (
            MessageBuilder()
            .system("You are a helper.")
            .user("Hello")
            .assistant("Hi there!")
            .build()
        )
        assert len(messages) == 3
        assert messages[0] == {"role": "system", "content": "You are a helper."}
        assert messages[1] == {"role": "user", "content": "Hello"}
        assert messages[2] == {"role": "assistant", "content": "Hi there!"}

    def test_add_generic(self):
        builder = MessageBuilder()
        builder.add(MessageRole.USER, "test message")
        messages = builder.build()
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "test message"

    def test_clear(self):
        builder = MessageBuilder().system("sys").user("usr")
        assert builder.size == 2
        builder.clear()
        assert builder.size == 0

    def test_pop_oldest_non_system(self):
        builder = (
            MessageBuilder()
            .system("sys")
            .user("msg1")
            .assistant("msg2")
            .user("msg3")
        )
        assert builder.size == 4
        builder.pop_oldest_non_system()
        assert builder.size == 3
        # system should still be there; first user removed
        messages = builder.build()
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "msg2"

    def test_pop_oldest_non_system_only_system(self):
        builder = MessageBuilder().system("sys")
        builder.pop_oldest_non_system()
        # Should not remove system message
        assert builder.size == 1

    def test_messages_property(self):
        builder = MessageBuilder().system("sys")
        msgs = builder.messages
        assert len(msgs) == 1
        assert isinstance(msgs[0], Message)

    def test_metadata(self):
        builder = MessageBuilder()
        builder.system("content", key="value")
        msg = builder.messages[0]
        assert msg.metadata == {"key": "value"}


# ============================================================
# ContextWindow 测试
# ============================================================

class TestContextWindow:
    def test_available_tokens(self):
        window = ContextWindow(max_tokens=8000, reserved_for_output=2000)
        assert window.available_tokens == 6000

    def test_fit_messages_within_limit(self):
        window = ContextWindow(max_tokens=10000, reserved_for_output=2000)
        builder = MessageBuilder().system("sys").user("Hello")
        result = window.fit_messages(builder)
        assert result.size == 2  # nothing dropped

    def test_fit_messages_drops_old(self):
        window = ContextWindow(max_tokens=100, reserved_for_output=20)
        builder = MessageBuilder().system("system prompt")
        for i in range(50):
            builder.user(f"message {i} " * 20)
        original_size = builder.size
        window.fit_messages(builder)
        assert builder.size < original_size
        # system message should survive
        assert builder.messages[0].role == MessageRole.SYSTEM

    def test_get_token_usage(self):
        window = ContextWindow(max_tokens=8000, reserved_for_output=2000)
        messages = [{"role": "user", "content": "Hello"}]
        usage = window.get_token_usage(messages)
        assert "used" in usage
        assert "available" in usage
        assert "utilization" in usage
        assert usage["available"] == 6000

    def test_statistics(self):
        window = ContextWindow(max_tokens=10000)
        builder = MessageBuilder().user("test")
        window.fit_messages(builder)
        stats = window.get_statistics()
        assert stats["total_tokens_processed"] > 0


# ============================================================
# ContextCompressor 测试
# ============================================================

class TestContextCompressor:
    def test_truncate_short_text(self):
        compressor = ContextCompressor()
        text = "short text"
        assert compressor.truncate(text, 1000) == text

    def test_truncate_long_text_keep_start(self):
        compressor = ContextCompressor()
        text = "word " * 1000
        result = compressor.truncate(text, 50)
        assert len(result) < len(text)
        assert result.endswith("...(truncated)")

    def test_truncate_long_text_keep_end(self):
        compressor = ContextCompressor()
        text = "\n".join(f"line {i}" for i in range(200))
        result = compressor.truncate(text, 50, keep_end=True)
        assert len(result) < len(text)
        assert "...(truncated)" in result

    def test_compress_history_short(self):
        compressor = ContextCompressor()
        steps = [
            {"step_number": 1, "thought": "think", "action": "act", "observation": "obs"},
        ]
        result = compressor.compress_history(steps, max_tokens=1000, keep_recent=3)
        assert len(result) == 1

    def test_compress_history_drops_old(self):
        compressor = ContextCompressor()
        steps = [
            {"step_number": i, "thought": f"thinking step {i} " * 50, "action": f"action_{i}", "observation": f"obs {i} " * 50}
            for i in range(10)
        ]
        result = compressor.compress_history(steps, max_tokens=2000, keep_recent=2)
        # Recent 2 steps should be intact
        assert result[-1]["thought"] == steps[-1]["thought"]
        assert result[-2]["thought"] == steps[-2]["thought"]
        # Older steps should be summarized (truncated)
        if len(result) > 2:
            assert len(result[0]["thought"]) <= 103  # max_chars + "..."

    def test_compress_history_empty(self):
        compressor = ContextCompressor()
        assert compressor.compress_history([], max_tokens=1000) == []


# ============================================================
# FileContextStore 测试
# ============================================================

class TestFileContextStore:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileContextStore(base_dir=tmpdir)
            data = {"task": "analyze logs", "step": 3}
            store.save("task_001", data)

            loaded = store.load("task_001")
            assert loaded == data

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileContextStore(base_dir=tmpdir)
            assert store.load("nonexistent") is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileContextStore(base_dir=tmpdir)
            store.save("task_002", {"key": "value"})
            assert store.delete("task_002") is True
            assert store.load("task_002") is None

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileContextStore(base_dir=tmpdir)
            assert store.delete("nonexistent") is False

    def test_list_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileContextStore(base_dir=tmpdir)
            store.save("task_a", {"a": 1})
            store.save("task_b", {"b": 2})
            tasks = store.list_tasks()
            assert set(tasks) == {"task_a", "task_b"}

    def test_safe_task_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileContextStore(base_dir=tmpdir)
            # task_id with special characters
            store.save("task/with:special chars!", {"safe": True})
            # Should still be loadable
            loaded = store.load("task/with:special chars!")
            assert loaded == {"safe": True}
