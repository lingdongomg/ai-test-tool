"""
CoT 链式推理引擎单元测试
"""

import json
import time
from unittest.mock import Mock, patch, MagicMock

import pytest

from ai_test_tool.reasoning.engine import ChainOfThoughtEngine, create_engine
from ai_test_tool.reasoning.models import (
    ThinkingStep,
    StepResult,
    ChainConfig,
    ChainResult,
    ChainContext,
    StepStatus,
    ChainStatus,
    ReasoningStepType,
)


# ============================================================
# Helper
# ============================================================

def make_mock_provider(responses: list[str]) -> Mock:
    """创建返回预设响应序列的 Mock LLM Provider"""
    provider = Mock()
    provider.generate = Mock(side_effect=responses)
    return provider


def make_step(
    step_id: str = "step1",
    name: str = "Step 1",
    template: str = "Analyze: {input}",
    depends_on: list[str] | None = None,
    output_key: str = "",
    order: int = 0,
    condition=None,
    retry_count: int = 1,
    post_processor=None,
) -> ThinkingStep:
    return ThinkingStep(
        step_id=step_id,
        name=name,
        description=f"Description for {name}",
        prompt_template=template,
        depends_on=depends_on or [],
        output_key=output_key,
        order=order,
        condition=condition,
        retry_count=retry_count,
        post_processor=post_processor,
    )


# ============================================================
# ThinkingStep 测试
# ============================================================

class TestThinkingStep:
    def test_get_prompt_simple(self):
        step = make_step(template="Analyze: {input}")
        prompt = step.get_prompt({"input": "hello world"})
        assert prompt == "Analyze: hello world"

    def test_get_prompt_multiple_placeholders(self):
        step = make_step(template="API: {endpoint}, Method: {method}")
        prompt = step.get_prompt({"endpoint": "/users", "method": "GET"})
        assert prompt == "API: /users, Method: GET"

    def test_get_prompt_dict_value_serialized_as_json(self):
        step = make_step(template="Data: {data}")
        prompt = step.get_prompt({"data": {"key": "value"}})
        assert '"key": "value"' in prompt

    def test_get_prompt_list_value_serialized_as_json(self):
        step = make_step(template="Items: {items}")
        prompt = step.get_prompt({"items": [1, 2, 3]})
        assert "[" in prompt and "1" in prompt

    def test_get_prompt_missing_placeholder_unchanged(self):
        step = make_step(template="Hello {name}, your id is {id}")
        prompt = step.get_prompt({"name": "Alice"})
        assert "Alice" in prompt
        assert "{id}" in prompt

    def test_should_execute_no_condition(self):
        step = make_step()
        assert step.should_execute({}) is True

    def test_should_execute_condition_true(self):
        step = make_step(condition=lambda ctx: ctx.get("run") is True)
        assert step.should_execute({"run": True}) is True

    def test_should_execute_condition_false(self):
        step = make_step(condition=lambda ctx: ctx.get("run") is True)
        assert step.should_execute({"run": False}) is False

    def test_to_dict(self):
        step = make_step(step_id="s1", name="Analysis")
        d = step.to_dict()
        assert d["step_id"] == "s1"
        assert d["name"] == "Analysis"
        assert d["step_type"] == "analysis"
        assert d["required"] is True


# ============================================================
# ChainContext 测试
# ============================================================

