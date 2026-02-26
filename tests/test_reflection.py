"""
Reflection 引擎单元测试
"""

import json
from unittest.mock import Mock

import pytest

from ai_test_tool.reflection.models import ReflectionResult, RefinedOutput, ReflectionConfig
from ai_test_tool.reflection.engine import ReflectionEngine


# ============================================================
# Models 测试
# ============================================================

class TestReflectionResult:
    def test_to_dict(self):
        result = ReflectionResult(
            score=0.8,
            passed=True,
            feedback="Good output",
            issues=["minor issue"],
            suggestions=["try X"],
            round_number=1,
        )
        d = result.to_dict()
        assert d["score"] == 0.8
        assert d["passed"] is True
        assert len(d["issues"]) == 1


class TestRefinedOutput:
    def test_improved_true(self):
        output = RefinedOutput(
            original="version 1",
            refined="version 2",
            total_rounds=1,
            final_passed=True,
        )
        assert output.improved is True

    def test_improved_false(self):
        output = RefinedOutput(
            original="same",
            refined="same",
            total_rounds=1,
            final_passed=True,
        )
        assert output.improved is False

    def test_to_dict(self):
        output = RefinedOutput(
            original="a",
            refined="b",
            total_rounds=2,
            final_passed=True,
        )
        d = output.to_dict()
        assert d["improved"] is True
        assert d["total_rounds"] == 2


# ============================================================
# ReflectionEngine 测试
# ============================================================

def make_reflect_response(score: float, passed: bool, feedback: str = "ok") -> str:
    return json.dumps({
        "score": score,
        "passed": passed,
        "feedback": feedback,
        "issues": ["issue1"] if not passed else [],
        "suggestions": ["suggestion1"] if not passed else [],
    })


class TestReflectionEngine:
    def test_reflect_passes(self):
        provider = Mock()
        provider.generate = Mock(return_value=make_reflect_response(0.9, True, "Great!"))

        engine = ReflectionEngine(llm_provider=provider)
        result = engine.reflect("test output", task="test task")

        assert result.passed is True
        assert result.score == 0.9
        assert result.feedback == "Great!"
        provider.generate.assert_called_once()

    def test_reflect_fails(self):
        provider = Mock()
        provider.generate = Mock(return_value=make_reflect_response(0.3, False, "Needs improvement"))

        engine = ReflectionEngine(llm_provider=provider)
        result = engine.reflect("poor output")

        assert result.passed is False
        assert result.score == 0.3
        assert len(result.issues) == 1

    def test_reflect_llm_error(self):
        provider = Mock()
        provider.generate = Mock(side_effect=RuntimeError("LLM down"))

        engine = ReflectionEngine(llm_provider=provider)
        result = engine.reflect("test")

        # Should default to passed=True to avoid blocking
        assert result.passed is True
        assert "出错" in result.feedback

    def test_refine(self):
        provider = Mock()
        provider.generate = Mock(return_value="improved output")

        engine = ReflectionEngine(llm_provider=provider)
        reflection = ReflectionResult(
            score=0.3,
            passed=False,
            feedback="needs work",
            issues=["issue1"],
            suggestions=["do better"],
        )
        refined = engine.refine("original", reflection, task="task")
        assert refined == "improved output"

    def test_refine_llm_error(self):
        provider = Mock()
        provider.generate = Mock(side_effect=RuntimeError("fail"))

        engine = ReflectionEngine(llm_provider=provider)
        reflection = ReflectionResult(score=0.3, passed=False, feedback="bad")
        refined = engine.refine("original", reflection)
        assert refined == "original"  # returns original on error


class TestReflectAndRefine:
    def test_single_round_pass(self):
        provider = Mock()
        provider.generate = Mock(return_value=make_reflect_response(0.9, True))

        config = ReflectionConfig(max_rounds=3)
        engine = ReflectionEngine(llm_provider=provider, config=config)
        result = engine.reflect_and_refine("good output", task="task")

        assert result.final_passed is True
        assert result.total_rounds == 1
        assert result.refined == "good output"  # no refinement needed
        assert provider.generate.call_count == 1  # only reflect, no refine

    def test_multi_round_improvement(self):
        provider = Mock()
        # Round 1: fail -> refine -> Round 2: pass
        provider.generate = Mock(side_effect=[
            make_reflect_response(0.3, False, "needs work"),  # reflect round 1
            "improved output",                                 # refine round 1
            make_reflect_response(0.9, True, "great"),         # reflect round 2
        ])

        config = ReflectionConfig(max_rounds=3)
        engine = ReflectionEngine(llm_provider=provider, config=config)
        result = engine.reflect_and_refine("poor output", task="task")

        assert result.final_passed is True
        assert result.total_rounds == 2
        assert result.refined == "improved output"
        assert result.improved is True

    def test_max_rounds_exhausted(self):
        provider = Mock()
        # Always fails
        provider.generate = Mock(side_effect=[
            make_reflect_response(0.2, False),
            "slightly better",
            make_reflect_response(0.3, False),
            "a bit better",
            make_reflect_response(0.4, False),
        ])

        config = ReflectionConfig(max_rounds=3)
        engine = ReflectionEngine(llm_provider=provider, config=config)
        result = engine.reflect_and_refine("bad output")

        assert result.total_rounds == 3
        assert result.final_passed is False


class TestParseReflection:
    def test_parse_json_block(self):
        engine = ReflectionEngine(llm_provider=Mock())
        raw = '```json\n{"score": 0.8, "passed": true, "feedback": "good"}\n```'
        result = engine._parse_reflection(raw, 1)
        assert result.score == 0.8
        assert result.passed is True

    def test_parse_bare_json(self):
        engine = ReflectionEngine(llm_provider=Mock())
        raw = '{"score": 0.5, "passed": false, "feedback": "meh", "issues": ["a"]}'
        result = engine._parse_reflection(raw, 1)
        assert result.score == 0.5
        assert result.passed is False

    def test_parse_invalid_json(self):
        engine = ReflectionEngine(llm_provider=Mock())
        raw = "This is not JSON at all"
        result = engine._parse_reflection(raw, 1)
        # Should fall back to defaults
        assert result.score == 0.5
        assert result.feedback  # should have some text

    def test_parse_score_determines_passed(self):
        engine = ReflectionEngine(
            llm_provider=Mock(),
            config=ReflectionConfig(pass_threshold=0.7),
        )
        raw = '{"score": 0.8}'
        result = engine._parse_reflection(raw, 1)
        assert result.passed is True  # score > threshold
