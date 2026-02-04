"""
因果推理引擎

执行因果分析、根因定位、影响评估
"""

import json
import logging
import time
from typing import Any

from .models import (
    CausalGraph,
    CausalChain,
    CausalAnalysisResult,
    CausalConfig,
    CausalNode,
    ImpactLevel,
    NodeType,
)
from .builder import CausalGraphBuilder
from ..llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


# LLM推理Prompt
CAUSAL_REASONING_PROMPT = """你是一个因果分析专家。请分析以下因果图，找出根本原因并评估影响。

## 因果图信息

节点列表：
{nodes}

边列表（因果关系）：
{edges}

当前识别的根因候选：
{root_candidates}

## 分析目标
{analysis_goal}

## 任务
1. 分析因果链，确定最可能的根本原因
2. 评估每个根因的置信度
3. 描述故障传播路径
4. 评估影响范围
5. 给出修复建议

## 输出格式（JSON）
```json
{{
  "primary_root_cause": {{
    "node_id": "根因节点ID",
    "name": "根因名称",
    "confidence": 0.0-1.0,
    "reasoning": "判断依据"
  }},
  "secondary_root_causes": [
    {{
      "node_id": "节点ID",
      "name": "名称",
      "confidence": 置信度,
      "reasoning": "依据"
    }}
  ],
  "propagation_path": "故障传播路径描述",
  "impact_assessment": {{
    "scope": "single_service/multiple_services/system_wide",
    "severity": "critical/high/medium/low",
    "affected_components": ["受影响的组件"],
    "business_impact": "业务影响描述"
  }},
  "recommendations": [
    "修复建议1",
    "修复建议2"
  ],
  "overall_confidence": 0.0-1.0
}}
```

请直接输出JSON："""