class TestChainContext:
    def test_get_from_original_input(self):
        ctx = ChainContext(original_input={"key": "from_input"})
        assert ctx.get("key") == "from_input"

    def test_get_from_intermediate_data(self):
        ctx = ChainContext()
        ctx.set("key", "from_intermediate")
        assert ctx.get("key") == "from_intermediate"

    def test_get_from_step_outputs(self):
        ctx = ChainContext()
        ctx.set_step_output("key", "from_step")
        assert ctx.get("key") == "from_step"

    def test_get_priority_step_outputs_over_intermediate(self):
        ctx = ChainContext()
        ctx.set("key", "intermediate")
        ctx.set_step_output("key", "step_output")
        assert ctx.get("key") == "step_output"

    def test_get_priority_intermediate_over_input(self):
        ctx = ChainContext(original_input={"key": "input_val"})
        ctx.set("key", "intermediate_val")
        assert ctx.get("key") == "intermediate_val"

    def test_get_default(self):
        ctx = ChainContext()
        assert ctx.get("missing") is None
        assert ctx.get("missing", "fallback") == "fallback"

    def test_contains(self):
        ctx = ChainContext(original_input={"a": 1})
        ctx.set("b", 2)
        ctx.set_step_output("c", 3)
        assert "a" in ctx
        assert "b" in ctx
        assert "c" in ctx
        assert "d" not in ctx

    def test_getitem_setitem(self):
        ctx = ChainContext()
        ctx["foo"] = "bar"
        assert ctx["foo"] == "bar"

    def test_to_dict_merges_all(self):
        ctx = ChainContext(original_input={"a": 1})
        ctx.set("b", 2)
        ctx.set_step_output("c", 3)
        d = ctx.to_dict()
        assert d["a"] == 1
        assert d["b"] == 2
        assert d["c"] == 3

    def test_to_dict_step_outputs_override(self):
        ctx = ChainContext(original_input={"key": "original"})
        ctx.set_step_output("key", "overridden")
        d = ctx.to_dict()
        assert d["key"] == "overridden"


# ============================================================
# StepResult 测试
# ============================================================

class TestStepResult:
    def test_is_success_completed(self):
        r = StepResult(step_id="s1", status=StepStatus.COMPLETED)
        assert r.is_success is True

    def test_is_success_failed(self):
        r = StepResult(step_id="s1", status=StepStatus.FAILED)
        assert r.is_success is False

    def test_is_success_skipped(self):
        r = StepResult(step_id="s1", status=StepStatus.SKIPPED)
        assert r.is_success is False

    def test_duration_seconds(self):
        r = StepResult(step_id="s1", status=StepStatus.COMPLETED, execution_time_ms=1500)
        assert r.duration_seconds == 1.5

    def test_to_dict(self):
        r = StepResult(
            step_id="s1",
            status=StepStatus.COMPLETED,
            output="result",
            thinking="I thought...",
            execution_time_ms=100,
        )
        d = r.to_dict()
        assert d["step_id"] == "s1"
        assert d["status"] == "completed"
        assert d["output"] == "result"
        assert d["thinking"] == "I thought..."


# ============================================================
# ChainResult 测试
# ============================================================

class TestChainResult:
    def _make_result(self, statuses: list[StepStatus]) -> ChainResult:
        steps = [make_step(step_id=f"s{i}") for i in range(len(statuses))]
        results = [
            StepResult(step_id=f"s{i}", status=s)
            for i, s in enumerate(statuses)
        ]
        return ChainResult(
            chain_id="test",
            status=ChainStatus.COMPLETED,
            steps=steps,
            step_results=results,
        )

    def test_is_success(self):
        r = ChainResult(
            chain_id="t", status=ChainStatus.COMPLETED, steps=[], step_results=[]
        )
        assert r.is_success is True

    def test_is_success_false(self):
        r = ChainResult(
            chain_id="t", status=ChainStatus.FAILED, steps=[], step_results=[]
        )
        assert r.is_success is False

    def test_completed_steps(self):
        r = self._make_result([StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.COMPLETED])
        assert r.completed_steps == 2

    def test_failed_steps(self):
        r = self._make_result([StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED])
        assert r.failed_steps == 1

    def test_thinking_trace(self):
        steps = [make_step(step_id="s0", name="Analysis")]
        results = [
            StepResult(
                step_id="s0",
                status=StepStatus.COMPLETED,
                thinking="deep thought",
                output="answer",
                execution_time_ms=50,
            )
        ]
        r = ChainResult(
            chain_id="t",
            status=ChainStatus.COMPLETED,
            steps=steps,
            step_results=results,
        )
        trace = r.thinking_trace
        assert len(trace) == 1
        assert trace[0]["name"] == "Analysis"
        assert trace[0]["thinking"] == "deep thought"

    def test_get_step_output(self):
        results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED, output="out1"),
            StepResult(step_id="s2", status=StepStatus.COMPLETED, output="out2"),
        ]
        r = ChainResult(
            chain_id="t",
            status=ChainStatus.COMPLETED,
            steps=[],
            step_results=results,
        )
        assert r.get_step_output("s2") == "out2"
        assert r.get_step_output("missing") is None

    def test_to_dict(self):
        r = ChainResult(
            chain_id="test",
            status=ChainStatus.COMPLETED,
            steps=[],
            step_results=[],
            final_output="final",
            error_message="",
        )
        d = r.to_dict()
        assert d["chain_id"] == "test"
        assert d["status"] == "completed"
        assert d["final_output"] == "final"


