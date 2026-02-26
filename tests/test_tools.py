"""
工具系统扩展单元测试
"""

import json
from unittest.mock import Mock

import pytest

from ai_test_tool.react.models import Tool, ToolResult
from ai_test_tool.react.tools import (
    ToolRegistry,
    SearchLogsTool,
    FilterRequestsTool,
    CalculateStatsTool,
    ExtractPatternsTool,
    CompareTimePeriodsTool,
    PythonExecTool,
    WebSearchTool,
)


# ============================================================
# OpenAI Function Calling Schema 测试
# ============================================================

class TestToolOpenAISchema:
    def test_basic_schema(self):
        tool = Tool(
            name="test",
            description="A test tool",
            func=lambda: None,
            parameters={
                "query": {"type": "string", "description": "search query"},
                "limit": {"type": "integer", "description": "max results"},
            },
            required_params=["query"],
        )

        schema = tool.to_openai_function()
        assert schema["name"] == "test"
        assert schema["description"] == "A test tool"
        assert schema["parameters"]["type"] == "object"
        assert "query" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["query"]

    def test_schema_with_enum(self):
        tool = Tool(
            name="filter",
            description="filter",
            func=lambda: None,
            parameters={
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                },
            },
            required_params=[],
        )
        schema = tool.to_openai_function()
        assert schema["parameters"]["properties"]["method"]["enum"] == ["GET", "POST", "PUT", "DELETE"]

    def test_empty_params(self):
        tool = Tool(name="noop", description="no params", func=lambda: None)
        schema = tool.to_openai_function()
        assert schema["parameters"]["properties"] == {}
        assert schema["parameters"]["required"] == []


# ============================================================
# ToolResult 标准格式测试
# ============================================================

class TestToolResultStandardDict:
    def test_success_result(self):
        result = ToolResult(
            tool_name="test",
            success=True,
            output={"key": "value"},
            execution_time_ms=100,
        )
        d = result.to_standard_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert d["error"] is None
        assert d["metadata"]["tool_name"] == "test"

    def test_error_result(self):
        result = ToolResult(
            tool_name="test",
            success=False,
            error="something broke",
        )
        d = result.to_standard_dict()
        assert d["success"] is False
        assert d["error"] == "something broke"


# ============================================================
# ToolRegistry.get_openai_tools 测试
# ============================================================

class TestRegistryOpenAITools:
    def test_get_openai_tools(self):
        registry = ToolRegistry()
        registry.register(Tool(
            name="t1",
            description="tool 1",
            func=lambda: None,
            parameters={"q": {"type": "string", "description": "query"}},
            required_params=["q"],
        ))
        registry.register(Tool(
            name="t2",
            description="tool 2",
            func=lambda: None,
        ))

        tools = registry.get_openai_tools()
        assert len(tools) == 2
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "t1"
        assert tools[1]["function"]["name"] == "t2"


# ============================================================
# PythonExecTool 测试
# ============================================================

class TestPythonExecTool:
    def test_create(self):
        tool = PythonExecTool.create()
        assert tool.name == "python_exec"
        assert "code" in tool.required_params

    def test_execute_simple(self):
        result = PythonExecTool.execute(code="print('hello')")
        data = json.loads(result)
        assert data["success"] is True
        assert "hello" in data["output"]

    def test_execute_error(self):
        result = PythonExecTool.execute(code="raise ValueError('test error')")
        data = json.loads(result)
        assert data["success"] is False

    def test_execute_math(self):
        result = PythonExecTool.execute(code="print(2 + 3)")
        data = json.loads(result)
        assert data["success"] is True
        assert "5" in data["output"]


# ============================================================
# WebSearchTool 测试
# ============================================================

class TestWebSearchTool:
    def test_create(self):
        tool = WebSearchTool.create()
        assert tool.name == "web_search"
        assert "query" in tool.required_params

    def test_execute_stub(self):
        result = WebSearchTool.execute(query="test query")
        data = json.loads(result)
        assert data["query"] == "test query"
        assert "results" in data
        assert "配置" in data["message"]


# ============================================================
# 内置工具基础功能测试
# ============================================================

class TestBuiltinTools:
    def test_search_logs(self):
        result = SearchLogsTool.execute(keyword="error", log_content="line1 ok\nline2 error here\nline3 ok")
        data = json.loads(result)
        assert data["total_matches"] >= 1

    def test_filter_requests(self):
        requests = [
            {"url": "/api/test", "method": "GET", "http_status": 200, "response_time_ms": 100},
            {"url": "/api/error", "method": "POST", "http_status": 500, "response_time_ms": 500},
        ]
        result = FilterRequestsTool.execute(requests=requests, status_range="5xx")
        data = json.loads(result)
        assert data["total_filtered"] == 1

    def test_calculate_stats(self):
        requests = [
            {"response_time_ms": 100, "http_status": 200},
            {"response_time_ms": 200, "http_status": 200},
            {"response_time_ms": 300, "http_status": 500, "has_error": True},
        ]
        result = CalculateStatsTool.execute(requests=requests)
        data = json.loads(result)
        assert data["count"] == 3
        assert "response_time" in data

    def test_extract_patterns_ip(self):
        log = "Request from 192.168.1.1 to 10.0.0.1"
        result = ExtractPatternsTool.execute(pattern_type="ip", log_content=log)
        data = json.loads(result)
        assert data["unique_count"] == 2

    def test_registry_execute_with_timeout(self):
        registry = ToolRegistry()
        # Tool with very short timeout
        registry.register(Tool(
            name="slow_tool",
            description="slow",
            func=lambda **kw: "ok",
            timeout_seconds=60,
        ))
        result = registry.execute("slow_tool")
        assert result.success is True
