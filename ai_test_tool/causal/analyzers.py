"""
预定义因果分析器

提供针对特定场景的因果分析器模板
"""

from typing import Any

from .models import (
    CausalGraph,
    CausalAnalysisResult,
    CausalConfig,
    CausalNode,
    CausalEdge,
    NodeType,
    EdgeType,
    ImpactLevel,
)
from .builder import CausalGraphBuilder
from .engine import CausalEngine
from ..llm.provider import LLMProvider


class CausalAnalyzer:
    """
    通用因果分析器

    提供完整的因果分析流程
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        config: CausalConfig | None = None
    ):
        """
        初始化分析器

        Args:
            llm_provider: LLM提供者
            config: 配置
        """
        self.config = config or CausalConfig()
        self.engine = CausalEngine(
            llm_provider=llm_provider,
            config=self.config
        )

    def analyze(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        focus: str = ""
    ) -> CausalAnalysisResult:
        """
        执行因果分析

        Args:
            log_content: 日志内容
            requests: 请求数据
            focus: 分析焦点

        Returns:
            分析结果
        """
        return self.engine.analyze(
            log_content=log_content,
            requests=requests,
            focus=focus
        )


class RootCauseAnalyzer:
    """
    根因分析器

    专注于找出问题的根本原因
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        config: CausalConfig | None = None
    ):
        self.config = config or CausalConfig(
            enable_llm_reasoning=True,
            top_k_root_causes=5
        )
        self.engine = CausalEngine(
            llm_provider=llm_provider,
            config=self.config
        )

    def find_root_causes(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        symptoms: list[str] | None = None
    ) -> dict[str, Any]:
        """
        查找根因

        Args:
            log_content: 日志内容
            requests: 请求数据
            symptoms: 已知症状列表

        Returns:
            根因分析结果
        """
        # 构建分析目标
        focus = "找出导致以下症状的根本原因"
        if symptoms:
            focus += f": {', '.join(symptoms)}"

        result = self.engine.analyze(
            log_content=log_content,
            requests=requests,
            focus=focus
        )

        return {
            "primary_root_cause": result.primary_root_cause,
            "all_root_causes": result.root_causes,
            "confidence": result.overall_confidence,
            "reasoning": result.reasoning,
            "recommendations": result.recommendations,
            "causal_chains": [c.to_dict() for c in result.causal_chains[:5]],
        }