# ============================================================
# _extract_thinking 测试
# ============================================================

class TestExtractThinking:
    def setup_method(self):
        self.engine = ChainOfThoughtEngine(llm_provider=Mock())

    def test_think_tag(self):
        response = "<think>I need to analyze this</think>The answer is 42"
        thinking, clean = self.engine._extract_thinking(response)
        assert thinking == "I need to analyze this"
        assert "42" in clean
        assert "<think>" not in clean

    def test_thinking_tag(self):
        response = "<thinking>Step by step analysis</thinking>\nResult: done"
        thinking, clean = self.engine._extract_thinking(response)
        assert thinking == "Step by step analysis"
        assert "Result: done" in clean

    def test_think_tag_case_insensitive(self):
        response = "<THINK>Case insensitive</THINK>output"
        thinking, clean = self.engine._extract_thinking(response)
        assert thinking == "Case insensitive"
        assert "output" in clean

    def test_think_tag_multiline(self):
        response = "<think>\nLine 1\nLine 2\n</think>\nFinal answer"
        thinking, clean = self.engine._extract_thinking(response)
        assert "Line 1" in thinking
        assert "Line 2" in thinking
        assert "Final answer" in clean

    def test_bold_thinking_format(self):
        response = "**Thinking**: I analyzed the input\n\nThe result is X"
        thinking, clean = self.engine._extract_thinking(response)
        assert "analyzed" in thinking

    def test_bold_analysis_format(self):
        response = "**Analysis**: Examined endpoints\n\nConclusion here"
        thinking, clean = self.engine._extract_thinking(response)
        assert "Examined" in thinking

    def test_no_thinking_present(self):
        response = "Just a plain response with no thinking tags"
        thinking, clean = self.engine._extract_thinking(response)
        assert thinking == ""
        assert clean == response

    def test_empty_response(self):
        thinking, clean = self.engine._extract_thinking("")
        assert thinking == ""
        assert clean == ""


# ============================================================
# _parse_response 测试
# ============================================================

class TestParseResponse:
    def setup_method(self):
        self.engine = ChainOfThoughtEngine(llm_provider=Mock())

    def test_direct_json_object(self):
        response = '{"key": "value", "count": 3}'
        result = self.engine._parse_response(response)
        assert result == {"key": "value", "count": 3}

    def test_direct_json_array(self):
        response = '[1, 2, 3]'
        result = self.engine._parse_response(response)
        assert result == [1, 2, 3]

    def test_json_in_code_block(self):
        response = 'Here is the result:\n```json\n{"status": "ok"}\n```'
        result = self.engine._parse_response(response)
        assert result == {"status": "ok"}

    def test_json_in_generic_code_block(self):
        response = '```\n{"items": [1, 2]}\n```'
        result = self.engine._parse_response(response)
        assert result == {"items": [1, 2]}

    def test_json_object_embedded_in_text(self):
        response = 'The analysis result is {"score": 0.95, "pass": true} which is good.'
        result = self.engine._parse_response(response)
        assert result == {"score": 0.95, "pass": True}

    def test_json_array_embedded_in_text(self):
        response = 'Found items: ["a", "b", "c"] in the log.'
        result = self.engine._parse_response(response)
        assert result == ["a", "b", "c"]

    def test_plain_text_fallback(self):
        response = "No JSON here, just plain text."
        result = self.engine._parse_response(response)
        assert result == "No JSON here, just plain text."

    def test_invalid_json_fallback(self):
        response = '{not valid json at all}'
        result = self.engine._parse_response(response)
        assert isinstance(result, str)

    def test_whitespace_stripped(self):
        response = '  \n {"key": "value"} \n  '
        result = self.engine._parse_response(response)
        assert result == {"key": "value"}

    def test_nested_braces_in_text(self):
        """When braces contain valid JSON, it should be parsed."""
        response = 'Result: {"nested": {"a": 1}}'
        result = self.engine._parse_response(response)
        assert result == {"nested": {"a": 1}}


