"""
CoT链式推理模块

将复杂问题分解为步骤链，每步输出中间结果，支持追溯

使用示例：

1. 使用内置推理链：
```python
from ai_test_tool.reasoning import ErrorDiagnosisChain

chain = ErrorDiagnosisChain()
result = chain.diagnose(log_content="...")
print(result.final_output)
print(result.thinking_trace)  # 查看思考过程
```

2. 使用ChainBuilder构建自定义链：
```python
from ai_test_tool.reasoning import ChainBuilder

chain = (
    ChainBuilder("my_chain", "自定义分析链")
    .add_extraction_step("extract", "提取", "从{input}提取信息")
    .add_analysis_step("analyze", "分析", "分析{extract}", depends_on=["extract"])
    .with_config(stop_on_error=True)
    .build()
)
result = chain.execute({"input": "..."})
```

3. 使用预定义模板：
```python
from ai_test_tool.reasoning.builder import create_simple_analysis_chain

chain = create_simple_analysis_chain("test")
result = chain.execute({"input": "..."})
```
"""

from .models import (
    ThinkingStep,
    StepResult,
    ChainConfig,
    ChainResult,
    ChainContext,
    StepStatus,
    ChainStatus,
    ReasoningStepType,
)
from .engine import ChainOfThoughtEngine, create_engine
from .chains import (
    ErrorDiagnosisChain,
    PerformanceAnalysisChain,
    RootCauseChain,
    SecurityAuditChain,
)
from .builder import (
    ChainBuilder,
    create_simple_analysis_chain,
    create_problem_solving_chain,
    create_comparison_chain,
)

__all__ = [
    # 数据模型
    "ThinkingStep",
    "StepResult",
    "ChainConfig",
    "ChainResult",
    "ChainContext",
    "StepStatus",
    "ChainStatus",
    "ReasoningStepType",
    # 引擎
    "ChainOfThoughtEngine",
    "create_engine",
    # 内置推理链
    "ErrorDiagnosisChain",
    "PerformanceAnalysisChain",
    "RootCauseChain",
    "SecurityAuditChain",
    # 构建器
    "ChainBuilder",
    # 预定义模板
    "create_simple_analysis_chain",
    "create_problem_solving_chain",
    "create_comparison_chain",
]