class ImpactAnalyzer:
    """
    影响分析器

    专注于评估问题的影响范围
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        config: CausalConfig | None = None
    ):
        self.config = config or CausalConfig(
            enable_llm_reasoning=True
        )
        self.engine = CausalEngine(
            llm_provider=llm_provider,
            config=self.config
        )
        self.builder = CausalGraphBuilder(config=self.config)

    def assess_impact(
        self,
        root_cause: str,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        评估影响

        Args:
            root_cause: 已知根因
            log_content: 日志内容
            requests: 请求数据

        Returns:
            影响评估结果
        """
        # 构建因果图
        graph = self.builder.build(
            log_content=log_content,
            requests=requests
        )

        # 确保根因节点存在
        if not graph.get_node(root_cause):
            graph.add_node(CausalNode(
                node_id=root_cause,
                name=root_cause,
                node_type=NodeType.ROOT_CAUSE,
                severity=ImpactLevel.HIGH
            ))

        # 计算影响
        impact = graph.calculate_node_impact(root_cause)

        # 找出所有受影响的因果链
        chains = graph.find_causal_chains(from_node=root_cause)

        # 收集受影响的组件
        affected_components: set[str] = set()
        affected_nodes: list[dict] = []

        for node_id in impact.get("affected_nodes", []):
            node = graph.get_node(node_id)
            if node:
                affected_nodes.append({
                    "id": node.node_id,
                    "name": node.name,
                    "severity": node.severity.value,
                    "component": node.component
                })
                if node.component:
                    affected_components.add(node.component)

        return {
            "root_cause": root_cause,
            "impact_level": impact.get("impact_level", ImpactLevel.MEDIUM).value,
            "affected_nodes_count": len(affected_nodes),
            "affected_nodes": affected_nodes[:20],
            "affected_components": list(affected_components),
            "propagation_chains": [c.to_dict() for c in chains[:5]],
            "severity_score": impact.get("total_severity_score", 0),
            "graph_summary": {
                "total_nodes": graph.node_count,
                "total_edges": graph.edge_count
            }
        }

    def predict_impact(
        self,
        potential_issue: str,
        component: str = "",
        severity: str = "medium"
    ) -> dict[str, Any]:
        """
        预测潜在问题的影响

        Args:
            potential_issue: 潜在问题描述
            component: 问题组件
            severity: 严重程度

        Returns:
            影响预测
        """
        # 基于预定义的依赖关系预测影响
        component_deps = {
            "database": {
                "downstream": ["api", "auth", "cache"],
                "typical_impact": "数据库问题通常导致API响应变慢或失败"
            },
            "cache": {
                "downstream": ["api"],
                "typical_impact": "缓存问题导致请求直接打到数据库，可能引发雪崩"
            },
            "auth": {
                "downstream": ["api", "gateway"],
                "typical_impact": "认证服务问题导致用户无法访问"
            },
            "gateway": {
                "downstream": [],
                "typical_impact": "网关问题导致所有入口流量受影响"
            },
            "api": {
                "downstream": [],
                "typical_impact": "API问题直接影响用户功能"
            }
        }

        severity_map = {
            "critical": ImpactLevel.CRITICAL,
            "high": ImpactLevel.HIGH,
            "medium": ImpactLevel.MEDIUM,
            "low": ImpactLevel.LOW
        }

        impact_level = severity_map.get(severity, ImpactLevel.MEDIUM)
        affected = []
        typical_impact = "未知影响"

        if component in component_deps:
            dep_info = component_deps[component]
            affected = dep_info["downstream"]
            typical_impact = dep_info["typical_impact"]

        return {
            "potential_issue": potential_issue,
            "component": component,
            "severity": severity,
            "predicted_impact_level": impact_level.value,
            "potentially_affected_components": affected,
            "typical_impact": typical_impact,
            "mitigation_suggestions": self._get_mitigation_suggestions(component, severity)
        }

    def _get_mitigation_suggestions(self, component: str, severity: str) -> list[str]:
        """获取缓解建议"""
        suggestions = []

        if severity in ("critical", "high"):
            suggestions.append("立即启动应急响应流程")
            suggestions.append("考虑启用降级方案")

        if component == "database":
            suggestions.extend([
                "检查数据库连接池状态",
                "准备只读副本切换方案",
                "考虑启用缓存降级"
            ])
        elif component == "cache":
            suggestions.extend([
                "检查缓存服务健康状态",
                "准备直连数据库的降级方案",
                "监控数据库压力"
            ])
        elif component == "auth":
            suggestions.extend([
                "检查token服务状态",
                "准备临时访问方案",
                "通知相关用户"
            ])

        return suggestions


