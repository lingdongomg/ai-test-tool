"""
因果图构建器

从日志、请求等原始数据自动构建因果图
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from .models import (
    CausalNode,
    CausalEdge,
    CausalGraph,
    CausalConfig,
    NodeType,
    EdgeType,
    ImpactLevel,
)

logger = logging.getLogger(__name__)


class CausalGraphBuilder:
    """
    因果图构建器

    功能：
    1. 从日志中提取事件节点
    2. 从请求数据中提取事件节点
    3. 基于时序关系推断因果边
    4. 基于模式匹配推断因果边
    """

    # 预定义的错误模式和因果关系
    ERROR_PATTERNS = {
        "timeout": {
            "patterns": [r"(?i)timeout", r"(?i)timed?\s*out", r"(?i)deadline\s*exceeded"],
            "node_type": NodeType.SYMPTOM,
            "severity": ImpactLevel.HIGH,
            "possible_causes": ["high_latency", "resource_exhaustion", "network_issue"]
        },
        "connection_error": {
            "patterns": [r"(?i)connection\s*(refused|reset|failed)", r"(?i)ECONNREFUSED"],
            "node_type": NodeType.EVENT,
            "severity": ImpactLevel.HIGH,
            "possible_causes": ["service_down", "network_issue", "port_blocked"]
        },
        "out_of_memory": {
            "patterns": [r"(?i)out\s*of\s*memory", r"(?i)OOM", r"(?i)heap\s*space"],
            "node_type": NodeType.ROOT_CAUSE,
            "severity": ImpactLevel.CRITICAL,
            "possible_causes": ["memory_leak", "high_load"]
        },
        "database_error": {
            "patterns": [r"(?i)database\s*error", r"(?i)sql\s*exception", r"(?i)deadlock"],
            "node_type": NodeType.EVENT,
            "severity": ImpactLevel.HIGH,
            "possible_causes": ["db_overload", "lock_contention", "connection_pool_exhausted"]
        },
        "auth_failure": {
            "patterns": [r"(?i)authentication\s*fail", r"(?i)unauthorized", r"(?i)403\s*forbidden"],
            "node_type": NodeType.EVENT,
            "severity": ImpactLevel.MEDIUM,
            "possible_causes": ["token_expired", "permission_denied", "invalid_credentials"]
        },
        "high_latency": {
            "patterns": [r"(?i)slow\s*query", r"(?i)high\s*latency", r"(?i)response\s*time.*>\s*\d{4}"],
            "node_type": NodeType.SYMPTOM,
            "severity": ImpactLevel.MEDIUM,
            "possible_causes": ["db_slow", "cpu_high", "network_congestion"]
        },
        "service_unavailable": {
            "patterns": [r"(?i)service\s*unavailable", r"(?i)503", r"(?i)circuit\s*breaker\s*open"],
            "node_type": NodeType.EVENT,
            "severity": ImpactLevel.CRITICAL,
            "possible_causes": ["downstream_failure", "overload", "deployment_issue"]
        },
        "null_pointer": {
            "patterns": [r"(?i)null\s*pointer", r"(?i)NullPointerException", r"(?i)TypeError.*None"],
            "node_type": NodeType.ROOT_CAUSE,
            "severity": ImpactLevel.HIGH,
            "possible_causes": ["code_bug", "missing_data"]
        },
    }

    # 组件识别模式
    COMPONENT_PATTERNS = {
        "database": [r"(?i)(mysql|postgres|mongodb|redis|db|database)", r"(?i)sql"],
        "cache": [r"(?i)(redis|memcache|cache)"],
        "queue": [r"(?i)(kafka|rabbitmq|mq|queue|pulsar)"],
        "api": [r"(?i)(api|rest|http|endpoint)"],
        "auth": [r"(?i)(auth|login|token|oauth)"],
        "gateway": [r"(?i)(gateway|nginx|proxy|loadbalancer)"],
    }

    def __init__(self, config: CausalConfig | None = None):
        """
        初始化构建器

        Args:
            config: 构建配置
        """
        self.config = config or CausalConfig()

    def build(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None
    ) -> CausalGraph:
        """
        构建因果图

        Args:
            log_content: 日志内容
            requests: 请求数据
            events: 预定义事件列表

        Returns:
            构建的因果图
        """
        graph = CausalGraph()

        # 1. 从日志提取事件
        if log_content:
            log_nodes = self._extract_nodes_from_log(log_content)
            for node in log_nodes[:self.config.max_nodes // 2]:
                graph.add_node(node)

        # 2. 从请求数据提取事件
        if requests:
            request_nodes = self._extract_nodes_from_requests(requests)
            for node in request_nodes[:self.config.max_nodes // 2]:
                graph.add_node(node)

        # 3. 添加预定义事件
        if events:
            for event in events[:self.config.max_nodes // 4]:
                node = self._event_to_node(event)
                if node:
                    graph.add_node(node)

        # 4. 推断因果边
        edges = self._infer_edges(graph)
        for edge in edges:
            graph.add_edge(edge)

        logger.info(f"构建因果图完成: {graph.node_count} 节点, {graph.edge_count} 边")
        return graph

    def _extract_nodes_from_log(self, log_content: str) -> list[CausalNode]:
        """从日志内容提取事件节点"""
        nodes: list[CausalNode] = []
        lines = log_content.split("\n")

        # 按错误模式匹配
        node_counter: dict[str, int] = defaultdict(int)

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            for error_type, info in self.ERROR_PATTERNS.items():
                for pattern in info["patterns"]:
                    if re.search(pattern, line):
                        node_counter[error_type] += 1

                        # 每种类型只创建一个节点（聚合）
                        if node_counter[error_type] == 1:
                            # 提取时间戳
                            timestamp = self._extract_timestamp(line)
                            # 识别组件
                            component = self._identify_component(line)

                            node = CausalNode(
                                node_id=f"log_{error_type}",
                                name=error_type.replace("_", " ").title(),
                                node_type=info["node_type"],
                                description=line[:200],
                                timestamp=timestamp,
                                severity=info["severity"],
                                frequency=1,
                                component=component,
                                evidence=[line[:500]],
                                source="log",
                                metadata={"line_number": i + 1}
                            )
                            nodes.append(node)
                        else:
                            # 更新频率
                            for node in nodes:
                                if node.node_id == f"log_{error_type}":
                                    node.frequency = node_counter[error_type]
                                    if len(node.evidence) < 5:
                                        node.evidence.append(line[:200])
                        break

        return nodes

    def _extract_nodes_from_requests(
        self,
        requests: list[dict[str, Any]]
    ) -> list[CausalNode]:
        """从请求数据提取事件节点"""
        nodes: list[CausalNode] = []

        # 按端点和状态聚合
        endpoint_errors: dict[str, dict] = defaultdict(lambda: {
            "count": 0,
            "statuses": [],
            "response_times": [],
            "errors": []
        })

        for req in requests:
            url = req.get("url", "").split("?")[0]
            status = req.get("http_status", 0)
            has_error = req.get("has_error", False) or status >= 400
            rt = req.get("response_time_ms", 0)

            if has_error or rt > 3000:
                key = f"{url}_{status // 100}xx" if status else url
                endpoint_errors[key]["count"] += 1
                endpoint_errors[key]["statuses"].append(status)
                endpoint_errors[key]["response_times"].append(rt)
                if req.get("error_message"):
                    endpoint_errors[key]["errors"].append(req.get("error_message", "")[:100])

        # 创建节点
        for endpoint, data in endpoint_errors.items():
            if data["count"] < 1:
                continue

            # 确定节点类型和严重性
            avg_status = sum(data["statuses"]) / len(data["statuses"]) if data["statuses"] else 0
            avg_rt = sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0

            if avg_status >= 500:
                node_type = NodeType.EVENT
                severity = ImpactLevel.HIGH
            elif avg_status >= 400:
                node_type = NodeType.EVENT
                severity = ImpactLevel.MEDIUM
            elif avg_rt > 5000:
                node_type = NodeType.SYMPTOM
                severity = ImpactLevel.HIGH
            else:
                node_type = NodeType.SYMPTOM
                severity = ImpactLevel.MEDIUM

            node = CausalNode(
                node_id=f"req_{hash(endpoint) % 10000}",
                name=f"Endpoint Error: {endpoint[:50]}",
                node_type=node_type,
                description=f"端点 {endpoint} 出现问题",
                severity=severity,
                frequency=data["count"],
                component=self._identify_component(endpoint),
                evidence=data["errors"][:5],
                source="request",
                metadata={
                    "endpoint": endpoint,
                    "avg_status": avg_status,
                    "avg_response_time": avg_rt
                }
            )
            nodes.append(node)

        # 添加高层次的聚合节点
        total_errors = sum(e["count"] for e in endpoint_errors.values())
        if total_errors > 10:
            error_rate = total_errors / len(requests) if requests else 0
            if error_rate > 0.1:
                nodes.append(CausalNode(
                    node_id="high_error_rate",
                    name="High Error Rate",
                    node_type=NodeType.SYMPTOM,
                    description=f"系统错误率过高: {error_rate:.1%}",
                    severity=ImpactLevel.CRITICAL if error_rate > 0.3 else ImpactLevel.HIGH,
                    frequency=total_errors,
                    source="request",
                    metadata={"error_rate": error_rate}
                ))

        return nodes

    def _event_to_node(self, event: dict[str, Any]) -> CausalNode | None:
        """将事件字典转换为节点"""
        if "id" not in event and "name" not in event:
            return None

        return CausalNode(
            node_id=event.get("id", f"event_{hash(str(event)) % 10000}"),
            name=event.get("name", "Unknown Event"),
            node_type=NodeType(event.get("type", "event")),
            description=event.get("description", ""),
            timestamp=self._parse_timestamp(event.get("timestamp")),
            severity=ImpactLevel(event.get("severity", "medium")),
            component=event.get("component", ""),
            service=event.get("service", ""),
            evidence=event.get("evidence", []),
            source="event"
        )

    def _infer_edges(self, graph: CausalGraph) -> list[CausalEdge]:
        """推断因果边"""
        edges: list[CausalEdge] = []
        nodes = graph.nodes

        # 1. 基于预定义因果关系
        for node in nodes:
            node_type = node.node_id.replace("log_", "").replace("req_", "")
            if node_type in self.ERROR_PATTERNS:
                possible_causes = self.ERROR_PATTERNS[node_type].get("possible_causes", [])
                for cause in possible_causes:
                    # 检查是否存在对应的原因节点
                    cause_node_id = f"log_{cause}"
                    if graph.get_node(cause_node_id):
                        edges.append(CausalEdge(
                            source=cause_node_id,
                            target=node.node_id,
                            edge_type=EdgeType.CAUSES,
                            confidence=0.6,
                            reasoning=f"基于预定义规则: {cause} -> {node_type}"
                        ))

        # 2. 基于时序关系
        time_sorted_nodes = [n for n in nodes if n.timestamp]
        time_sorted_nodes.sort(key=lambda n: n.timestamp)

        for i, earlier_node in enumerate(time_sorted_nodes):
            for later_node in time_sorted_nodes[i + 1:]:
                time_diff = (later_node.timestamp - earlier_node.timestamp).total_seconds() * 1000
                if time_diff > self.config.time_window_ms:
                    break

                # 时间接近的事件可能有因果关系
                if earlier_node.component and later_node.component:
                    # 同组件的事件更可能相关
                    if earlier_node.component == later_node.component:
                        confidence = 0.5
                    else:
                        confidence = 0.3
                else:
                    confidence = 0.4

                edges.append(CausalEdge(
                    source=earlier_node.node_id,
                    target=later_node.node_id,
                    edge_type=EdgeType.PRECEDES,
                    confidence=confidence,
                    delay_ms=time_diff,
                    reasoning=f"时序关系: {earlier_node.name} 早于 {later_node.name} {time_diff:.0f}ms"
                ))

        # 3. 基于组件依赖关系
        component_deps = {
            "api": ["database", "cache", "auth"],
            "gateway": ["api"],
            "auth": ["database"],
        }

        for node in nodes:
            if node.component in component_deps:
                for dep in component_deps[node.component]:
                    # 查找依赖组件的节点
                    dep_nodes = [n for n in nodes if n.component == dep]
                    for dep_node in dep_nodes:
                        edges.append(CausalEdge(
                            source=dep_node.node_id,
                            target=node.node_id,
                            edge_type=EdgeType.CONTRIBUTES,
                            confidence=0.5,
                            reasoning=f"组件依赖: {dep} -> {node.component}"
                        ))

        # 4. 高错误率与具体错误的关系
        high_error_node = graph.get_node("high_error_rate")
        if high_error_node:
            for node in nodes:
                if node.node_id != "high_error_rate" and node.node_type == NodeType.EVENT:
                    edges.append(CausalEdge(
                        source=node.node_id,
                        target="high_error_rate",
                        edge_type=EdgeType.CONTRIBUTES,
                        confidence=0.7,
                        reasoning=f"{node.name} 贡献到整体错误率"
                    ))

        # 去重
        seen = set()
        unique_edges = []
        for edge in edges:
            key = (edge.source, edge.target, edge.edge_type)
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)

        return unique_edges

    def _extract_timestamp(self, line: str) -> datetime | None:
        """从日志行提取时间戳"""
        patterns = [
            r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})",
            r"(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})",
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    ts_str = match.group(1)
                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
                        try:
                            return datetime.strptime(ts_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass

        return None

    def _parse_timestamp(self, ts: Any) -> datetime | None:
        """解析时间戳"""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            return self._extract_timestamp(ts)
        return None

    def _identify_component(self, text: str) -> str:
        """识别文本中的组件"""
        for component, patterns in self.COMPONENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return component
        return ""
