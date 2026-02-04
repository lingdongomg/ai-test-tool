"""
ReAct循环推理模块

实现Reasoning + Acting循环模式，支持工具调用和环境交互

核心概念：
- Thought（思考）: LLM分析当前状态，决定下一步行动
- Action（行动）: 执行工具调用或操作
- Observation（观察）: 获取行动结果，更新状态
- 循环: 重复以上步骤直到任务完成或达到限制

使用示例：

1. 使用预定义Agent：
```python
from ai_test_tool.react import LogAnalysisAgent

agent = LogAnalysisAgent()
result = agent.run(
    task="分析日志中的错误并找出根因",
    log_content="...",
    requests=[...]
)
print(result.final_answer)
print(result.trajectory)  # 查看推理轨迹
```

2. 使用ReActEngine自定义Agent：
```python
from ai_test_tool.react import ReActEngine, Tool

# 注册自定义工具
engine = ReActEngine()
engine.register_tool(Tool(
    name="search_logs",
    description="搜索日志中的关键词",
    func=lambda keyword: search_in_logs(keyword)
))

result = engine.run(task="查找所有超时错误")
```

3. 使用装饰器注册工具：
```python
from ai_test_tool.react import tool

@tool(name="query_db", description="查询数据库")
def query_database(sql: str) -> str:
    return execute_sql(sql)
```
"""

from .models import (
    Thought,
    Action,
    Observation,
    ReActStep,
    ReActResult,
    ReActConfig,
    Tool,
    ToolResult,
    StopReason,
    ActionType,
    AgentContext,
)
from .tools import (
    ToolRegistry,
    tool,
    get_tool_registry,
    register_tool,
    # 内置工具
    SearchLogsTool,
    FilterRequestsTool,
    CalculateStatsTool,
    ExtractPatternsTool,
    CompareTimePeriodsTool,
)
from .engine import ReActEngine, create_react_engine
from .agents import (
    LogAnalysisAgent,
    PerformanceDebugAgent,
    SecurityInvestigationAgent,
    AnomalyHuntingAgent,
)

__all__ = [
    # 数据模型
    "Thought",
    "Action",
    "Observation",
    "ReActStep",
    "ReActResult",
    "ReActConfig",
    "Tool",
    "ToolResult",
    "StopReason",
    "ActionType",
    "AgentContext",
    # 工具注册
    "ToolRegistry",
    "tool",
    "get_tool_registry",
    "register_tool",
    # 内置工具
    "SearchLogsTool",
    "FilterRequestsTool",
    "CalculateStatsTool",
    "ExtractPatternsTool",
    "CompareTimePeriodsTool",
    # 引擎
    "ReActEngine",
    "create_react_engine",
    # 预定义Agent
    "LogAnalysisAgent",
    "PerformanceDebugAgent",
    "SecurityInvestigationAgent",
    "AnomalyHuntingAgent",
]
