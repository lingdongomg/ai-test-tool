"""
ChainBuilder - 流式推理链构建器

提供流式API来构建自定义推理链
"""

from typing import Any, Callable

from .models import ThinkingStep, ChainConfig, StepType
from .engine import ChainOfThoughtEngine
from ..llm.provider import LLMProvider


class ChainBuilder:
    """
    推理链流式构建器

    使用示例：
    ```python
    chain = (
        ChainBuilder("my_chain", "我的推理链")
        .add_step(
            step_id="step1",
            name="分析",
            prompt="分析以下内容：{input}"
        )
        .add_step(
            step_id="step2",
            name="总结",
            prompt="基于分析结果总结：{step1}",
            depends_on=["step1"]
        )
        .with_config(stop_on_error=True)
        .build()
    )

    result = chain.execute({"input": "..."})
    ```
    """

    def __init__(
        self,
        chain_id: str,
        name: str,
        description: str = "",
        llm_provider: LLMProvider | None = None
    ):
        """
        初始化构建器

        Args:
            chain_id: 链唯一标识
            name: 链名称
            description: 链描述
            llm_provider: LLM提供者
        """
        self._chain_id = chain_id
        self._name = name
        self._description = description
        self._llm_provider = llm_provider
        self._steps: list[ThinkingStep] = []
        self._config_kwargs: dict[str, Any] = {}

    def add_step(
        self,
        step_id: str,
        name: str,
        prompt: str,
        description: str = "",
        step_type: StepType = StepType.ANALYSIS,
        depends_on: list[str] | None = None,
        input_keys: list[str] | None = None,
        output_key: str = "",
        required: bool = True,
        timeout_seconds: int = 60,
        retry_count: int = 1,
        condition: Callable[[dict], bool] | None = None,
        post_processor: Callable[[dict, str], Any] | None = None,
        **metadata: Any
    ) -> "ChainBuilder":
        """
        添加推理步骤

        Args:
            step_id: 步骤ID
            name: 步骤名称
            prompt: Prompt模板
            description: 步骤描述
            step_type: 步骤类型
            depends_on: 依赖的步骤ID列表
            input_keys: 输入键列表
            output_key: 输出键
            required: 是否必须执行
            timeout_seconds: 超时时间
            retry_count: 重试次数
            condition: 执行条件函数
            post_processor: 后处理函数
            **metadata: 额外元数据

        Returns:
            self（支持链式调用）
        """
        step = ThinkingStep(
            step_id=step_id,
            name=name,
            description=description or name,
            prompt_template=prompt,
            step_type=step_type,
            order=len(self._steps) + 1,
            depends_on=depends_on or [],
            input_keys=input_keys or [],
            output_key=output_key or step_id,
            required=required,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            condition=condition,
            post_processor=post_processor,
            metadata=metadata
        )
        self._steps.append(step)
        return self

    def add_analysis_step(
        self,
        step_id: str,
        name: str,
        prompt: str,
        **kwargs: Any
    ) -> "ChainBuilder":
        """添加分析类型步骤（快捷方法）"""
        return self.add_step(
            step_id=step_id,
            name=name,
            prompt=prompt,
            step_type=StepType.ANALYSIS,
            **kwargs
        )

    def add_extraction_step(
        self,
        step_id: str,
        name: str,
        prompt: str,
        **kwargs: Any
    ) -> "ChainBuilder":
        """添加提取类型步骤（快捷方法）"""
        return self.add_step(
            step_id=step_id,
            name=name,
            prompt=prompt,
            step_type=StepType.EXTRACTION,
            **kwargs
        )

    def add_inference_step(
        self,
        step_id: str,
        name: str,
        prompt: str,
        **kwargs: Any
    ) -> "ChainBuilder":
        """添加推理类型步骤（快捷方法）"""
        return self.add_step(
            step_id=step_id,
            name=name,
            prompt=prompt,
            step_type=StepType.INFERENCE,
            **kwargs
        )

    def add_synthesis_step(
        self,
        step_id: str,
        name: str,
        prompt: str,
        **kwargs: Any
    ) -> "ChainBuilder":
        """添加综合类型步骤（快捷方法）"""
        return self.add_step(
            step_id=step_id,
            name=name,
            prompt=prompt,
            step_type=StepType.SYNTHESIS,
            **kwargs
        )

    def add_validation_step(
        self,
        step_id: str,
        name: str,
        prompt: str,
        **kwargs: Any
    ) -> "ChainBuilder":
        """添加验证类型步骤（快捷方法）"""
        return self.add_step(
            step_id=step_id,
            name=name,
            prompt=prompt,
            step_type=StepType.VALIDATION,
            **kwargs
        )

    def add_action_step(
        self,
        step_id: str,
        name: str,
        prompt: str,
        **kwargs: Any
    ) -> "ChainBuilder":
        """添加动作类型步骤（快捷方法）"""
        return self.add_step(
            step_id=step_id,
            name=name,
            prompt=prompt,
            step_type=StepType.ACTION,
            **kwargs
        )

    def with_config(
        self,
        max_steps: int | None = None,
        total_timeout_seconds: int | None = None,
        stop_on_error: bool | None = None,
        enable_cache: bool | None = None,
        enable_thinking_extraction: bool | None = None,
        parallel_independent_steps: bool | None = None,
        verbose: bool | None = None,
        **metadata: Any
    ) -> "ChainBuilder":
        """
        配置链参数

        Args:
            max_steps: 最大步骤数
            total_timeout_seconds: 总超时时间
            stop_on_error: 遇错停止
            enable_cache: 启用缓存
            enable_thinking_extraction: 提取思考过程
            parallel_independent_steps: 并行执行独立步骤
            verbose: 详细日志
            **metadata: 额外元数据

        Returns:
            self（支持链式调用）
        """
        if max_steps is not None:
            self._config_kwargs["max_steps"] = max_steps
        if total_timeout_seconds is not None:
            self._config_kwargs["total_timeout_seconds"] = total_timeout_seconds
        if stop_on_error is not None:
            self._config_kwargs["stop_on_error"] = stop_on_error
        if enable_cache is not None:
            self._config_kwargs["enable_cache"] = enable_cache
        if enable_thinking_extraction is not None:
            self._config_kwargs["enable_thinking_extraction"] = enable_thinking_extraction
        if parallel_independent_steps is not None:
            self._config_kwargs["parallel_independent_steps"] = parallel_independent_steps
        if verbose is not None:
            self._config_kwargs["verbose"] = verbose
        if metadata:
            self._config_kwargs.setdefault("metadata", {}).update(metadata)
        return self

    def with_llm(self, llm_provider: LLMProvider) -> "ChainBuilder":
        """
        设置LLM提供者

        Args:
            llm_provider: LLM提供者

        Returns:
            self（支持链式调用）
        """
        self._llm_provider = llm_provider
        return self

    def build(self) -> ChainOfThoughtEngine:
        """
        构建推理引擎

        Returns:
            配置好的ChainOfThoughtEngine实例
        """
        config = ChainConfig(
            chain_id=self._chain_id,
            name=self._name,
            description=self._description,
            **self._config_kwargs
        )

        engine = ChainOfThoughtEngine(
            llm_provider=self._llm_provider,
            config=config
        )

        engine.add_steps(self._steps)
        return engine

    def __repr__(self) -> str:
        return (
            f"ChainBuilder(chain_id={self._chain_id!r}, "
            f"name={self._name!r}, "
            f"steps={len(self._steps)})"
        )