# ============================================================
# _check_dependencies 测试
# ============================================================

class TestCheckDependencies:
    def setup_method(self):
        self.engine = ChainOfThoughtEngine(llm_provider=Mock())

    def test_no_dependencies(self):
        step = make_step(depends_on=[])
        assert self.engine._check_dependencies(step, []) is True

    def test_dependency_satisfied(self):
        step = make_step(depends_on=["dep1"])
        completed = [
            StepResult(step_id="dep1", status=StepStatus.COMPLETED)
        ]
        assert self.engine._check_dependencies(step, completed) is True

    def test_dependency_not_satisfied(self):
        step = make_step(depends_on=["dep1"])
        completed = [
            StepResult(step_id="dep1", status=StepStatus.FAILED)
        ]
        assert self.engine._check_dependencies(step, completed) is False

    def test_dependency_missing(self):
        step = make_step(depends_on=["dep1"])
        assert self.engine._check_dependencies(step, []) is False

    def test_multiple_dependencies_all_met(self):
        step = make_step(depends_on=["dep1", "dep2"])
        completed = [
            StepResult(step_id="dep1", status=StepStatus.COMPLETED),
            StepResult(step_id="dep2", status=StepStatus.COMPLETED),
        ]
        assert self.engine._check_dependencies(step, completed) is True

    def test_multiple_dependencies_partial(self):
        step = make_step(depends_on=["dep1", "dep2"])
        completed = [
            StepResult(step_id="dep1", status=StepStatus.COMPLETED),
            StepResult(step_id="dep2", status=StepStatus.FAILED),
        ]
        assert self.engine._check_dependencies(step, completed) is False


# ============================================================
# Engine execute() - 单步测试
# ============================================================

