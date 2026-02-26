"""
ReAct 引擎单元测试
"""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest

from ai_test_tool.react.engine import ReActEngine, create_react_engine, REACT_SYSTEM_PROMPT
from ai_test_tool.react.models import (
    ReActConfig,
    ReActResult,
    ReActStep,
    Thought,
    Action,
    ActionType,
    Observation,
    StopReason,
    AgentContext,
    Tool,
    ToolResult,
)
from ai_test_tool.react.tools import ToolRegistry


# ============================================================
# Helper: 创建 Mock LLM Provider
# ============================================================

def make_mock_provider(responses: list[str]) -> Mock:
    """创建返回预设响应序列的 Mock LLM Provider"""
    provider = Mock()
    provider.generate = Mock(side_effect=responses)
    provider.chat = Mock(side_effect=responses)
    return provider


def make_finish_response(answer: str = "done") -> str:
    return f'Thought: 分析完成\nAction: finish\nAction Input: {{"answer": "{answer}"}}'


def make_tool_response(tool_name: str = "search_logs", params: dict | None = None) -> str:
    params = params or {"keyword": "error"}
    return f'Thought: 需要搜索日志\nAction: {tool_name}\nAction Input: {json.dumps(params)}'


# ============================================================
# ReActEngine 基础测试
# ============================================================

class TestReActEngineInit:
    def test_default_config(self):
        engine = ReActEngine()
        assert engine.config.max_iterations == 10
        assert engine.use_messages is True

    def test_custom_config(self):
        config = ReActConfig(max_iterations=5)
        engine = ReActEngine(config=config)
        assert engine.config.max_iterations == 5

    def test_use_messages_flag(self):
        engine = ReActEngine(use_messages=False)
        assert engine.use_messages is False

    def test_register_tool(self):
        registry = ToolRegistry()
        engine = ReActEngine(tool_registry=registry)
        tool = Tool(name="test_tool", description="test", func=lambda: "ok")
        engine.register_tool(tool)
        assert registry.get("test_tool") is not None


# ============================================================
# _parse_response 测试
# ============================================================

class TestParseResponse:
    def setup_method(self):
        self.engine = ReActEngine()

    def test_parse_tool_call(self):
        response = 'Thought: I need to search logs\nAction: search_logs\nAction Input: {"keyword": "error"}'
        thought, action = self.engine._parse_response(response, 1)
        assert "search logs" in thought.content
        assert action.action_type == ActionType.TOOL_CALL
        assert action.tool_name == "search_logs"
        assert action.tool_input == {"keyword": "error"}

    def test_parse_finish(self):
        response = 'Thought: Done analyzing\nAction: finish\nAction Input: {"answer": "No errors found"}'
        thought, action = self.engine._parse_response(response, 1)
        assert action.action_type == ActionType.FINISH
        assert action.final_answer == "No errors found"

    def test_parse_no_action(self):
        response = "Just some random text without proper format"
        thought, action = self.engine._parse_response(response, 1)
        assert action.action_type == ActionType.FINISH  # falls back to finish

    def test_parse_invalid_json_input(self):
        response = "Thought: test\nAction: search_logs\nAction Input: {invalid json}"
        thought, action = self.engine._parse_response(response, 1)
        assert action.tool_name == "search_logs"
        assert action.tool_input == {}  # fails to parse

    def test_parse_single_quote_json(self):
        response = "Thought: test\nAction: search_logs\nAction Input: {'keyword': 'error'}"
        thought, action = self.engine._parse_response(response, 1)
        assert action.tool_input == {"keyword": "error"}


# ============================================================
# _build_messages 测试
# ============================================================

class TestBuildMessages:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.engine = ReActEngine(tool_registry=self.registry, use_messages=True)

    def test_basic_messages_structure(self):
        context = AgentContext(task="分析错误日志")
        messages = self.engine._build_messages(context)
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "分析错误日志" in messages[1]["content"]

    def test_messages_include_history(self):
        context = AgentContext(task="test task")
        # Add a history step
        step = ReActStep(
            step_number=1,
            thought=Thought(content="thinking", step_number=1),
            action=Action(action_type=ActionType.TOOL_CALL, tool_name="search_logs", tool_input={"keyword": "err"}, step_number=1),
            observation=Observation(content="found 3 errors", step_number=1),
        )
        context.add_step(step)

        messages = self.engine._build_messages(context)
        # system + user(task) + assistant(thought+action) + user(observation) + user(continue)
        assert len(messages) >= 5
        # Find assistant message with thought
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) >= 1
        assert "thinking" in assistant_msgs[0]["content"]

    def test_messages_with_data(self):
        context = AgentContext(
            task="test",
            log_content="some log data",
            requests=[{"url": "/api/test"}],
        )
        messages = self.engine._build_messages(context)
        user_msg = messages[1]["content"]
        assert "有" in user_msg  # has log content
        assert "1 条记录" in user_msg