class CausalEngine:
    """
    因果推理引擎

    功能：
    1. 协调因果图构建
    2. 执行根因分析
    3. 评估影响范围
    4. 生成分析报告
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        config: CausalConfig | None = None
    ):
        """
        初始化引擎

        Args:
            llm_provider: LLM提供者
            config: 配置
        """
        self._llm_provider = llm_provider
        self.config = config or CausalConfig()
        self.builder = CausalGraphBuilder(config=self.config)

    @property
    def llm_provider(self) -> LLMProvider:
        """懒加载LLM提供者"""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    def analyze(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
        focus: str = "",
        graph: CausalGraph | None = None
    ) -> CausalAnalysisResult:
        """
        执行因果分析

        Args:
            log_content: 日志内容
            requests: 请求数据
            events: 事件列表
            focus: 分析焦点/目标
            graph: 预构建的因果图（可选）

        Returns:
            因果分析结果
        """
        start_time = time.time()

        result = CausalAnalysisResult()

        try:
            # 1. 构建因果图
            if graph is None:
                graph = self.builder.build(
                    log_content=log_content,
                    requests=requests,
                    events=events
                )
            result.graph = graph
            result.total_events = graph.node_count

            if graph.node_count == 0:
                result.reasoning = "未检测到任何事件，无法进行因果分析"
                return result

            # 2. 基础图分析
            root_causes = self._analyze_root_causes(graph)
            result.root_causes = root_causes

            # 3. 提取因果链
            causal_chains = graph.find_causal_chains(
                min_confidence=self.config.min_confidence
            )
            result.causal_chains = causal_chains[:self.config.top_k_chains]

            # 4. 找出关键路径
            if causal_chains:
                result.critical_path = causal_chains[0]

            # 5. 评估影响
            impact = self._assess_impact(graph, root_causes)
            result.impact_assessment = impact
            result.affected_components = impact.get("affected_components", [])

            # 6. LLM增强推理（如果启用）
            if self.config.enable_llm_reasoning and graph.node_count > 0:
                llm_result = self._llm_reasoning(graph, root_causes, focus)
                if llm_result:
                    # 合并LLM结果
                    if llm_result.get("primary_root_cause"):
                        result.primary_root_cause = llm_result["primary_root_cause"]
                    result.recommendations = llm_result.get("recommendations", [])
                    result.reasoning = llm_result.get("propagation_path", "")
                    result.overall_confidence = llm_result.get("overall_confidence", 0.5)

                    # 更新影响评估
                    if llm_result.get("impact_assessment"):
                        result.impact_assessment.update(llm_result["impact_assessment"])
            else:
                # 不使用LLM时，基于规则生成
                if root_causes:
                    result.primary_root_cause = root_causes[0]
                    result.overall_confidence = root_causes[0].get("confidence", 0.5)
                result.recommendations = self._generate_recommendations(graph, root_causes)
                result.reasoning = self._generate_reasoning(graph, causal_chains)

        except Exception as e:
            logger.error(f"因果分析失败: {e}")
            result.reasoning = f"分析过程出错: {str(e)}"

        result.analysis_time_ms = (time.time() - start_time) * 1000
        return result

    def _analyze_root_causes(self, graph: CausalGraph) -> list[dict[str, Any]]:
        """分析根因"""
        root_causes: list[dict[str, Any]] = []

        # 找出图中的根节点（无入边）
        root_nodes = graph.find_root_causes()

        for node in root_nodes:
            # 计算影响力
            impact = graph.calculate_node_impact(node.node_id)

            # 计算置信度
            confidence = self._calculate_root_cause_confidence(node, impact)

            root_causes.append({
                "node_id": node.node_id,
                "name": node.name,
                "type": node.node_type.value,
                "severity": node.severity.value,
                "frequency": node.frequency,
                "confidence": confidence,
                "impact_score": impact.get("total_severity_score", 0),
                "affected_count": impact.get("affected_nodes_count", 0),
                "evidence": node.evidence[:3],
                "component": node.component,
            })

        # 按置信度和影响力排序
        root_causes.sort(
            key=lambda x: (x["confidence"], x["impact_score"]),
            reverse=True
        )

        return root_causes[:self.config.top_k_root_causes]

    def _calculate_root_cause_confidence(
        self,
        node: CausalNode,
        impact: dict[str, Any]
    ) -> float:
        """计算根因置信度"""
        confidence = 0.5

        # 1. 节点类型加成
        if node.node_type == NodeType.ROOT_CAUSE:
            confidence += 0.2
        elif node.node_type == NodeType.EVENT:
            confidence += 0.1

        # 2. 严重程度加成
        severity_bonus = {
            ImpactLevel.CRITICAL: 0.15,
            ImpactLevel.HIGH: 0.1,
            ImpactLevel.MEDIUM: 0.05,
        }
        confidence += severity_bonus.get(node.severity, 0)

        # 3. 频率加成
        if node.frequency > 10:
            confidence += 0.1
        elif node.frequency > 5:
            confidence += 0.05

        # 4. 影响范围加成
        affected = impact.get("affected_nodes_count", 0)
        if affected > 5:
            confidence += 0.1
        elif affected > 2:
            confidence += 0.05

        # 5. 证据加成
        if len(node.evidence) > 2:
            confidence += 0.05

        return min(confidence, 1.0)

    def _assess_impact(
        self,
        graph: CausalGraph,
        root_causes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """评估影响"""
        # 收集所有受影响的节点和组件
        all_affected: set[str] = set()
        affected_components: set[str] = set()

        for rc in root_causes:
            node_id = rc["node_id"]
            impact = graph.calculate_node_impact(node_id)
            all_affected.update(impact.get("affected_nodes", []))

            # 收集组件
            for affected_id in impact.get("affected_nodes", []):
                node = graph.get_node(affected_id)
                if node and node.component:
                    affected_components.add(node.component)

        # 计算整体严重程度
        total_severity = sum(rc.get("impact_score", 0) for rc in root_causes)

        if total_severity >= 15 or len(affected_components) >= 3:
            scope = "system_wide"
            severity = "critical"
        elif total_severity >= 8 or len(affected_components) >= 2:
            scope = "multiple_services"
            severity = "high"
        elif total_severity >= 4:
            scope = "single_service"
            severity = "medium"
        else:
            scope = "single_service"
            severity = "low"

        return {
            "scope": scope,
            "severity": severity,
            "affected_nodes_count": len(all_affected),
            "affected_components": list(affected_components),
            "total_severity_score": total_severity,
        }

    def _llm_reasoning(
        self,
        graph: CausalGraph,
        root_causes: list[dict[str, Any]],
        focus: str
    ) -> dict[str, Any] | None:
        """使用LLM进行深度推理"""
        try:
            # 准备节点信息
            nodes_info = []
            for node in graph.nodes[:30]:  # 限制数量
                nodes_info.append({
                    "id": node.node_id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "severity": node.severity.value,
                    "frequency": node.frequency,
                    "component": node.component,
                })

            # 准备边信息
            edges_info = []
            for edge in graph.edges[:50]:
                edges_info.append({
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.edge_type.value,
                    "confidence": edge.confidence,
                })

            # 构建prompt
            prompt = CAUSAL_REASONING_PROMPT.format(
                nodes=json.dumps(nodes_info, ensure_ascii=False, indent=2),
                edges=json.dumps(edges_info, ensure_ascii=False, indent=2),
                root_candidates=json.dumps(root_causes[:5], ensure_ascii=False, indent=2),
                analysis_goal=focus or "找出系统问题的根本原因并评估影响"
            )

            # 调用LLM
            response = self.llm_provider.generate(prompt)

            # 解析响应
            return self._parse_llm_response(response)

        except Exception as e:
            logger.warning(f"LLM推理失败: {e}")
            return None

    def _parse_llm_response(self, response: str) -> dict[str, Any] | None:
        """解析LLM响应"""
        import re

        # 尝试提取JSON
        # 1. 从代码块提取
        code_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 2. 直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 3. 从花括号提取
        brace_start = response.find("{")
        brace_end = response.rfind("}") + 1
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(response[brace_start:brace_end])
            except json.JSONDecodeError:
                pass

        return None

    def _generate_recommendations(
        self,
        graph: CausalGraph,
        root_causes: list[dict[str, Any]]
    ) -> list[str]:
        """生成修复建议"""
        recommendations: list[str] = []

        for rc in root_causes[:3]:
            node_id = rc["node_id"]
            name = rc["name"]
            component = rc.get("component", "")

            # 基于错误类型生成建议
            if "timeout" in node_id.lower():
                recommendations.append(f"排查 {name}: 检查超时配置和下游服务响应时间")
            elif "memory" in node_id.lower() or "oom" in node_id.lower():
                recommendations.append(f"排查 {name}: 检查内存使用情况，排查内存泄漏")
            elif "connection" in node_id.lower():
                recommendations.append(f"排查 {name}: 检查网络连接和服务可用性")
            elif "database" in node_id.lower() or component == "database":
                recommendations.append(f"排查 {name}: 检查数据库性能和连接池状态")
            elif "auth" in node_id.lower() or component == "auth":
                recommendations.append(f"排查 {name}: 检查认证服务和token有效性")
            else:
                recommendations.append(f"排查 {name}: 检查相关服务日志和监控指标")

        # 通用建议
        if graph.node_count > 5:
            recommendations.append("建议查看完整的因果链，理解故障传播路径")

        cycles = graph.detect_cycles()
        if cycles:
            recommendations.append("警告: 检测到循环依赖，可能存在级联故障风险")

        return recommendations

    def _generate_reasoning(
        self,
        graph: CausalGraph,
        chains: list[CausalChain]
    ) -> str:
        """生成推理描述"""
        if not chains:
            return "未发现明确的因果链"

        # 描述主要因果链
        main_chain = chains[0]
        nodes_desc = []
        for node_id in main_chain.nodes:
            node = graph.get_node(node_id)
            if node:
                nodes_desc.append(node.name)

        path_desc = " -> ".join(nodes_desc)
        return f"主要故障传播路径: {path_desc} (置信度: {main_chain.total_confidence:.0%})"


def create_causal_engine(
    config: CausalConfig | None = None,
    llm_provider: LLMProvider | None = None,
    **config_kwargs: Any
) -> CausalEngine:
    """
    创建因果引擎的便捷函数

    Args:
        config: 配置对象
        llm_provider: LLM提供者
        **config_kwargs: 配置参数

    Returns:
        CausalEngine实例
    """
    if config is None:
        config = CausalConfig(**config_kwargs)

    return CausalEngine(
        llm_provider=llm_provider,
        config=config
    )