class TestEngineSingleStep:
    def test_single_step_success(self):
        provider = make_mock_provider(['{"result": "success"}'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(template="Analyze: {input}"))

        result = engine.execute({"input": "test data"})

        assert result.status == ChainStatus.COMPLETED
        assert result.is_success is True
        assert result.completed_steps == 1
        assert result.failed_steps == 0
        provider.generate.assert_called_once()

    def test_single_step_output_stored(self):
        provider = make_mock_provider(['{"answer": 42}'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(output_key="analysis"))

        result = engine.execute({"input": "data"})

        assert result.final_output == {"answer": 42}
        assert "analysis" in result.context

    def test_single_step_plain_text_response(self):
        provider = make_mock_provider(["The analysis shows no issues."])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step())

        result = engine.execute({"input": "data"})

        assert result.is_success
        assert "no issues" in result.final_output

    def test_no_steps_returns_failed(self):
        engine = ChainOfThoughtEngine(llm_provider=Mock())
        result = engine.execute({"input": "data"})

        assert result.status == ChainStatus.FAILED
        assert "没有定义推理步骤" in result.error_message


# ============================================================
# Engine execute() - 多步测试
# ============================================================

class TestEngineMultiStep:
    def test_two_steps_sequential(self):
        provider = make_mock_provider([
            '{"analysis": "found issues"}',
            '{"recommendation": "fix bug"}',
        ])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1", name="Analyze", output_key="analysis"))
        engine.add_step(make_step(step_id="s2", name="Recommend", template="Based on {analysis}"))

        result = engine.execute({"input": "data"})

        assert result.is_success
        assert result.completed_steps == 2
        assert provider.generate.call_count == 2

    def test_output_key_forwarded_to_next_step(self):
        provider = make_mock_provider([
            '{"findings": "bug in auth"}',
            '{"fix": "patch auth module"}',
        ])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(
            step_id="s1", output_key="step1_result", template="Analyze {input}"
        ))
        engine.add_step(make_step(
            step_id="s2", template="Fix based on: {step1_result}"
        ))

        result = engine.execute({"input": "code"})

        assert result.is_success
        # Verify second call used the output of the first
        second_call_prompt = provider.generate.call_args_list[1][0][0]
        assert "findings" in second_call_prompt or "bug" in second_call_prompt

    def test_output_key_specified_in_execute(self):
        provider = make_mock_provider([
            '"intermediate"',
            '"final_value"',
        ])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1", output_key="mid"))
        engine.add_step(make_step(step_id="s2", output_key="end"))

        result = engine.execute({"input": "x"}, output_key="mid")

        assert result.final_output == "intermediate"

    def test_step_ordering(self):
        provider = make_mock_provider(['"first"', '"second"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s2", name="Second", order=2))
        engine.add_step(make_step(step_id="s1", name="First", order=1))

        result = engine.execute({"input": "data"})

        assert result.is_success
        assert result.step_results[0].step_id == "s1"
        assert result.step_results[1].step_id == "s2"


# ============================================================
# Engine execute() - 依赖测试
# ============================================================

class TestEngineDependencies:
    def test_dependency_met(self):
        provider = make_mock_provider(['"result_a"', '"result_b"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="a", order=1))
        engine.add_step(make_step(step_id="b", order=2, depends_on=["a"]))

        result = engine.execute({"input": "data"})

        assert result.is_success
        assert result.completed_steps == 2

    def test_dependency_not_met_skips_step(self):
        provider = Mock()
        provider.generate = Mock(side_effect=RuntimeError("LLM error"))
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="a", order=1))
        engine.add_step(make_step(step_id="b", order=2, depends_on=["a"]))

        result = engine.execute({"input": "data"})

        assert result.step_results[0].status == StepStatus.FAILED
        assert result.step_results[1].status == StepStatus.SKIPPED
        assert "依赖步骤未完成" in result.step_results[1].error_message


# ============================================================
# Engine execute() - 条件执行测试
# ============================================================

class TestEngineConditionalExecution:
    def test_condition_false_skips(self):
        provider = make_mock_provider(['"result"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(
            step_id="s1",
            condition=lambda ctx: ctx.get("should_run") is True,
        ))

        result = engine.execute({"input": "data", "should_run": False})

        assert result.step_results[0].status == StepStatus.SKIPPED
        assert "条件不满足" in result.step_results[0].error_message
        provider.generate.assert_not_called()

    def test_condition_true_executes(self):
        provider = make_mock_provider(['"done"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(
            step_id="s1",
            condition=lambda ctx: ctx.get("should_run") is True,
        ))

        result = engine.execute({"input": "data", "should_run": True})

        assert result.step_results[0].status == StepStatus.COMPLETED
        provider.generate.assert_called_once()


# ============================================================
# Engine execute() - 缓存测试
# ============================================================

class TestEngineCache:
    def test_cache_hit(self):
        provider = make_mock_provider(['{"cached": true}', '{"cached": false}'])
        config = ChainConfig(chain_id="test", name="Test", enable_cache=True)
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step(step_id="s1"))

        # First execution - populates cache
        result1 = engine.execute({"input": "same_data"})
        assert result1.is_success
        assert provider.generate.call_count == 1

        # Second execution with same input - should hit cache
        result2 = engine.execute({"input": "same_data"})
        assert result2.is_success
        # generate should NOT be called again
        assert provider.generate.call_count == 1
        assert result2.step_results[0].metadata.get("from_cache") is True

    def test_cache_disabled(self):
        provider = make_mock_provider(['"first"', '"second"'])
        config = ChainConfig(chain_id="test", name="Test", enable_cache=False)
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step(step_id="s1"))

        engine.execute({"input": "data"})
        engine.execute({"input": "data"})

        assert provider.generate.call_count == 2

    def test_clear_cache(self):
        provider = make_mock_provider(['"first"', '"second"'])
        config = ChainConfig(chain_id="test", name="Test", enable_cache=True)
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step(step_id="s1"))

        engine.execute({"input": "data"})
        engine.clear_cache()
        engine.execute({"input": "data"})

        assert provider.generate.call_count == 2