# ============================================================
# _build_prompt (旧模式) 测试
# ============================================================

class TestBuildPrompt:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.engine = ReActEngine(tool_registry=self.registry, use_messages=False)

    def test_basic_prompt_contains_task(self):
        context = AgentContext(task="分析错误日志")
        prompt = self.engine._build_prompt(context)
        assert "分析错误日志" in prompt

    def test_prompt_contains_data_info(self):
        context = AgentContext(task="test", log_content="log data", requests=[{"url": "/test"}])
        prompt = self.engine._build_prompt(context)
        assert "有" in prompt
        assert "1 条记录" in prompt


# ============================================================
# run() 集成测试（使用 Mock）
# ============================================================

class TestReActEngineRun:
    def test_single_step_finish(self):
        provider = make_mock_provider([make_finish_response("analysis complete")])
        registry = ToolRegistry()
        engine = ReActEngine(llm_provider=provider, tool_registry=registry, use_messages=True)

        result = engine.run("analyze logs")
        assert result.is_success
        assert result.final_answer == "analysis complete"
        assert result.total_iterations == 1
        assert result.stop_reason == StopReason.TASK_COMPLETED

    def test_tool_call_then_finish(self):
        def mock_search(**kwargs):
            return '{"matches": 3}'

        registry = ToolRegistry()
        registry.register(Tool(name="search_logs", description="search", func=mock_search))

        provider = make_mock_provider([
            make_tool_response("search_logs", {"keyword": "error"}),
            make_finish_response("Found 3 errors"),
        ])
        engine = ReActEngine(llm_provider=provider, tool_registry=registry, use_messages=True)

        result = engine.run("find errors")
        assert result.is_success
        assert result.total_iterations == 2
        assert result.total_tool_calls == 1
        assert "3 errors" in result.final_answer

    def test_max_iterations(self):
        # Always returns tool call, never finish
        provider = make_mock_provider([
            make_tool_response("search_logs") for _ in range(15)
        ])
        registry = ToolRegistry()
        registry.register(Tool(name="search_logs", description="search", func=lambda **kw: "result"))

        config = ReActConfig(max_iterations=3)
        engine = ReActEngine(llm_provider=provider, tool_registry=registry, config=config)

        result = engine.run("test")
        assert result.stop_reason == StopReason.MAX_ITERATIONS
        assert result.total_iterations == 3

    def test_llm_error(self):
        provider = Mock()
        provider.chat = Mock(side_effect=RuntimeError("LLM service down"))
        registry = ToolRegistry()

        config = ReActConfig(llm_retry_count=1)
        engine = ReActEngine(llm_provider=provider, tool_registry=registry, config=config)

        result = engine.run("test")
        assert result.stop_reason == StopReason.ERROR
        assert "LLM service down" in result.error_message

    def test_fallback_mode(self):
        provider = make_mock_provider([make_finish_response("done")])
        registry = ToolRegistry()
        engine = ReActEngine(
            llm_provider=provider,
            tool_registry=registry,
            use_messages=False,
        )

        result = engine.run("test")
        assert result.is_success
        # Should have called generate(), not chat()
        provider.generate.assert_called_once()
        provider.chat.assert_not_called()

    def test_token_usage_tracked(self):
        provider = make_mock_provider([make_finish_response("done")])
        registry = ToolRegistry()
        engine = ReActEngine(llm_provider=provider, tool_registry=registry, use_messages=True)

        result = engine.run("test task")
        # total_tokens_used should be > 0 since we counted input
        assert result.total_tokens_used > 0


# ============================================================
# AgentContext token_usage 测试
# ============================================================

class TestAgentContextTokenUsage:
    def test_token_usage_initialized_empty(self):
        ctx = AgentContext(task="test")
        assert ctx.token_usage == {}

    def test_token_usage_accumulates(self):
        ctx = AgentContext(task="test")
        ctx.token_usage["total_input_tokens"] = 100
        ctx.token_usage["total_input_tokens"] += 50
        assert ctx.token_usage["total_input_tokens"] == 150


# ============================================================
# create_react_engine 便捷函数测试
# ============================================================

class TestCreateReactEngine:
    def test_default(self):
        engine = create_react_engine()
        assert engine.config.max_iterations == 10
        assert engine.use_messages is True

    def test_with_kwargs(self):
        engine = create_react_engine(max_iterations=5)
        assert engine.config.max_iterations == 5

    def test_with_use_messages_false(self):
        engine = create_react_engine(use_messages=False)
        assert engine.use_messages is False
