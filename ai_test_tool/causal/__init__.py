"""
因果分析模块

基于因果图进行根因定位、影响分析和传播追踪

核心概念：
- CausalNode（因果节点）: 代表一个事件或状态
- CausalEdge（因果边）: 代表因果关系
- CausalGraph（因果图）: 节点和边组成的有向图
- 传播分析: 追踪故障如何在系统中传播
- 根因定位: 找出问题的根本原因
- 影响评估: 评估故障的影响范围

使用示例：

1. 使用CausalAnalyzer进行分析：
```python
from ai_test_tool.causal import CausalAnalyzer

analyzer = CausalAnalyzer()
result = analyzer.analyze(
    log_content="...",
    requests=[...],
    focus="找出导致超时的根本原因"
)
print(result.root_causes)
print(result.causal_chains)
print(result.impact_assessment)
```

2. 手动构建因果图：
```python
from ai_test_tool.causal import CausalGraph, CausalNode, CausalEdge

graph = CausalGraph()
graph.add_node(CausalNode(node_id="db_slow", name="数据库慢查询"))
graph.add_node(CausalNode(node_id="api_timeout", name="API超时"))
graph.add_edge(CausalEdge(source="db_slow", target="api_timeout"))

# 分析根因
root_causes = graph.find_root_causes()
```

3. 使用GraphBuilder自动构建：
```python
from ai_test_tool.causal import CausalGraphBuilder

builder = CausalGraphBuilder()
graph = builder.build_from_events(events)
```
"""

from .models import (
    CausalNode,
    CausalEdge,
    CausalGraph,
    CausalChain,
    CausalAnalysisResult,
    CausalConfig,
    NodeType,
    EdgeType,
    ImpactLevel,
    ConfidenceLevel,
)
from .builder import CausalGraphBuilder
from .engine import CausalEngine
from .analyzers import (
    CausalAnalyzer,
    RootCauseAnalyzer,
    ImpactAnalyzer,
    PropagationAnalyzer,
)

__all__ = [
    # 数据模型
    "CausalNode",
    "CausalEdge",
    "CausalGraph",
    "CausalChain",
    "CausalAnalysisResult",
    "CausalConfig",
    "NodeType",
    "EdgeType",
    "ImpactLevel",
    "ConfidenceLevel",
    # 构建器
    "CausalGraphBuilder",
    # 引擎
    "CausalEngine",
    # 分析器
    "CausalAnalyzer",
    "RootCauseAnalyzer",
    "ImpactAnalyzer",
    "PropagationAnalyzer",
]