# ============================================================
# Engine execute() - 错误与重试测试
# ============================================================

class TestEngineErrorAndRetry:
    @patch("ai_test_tool.reasoning.engine.time.sleep")
    def test_retry_then_succeed(self, mock_sleep):
        provider = Mock()
        provider.generate = Mock(side_effect=[
            RuntimeError("temporary failure"),
            '{"result": "ok"}',
        ])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1", retry_count=2))

        result = engine.execute({"input": "data"})

        assert result.is_success
        assert result.step_results[0].retry_count == 1  # succeeded on 2nd attempt (index 1)
        assert provider.generate.call_count == 2

    @patch("ai_test_tool.reasoning.engine.time.sleep")
    def test_all_retries_fail(self, mock_sleep):
        provider = Mock()
        provider.generate = Mock(side_effect=RuntimeError("persistent failure"))
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1", retry_count=3))

        result = engine.execute({"input": "data"})

        assert result.step_results[0].status == StepStatus.FAILED
        assert "persistent failure" in result.step_results[0].error_message
        assert provider.generate.call_count == 3

    def test_stop_on_error(self):
        provider = Mock()
        provider.generate = Mock(side_effect=RuntimeError("fail"))
        config = ChainConfig(chain_id="test", name="Test", stop_on_error=True)
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step(step_id="s1", order=1))
        engine.add_step(make_step(step_id="s2", order=2))

        result = engine.execute({"input": "data"})

        assert result.step_results[0].status == StepStatus.FAILED
        assert len(result.step_results) == 1  # second step never attempted

    def test_continue_on_error(self):
        provider = Mock()
        provider.generate = Mock(side_effect=[
            RuntimeError("step 1 fails"),
            '"step 2 ok"',
        ])
        config = ChainConfig(chain_id="test", name="Test", stop_on_error=False)
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step(step_id="s1", order=1))
        engine.add_step(make_step(step_id="s2", order=2))

        result = engine.execute({"input": "data"})

        assert result.step_results[0].status == StepStatus.FAILED
        assert result.step_results[1].status == StepStatus.COMPLETED
        assert result.status == ChainStatus.PARTIAL


# ============================================================
# Engine execute() - 超时测试
# ============================================================

class TestEngineTimeout:
    @patch("ai_test_tool.reasoning.engine.time.time")
    def test_total_timeout(self, mock_time):
        # Simulate: start=0, first check=0, after step1=400 (exceeds 300s default)
        mock_time.side_effect = [
            0,      # start_time
            0,      # elapsed check step 1
            100,    # step_start in _execute_step
            150,    # step end in _execute_step
            400,    # elapsed check step 2 -> exceeds 300
            400,    # final time calc
        ]
        provider = make_mock_provider(['"ok"', '"should not run"'])
        config = ChainConfig(chain_id="test", name="Test", total_timeout_seconds=300)
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step(step_id="s1", order=1))
        engine.add_step(make_step(step_id="s2", order=2))

        result = engine.execute({"input": "data"})

        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.step_results[1].status == StepStatus.SKIPPED
        assert "超时" in result.step_results[1].error_message


# ============================================================
# Engine execute() - thinking extraction 集成测试
# ============================================================