# 预定义的推理链模板
def create_simple_analysis_chain(
    name: str = "simple_analysis",
    llm_provider: LLMProvider | None = None
) -> ChainOfThoughtEngine:
    """
    创建简单分析链

    步骤：提取 -> 分析 -> 总结
    """
    return (
        ChainBuilder(f"{name}_chain", f"{name}分析链", llm_provider=llm_provider)
        .add_extraction_step(
            "extract",
            "信息提取",
            """从以下内容中提取关键信息：

{input}

请以JSON格式输出提取的关键信息："""
        )
        .add_analysis_step(
            "analyze",
            "深入分析",
            """基于提取的信息进行分析：

提取结果：
{extract}

请分析其中的模式、问题和关联，以JSON格式输出：""",
            depends_on=["extract"]
        )
        .add_synthesis_step(
            "summarize",
            "综合总结",
            """基于以上分析生成总结：

提取结果：
{extract}

分析结果：
{analyze}

请生成结构化的总结报告，以JSON格式输出：""",
            depends_on=["extract", "analyze"]
        )
        .build()
    )


def create_problem_solving_chain(
    name: str = "problem_solving",
    llm_provider: LLMProvider | None = None
) -> ChainOfThoughtEngine:
    """
    创建问题解决链

    步骤：理解问题 -> 分析原因 -> 生成方案 -> 评估方案
    """
    return (
        ChainBuilder(f"{name}_chain", f"{name}问题解决链", llm_provider=llm_provider)
        .add_extraction_step(
            "understand",
            "理解问题",
            """理解以下问题的核心：

问题描述：
{problem}

请识别：
1. 问题的核心是什么
2. 问题的边界条件
3. 相关的约束

以JSON格式输出："""
        )
        .add_analysis_step(
            "analyze_cause",
            "分析原因",
            """分析问题的可能原因：

问题理解：
{understand}

原始问题：
{problem}

请分析可能的原因，以JSON格式输出：""",
            depends_on=["understand"]
        )
        .add_inference_step(
            "generate_solutions",
            "生成方案",
            """基于分析生成解决方案：

问题理解：
{understand}

原因分析：
{analyze_cause}

请生成多个解决方案，以JSON格式输出：""",
            depends_on=["understand", "analyze_cause"]
        )
        .add_validation_step(
            "evaluate",
            "评估方案",
            """评估各个解决方案：

方案列表：
{generate_solutions}

请评估每个方案的优缺点和可行性，推荐最佳方案，以JSON格式输出：""",
            depends_on=["generate_solutions"]
        )
        .build()
    )


def create_comparison_chain(
    name: str = "comparison",
    llm_provider: LLMProvider | None = None
) -> ChainOfThoughtEngine:
    """
    创建对比分析链

    步骤：提取特征 -> 对比分析 -> 总结结论
    """
    return (
        ChainBuilder(f"{name}_chain", f"{name}对比分析链", llm_provider=llm_provider)
        .add_extraction_step(
            "extract_features",
            "提取特征",
            """从以下对象中提取可比较的特征：

对象A：
{object_a}

对象B：
{object_b}

请提取两者的关键特征，以JSON格式输出："""
        )
        .add_analysis_step(
            "compare",
            "对比分析",
            """对比两个对象的特征：

特征提取结果：
{extract_features}

请进行详细对比，以JSON格式输出：""",
            depends_on=["extract_features"]
        )
        .add_synthesis_step(
            "conclude",
            "总结结论",
            """基于对比分析得出结论：

对比结果：
{compare}

请总结主要差异和结论，以JSON格式输出：""",
            depends_on=["compare"]
        )
        .build()
    )
