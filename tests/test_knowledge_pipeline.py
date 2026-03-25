"""
知识提取管线 V2 单元测试
"""

import pytest
from ai_test_tool.knowledge.pipeline import (
    ClusteringStage,
    PatternRecognitionStage,
    PostProcessingStage,
    ExtractionPipeline,
    PipelineContext,
)
from ai_test_tool.knowledge.models import KnowledgeSuggestion


# =====================================================
# 测试数据
# =====================================================

def _make_requests(count=20, url_prefix="/api/user", method="GET",
                   status=200, has_error=False, resp_time=50.0,
                   auth_header=True):
    """生成模拟请求数据"""
    reqs = []
    for i in range(count):
        headers = {"Content-Type": "application/json"}
        if auth_header:
            headers["Authorization"] = f"Bearer test_token_{i % 3}"
        reqs.append({
            "url": f"{url_prefix}/{i}?page=1",
            "method": method,
            "http_status": status,
            "has_error": has_error,
            "response_time_ms": resp_time + (i * 2),
            "headers": headers,
            "error_message": f"Error {status}" if has_error else "",
        })
    return reqs


def _sample_requests():
    """多样化的样本请求"""
    reqs = []
    # 正常请求
    reqs.extend(_make_requests(30, "/api/user", "GET", 200, resp_time=50))
    reqs.extend(_make_requests(10, "/api/user", "POST", 201, resp_time=80))
    # 错误请求
    reqs.extend(_make_requests(5, "/api/user", "GET", 401, has_error=True, auth_header=False))
    reqs.extend(_make_requests(3, "/api/order", "POST", 500, has_error=True))
    # 登录接口
    reqs.extend(_make_requests(5, "/api/auth/login", "POST", 200, resp_time=100))
    # 带敏感参数的请求
    for i in range(2):
        reqs.append({
            "url": f"/api/user/reset?password=secret123&token=abc",
            "method": "POST",
            "http_status": 200,
            "has_error": False,
            "response_time_ms": 30,
            "headers": {"Content-Type": "application/json"},
        })
    return reqs


# =====================================================
# Stage 1: ClusteringStage 测试
# =====================================================

class TestClusteringStage:
    def test_basic_clustering(self):
        stage = ClusteringStage()
        reqs = _make_requests(10, "/api/user") + _make_requests(5, "/api/order")
        ctx = PipelineContext(raw_requests=reqs)

        result = stage.process(ctx)

        assert len(result.url_clusters) >= 2
        patterns = [c.pattern for c in result.url_clusters]
        assert any("/api/user" in p for p in patterns)
        assert any("/api/order" in p for p in patterns)

    def test_id_normalization(self):
        stage = ClusteringStage()
        reqs = [
            {"url": "/api/user/123", "method": "GET", "http_status": 200},
            {"url": "/api/user/456", "method": "GET", "http_status": 200},
            {"url": "/api/user/789", "method": "GET", "http_status": 200},
        ]
        ctx = PipelineContext(raw_requests=reqs)

        result = stage.process(ctx)

        # 数字 ID 应归入同一聚类
        assert len(result.url_clusters) == 1
        assert "{id}" in result.url_clusters[0].pattern

    def test_error_clustering(self):
        stage = ClusteringStage()
        reqs = _make_requests(5, status=401, has_error=True) + _make_requests(3, status=500, has_error=True)
        ctx = PipelineContext(raw_requests=reqs)

        result = stage.process(ctx)

        assert 401 in result.error_clusters
        assert 500 in result.error_clusters

    def test_empty_input(self):
        stage = ClusteringStage()
        ctx = PipelineContext(raw_requests=[])
        result = stage.process(ctx)
        assert len(result.url_clusters) == 0


# =====================================================
# Stage 2: PatternRecognitionStage 测试
# =====================================================