class TestEngineThinkingExtraction:
    def test_thinking_extracted_in_result(self):
        provider = make_mock_provider([
            '<think>Analyzing the input carefully</think>{"answer": "yes"}'
        ])
        config = ChainConfig(
            chain_id="test", name="Test", enable_thinking_extraction=True
        )
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step())

        result = engine.execute({"input": "data"})

        assert result.is_success
        step_result = result.step_results[0]
        assert "Analyzing the input carefully" in step_result.thinking
        assert step_result.output == {"answer": "yes"}

    def test_thinking_extraction_disabled(self):
        provider = make_mock_provider([
            '<think>hidden</think>{"answer": "yes"}'
        ])
        config = ChainConfig(
            chain_id="test", name="Test", enable_thinking_extraction=False
        )
        engine = ChainOfThoughtEngine(llm_provider=provider, config=config)
        engine.add_step(make_step())

        result = engine.execute({"input": "data"})

        assert result.is_success
        step_result = result.step_results[0]
        assert step_result.thinking == ""


# ============================================================
# Engine execute() - post_processor 测试
# ============================================================

class TestEnginePostProcessor:
    def test_post_processor_applied(self):
        provider = make_mock_provider(['{"value": 10}'])
        engine = ChainOfThoughtEngine(llm_provider=provider)

        def double_value(context, output):
            if isinstance(output, dict) and "value" in output:
                output["value"] *= 2
            return output

        engine.add_step(make_step(post_processor=double_value))

        result = engine.execute({"input": "data"})

        assert result.is_success
        assert result.final_output == {"value": 20}


# ============================================================
# Engine - _critic_validate (CRITIC 模式) 测试
# ============================================================

