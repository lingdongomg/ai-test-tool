"""
因果分析引擎单元测试
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from ai_test_tool.causal.models import (
    CausalGraph,
    CausalNode,
    CausalEdge,
    CausalChain,
    CausalConfig,
    CausalAnalysisResult,
    NodeType,
    EdgeType,
    ImpactLevel,
    ConfidenceLevel,
)
from ai_test_tool.causal.engine import CausalEngine


# ============================================================
# Helpers
# ============================================================

def make_node(node_id: str, name: str = "", **kwargs) -> CausalNode:
    return CausalNode(node_id=node_id, name=name or node_id, **kwargs)


def make_edge(src: str, tgt: str, **kwargs) -> CausalEdge:
    return CausalEdge(source=src, target=tgt, **kwargs)


def build_linear_graph() -> CausalGraph:
    """A -> B -> C  (linear chain)"""
    g = CausalGraph("linear")
    g.add_node(make_node("A", node_type=NodeType.ROOT_CAUSE, severity=ImpactLevel.CRITICAL))
    g.add_node(make_node("B", node_type=NodeType.EVENT, severity=ImpactLevel.HIGH))
    g.add_node(make_node("C", node_type=NodeType.SYMPTOM, severity=ImpactLevel.MEDIUM))
    g.add_edge(make_edge("A", "B", confidence=0.9))
    g.add_edge(make_edge("B", "C", confidence=0.8))
    return g


def build_diamond_graph() -> CausalGraph:
    """
    A -> B -> D
    A -> C -> D
    """
    g = CausalGraph("diamond")
    g.add_node(make_node("A", node_type=NodeType.ROOT_CAUSE))
    g.add_node(make_node("B"))
    g.add_node(make_node("C"))
    g.add_node(make_node("D", node_type=NodeType.SYMPTOM))
    g.add_edge(make_edge("A", "B", confidence=0.8))
    g.add_edge(make_edge("A", "C", confidence=0.7))
    g.add_edge(make_edge("B", "D", confidence=0.9))
    g.add_edge(make_edge("C", "D", confidence=0.6))
    return g


def build_multi_root_graph() -> CausalGraph:
    """
    R1 -> M -> L
    R2 -> M
    """
    g = CausalGraph("multi_root")
    g.add_node(make_node("R1", node_type=NodeType.ROOT_CAUSE, severity=ImpactLevel.HIGH))
    g.add_node(make_node("R2", node_type=NodeType.CONDITION, severity=ImpactLevel.LOW))
    g.add_node(make_node("M", node_type=NodeType.EVENT, severity=ImpactLevel.MEDIUM))
    g.add_node(make_node("L", node_type=NodeType.SYMPTOM, severity=ImpactLevel.HIGH))
    g.add_edge(make_edge("R1", "M", confidence=0.8))
    g.add_edge(make_edge("R2", "M", confidence=0.5))
    g.add_edge(make_edge("M", "L", confidence=0.9))
    return g


def make_mock_provider(response: str = "{}") -> Mock:
    provider = Mock()
    provider.generate = Mock(return_value=response)
    provider.chat = Mock(return_value=response)
    return provider


# ============================================================
# CausalNode tests
# ============================================================

class TestCausalNode:
    def test_is_root_cause_true(self):
        node = make_node("rc", node_type=NodeType.ROOT_CAUSE)
        assert node.is_root_cause is True

    def test_is_root_cause_false(self):
        node = make_node("ev", node_type=NodeType.EVENT)
        assert node.is_root_cause is False

    def test_to_dict_basic_fields(self):
        node = make_node("n1", name="Node 1", node_type=NodeType.SYMPTOM,
                         severity=ImpactLevel.HIGH, component="database")
        d = node.to_dict()
        assert d["node_id"] == "n1"
        assert d["name"] == "Node 1"
        assert d["node_type"] == "symptom"
        assert d["severity"] == "high"
        assert d["component"] == "database"
        assert d["timestamp"] is None

    def test_to_dict_with_timestamp(self):
        ts = datetime(2025, 1, 15, 10, 30, 0)
        node = make_node("n2", timestamp=ts)
        d = node.to_dict()
        assert d["timestamp"] == ts.isoformat()

    def test_to_dict_evidence(self):
        node = make_node("n3", evidence=["e1", "e2"])
        assert node.to_dict()["evidence"] == ["e1", "e2"]

    def test_default_values(self):
        node = CausalNode(node_id="x", name="x")
        assert node.node_type == NodeType.EVENT
        assert node.severity == ImpactLevel.MEDIUM
        assert node.frequency == 1
        assert node.evidence == []


# ============================================================
# CausalEdge tests
# ============================================================

class TestCausalEdge:
    @pytest.mark.parametrize("confidence,expected", [
        (0.95, ConfidenceLevel.CERTAIN),
        (0.91, ConfidenceLevel.CERTAIN),
        (0.85, ConfidenceLevel.HIGH),
        (0.71, ConfidenceLevel.HIGH),
        (0.60, ConfidenceLevel.MEDIUM),
        (0.51, ConfidenceLevel.MEDIUM),
        (0.40, ConfidenceLevel.LOW),
        (0.31, ConfidenceLevel.LOW),
        (0.20, ConfidenceLevel.UNCERTAIN),
        (0.0,  ConfidenceLevel.UNCERTAIN),
    ])
    def test_confidence_level(self, confidence, expected):
        edge = make_edge("a", "b", confidence=confidence)
        assert edge.confidence_level == expected

    def test_confidence_boundary_090(self):
        edge = make_edge("a", "b", confidence=0.9)
        assert edge.confidence_level == ConfidenceLevel.HIGH

    def test_confidence_boundary_070(self):
        edge = make_edge("a", "b", confidence=0.7)
        assert edge.confidence_level == ConfidenceLevel.MEDIUM

    def test_confidence_boundary_050(self):
        edge = make_edge("a", "b", confidence=0.5)
        assert edge.confidence_level == ConfidenceLevel.LOW

    def test_confidence_boundary_030(self):
        edge = make_edge("a", "b", confidence=0.3)
        assert edge.confidence_level == ConfidenceLevel.UNCERTAIN

    def test_to_dict(self):
        edge = make_edge("s", "t", edge_type=EdgeType.TRIGGERS,
                         weight=2.0, confidence=0.75, delay_ms=100,
                         reasoning="test reason")
        d = edge.to_dict()
        assert d["source"] == "s"
        assert d["target"] == "t"
        assert d["edge_type"] == "triggers"
        assert d["weight"] == 2.0
        assert d["confidence"] == 0.75
        assert d["confidence_level"] == "high"
        assert d["delay_ms"] == 100
        assert d["reasoning"] == "test reason"

    def test_default_values(self):
        edge = CausalEdge(source="a", target="b")
        assert edge.edge_type == EdgeType.CAUSES
        assert edge.weight == 1.0
        assert edge.confidence == 0.5
        assert edge.delay_ms == 0


# ============================================================
# CausalChain tests
# ============================================================

class TestCausalChain:
    def test_length(self):
        chain = CausalChain(chain_id="c1", nodes=["A", "B", "C"], edges=[])
        assert chain.length == 3

    def test_length_empty(self):
        chain = CausalChain(chain_id="c0", nodes=[], edges=[])
        assert chain.length == 0

    def test_root(self):
        chain = CausalChain(chain_id="c1", nodes=["X", "Y"], edges=[])
        assert chain.root == "X"

    def test_root_empty(self):
        chain = CausalChain(chain_id="c0", nodes=[], edges=[])
        assert chain.root == ""

    def test_leaf(self):
        chain = CausalChain(chain_id="c1", nodes=["X", "Y", "Z"], edges=[])
        assert chain.leaf == "Z"

    def test_leaf_empty(self):
        chain = CausalChain(chain_id="c0", nodes=[], edges=[])
        assert chain.leaf == ""

    def test_to_dict(self):
        chain = CausalChain(
            chain_id="c1", nodes=["A", "B"], edges=[],
            total_confidence=0.72, total_delay_ms=150, description="test"
        )
        d = chain.to_dict()
        assert d["chain_id"] == "c1"
        assert d["length"] == 2
        assert d["root"] == "A"
        assert d["leaf"] == "B"
        assert d["total_confidence"] == 0.72
        assert d["total_delay_ms"] == 150
        assert d["description"] == "test"


# ============================================================
# CausalGraph tests
# ============================================================

class TestCausalGraphBasic:
    def test_add_node(self):
        g = CausalGraph()
        g.add_node(make_node("n1"))
        assert g.node_count == 1
        assert g.get_node("n1") is not None

    def test_add_node_returns_self(self):
        g = CausalGraph()
        result = g.add_node(make_node("n1"))
        assert result is g

    def test_add_edge(self):
        g = CausalGraph()
        g.add_node(make_node("a"))
        g.add_node(make_node("b"))
        g.add_edge(make_edge("a", "b"))
        assert g.edge_count == 1

    def test_add_edge_returns_self(self):
        g = CausalGraph()
        result = g.add_edge(make_edge("a", "b"))
        assert result is g

    def test_add_edge_auto_creates_nodes(self):
        g = CausalGraph()
        g.add_edge(make_edge("x", "y"))
        assert g.node_count == 2
        assert g.get_node("x") is not None
        assert g.get_node("y") is not None

    def test_get_node_missing(self):
        g = CausalGraph()
        assert g.get_node("missing") is None

    def test_get_edge(self):
        g = CausalGraph()
        g.add_edge(make_edge("a", "b", confidence=0.9))
        edge = g.get_edge("a", "b")
        assert edge is not None
        assert edge.confidence == 0.9

    def test_get_edge_missing(self):
        g = CausalGraph()
        assert g.get_edge("a", "b") is None

    def test_successors(self):
        g = build_linear_graph()
        assert "B" in g.get_successors("A")
        assert "C" in g.get_successors("B")
        assert g.get_successors("C") == []

    def test_predecessors(self):
        g = build_linear_graph()
        assert g.get_predecessors("A") == []
        assert "A" in g.get_predecessors("B")
        assert "B" in g.get_predecessors("C")

    def test_nodes_property(self):
        g = build_linear_graph()
        ids = {n.node_id for n in g.nodes}
        assert ids == {"A", "B", "C"}

    def test_edges_property(self):
        g = build_linear_graph()
        assert len(g.edges) == 2

    def test_empty_graph(self):
        g = CausalGraph()
        assert g.node_count == 0
        assert g.edge_count == 0


class TestCausalGraphRootAndLeaf:
    def test_find_root_causes_linear(self):
        g = build_linear_graph()
        roots = g.find_root_causes()
        assert len(roots) == 1
        assert roots[0].node_id == "A"

    def test_find_root_causes_multi_root(self):
        g = build_multi_root_graph()
        root_ids = {n.node_id for n in g.find_root_causes()}
        assert root_ids == {"R1", "R2"}

    def test_find_leaf_nodes_linear(self):
        g = build_linear_graph()
        leaves = g.find_leaf_nodes()
        assert len(leaves) == 1
        assert leaves[0].node_id == "C"

    def test_find_leaf_nodes_diamond(self):
        g = build_diamond_graph()
        leaves = g.find_leaf_nodes()
        assert len(leaves) == 1
        assert leaves[0].node_id == "D"

    def test_isolated_node_is_both_root_and_leaf(self):
        g = CausalGraph()
        g.add_node(make_node("alone"))
        roots = g.find_root_causes()
        leaves = g.find_leaf_nodes()
        assert len(roots) == 1 and roots[0].node_id == "alone"
        assert len(leaves) == 1 and leaves[0].node_id == "alone"


class TestCausalGraphPaths:
    def test_find_paths_linear(self):
        g = build_linear_graph()
        paths = g.find_paths("A", "C")
        assert len(paths) == 1
        assert paths[0] == ["A", "B", "C"]

    def test_find_paths_diamond(self):
        g = build_diamond_graph()
        paths = g.find_paths("A", "D")
        assert len(paths) == 2
        path_sets = {tuple(p) for p in paths}
        assert ("A", "B", "D") in path_sets
        assert ("A", "C", "D") in path_sets

    def test_find_paths_no_path(self):
        g = build_linear_graph()
        paths = g.find_paths("C", "A")
        assert paths == []

    def test_find_paths_max_depth(self):
        g = build_linear_graph()
        paths = g.find_paths("A", "C", max_depth=1)
        assert paths == []

    def test_find_paths_same_node(self):
        g = build_linear_graph()
        paths = g.find_paths("A", "A")
        assert len(paths) == 1
        assert paths[0] == ["A"]


class TestCausalGraphCausalChains:
    def test_find_causal_chains_linear(self):
        g = build_linear_graph()
        chains = g.find_causal_chains()
        assert len(chains) >= 1
        top = chains[0]
        assert top.root == "A"
        assert top.leaf == "C"
        assert top.length == 3

    def test_chain_confidence_product(self):
        g = build_linear_graph()
        chains = g.find_causal_chains()
        top = chains[0]
        assert abs(top.total_confidence - round(0.9 * 0.8, 4)) < 1e-6

    def test_min_confidence_filter(self):
        g = build_linear_graph()
        chains = g.find_causal_chains(min_confidence=0.8)
        assert len(chains) == 0  # 0.9*0.8=0.72 < 0.8

    def test_from_node(self):
        g = build_diamond_graph()
        chains = g.find_causal_chains(from_node="A")
        for c in chains:
            assert c.root == "A"

    def test_to_node(self):
        g = build_diamond_graph()
        chains = g.find_causal_chains(to_node="D")
        for c in chains:
            assert c.leaf == "D"

    def test_sorted_by_confidence(self):
        g = build_diamond_graph()
        chains = g.find_causal_chains()
        for i in range(len(chains) - 1):
            assert chains[i].total_confidence >= chains[i + 1].total_confidence


class TestCausalGraphImpact:
    def test_calculate_node_impact_root(self):
        g = build_linear_graph()
        impact = g.calculate_node_impact("A")
        assert impact["affected_nodes_count"] == 2
        assert "B" in impact["affected_nodes"]
        assert "C" in impact["affected_nodes"]
        assert impact["total_severity_score"] > 0

    def test_calculate_node_impact_leaf(self):
        g = build_linear_graph()
        impact = g.calculate_node_impact("C")
        assert impact["affected_nodes_count"] == 0

    def test_impact_level_calculation(self):
        g = build_linear_graph()
        impact = g.calculate_node_impact("A")
        assert isinstance(impact["impact_level"], ImpactLevel)

    def test_calculate_impact_level_thresholds(self):
        g = CausalGraph()
        assert g._calculate_impact_level(0, 0) == ImpactLevel.NONE
        assert g._calculate_impact_level(1, 0) == ImpactLevel.LOW
        assert g._calculate_impact_level(2, 1) == ImpactLevel.MEDIUM
        assert g._calculate_impact_level(4, 3) == ImpactLevel.HIGH
        assert g._calculate_impact_level(10, 5) == ImpactLevel.CRITICAL


class TestCausalGraphTopologicalSort:
    def test_linear(self):
        g = build_linear_graph()
        order = g.topological_sort()
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")

    def test_diamond(self):
        g = build_diamond_graph()
        order = g.topological_sort()
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_includes_all_nodes(self):
        g = build_linear_graph()
        order = g.topological_sort()
        assert set(order) == {"A", "B", "C"}

    def test_cycle_produces_partial_result(self):
        g = CausalGraph()
        g.add_node(make_node("X"))
        g.add_node(make_node("Y"))
        g.add_edge(make_edge("X", "Y"))
        g.add_edge(make_edge("Y", "X"))
        order = g.topological_sort()
        assert len(order) < 2  # cycle prevents full ordering


class TestCausalGraphDetectCycles:
    def test_no_cycles(self):
        g = build_linear_graph()
        cycles = g.detect_cycles()
        assert cycles == []

    def test_simple_cycle(self):
        g = CausalGraph()
        g.add_node(make_node("X"))
        g.add_node(make_node("Y"))
        g.add_edge(make_edge("X", "Y"))
        g.add_edge(make_edge("Y", "X"))
        cycles = g.detect_cycles()
        assert len(cycles) >= 1

    def test_diamond_no_cycle(self):
        g = build_diamond_graph()
        cycles = g.detect_cycles()
        assert cycles == []


class TestCausalGraphMermaid:
    def test_to_mermaid_starts_with_graph_td(self):
        g = build_linear_graph()
        mermaid = g.to_mermaid()
        assert mermaid.startswith("graph TD")

    def test_root_cause_node_shape(self):
        g = CausalGraph()
        g.add_node(make_node("rc", node_type=NodeType.ROOT_CAUSE))
        mermaid = g.to_mermaid()
        assert "([" in mermaid and "])" in mermaid

    def test_non_root_cause_node_shape(self):
        g = CausalGraph()
        g.add_node(make_node("ev", node_type=NodeType.EVENT))
        mermaid = g.to_mermaid()
        assert "((" in mermaid and "))" in mermaid

    def test_causes_arrow(self):
        g = CausalGraph()
        g.add_edge(make_edge("a", "b", edge_type=EdgeType.CAUSES))
        mermaid = g.to_mermaid()
        assert "-->" in mermaid

    def test_non_causes_arrow(self):
        g = CausalGraph()
        g.add_edge(make_edge("a", "b", edge_type=EdgeType.CONTRIBUTES))
        mermaid = g.to_mermaid()
        assert "-.->" in mermaid
        assert "|contributes|" in mermaid

    def test_to_dict(self):
        g = build_linear_graph()
        d = g.to_dict()
        assert d["graph_id"] == "linear"
        assert d["node_count"] == 3
        assert d["edge_count"] == 2
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 2


# ============================================================
# CausalConfig tests
# ============================================================

class TestCausalConfig:
    def test_defaults(self):
        c = CausalConfig()
        assert c.min_confidence == 0.3
        assert c.enable_llm_reasoning is True
        assert c.top_k_root_causes == 5

    def test_to_dict(self):
        c = CausalConfig(min_confidence=0.5)
        d = c.to_dict()
        assert d["min_confidence"] == 0.5
        assert "min_correlation" in d


# ============================================================
# CausalAnalysisResult tests
# ============================================================

class TestCausalAnalysisResult:
    def test_has_root_cause_true(self):
        r = CausalAnalysisResult(root_causes=[{"node_id": "rc1"}])
        assert r.has_root_cause is True

    def test_has_root_cause_false(self):
        r = CausalAnalysisResult()
        assert r.has_root_cause is False

    def test_to_dict(self):
        r = CausalAnalysisResult(
            graph=build_linear_graph(),
            root_causes=[{"node_id": "A"}],
            overall_confidence=0.8,
            recommendations=["fix it"],
        )
        d = r.to_dict()
        assert d["has_root_cause"] is True
        assert d["overall_confidence"] == 0.8
        assert d["graph_summary"]["node_count"] == 3

    def test_to_dict_no_graph(self):
        r = CausalAnalysisResult()
        d = r.to_dict()
        assert d["graph_summary"]["node_count"] == 0


# ============================================================
# CausalEngine tests
# ============================================================

class TestCausalEngineInit:
    def test_default_config(self):
        engine = CausalEngine()
        assert engine.config.enable_llm_reasoning is True

    def test_custom_config(self):
        cfg = CausalConfig(enable_llm_reasoning=False, min_confidence=0.5)
        engine = CausalEngine(config=cfg)
        assert engine.config.enable_llm_reasoning is False
        assert engine.config.min_confidence == 0.5

    def test_with_mock_provider(self):
        provider = make_mock_provider()
        engine = CausalEngine(llm_provider=provider)
        assert engine._llm_provider is provider


class TestCausalEngineAnalyze:
    """Test analyze() with pre-built graph and enable_llm_reasoning=False."""

    def setup_method(self):
        self.config = CausalConfig(enable_llm_reasoning=False)
        self.engine = CausalEngine(config=self.config)

    def test_empty_graph(self):
        g = CausalGraph()
        result = self.engine.analyze(graph=g)
        assert result.total_events == 0
        assert "无法进行因果分析" in result.reasoning

    def test_linear_graph(self):
        g = build_linear_graph()
        result = self.engine.analyze(graph=g)
        assert result.graph is g
        assert result.total_events == 3
        assert result.has_root_cause is True
        assert result.primary_root_cause is not None
        assert result.primary_root_cause["node_id"] == "A"

    def test_causal_chains_populated(self):
        g = build_linear_graph()
        result = self.engine.analyze(graph=g)
        assert len(result.causal_chains) >= 1
        assert result.critical_path is not None
        assert result.critical_path.root == "A"

    def test_impact_assessment(self):
        g = build_linear_graph()
        result = self.engine.analyze(graph=g)
        assert "scope" in result.impact_assessment
        assert "severity" in result.impact_assessment

    def test_recommendations_generated(self):
        g = build_linear_graph()
        result = self.engine.analyze(graph=g)
        assert isinstance(result.recommendations, list)

    def test_overall_confidence(self):
        g = build_linear_graph()
        result = self.engine.analyze(graph=g)
        assert 0 < result.overall_confidence <= 1.0

    def test_reasoning_generated(self):
        g = build_linear_graph()
        result = self.engine.analyze(graph=g)
        assert len(result.reasoning) > 0

    def test_analysis_time_tracked(self):
        g = build_linear_graph()
        result = self.engine.analyze(graph=g)
        assert result.analysis_time_ms > 0

    def test_diamond_graph_multiple_chains(self):
        g = build_diamond_graph()
        result = self.engine.analyze(graph=g)
        assert len(result.causal_chains) >= 2

    def test_multi_root_graph(self):
        g = build_multi_root_graph()
        result = self.engine.analyze(graph=g)
        assert len(result.root_causes) == 2
        # R1 should rank higher (ROOT_CAUSE type + HIGH severity)
        assert result.root_causes[0]["node_id"] == "R1"

    def test_top_k_root_causes(self):
        cfg = CausalConfig(enable_llm_reasoning=False, top_k_root_causes=1)
        engine = CausalEngine(config=cfg)
        g = build_multi_root_graph()
        result = engine.analyze(graph=g)
        assert len(result.root_causes) <= 1

    def test_top_k_chains(self):
        cfg = CausalConfig(enable_llm_reasoning=False, top_k_chains=1)
        engine = CausalEngine(config=cfg)
        g = build_diamond_graph()
        result = engine.analyze(graph=g)
        assert len(result.causal_chains) <= 1


class TestCausalEngineAnalyzeRootCauses:
    def setup_method(self):
        self.config = CausalConfig(enable_llm_reasoning=False)
        self.engine = CausalEngine(config=self.config)

    def test_root_cause_fields(self):
        g = build_linear_graph()
        rcs = self.engine._analyze_root_causes(g)
        assert len(rcs) == 1
        rc = rcs[0]
        assert "node_id" in rc
        assert "name" in rc
        assert "type" in rc
        assert "severity" in rc
        assert "confidence" in rc
        assert "impact_score" in rc
        assert "affected_count" in rc

    def test_sorted_by_confidence(self):
        g = build_multi_root_graph()
        rcs = self.engine._analyze_root_causes(g)
        for i in range(len(rcs) - 1):
            assert rcs[i]["confidence"] >= rcs[i + 1]["confidence"]


class TestCalculateRootCauseConfidence:
    def setup_method(self):
        self.engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))

    def _calc(self, node, impact=None):
        impact = impact or {"affected_nodes_count": 0}
        return self.engine._calculate_root_cause_confidence(node, impact)

    def test_base_confidence(self):
        node = make_node("n", node_type=NodeType.SYMPTOM, severity=ImpactLevel.LOW)
        c = self._calc(node)
        assert c == 0.5

    def test_root_cause_type_bonus(self):
        node = make_node("n", node_type=NodeType.ROOT_CAUSE, severity=ImpactLevel.LOW)
        c = self._calc(node)
        assert c >= 0.7  # base 0.5 + 0.2

    def test_event_type_bonus(self):
        node = make_node("n", node_type=NodeType.EVENT, severity=ImpactLevel.LOW)
        c = self._calc(node)
        assert c >= 0.6  # base 0.5 + 0.1

    def test_severity_bonus_critical(self):
        node = make_node("n", node_type=NodeType.SYMPTOM, severity=ImpactLevel.CRITICAL)
        c = self._calc(node)
        assert c >= 0.65  # 0.5 + 0.15

    def test_frequency_bonus_high(self):
        node = make_node("n", node_type=NodeType.SYMPTOM, severity=ImpactLevel.LOW, frequency=15)
        c = self._calc(node)
        assert c >= 0.6  # 0.5 + 0.1

    def test_frequency_bonus_medium(self):
        node = make_node("n", node_type=NodeType.SYMPTOM, severity=ImpactLevel.LOW, frequency=7)
        c = self._calc(node)
        assert c >= 0.55  # 0.5 + 0.05

    def test_affected_nodes_bonus(self):
        node = make_node("n", node_type=NodeType.SYMPTOM, severity=ImpactLevel.LOW)
        c = self._calc(node, {"affected_nodes_count": 6})
        assert c >= 0.6  # 0.5 + 0.1

    def test_evidence_bonus(self):
        node = make_node("n", node_type=NodeType.SYMPTOM, severity=ImpactLevel.LOW,
                         evidence=["e1", "e2", "e3"])
        c = self._calc(node)
        assert c >= 0.55  # 0.5 + 0.05

    def test_capped_at_1(self):
        node = make_node("n", node_type=NodeType.ROOT_CAUSE,
                         severity=ImpactLevel.CRITICAL, frequency=20,
                         evidence=["a", "b", "c"])
        c = self._calc(node, {"affected_nodes_count": 10})
        assert c <= 1.0


class TestAssessImpact:
    def setup_method(self):
        self.engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))

    def test_basic_impact(self):
        g = build_linear_graph()
        rcs = self.engine._analyze_root_causes(g)
        impact = self.engine._assess_impact(g, rcs)
        assert "scope" in impact
        assert "severity" in impact
        assert "affected_nodes_count" in impact
        assert "affected_components" in impact

    def test_system_wide_scope(self):
        g = CausalGraph()
        for i in range(6):
            g.add_node(make_node(f"n{i}", severity=ImpactLevel.CRITICAL,
                                 component=f"comp{i}"))
        g.add_node(make_node("root", node_type=NodeType.ROOT_CAUSE,
                              severity=ImpactLevel.CRITICAL))
        for i in range(6):
            g.add_edge(make_edge("root", f"n{i}"))
        rcs = self.engine._analyze_root_causes(g)
        impact = self.engine._assess_impact(g, rcs)
        assert impact["scope"] == "system_wide"
        assert impact["severity"] == "critical"

    def test_low_severity(self):
        g = CausalGraph()
        g.add_node(make_node("root", severity=ImpactLevel.LOW))
        g.add_node(make_node("leaf", severity=ImpactLevel.LOW))
        g.add_edge(make_edge("root", "leaf"))
        rcs = self.engine._analyze_root_causes(g)
        impact = self.engine._assess_impact(g, rcs)
        assert impact["severity"] in ("low", "medium")


class TestGenerateRecommendations:
    def setup_method(self):
        self.engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))

    def test_timeout_recommendation(self):
        g = CausalGraph()
        g.add_node(make_node("timeout_issue"))
        rcs = [{"node_id": "timeout_issue", "name": "Timeout Issue", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("超时" in r or "timeout" in r.lower() for r in recs)

    def test_memory_recommendation(self):
        g = CausalGraph()
        g.add_node(make_node("memory_leak"))
        rcs = [{"node_id": "memory_leak", "name": "Memory Leak", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("内存" in r or "memory" in r.lower() for r in recs)

    def test_connection_recommendation(self):
        g = CausalGraph()
        g.add_node(make_node("connection_error"))
        rcs = [{"node_id": "connection_error", "name": "Connection Error", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("连接" in r or "网络" in r for r in recs)

    def test_database_recommendation_by_node_id(self):
        g = CausalGraph()
        g.add_node(make_node("database_slow"))
        rcs = [{"node_id": "database_slow", "name": "Database Slow", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("数据库" in r for r in recs)

    def test_database_recommendation_by_component(self):
        g = CausalGraph()
        g.add_node(make_node("slow_query"))
        rcs = [{"node_id": "slow_query", "name": "Slow Query", "component": "database"}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("数据库" in r for r in recs)

    def test_auth_recommendation(self):
        g = CausalGraph()
        g.add_node(make_node("auth_failure"))
        rcs = [{"node_id": "auth_failure", "name": "Auth Failure", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("认证" in r for r in recs)

    def test_generic_recommendation(self):
        g = CausalGraph()
        g.add_node(make_node("unknown_error"))
        rcs = [{"node_id": "unknown_error", "name": "Unknown Error", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("日志" in r or "监控" in r for r in recs)

    def test_large_graph_recommendation(self):
        g = CausalGraph()
        for i in range(6):
            g.add_node(make_node(f"n{i}"))
        rcs = [{"node_id": "n0", "name": "N0", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("因果链" in r for r in recs)

    def test_cycle_warning(self):
        g = CausalGraph()
        g.add_node(make_node("X"))
        g.add_node(make_node("Y"))
        g.add_edge(make_edge("X", "Y"))
        g.add_edge(make_edge("Y", "X"))
        rcs = [{"node_id": "X", "name": "X", "component": ""}]
        recs = self.engine._generate_recommendations(g, rcs)
        assert any("循环" in r for r in recs)


class TestGenerateReasoning:
    def setup_method(self):
        self.engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))

    def test_no_chains(self):
        g = build_linear_graph()
        reasoning = self.engine._generate_reasoning(g, [])
        assert "未发现" in reasoning

    def test_with_chains(self):
        g = build_linear_graph()
        chains = g.find_causal_chains()
        reasoning = self.engine._generate_reasoning(g, chains)
        assert "主要故障传播路径" in reasoning
        assert "置信度" in reasoning


class TestCausalEngineLLMPath:
    """Test the LLM reasoning path with mocked provider."""

    def test_llm_reasoning_called_when_enabled(self):
        provider = make_mock_provider('{"primary_root_cause": {"node_id": "A", '
                                      '"name": "A", "confidence": 0.9, '
                                      '"reasoning": "test"}, '
                                      '"recommendations": ["fix A"], '
                                      '"propagation_path": "A -> B -> C", '
                                      '"overall_confidence": 0.85, '
                                      '"impact_assessment": {"scope": "single_service"}}')
        cfg = CausalConfig(enable_llm_reasoning=True)
        engine = CausalEngine(llm_provider=provider, config=cfg)

        g = build_linear_graph()
        result = engine.analyze(graph=g)

        provider.generate.assert_called_once()
        assert result.primary_root_cause["node_id"] == "A"
        assert result.recommendations == ["fix A"]
        assert result.overall_confidence == 0.85

    def test_llm_failure_gracefully_handled(self):
        provider = Mock()
        provider.generate = Mock(side_effect=RuntimeError("LLM down"))
        cfg = CausalConfig(enable_llm_reasoning=True)
        engine = CausalEngine(llm_provider=provider, config=cfg)

        g = build_linear_graph()
        result = engine.analyze(graph=g)
        # Should not crash; falls back gracefully
        assert result.graph is g
        assert result.total_events == 3

    def test_llm_not_called_when_disabled(self):
        provider = make_mock_provider()
        cfg = CausalConfig(enable_llm_reasoning=False)
        engine = CausalEngine(llm_provider=provider, config=cfg)

        g = build_linear_graph()
        engine.analyze(graph=g)
        provider.generate.assert_not_called()

    def test_parse_llm_response_json_block(self):
        engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))
        resp = '```json\n{"key": "value"}\n```'
        result = engine._parse_llm_response(resp)
        assert result == {"key": "value"}

    def test_parse_llm_response_plain_json(self):
        engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))
        resp = '{"key": "value"}'
        result = engine._parse_llm_response(resp)
        assert result == {"key": "value"}

    def test_parse_llm_response_embedded_json(self):
        engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))
        resp = 'Some text before {"key": "value"} some text after'
        result = engine._parse_llm_response(resp)
        assert result == {"key": "value"}

    def test_parse_llm_response_invalid(self):
        engine = CausalEngine(config=CausalConfig(enable_llm_reasoning=False))
        result = engine._parse_llm_response("not json at all")
        assert result is None


# ============================================================
# Enum value tests
# ============================================================

class TestEnums:
    def test_node_type_values(self):
        assert NodeType.EVENT.value == "event"
        assert NodeType.ROOT_CAUSE.value == "root_cause"
        assert NodeType.SYMPTOM.value == "symptom"
        assert NodeType.COMPONENT.value == "component"

    def test_edge_type_values(self):
        assert EdgeType.CAUSES.value == "causes"
        assert EdgeType.TRIGGERS.value == "triggers"
        assert EdgeType.PREVENTS.value == "prevents"

    def test_impact_level_values(self):
        assert ImpactLevel.CRITICAL.value == "critical"
        assert ImpactLevel.NONE.value == "none"

    def test_confidence_level_values(self):
        assert ConfidenceLevel.CERTAIN.value == "certain"
        assert ConfidenceLevel.UNCERTAIN.value == "uncertain"
