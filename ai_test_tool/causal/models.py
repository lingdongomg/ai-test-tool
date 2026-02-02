"""
因果分析数据模型

定义因果图的节点、边、链等核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import json


class NodeType(str, Enum):
    """节点类型"""
    EVENT = "event"                 # 事件（如错误发生）
    STATE = "state"                 # 状态（如服务不可用）
    SYMPTOM = "symptom"             # 症状（如响应慢）
    ROOT_CAUSE = "root_cause"       # 根因
    CONDITION = "condition"         # 条件（如高负载）
    ACTION = "action"               # 动作（如重启服务）
    COMPONENT = "component"         # 组件（如数据库）


class EdgeType(str, Enum):
    """边类型"""
    CAUSES = "causes"               # A导致B
    CONTRIBUTES = "contributes"     # A促成B
    CORRELATES = "correlates"       # A与B相关
    PRECEDES = "precedes"           # A先于B发生
    TRIGGERS = "triggers"           # A触发B
    PREVENTS = "prevents"           # A阻止B
    MITIGATES = "mitigates"         # A缓解B


class ImpactLevel(str, Enum):
    """影响级别"""
    CRITICAL = "critical"           # 严重
    HIGH = "high"                   # 高
    MEDIUM = "medium"               # 中
    LOW = "low"                     # 低
    NONE = "none"                   # 无


class ConfidenceLevel(str, Enum):
    """置信度级别"""
    CERTAIN = "certain"             # 确定 (>90%)
    HIGH = "high"                   # 高 (70-90%)
    MEDIUM = "medium"               # 中 (50-70%)
    LOW = "low"                     # 低 (30-50%)
    UNCERTAIN = "uncertain"         # 不确定 (<30%)


@dataclass
class CausalNode:
    """
    因果图节点

    表示因果关系中的一个实体（事件、状态、组件等）
    """
    node_id: str                                # 节点唯一标识
    name: str                                   # 节点名称
    node_type: NodeType = NodeType.EVENT        # 节点类型
    description: str = ""                       # 描述
    timestamp: datetime | None = None           # 发生时间
    duration_ms: float = 0                      # 持续时间

    # 属性
    severity: ImpactLevel = ImpactLevel.MEDIUM  # 严重程度
    frequency: int = 1                          # 发生频率
    component: str = ""                         # 所属组件
    service: str = ""                           # 所属服务

    # 证据
    evidence: list[str] = field(default_factory=list)  # 支持该节点的证据
    source: str = ""                            # 数据来源（log/request/metric）

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_root_cause(self) -> bool:
        """是否为根因节点"""
        return self.node_type == NodeType.ROOT_CAUSE

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity.value,
            "frequency": self.frequency,
            "component": self.component,
            "service": self.service,
            "evidence": self.evidence,
        }


@dataclass
class CausalEdge:
    """
    因果图边

    表示两个节点之间的因果关系
    """
    source: str                                 # 源节点ID
    target: str                                 # 目标节点ID
    edge_type: EdgeType = EdgeType.CAUSES       # 边类型
    weight: float = 1.0                         # 权重（因果强度）
    confidence: float = 0.5                     # 置信度 (0-1)
    delay_ms: float = 0                         # 因果传播延迟

    # 证据
    evidence: list[str] = field(default_factory=list)
    reasoning: str = ""                         # 推理依据

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """获取置信度级别"""
        if self.confidence > 0.9:
            return ConfidenceLevel.CERTAIN
        elif self.confidence > 0.7:
            return ConfidenceLevel.HIGH
        elif self.confidence > 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.confidence > 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "delay_ms": self.delay_ms,
            "reasoning": self.reasoning,
        }


@dataclass
class CausalChain:
    """
    因果链

    从根因到最终影响的完整路径
    """
    chain_id: str                               # 链ID
    nodes: list[str]                            # 节点ID序列
    edges: list[CausalEdge]                     # 边序列
    total_confidence: float = 0.0               # 整体置信度
    total_delay_ms: float = 0.0                 # 总延迟
    description: str = ""                       # 链描述

    @property
    def length(self) -> int:
        """链长度"""
        return len(self.nodes)

    @property
    def root(self) -> str:
        """根节点"""
        return self.nodes[0] if self.nodes else ""

    @property
    def leaf(self) -> str:
        """叶节点"""
        return self.nodes[-1] if self.nodes else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "nodes": self.nodes,
            "length": self.length,
            "total_confidence": self.total_confidence,
            "total_delay_ms": self.total_delay_ms,
            "root": self.root,
            "leaf": self.leaf,
            "description": self.description,
        }


class CausalGraph:
    """
    因果图

    管理节点和边，提供图操作和查询功能
    """

    def __init__(self, graph_id: str = "default"):
        self.graph_id = graph_id
        self._nodes: dict[str, CausalNode] = {}
        self._edges: list[CausalEdge] = []
        self._adjacency: dict[str, list[str]] = {}      # 正向邻接表
        self._reverse_adjacency: dict[str, list[str]] = {}  # 反向邻接表

    def add_node(self, node: CausalNode) -> "CausalGraph":
        """添加节点"""
        self._nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = []
        if node.node_id not in self._reverse_adjacency:
            self._reverse_adjacency[node.node_id] = []
        return self

    def add_edge(self, edge: CausalEdge) -> "CausalGraph":
        """添加边"""
        # 确保节点存在
        if edge.source not in self._nodes:
            self.add_node(CausalNode(node_id=edge.source, name=edge.source))
        if edge.target not in self._nodes:
            self.add_node(CausalNode(node_id=edge.target, name=edge.target))

        self._edges.append(edge)
        self._adjacency[edge.source].append(edge.target)
        self._reverse_adjacency[edge.target].append(edge.source)
        return self

    def get_node(self, node_id: str) -> CausalNode | None:
        """获取节点"""
        return self._nodes.get(node_id)

    def get_edge(self, source: str, target: str) -> CausalEdge | None:
        """获取边"""
        for edge in self._edges:
            if edge.source == source and edge.target == target:
                return edge
        return None

    def get_successors(self, node_id: str) -> list[str]:
        """获取后继节点（被当前节点影响的节点）"""
        return self._adjacency.get(node_id, [])

    def get_predecessors(self, node_id: str) -> list[str]:
        """获取前驱节点（影响当前节点的节点）"""
        return self._reverse_adjacency.get(node_id, [])

    def find_root_causes(self) -> list[CausalNode]:
        """
        找出所有根因节点

        根因节点是没有入边（没有前驱）的节点
        """
        roots = []
        for node_id, node in self._nodes.items():
            if not self._reverse_adjacency.get(node_id):
                roots.append(node)
        return roots

    def find_leaf_nodes(self) -> list[CausalNode]:
        """
        找出所有叶节点

        叶节点是没有出边（没有后继）的节点
        """
        leaves = []
        for node_id, node in self._nodes.items():
            if not self._adjacency.get(node_id):
                leaves.append(node)
        return leaves

    def find_paths(
        self,
        start: str,
        end: str,
        max_depth: int = 10
    ) -> list[list[str]]:
        """
        找出从start到end的所有路径

        使用DFS查找所有路径
        """
        paths: list[list[str]] = []

        def dfs(current: str, target: str, path: list[str], depth: int):
            if depth > max_depth:
                return
            if current == target:
                paths.append(list(path))
                return
            for next_node in self._adjacency.get(current, []):
                if next_node not in path:  # 避免环
                    path.append(next_node)
                    dfs(next_node, target, path, depth + 1)
                    path.pop()

        dfs(start, end, [start], 0)
        return paths

    def find_causal_chains(
        self,
        from_node: str | None = None,
        to_node: str | None = None,
        min_confidence: float = 0.0
    ) -> list[CausalChain]:
        """
        找出因果链

        Args:
            from_node: 起始节点（如果为None，从所有根因开始）
            to_node: 结束节点（如果为None，到所有叶节点）
            min_confidence: 最小置信度阈值
        """
        chains: list[CausalChain] = []

        # 确定起始和结束节点
        start_nodes = [from_node] if from_node else [n.node_id for n in self.find_root_causes()]
        end_nodes = [to_node] if to_node else [n.node_id for n in self.find_leaf_nodes()]

        chain_id = 0
        for start in start_nodes:
            for end in end_nodes:
                if start == end:
                    continue
                paths = self.find_paths(start, end)
                for path in paths:
                    # 收集边并计算置信度
                    edges = []
                    total_confidence = 1.0
                    total_delay = 0.0

                    for i in range(len(path) - 1):
                        edge = self.get_edge(path[i], path[i + 1])
                        if edge:
                            edges.append(edge)
                            total_confidence *= edge.confidence
                            total_delay += edge.delay_ms

                    if total_confidence >= min_confidence:
                        chain_id += 1
                        chain = CausalChain(
                            chain_id=f"chain_{chain_id}",
                            nodes=path,
                            edges=edges,
                            total_confidence=round(total_confidence, 4),
                            total_delay_ms=total_delay
                        )
                        chains.append(chain)

        # 按置信度排序
        chains.sort(key=lambda c: c.total_confidence, reverse=True)
        return chains

    def calculate_node_impact(self, node_id: str) -> dict[str, Any]:
        """
        计算节点的影响力

        通过分析该节点影响的所有下游节点来评估
        """
        affected_nodes: set[str] = set()
        total_severity_score = 0

        def dfs(current: str, depth: int):
            if depth > 20:  # 防止无限递归
                return
            for next_node in self._adjacency.get(current, []):
                if next_node not in affected_nodes:
                    affected_nodes.add(next_node)
                    node = self._nodes.get(next_node)
                    if node:
                        nonlocal total_severity_score
                        severity_map = {
                            ImpactLevel.CRITICAL: 4,
                            ImpactLevel.HIGH: 3,
                            ImpactLevel.MEDIUM: 2,
                            ImpactLevel.LOW: 1,
                            ImpactLevel.NONE: 0
                        }
                        total_severity_score += severity_map.get(node.severity, 0)
                    dfs(next_node, depth + 1)

        dfs(node_id, 0)

        return {
            "node_id": node_id,
            "affected_nodes_count": len(affected_nodes),
            "affected_nodes": list(affected_nodes),
            "total_severity_score": total_severity_score,
            "impact_level": self._calculate_impact_level(len(affected_nodes), total_severity_score)
        }

    def _calculate_impact_level(self, affected_count: int, severity_score: int) -> ImpactLevel:
        """计算影响级别"""
        combined_score = affected_count * 2 + severity_score
        if combined_score >= 20:
            return ImpactLevel.CRITICAL
        elif combined_score >= 10:
            return ImpactLevel.HIGH
        elif combined_score >= 5:
            return ImpactLevel.MEDIUM
        elif combined_score >= 1:
            return ImpactLevel.LOW
        else:
            return ImpactLevel.NONE

    def topological_sort(self) -> list[str]:
        """
        拓扑排序

        返回按因果顺序排列的节点ID列表
        """
        in_degree: dict[str, int] = {node_id: 0 for node_id in self._nodes}

        for edge in self._edges:
            in_degree[edge.target] += 1

        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            for next_node in self._adjacency.get(node_id, []):
                in_degree[next_node] -= 1
                if in_degree[next_node] == 0:
                    queue.append(next_node)

        return result

    def detect_cycles(self) -> list[list[str]]:
        """检测环"""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # 发现环
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    @property
    def node_count(self) -> int:
        """节点数量"""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """边数量"""
        return len(self._edges)

    @property
    def nodes(self) -> list[CausalNode]:
        """所有节点"""
        return list(self._nodes.values())

    @property
    def edges(self) -> list[CausalEdge]:
        """所有边"""
        return list(self._edges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
            "root_causes": [n.node_id for n in self.find_root_causes()],
            "leaf_nodes": [n.node_id for n in self.find_leaf_nodes()],
        }

    def to_mermaid(self) -> str:
        """导出为Mermaid图格式"""
        lines = ["graph TD"]
        for node in self._nodes.values():
            shape = "([" if node.is_root_cause else "(("
            end_shape = "])" if node.is_root_cause else "))"
            lines.append(f"    {node.node_id}{shape}{node.name}{end_shape}")

        for edge in self._edges:
            arrow = "-->" if edge.edge_type == EdgeType.CAUSES else "-.->"
            label = f"|{edge.edge_type.value}|" if edge.edge_type != EdgeType.CAUSES else ""
            lines.append(f"    {edge.source} {arrow}{label} {edge.target}")

        return "\n".join(lines)


@dataclass
class CausalConfig:
    """因果分析配置"""
    # 图构建
    min_correlation: float = 0.3                # 最小相关性阈值
    time_window_ms: int = 5000                  # 时间窗口（判断时序关系）
    max_nodes: int = 100                        # 最大节点数

    # 分析
    min_confidence: float = 0.3                 # 最小置信度
    max_chain_length: int = 10                  # 最大因果链长度
    enable_llm_reasoning: bool = True           # 启用LLM推理

    # 输出
    top_k_root_causes: int = 5                  # 返回top k个根因
    top_k_chains: int = 10                      # 返回top k条因果链

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_correlation": self.min_correlation,
            "time_window_ms": self.time_window_ms,
            "max_nodes": self.max_nodes,
            "min_confidence": self.min_confidence,
            "max_chain_length": self.max_chain_length,
        }


@dataclass
class CausalAnalysisResult:
    """
    因果分析结果
    """
    # 因果图
    graph: CausalGraph | None = None

    # 根因分析
    root_causes: list[dict[str, Any]] = field(default_factory=list)
    primary_root_cause: dict[str, Any] | None = None

    # 因果链
    causal_chains: list[CausalChain] = field(default_factory=list)
    critical_path: CausalChain | None = None

    # 影响分析
    impact_assessment: dict[str, Any] = field(default_factory=dict)
    affected_components: list[str] = field(default_factory=list)

    # 统计
    total_events: int = 0
    analysis_time_ms: float = 0

    # 置信度
    overall_confidence: float = 0.0
    reasoning: str = ""

    # 建议
    recommendations: list[str] = field(default_factory=list)

    @property
    def has_root_cause(self) -> bool:
        """是否找到根因"""
        return len(self.root_causes) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_root_cause": self.has_root_cause,
            "root_causes": self.root_causes,
            "primary_root_cause": self.primary_root_cause,
            "causal_chains": [c.to_dict() for c in self.causal_chains],
            "critical_path": self.critical_path.to_dict() if self.critical_path else None,
            "impact_assessment": self.impact_assessment,
            "affected_components": self.affected_components,
            "total_events": self.total_events,
            "analysis_time_ms": self.analysis_time_ms,
            "overall_confidence": self.overall_confidence,
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
            "graph_summary": {
                "node_count": self.graph.node_count if self.graph else 0,
                "edge_count": self.graph.edge_count if self.graph else 0,
            }
        }