class TestEngineCriticValidate:
    @patch("ai_test_tool.reasoning.engine.ReflectionEngine")
    def test_critic_improves_output(self, MockReflectionEngine):
        from ai_test_tool.reflection.models import RefinedOutput, ReflectionConfig

        mock_reflection = MockReflectionEngine.return_value
        mock_reflection.reflect_and_refine.return_value = RefinedOutput(
            original="original output",
            refined="improved output",
            total_rounds=2,
            final_passed=True,
        )

        provider = make_mock_provider(['"original output"'])
        reflection_config = ReflectionConfig(enabled=True, max_rounds=3)
        engine = ChainOfThoughtEngine(
            llm_provider=provider, reflection_config=reflection_config
        )
        engine.add_step(make_step(output_key="result"))

        result = engine.execute({"input": "data"})

        assert result.is_success
        mock_reflection.reflect_and_refine.assert_called_once()

    @patch("ai_test_tool.reasoning.engine.ReflectionEngine")
    def test_critic_no_improvement(self, MockReflectionEngine):
        from ai_test_tool.reflection.models import RefinedOutput, ReflectionConfig

        mock_reflection = MockReflectionEngine.return_value
        mock_reflection.reflect_and_refine.return_value = RefinedOutput(
            original="good output",
            refined="good output",
            total_rounds=1,
            final_passed=True,
        )

        provider = make_mock_provider(['"good output"'])
        reflection_config = ReflectionConfig(enabled=True)
        engine = ChainOfThoughtEngine(
            llm_provider=provider, reflection_config=reflection_config
        )
        engine.add_step(make_step(output_key="result"))

        result = engine.execute({"input": "data"})

        assert result.is_success
        # Output should remain unchanged
        assert result.step_results[0].output == "good output"

    def test_critic_disabled_by_default(self):
        provider = make_mock_provider(['"output"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step())

        with patch.object(engine, "_critic_validate") as mock_critic:
            engine.execute({"input": "data"})
            mock_critic.assert_not_called()


# ============================================================
# Engine - add_step / add_steps / clear_steps 管理测试
# ============================================================

class TestEngineStepManagement:
    def test_add_step_returns_self(self):
        engine = ChainOfThoughtEngine(llm_provider=Mock())
        returned = engine.add_step(make_step())
        assert returned is engine

    def test_add_steps_batch(self):
        engine = ChainOfThoughtEngine(llm_provider=Mock())
        engine.add_steps([make_step(step_id="a"), make_step(step_id="b")])
        assert engine.step_count == 2

    def test_clear_steps(self):
        engine = ChainOfThoughtEngine(llm_provider=Mock())
        engine.add_step(make_step())
        engine.clear_steps()
        assert engine.step_count == 0

    def test_steps_property_returns_copy(self):
        engine = ChainOfThoughtEngine(llm_provider=Mock())
        engine.add_step(make_step())
        steps = engine.steps
        steps.clear()
        assert engine.step_count == 1  # original not affected

    def test_auto_ordering(self):
        engine = ChainOfThoughtEngine(llm_provider=Mock())
        engine.add_step(make_step(step_id="a", order=0))
        engine.add_step(make_step(step_id="b", order=0))
        assert engine.steps[0].order == 1
        assert engine.steps[1].order == 2

    def test_chained_add(self):
        engine = ChainOfThoughtEngine(llm_provider=Mock())
        engine.add_step(make_step(step_id="a")).add_step(make_step(step_id="b"))
        assert engine.step_count == 2


# ============================================================
# Engine execute() - 状态计算测试
# ============================================================

class TestEngineStatusCalculation:
    def test_all_completed(self):
        provider = make_mock_provider(['"ok"', '"ok"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1"))
        engine.add_step(make_step(step_id="s2"))

        result = engine.execute({"input": "data"})
        assert result.status == ChainStatus.COMPLETED

    def test_partial_with_skipped(self):
        provider = make_mock_provider(['"ok"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1", order=1))
        engine.add_step(make_step(
            step_id="s2", order=2,
            condition=lambda ctx: False,  # always skip
        ))

        result = engine.execute({"input": "data"})

        assert result.status == ChainStatus.PARTIAL

    def test_all_failed(self):
        provider = Mock()
        provider.generate = Mock(side_effect=RuntimeError("fail"))
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1"))

        result = engine.execute({"input": "data"})
        assert result.status == ChainStatus.FAILED

    def test_token_usage_aggregated(self):
        provider = make_mock_provider(['"a"', '"b"'])
        engine = ChainOfThoughtEngine(llm_provider=provider)
        engine.add_step(make_step(step_id="s1"))
        engine.add_step(make_step(step_id="s2"))

        result = engine.execute({"input": "data"})

        # Token usage is empty by default (provider mock doesn't set it),
        # but the aggregation logic should not error
        assert isinstance(result.total_token_usage, dict)


# ============================================================
# create_engine 便捷函数测试
# ============================================================

class TestCreateEngine:
    def test_default(self):
        engine = create_engine()
        assert engine.config.chain_id == "default"
        assert engine.config.name == "Default Chain"

    def test_custom_id_and_name(self):
        engine = create_engine(chain_id="test_chain", name="My Chain")
        assert engine.config.chain_id == "test_chain"
        assert engine.config.name == "My Chain"

    def test_with_provider(self):
        provider = Mock()
        engine = create_engine(llm_provider=provider)
        assert engine._llm_provider is provider

    def test_with_config_kwargs(self):
        engine = create_engine(
            stop_on_error=True,
            enable_cache=False,
            total_timeout_seconds=60,
        )
        assert engine.config.stop_on_error is True
        assert engine.config.enable_cache is False
        assert engine.config.total_timeout_seconds == 60


# ============================================================
# Engine - lazy LLM provider 测试
# ============================================================

class TestEngineLazyProvider:
    @patch("ai_test_tool.reasoning.engine.get_llm_provider")
    def test_lazy_provider_loaded(self, mock_get):
        mock_provider = Mock()
        mock_provider.generate = Mock(return_value='"ok"')
        mock_get.return_value = mock_provider

        engine = ChainOfThoughtEngine()  # no provider given
        engine.add_step(make_step())

        result = engine.execute({"input": "data"})

        mock_get.assert_called_once()
        assert result.is_success