class TestPatternRecognitionStage:
    def _run_pipeline_to_stage2(self, reqs):
        ctx = PipelineContext(raw_requests=reqs, task_id="test")
        ctx = ClusteringStage().process(ctx)
        stage = PatternRecognitionStage()
        return stage.process(ctx)

    def test_auth_pattern_extraction(self):
        reqs = _make_requests(20, auth_header=True)
        result = self._run_pipeline_to_stage2(reqs)

        auth_suggestions = [s for s in result.rule_suggestions if s.type == "auth_config"]
        assert len(auth_suggestions) >= 1
        assert auth_suggestions[0].confidence >= 0.7

    def test_error_pattern_extraction(self):
        reqs = _make_requests(10, status=200) + _make_requests(5, status=500, has_error=True)
        result = self._run_pipeline_to_stage2(reqs)

        error_suggestions = [s for s in result.rule_suggestions if s.type == "error_pattern"]
        assert len(error_suggestions) >= 1

    def test_performance_extraction(self):
        reqs = _make_requests(15, resp_time=100)
        result = self._run_pipeline_to_stage2(reqs)

        perf_suggestions = [s for s in result.rule_suggestions if s.type == "performance_baseline"]
        assert len(perf_suggestions) >= 1
        assert "P50" in perf_suggestions[0].content or "P90" in perf_suggestions[0].content

    def test_security_extraction(self):
        reqs = [
            {"url": "/api/reset?password=secret&token=abc", "method": "POST",
             "http_status": 200, "headers": {}, "response_time_ms": 30},
        ] * 5
        result = self._run_pipeline_to_stage2(reqs)

        security_suggestions = [s for s in result.rule_suggestions if s.type == "security_rule"]
        assert len(security_suggestions) >= 1
        assert security_suggestions[0].confidence >= 0.9

    def test_dependency_extraction(self):
        reqs = _make_requests(3, "/api/auth/login", "POST", 200)
        reqs += _make_requests(20, "/api/user", "GET", 200)
        result = self._run_pipeline_to_stage2(reqs)

        dep_suggestions = [s for s in result.rule_suggestions if s.type == "api_dependency"]
        assert len(dep_suggestions) >= 1


# =====================================================
# Stage 4: PostProcessingStage 测试
# =====================================================

class TestPostProcessingStage:
    def test_deduplication(self):
        stage = PostProcessingStage()
        ctx = PipelineContext()
        # 两条相似的知识
        ctx.rule_suggestions = [
            KnowledgeSuggestion(
                title="/api/user 存在 401 错误 (30%)",
                content="接口存在认证问题",
                type="error_pattern", scope="/api/user", confidence=0.8,
            ),
            KnowledgeSuggestion(
                title="/api/user 存在 401 错误 (35%)",
                content="接口存在认证问题，需要 token",
                type="error_pattern", scope="/api/user", confidence=0.7,
            ),
        ]

        result = stage.process(ctx)

        # 应合并为一条
        assert len(result.final_suggestions) == 1
        assert result.final_suggestions[0].confidence == 0.8

    def test_filter_low_confidence(self):
        stage = PostProcessingStage()
        ctx = PipelineContext()
        ctx.rule_suggestions = [
            KnowledgeSuggestion(title="Good", content="Good knowledge",
                               type="auth_config", confidence=0.9),
            KnowledgeSuggestion(title="Bad", content="Low quality",
                               type="auth_config", confidence=0.1),
        ]

        result = stage.process(ctx)

        assert len(result.final_suggestions) == 1
        assert result.final_suggestions[0].title == "Good"


# =====================================================
# 完整管线测试（不含 LLM）
# =====================================================

class TestExtractionPipeline:
    def test_full_pipeline_no_llm(self):
        """完整管线（无 LLM），仅规则引擎"""
        pipeline = ExtractionPipeline(llm_chain=None)
        reqs = _sample_requests()

        suggestions = pipeline.run(reqs, task_id="test-001")

        assert len(suggestions) > 0
        # 应至少提取出认证模式
        types = {s.type for s in suggestions}
        assert "auth_config" in types or "error_pattern" in types

    def test_pipeline_with_few_requests(self):
        """少量请求也应正常运行（不崩溃）"""
        pipeline = ExtractionPipeline(llm_chain=None)
        reqs = [{"url": "/api/test", "method": "GET", "http_status": 200, "headers": {}}]

        suggestions = pipeline.run(reqs, task_id="test-002")
        # 少量请求可能不产出知识，但不应报错
        assert isinstance(suggestions, list)

    def test_pipeline_empty_input(self):
        pipeline = ExtractionPipeline(llm_chain=None)
        suggestions = pipeline.run([], task_id="test-003")
        assert suggestions == []