class PropagationAnalyzer:
    """
    传播分析器

    分析故障如何在系统中传播
    """

    def __init__(
        self,
        config: CausalConfig | None = None
    ):
        self.config = config or CausalConfig()
        self.builder = CausalGraphBuilder(config=self.config)

    def trace_propagation(
        self,
        start_event: str,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        追踪故障传播

        Args:
            start_event: 起始事件
            log_content: 日志内容
            requests: 请求数据

        Returns:
            传播追踪结果
        """
        # 构建因果图
        graph = self.builder.build(
            log_content=log_content,
            requests=requests
        )

        # 找到起始节点
        start_node = None
        for node in graph.nodes:
            if start_event.lower() in node.node_id.lower() or start_event.lower() in node.name.lower():
                start_node = node
                break

        if not start_node:
            return {
                "error": f"未找到匹配的起始事件: {start_event}",
                "available_events": [n.name for n in graph.nodes[:20]]
            }

        # 找出所有传播路径
        chains = graph.find_causal_chains(from_node=start_node.node_id)

        # 构建传播时间线
        timeline = self._build_propagation_timeline(graph, chains)

        # 计算传播速度和范围
        propagation_stats = self._calculate_propagation_stats(graph, start_node.node_id)

        return {
            "start_event": {
                "id": start_node.node_id,
                "name": start_node.name,
                "timestamp": start_node.timestamp.isoformat() if start_node.timestamp else None
            },
            "propagation_paths": [c.to_dict() for c in chains[:10]],
            "timeline": timeline,
            "stats": propagation_stats,
            "mermaid_diagram": graph.to_mermaid()
        }

    def _build_propagation_timeline(
        self,
        graph: CausalGraph,
        chains: list
    ) -> list[dict[str, Any]]:
        """构建传播时间线"""
        timeline_events: dict[str, dict] = {}

        for chain in chains:
            cumulative_delay = 0
            for i, node_id in enumerate(chain.nodes):
                node = graph.get_node(node_id)
                if node:
                    if node_id not in timeline_events:
                        timeline_events[node_id] = {
                            "node_id": node_id,
                            "name": node.name,
                            "order": i,
                            "cumulative_delay_ms": cumulative_delay,
                            "severity": node.severity.value
                        }

                if i < len(chain.edges):
                    cumulative_delay += chain.edges[i].delay_ms

        # 按顺序排序
        timeline = sorted(timeline_events.values(), key=lambda x: x["order"])
        return timeline

    def _calculate_propagation_stats(
        self,
        graph: CausalGraph,
        start_node: str
    ) -> dict[str, Any]:
        """计算传播统计"""
        impact = graph.calculate_node_impact(start_node)

        # 计算平均传播深度
        chains = graph.find_causal_chains(from_node=start_node)
        avg_depth = sum(c.length for c in chains) / len(chains) if chains else 0

        # 计算总传播延迟
        total_delay = sum(c.total_delay_ms for c in chains)
        avg_delay = total_delay / len(chains) if chains else 0

        return {
            "total_affected_nodes": impact.get("affected_nodes_count", 0),
            "propagation_paths_count": len(chains),
            "average_path_length": round(avg_depth, 2),
            "average_propagation_delay_ms": round(avg_delay, 2),
            "max_path_length": max((c.length for c in chains), default=0),
            "impact_level": impact.get("impact_level", ImpactLevel.MEDIUM).value
        }

    def find_critical_paths(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        找出关键传播路径

        关键路径是置信度高且影响范围大的路径

        Args:
            log_content: 日志内容
            requests: 请求数据

        Returns:
            关键路径列表
        """
        graph = self.builder.build(
            log_content=log_content,
            requests=requests
        )

        all_chains = graph.find_causal_chains()

        # 为每条链计算重要性分数
        scored_chains = []
        for chain in all_chains:
            # 重要性 = 置信度 * 长度权重 * 严重性权重
            length_weight = min(chain.length / 3, 2.0)  # 中等长度的链更重要

            severity_score = 0
            for node_id in chain.nodes:
                node = graph.get_node(node_id)
                if node:
                    severity_map = {
                        ImpactLevel.CRITICAL: 4,
                        ImpactLevel.HIGH: 3,
                        ImpactLevel.MEDIUM: 2,
                        ImpactLevel.LOW: 1
                    }
                    severity_score += severity_map.get(node.severity, 0)

            importance = chain.total_confidence * length_weight * (1 + severity_score / 10)

            scored_chains.append({
                "chain": chain.to_dict(),
                "importance_score": round(importance, 3),
                "severity_score": severity_score,
                "nodes_detail": [
                    {
                        "id": n,
                        "name": graph.get_node(n).name if graph.get_node(n) else n,
                        "severity": graph.get_node(n).severity.value if graph.get_node(n) else "unknown"
                    }
                    for n in chain.nodes
                ]
            })

        # 按重要性排序
        scored_chains.sort(key=lambda x: x["importance_score"], reverse=True)

        return scored_chains[:10]
