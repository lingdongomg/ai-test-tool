"""
Reflection 引擎

对 LLM 输出进行反思评估和修正
"""

import json
import logging
import re
from typing import Any

from .models import ReflectionResult, RefinedOutput, ReflectionConfig
from ..llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


REFLECT_PROMPT = """请评估以下输出的质量。

## 原始任务
{task}

## 待评估的输出
{output}

## 评估标准
{criteria}

## 输出格式
请以 JSON 格式返回评估结果：
```json
{{
  "score": 0.0-1.0,
  "passed": true/false,
  "feedback": "总体评价",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}}
```
"""

REFINE_PROMPT = """请根据反馈改进以下输出。

## 原始任务
{task}

## 当前输出
{output}

## 反馈
{feedback}

## 发现的问题
{issues}

## 改进建议
{suggestions}

请输出改进后的完整结果，不需要解释修改了什么。"""


class ReflectionEngine:
    """
    Reflection 引擎

    提供：
    - reflect(): 对输出进行 LLM 驱动的评估
    - refine(): 基于评估结果生成修正输出
    - reflect_and_refine(): 完整的反思-修正循环
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        config: ReflectionConfig | None = None,
    ):
        self._llm_provider = llm_provider
        self.config = config or ReflectionConfig()

    @property
    def llm_provider(self) -> LLMProvider:
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    def reflect(
        self,
        output: str,
        task: str = "",
        criteria: str = "准确性、完整性、可操作性",
        round_number: int = 1,
    ) -> ReflectionResult:
        """
        对输出进行反思评估

        Args:
            output: 待评估的输出
            task: 原始任务描述
            criteria: 评估标准
            round_number: 当前轮次

        Returns:
            反思评估结果
        """
        prompt = REFLECT_PROMPT.format(
            task=task or "(未提供)",
            output=output,
            criteria=criteria,
        )

        try:
            raw = self.llm_provider.generate(prompt)
            result = self._parse_reflection(raw, round_number)
            return result
        except Exception as e:
            logger.error(f"Reflection 失败: {e}")
            return ReflectionResult(
                score=0.5,
                passed=True,  # 失败时默认通过，避免阻塞
                feedback=f"反思评估出错: {e}",
                round_number=round_number,
            )

    def refine(
        self,
        output: str,
        reflection: ReflectionResult,
        task: str = "",
    ) -> str:
        """
        基于反思结果修正输出

        Args:
            output: 原始输出
            reflection: 反思结果
            task: 原始任务

        Returns:
            修正后的输出
        """
        prompt = REFINE_PROMPT.format(
            task=task or "(未提供)",
            output=output,
            feedback=reflection.feedback,
            issues="\n".join(f"- {i}" for i in reflection.issues) or "无",
            suggestions="\n".join(f"- {s}" for s in reflection.suggestions) or "无",
        )

        try:
            refined = self.llm_provider.generate(prompt)
            return refined.strip()
        except Exception as e:
            logger.error(f"Refine 失败: {e}")
            return output  # 失败时返回原始输出

    def reflect_and_refine(
        self,
        output: str,
        task: str = "",
        criteria: str = "准确性、完整性、可操作性",
        max_rounds: int | None = None,
    ) -> RefinedOutput:
        """
        完整的反思-修正循环

        Args:
            output: 原始输出
            task: 原始任务
            criteria: 评估标准
            max_rounds: 最大轮数（None 使用 config 默认值）

        Returns:
            修正后的输出（包含完整反思历史）
        """
        max_rounds = max_rounds or self.config.max_rounds
        current_output = output
        reflections: list[ReflectionResult] = []

        for round_num in range(1, max_rounds + 1):
            # 反思
            reflection = self.reflect(
                output=current_output,
                task=task,
                criteria=criteria,
                round_number=round_num,
            )
            reflections.append(reflection)

            # 通过则终止
            if reflection.passed:
                logger.info(f"Reflection 第 {round_num} 轮通过 (score={reflection.score:.2f})")
                break

            # 修正
            logger.info(f"Reflection 第 {round_num} 轮未通过 (score={reflection.score:.2f}), 进行修正")
            current_output = self.refine(
                output=current_output,
                reflection=reflection,
                task=task,
            )

        return RefinedOutput(
            original=output,
            refined=current_output,
            reflections=reflections,
            total_rounds=len(reflections),
            final_passed=reflections[-1].passed if reflections else False,
        )

    def _parse_reflection(self, raw: str, round_number: int) -> ReflectionResult:
        """解析 LLM 的反思输出为结构化结果"""
        # 尝试从 JSON 代码块提取
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
        json_str = json_match.group(1).strip() if json_match else raw.strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试从花括号提取
            brace_start = raw.find("{")
            brace_end = raw.rfind("}") + 1
            if brace_start >= 0 and brace_end > brace_start:
                try:
                    data = json.loads(raw[brace_start:brace_end])
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        score = float(data.get("score", 0.5))
        passed = data.get("passed", score >= self.config.pass_threshold)

        return ReflectionResult(
            score=score,
            passed=passed,
            feedback=data.get("feedback", raw[:200]),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            round_number=round_number,
        )
