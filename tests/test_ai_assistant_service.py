"""
AI 助手服务单元测试

覆盖: AIAssistantService, AIInsight, InsightType
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch, PropertyMock

import pytest

from ai_test_tool.services.ai_assistant import (
    AIAssistantService,
    AIInsight,
    InsightType,
)


# ============================================================
# Helpers
# ============================================================

def make_service(db_mock=None, provider_mock=None) -> AIAssistantService:
    """Create an AIAssistantService with mocked dependencies."""
    with patch("ai_test_tool.services.ai_assistant.get_db_manager") as mock_get_db, \
         patch("ai_test_tool.services.ai_assistant.get_logger") as mock_get_logger:
        mock_get_db.return_value = db_mock or Mock()
        logger = Mock()
        mock_get_logger.return_value = logger
        svc = AIAssistantService(verbose=False)
    if provider_mock is not None:
        svc._provider = provider_mock
    return svc


def make_endpoint(method: str, path: str, **kwargs) -> dict:
    """Create a minimal endpoint dict."""
    ep = {"method": method, "path": path}
    ep.update(kwargs)
    return ep


# ============================================================
# Model tests
# ============================================================

class TestInsightType:
    def test_values(self):
        assert InsightType.API_CHANGE.value == "api_change"
        assert InsightType.PERFORMANCE_TREND.value == "performance_trend"
        assert InsightType.USAGE_PATTERN.value == "usage_pattern"
        assert InsightType.RISK_ASSESSMENT.value == "risk_assessment"
        assert InsightType.OPTIMIZATION.value == "optimization"
        assert InsightType.COVERAGE_GAP.value == "coverage_gap"


class TestAIInsight:
    def test_defaults(self):
        insight = AIInsight(
            insight_id="abc",
            insight_type=InsightType.API_CHANGE,
            title="Test",
            description="desc",
            severity="high",
            confidence=0.9,
        )
        assert insight.details == {}
        assert insight.recommendations == []
        assert isinstance(insight.created_at, datetime)

    def test_with_details(self):
        insight = AIInsight(
            insight_id="id1",
            insight_type=InsightType.COVERAGE_GAP,
            title="Gap",
            description="Missing tests",
            severity="medium",
            confidence=1.0,
            details={"count": 5},
            recommendations=["Add tests"],
        )
        assert insight.details == {"count": 5}
        assert insight.recommendations == ["Add tests"]


# ============================================================
# _normalize_params tests
# ============================================================

class TestNormalizeParams:
    def setup_method(self):
        self.svc = make_service()

    def test_list_of_params(self):
        params = [{"name": "id", "type": "integer"}, {"name": "q", "type": "string"}]
        result = self.svc._normalize_params(params)
        assert "id" in result
        assert "q" in result
        assert result["id"]["type"] == "integer"

    def test_json_string(self):
        params = json.dumps([{"name": "page", "type": "integer"}])
        result = self.svc._normalize_params(params)
        assert "page" in result

    def test_empty_string(self):
        result = self.svc._normalize_params("")
        assert result == {}

    def test_not_list(self):
        result = self.svc._normalize_params({"invalid": True})
        assert result == {}

    def test_skips_params_without_name(self):
        params = [{"type": "string"}, {"name": "valid", "type": "string"}]
        result = self.svc._normalize_params(params)
        assert len(result) == 1
        assert "valid" in result


# ============================================================
# _compare_endpoints tests
# ============================================================

class TestCompareEndpoints:
    def setup_method(self):
        self.svc = make_service()

    def test_no_changes(self):
        ep = make_endpoint("GET", "/users", parameters=[], request_body={}, responses={})
        changes = self.svc._compare_endpoints(ep, ep)
        assert changes == []

    def test_added_required_parameter(self):
        old = make_endpoint("GET", "/users", parameters=[], request_body={}, responses={})
        new = make_endpoint("GET", "/users",
                            parameters=[{"name": "token", "type": "string", "required": True}],
                            request_body={}, responses={})
        changes = self.svc._compare_endpoints(old, new)
        assert len(changes) == 1
        assert changes[0]["type"] == "added"
        assert changes[0]["breaking"] is True
        assert "token" in changes[0]["field"]

    def test_added_optional_parameter(self):
        old = make_endpoint("GET", "/users", parameters=[], request_body={}, responses={})
        new = make_endpoint("GET", "/users",
                            parameters=[{"name": "page", "type": "integer", "required": False}],
                            request_body={}, responses={})
        changes = self.svc._compare_endpoints(old, new)
        assert len(changes) == 1
        assert changes[0]["breaking"] is False

    def test_removed_parameter(self):
        old = make_endpoint("GET", "/users",
                            parameters=[{"name": "q", "type": "string"}],
                            request_body={}, responses={})
        new = make_endpoint("GET", "/users", parameters=[], request_body={}, responses={})
        changes = self.svc._compare_endpoints(old, new)
        assert len(changes) == 1
        assert changes[0]["type"] == "removed"
        assert changes[0]["breaking"] is True

    def test_parameter_type_changed(self):
        old = make_endpoint("GET", "/users",
                            parameters=[{"name": "id", "type": "integer"}],
                            request_body={}, responses={})
        new = make_endpoint("GET", "/users",
                            parameters=[{"name": "id", "type": "string"}],
                            request_body={}, responses={})
        changes = self.svc._compare_endpoints(old, new)
        type_changes = [c for c in changes if "type" in c["field"] and c["type"] == "modified"]
        assert len(type_changes) == 1
        assert type_changes[0]["breaking"] is True

    def test_parameter_optional_to_required(self):
        old = make_endpoint("GET", "/users",
                            parameters=[{"name": "id", "type": "integer", "required": False}],
                            request_body={}, responses={})
        new = make_endpoint("GET", "/users",
                            parameters=[{"name": "id", "type": "integer", "required": True}],
                            request_body={}, responses={})
        changes = self.svc._compare_endpoints(old, new)
        req_changes = [c for c in changes if "required" in c["field"]]
        assert len(req_changes) == 1
        assert req_changes[0]["breaking"] is True

    def test_request_body_changed(self):
        old = make_endpoint("POST", "/users",
                            parameters=[], request_body={"type": "object"},
                            responses={})
        new = make_endpoint("POST", "/users",
                            parameters=[], request_body={"type": "array"},
                            responses={})
        changes = self.svc._compare_endpoints(old, new)
        body_changes = [c for c in changes if c["field"] == "request_body"]
        assert len(body_changes) == 1
        assert body_changes[0]["breaking"] is True

    def test_responses_changed(self):
        old = make_endpoint("GET", "/users",
                            parameters=[], request_body={},
                            responses={"200": {"description": "OK"}})
        new = make_endpoint("GET", "/users",
                            parameters=[], request_body={},
                            responses={"200": {"description": "Success"}, "404": {"description": "Not found"}})
        changes = self.svc._compare_endpoints(old, new)
        resp_changes = [c for c in changes if c["field"] == "responses"]
        assert len(resp_changes) == 1
        assert resp_changes[0]["breaking"] is False

    def test_string_body_json_parsed(self):
        old = make_endpoint("POST", "/data",
                            parameters=[],
                            request_body='{"type": "object"}',
                            responses='{}')
        new = make_endpoint("POST", "/data",
                            parameters=[],
                            request_body='{"type": "array"}',
                            responses='{}')
        changes = self.svc._compare_endpoints(old, new)
        assert any(c["field"] == "request_body" for c in changes)

    def test_empty_string_body(self):
        old = make_endpoint("POST", "/data",
                            parameters=[], request_body='', responses='')
        new = make_endpoint("POST", "/data",
                            parameters=[], request_body='', responses='')
        changes = self.svc._compare_endpoints(old, new)
        assert changes == []


# ============================================================
# _get_change_recommendations tests
# ============================================================

class TestGetChangeRecommendations:
    def setup_method(self):
        self.svc = make_service()

    def test_breaking_change(self):
        changes = [{"field": "parameter:id:type", "type": "modified", "breaking": True}]
        recs = self.svc._get_change_recommendations(changes)
        assert any("回归测试" in r for r in recs)

    def test_parameter_change(self):
        changes = [{"field": "parameter:token", "type": "added", "breaking": False}]
        recs = self.svc._get_change_recommendations(changes)
        assert any("参数" in r for r in recs)

    def test_body_change(self):
        changes = [{"field": "request_body", "type": "modified", "breaking": True}]
        recs = self.svc._get_change_recommendations(changes)
        assert any("请求体" in r for r in recs)

    def test_response_change(self):
        changes = [{"field": "responses", "type": "modified", "breaking": False}]
        recs = self.svc._get_change_recommendations(changes)
        assert any("断言" in r for r in recs)

    def test_no_breaking_no_param_no_body(self):
        changes = [{"field": "responses", "type": "modified", "breaking": False}]
        recs = self.svc._get_change_recommendations(changes)
        assert not any("回归测试" in r for r in recs)

    def test_multiple_change_types(self):
        changes = [
            {"field": "parameter:id", "type": "removed", "breaking": True},
            {"field": "request_body", "type": "modified", "breaking": True},
            {"field": "responses", "type": "modified", "breaking": False},
        ]
        recs = self.svc._get_change_recommendations(changes)
        assert any("回归测试" in r for r in recs)
        assert any("参数" in r for r in recs)
        assert any("请求体" in r for r in recs)
        assert any("断言" in r for r in recs)


# ============================================================
# detect_api_changes tests
# ============================================================

class TestDetectApiChanges:
    def setup_method(self):
        self.svc = make_service()

    def test_added_endpoint(self):
        old = []
        new = [make_endpoint("POST", "/users", name="Create User")]
        insights = self.svc.detect_api_changes(old, new)
        assert len(insights) == 1
        assert insights[0].insight_type == InsightType.API_CHANGE
        assert "新增" in insights[0].title
        assert insights[0].severity == "medium"
        assert insights[0].details["change_type"] == "added"

    def test_removed_endpoint(self):
        old = [make_endpoint("DELETE", "/users/{id}", name="Delete User")]
        new = []
        insights = self.svc.detect_api_changes(old, new)
        assert len(insights) == 1
        assert "删除" in insights[0].title
        assert insights[0].severity == "high"
        assert insights[0].details["change_type"] == "removed"

    def test_modified_endpoint(self):
        old = [make_endpoint("GET", "/users",
                             parameters=[{"name": "id", "type": "integer"}],
                             request_body={}, responses={})]
        new = [make_endpoint("GET", "/users",
                             parameters=[{"name": "id", "type": "string"}],
                             request_body={}, responses={})]
        insights = self.svc.detect_api_changes(old, new)
        assert len(insights) == 1
        assert insights[0].details["change_type"] == "modified"

    def test_modified_endpoint_breaking_severity_high(self):
        old = [make_endpoint("GET", "/users",
                             parameters=[{"name": "id", "type": "integer"}],
                             request_body={}, responses={})]
        new = [make_endpoint("GET", "/users",
                             parameters=[{"name": "id", "type": "string"}],
                             request_body={}, responses={})]
        insights = self.svc.detect_api_changes(old, new)
        assert insights[0].severity == "high"

    def test_modified_endpoint_non_breaking_severity_medium(self):
        old = [make_endpoint("GET", "/users",
                             parameters=[], request_body={},
                             responses={"200": {"description": "OK"}})]
        new = [make_endpoint("GET", "/users",
                             parameters=[], request_body={},
                             responses={"200": {"description": "Success"}})]
        insights = self.svc.detect_api_changes(old, new)
        assert insights[0].severity == "medium"

    def test_no_changes(self):
        ep = make_endpoint("GET", "/health", parameters=[], request_body={}, responses={})
        insights = self.svc.detect_api_changes([ep], [ep])
        assert len(insights) == 0

    def test_mixed_changes(self):
        old = [
            make_endpoint("GET", "/users", parameters=[], request_body={}, responses={}),
            make_endpoint("DELETE", "/old", parameters=[], request_body={}, responses={}),
        ]
        new = [
            make_endpoint("GET", "/users", parameters=[], request_body={}, responses={}),
            make_endpoint("POST", "/new", name="New"),
        ]
        insights = self.svc.detect_api_changes(old, new)
        types = {i.details["change_type"] for i in insights}
        assert "added" in types
        assert "removed" in types

    def test_confidence_always_1(self):
        old = []
        new = [make_endpoint("GET", "/test")]
        insights = self.svc.detect_api_changes(old, new)
        assert insights[0].confidence == 1.0

    def test_insight_id_deterministic(self):
        old = []
        new = [make_endpoint("GET", "/test")]
        i1 = self.svc.detect_api_changes(old, new)
        i2 = self.svc.detect_api_changes(old, new)
        assert i1[0].insight_id == i2[0].insight_id


# ============================================================
# analyze_performance_trend tests
# ============================================================

class TestAnalyzePerformanceTrend:
    def setup_method(self):
        self.db = Mock()
        self.svc = make_service(db_mock=self.db)

    def test_no_results(self):
        self.db.fetch_all.return_value = []
        insights = self.svc.analyze_performance_trend(days=7)
        assert insights == []

    def test_performance_degradation_detected(self):
        # Need at least 5+ records for analysis; recent 5 avg > older avg * 1.5 and > 1000ms
        older_data = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 800, "status": "passed", "executed_at": "2025-01-01"}
            for _ in range(6)
        ]
        recent_data = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 2000, "status": "passed", "executed_at": "2025-01-10"}
            for _ in range(5)
        ]
        self.db.fetch_all.return_value = older_data + recent_data

        insights = self.svc.analyze_performance_trend(days=14)

        perf_insights = [i for i in insights if i.insight_type == InsightType.PERFORMANCE_TREND]
        assert len(perf_insights) >= 1
        assert "性能下降" in perf_insights[0].title
        assert perf_insights[0].details["new_avg_ms"] == 2000

    def test_performance_improvement_detected(self):
        older_data = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 3000, "status": "passed", "executed_at": "2025-01-01"}
            for _ in range(6)
        ]
        recent_data = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 500, "status": "passed", "executed_at": "2025-01-10"}
            for _ in range(5)
        ]
        self.db.fetch_all.return_value = older_data + recent_data

        insights = self.svc.analyze_performance_trend(days=14)

        perf_insights = [i for i in insights if i.insight_type == InsightType.PERFORMANCE_TREND]
        assert len(perf_insights) >= 1
        assert "改善" in perf_insights[0].title

    def test_high_error_rate_detected(self):
        data = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 100, "status": "failed" if i < 5 else "passed",
             "executed_at": f"2025-01-{i+1:02d}"}
            for i in range(10)
        ]
        self.db.fetch_all.return_value = data

        insights = self.svc.analyze_performance_trend(days=14)

        risk_insights = [i for i in insights if i.insight_type == InsightType.RISK_ASSESSMENT]
        assert len(risk_insights) >= 1
        assert "错误率" in risk_insights[0].title

    def test_too_few_records_skipped(self):
        data = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 100, "status": "passed", "executed_at": "2025-01-01"}
            for _ in range(3)  # Less than 5
        ]
        self.db.fetch_all.return_value = data

        insights = self.svc.analyze_performance_trend(days=7)
        assert insights == []

    def test_with_endpoint_id_filter(self):
        self.db.fetch_all.return_value = []
        self.svc.analyze_performance_trend(endpoint_id="ep_123", days=7)

        call_args = self.db.fetch_all.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "ep_123%" in params[0]

    def test_without_endpoint_id(self):
        self.db.fetch_all.return_value = []
        self.svc.analyze_performance_trend(days=14)

        call_args = self.db.fetch_all.call_args
        params = call_args[0][1]
        assert params == (14,)

    def test_degradation_severity_high_when_over_100_percent(self):
        # older avg = 800, recent avg = 2400 (200% increase)
        older = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 800, "status": "passed", "executed_at": "2025-01-01"}
            for _ in range(6)
        ]
        recent = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 2400, "status": "passed", "executed_at": "2025-01-10"}
            for _ in range(5)
        ]
        self.db.fetch_all.return_value = older + recent

        insights = self.svc.analyze_performance_trend(days=14)
        perf = [i for i in insights if i.insight_type == InsightType.PERFORMANCE_TREND]
        assert perf[0].severity == "high"

    def test_error_rate_severity_high_when_over_30_percent(self):
        data = [
            {"case_id": "c1", "method": "GET", "url": "/api",
             "actual_response_time_ms": 100,
             "status": "failed" if i < 4 else "passed",
             "executed_at": f"2025-01-{i+1:02d}"}
            for i in range(10)
        ]
        self.db.fetch_all.return_value = data

        insights = self.svc.analyze_performance_trend(days=14)
        risk = [i for i in insights if i.insight_type == InsightType.RISK_ASSESSMENT]
        assert risk[0].severity == "high"  # 40% > 30%


# ============================================================
# get_test_recommendations / analyze_coverage_gaps / identify_high_risk_endpoints
# ============================================================

class TestTestRecommendations:
    def setup_method(self):
        self.db = Mock()
        self.svc = make_service(db_mock=self.db)

    def test_coverage_gaps_found(self):
        self.db.fetch_all.return_value = [
            {"endpoint_id": "ep1", "method": "GET", "path": "/users", "name": "List"},
            {"endpoint_id": "ep2", "method": "POST", "path": "/users", "name": "Create"},
        ]
        insights = self.svc.analyze_coverage_gaps()
        assert len(insights) == 1
        assert insights[0].insight_type == InsightType.COVERAGE_GAP
        assert insights[0].details["total_uncovered"] == 2

    def test_no_coverage_gaps(self):
        self.db.fetch_all.return_value = []
        insights = self.svc.analyze_coverage_gaps()
        assert insights == []

    def test_high_risk_endpoints_found(self):
        self.db.fetch_all.return_value = [
            {"case_id": "c1", "method": "GET", "url": "/broken",
             "total": 10, "failures": 8},
        ]
        insights = self.svc.identify_high_risk_endpoints()
        assert len(insights) == 1
        assert insights[0].insight_type == InsightType.RISK_ASSESSMENT
        assert insights[0].severity == "high"  # 80% > 50%

    def test_high_risk_medium_severity(self):
        self.db.fetch_all.return_value = [
            {"case_id": "c1", "method": "GET", "url": "/flaky",
             "total": 10, "failures": 3},
        ]
        insights = self.svc.identify_high_risk_endpoints()
        assert len(insights) == 1
        assert insights[0].severity == "medium"  # 30% > 20% but < 50%

    def test_low_failure_rate_skipped(self):
        self.db.fetch_all.return_value = [
            {"case_id": "c1", "method": "GET", "url": "/ok",
             "total": 100, "failures": 10},
        ]
        insights = self.svc.identify_high_risk_endpoints()
        # 10% <= 20% threshold -> no insight
        assert insights == []

    def test_get_test_recommendations_combines_all(self):
        # Mock all three sub-methods
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                # First two calls: _analyze_coverage_gaps + _analyze_high_risk_endpoints
                return []
            else:
                # Third call: _get_priority_recommendations
                return []

        self.db.fetch_all.return_value = []
        insights = self.svc.get_test_recommendations()
        assert isinstance(insights, list)

    def test_priority_recommendations(self):
        # First call returns uncovered endpoints (coverage gaps)
        # Second call returns high risk (empty)
        # Third call returns recently changed endpoints
        call_idx = {"n": 0}

        def db_fetch_all(sql, params=None):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return []  # coverage gaps
            elif call_idx["n"] == 2:
                return []  # high risk
            elif call_idx["n"] == 3:
                return [  # recently changed
                    {"endpoint_id": "ep1", "method": "GET", "path": "/api",
                     "name": "Test", "updated_at": datetime(2025, 1, 15)}
                ]
            return []

        self.db.fetch_all.side_effect = db_fetch_all
        insights = self.svc.get_test_recommendations()
        priority = [i for i in insights if i.insight_type == InsightType.OPTIMIZATION]
        assert len(priority) == 1
        assert "优先测试" in priority[0].title


# ============================================================
# generate_mock_data tests
# ============================================================

class TestGenerateMockData:
    def setup_method(self):
        self.db = Mock()
        self.provider = Mock()
        self.svc = make_service(db_mock=self.db, provider_mock=self.provider)

    def test_success(self):
        self.db.fetch_one.return_value = {
            "endpoint_id": "ep1", "method": "GET", "path": "/users",
            "name": "List Users", "description": "Get all users",
            "responses": '{"200": {"description": "OK"}}',
        }
        self.provider.generate.return_value = '[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'

        result = self.svc.generate_mock_data("ep1", count=2)

        assert result["endpoint_id"] == "ep1"
        assert result["method"] == "GET"
        assert len(result["mock_responses"]) == 2
        self.provider.generate.assert_called_once()

    def test_endpoint_not_found(self):
        self.db.fetch_one.return_value = None
        with pytest.raises(ValueError, match="接口不存在"):
            self.svc.generate_mock_data("missing_ep")

    def test_llm_returns_json_in_markdown(self):
        self.db.fetch_one.return_value = {
            "endpoint_id": "ep1", "method": "GET", "path": "/data",
            "name": "Data", "description": "",
            "responses": "{}",
        }
        self.provider.generate.return_value = 'Here is the data:\n[{"key": "value"}]\nDone.'

        result = self.svc.generate_mock_data("ep1", count=1)
        assert result["mock_responses"] == [{"key": "value"}]

    def test_llm_returns_invalid_json(self):
        self.db.fetch_one.return_value = {
            "endpoint_id": "ep1", "method": "GET", "path": "/data",
            "name": "Data", "description": "",
            "responses": "{}",
        }
        self.provider.generate.return_value = "Sorry, I can't generate that."

        result = self.svc.generate_mock_data("ep1", count=1)
        assert len(result["mock_responses"]) == 1
        assert "error" in result["mock_responses"][0]

    def test_responses_dict_not_string(self):
        self.db.fetch_one.return_value = {
            "endpoint_id": "ep1", "method": "POST", "path": "/items",
            "name": "Create", "description": "",
            "responses": {"201": {"description": "Created"}},
        }
        self.provider.generate.return_value = '[{"id": 1}]'

        result = self.svc.generate_mock_data("ep1")
        assert result["mock_responses"] == [{"id": 1}]


# ============================================================
# generate_test_code tests
# ============================================================

class TestGenerateTestCode:
    def setup_method(self):
        self.db = Mock()
        self.provider = Mock()
        self.svc = make_service(db_mock=self.db, provider_mock=self.provider)

    def test_success(self):
        self.db.fetch_one.return_value = {
            "endpoint_id": "ep1", "method": "GET", "path": "/users",
            "name": "List Users", "parameters": "[]", "request_body": "{}",
        }
        self.db.fetch_all.return_value = [
            {"name": "test_list", "category": "normal",
             "body": None, "expected_status_code": 200},
        ]
        self.provider.generate.return_value = "```python\nimport pytest\n\ndef test_list_users():\n    pass\n```"

        code = self.svc.generate_test_code("ep1", language="python", framework="pytest")

        assert "import pytest" in code
        assert "def test_list_users" in code
        # Markdown code block markers should be stripped
        assert "```" not in code

    def test_endpoint_not_found(self):
        self.db.fetch_one.return_value = None
        with pytest.raises(ValueError, match="接口不存在"):
            self.svc.generate_test_code("missing")

    def test_no_test_cases(self):
        self.db.fetch_one.return_value = {
            "endpoint_id": "ep1", "method": "GET", "path": "/test",
            "name": "Test", "parameters": "[]", "request_body": "{}",
        }
        self.db.fetch_all.return_value = []
        self.provider.generate.return_value = "def test_something(): pass"

        code = self.svc.generate_test_code("ep1")
        assert "test_something" in code

    def test_code_without_backticks(self):
        self.db.fetch_one.return_value = {
            "endpoint_id": "ep1", "method": "GET", "path": "/test",
            "name": "Test", "parameters": "[]", "request_body": "{}",
        }
        self.db.fetch_all.return_value = []
        self.provider.generate.return_value = "def test_plain(): pass"

        code = self.svc.generate_test_code("ep1")
        assert code == "def test_plain(): pass"


# ============================================================
# ask_question tests
# ============================================================

class TestAskQuestion:
    def setup_method(self):
        self.db = Mock()
        self.provider = Mock()
        self.svc = make_service(db_mock=self.db, provider_mock=self.provider)

    def _setup_stats(self, endpoint_count=10, test_case_count=50,
                     recent_executions=100, passed=80, total=100):
        """Set up DB mock for _get_system_stats calls."""
        self.db.fetch_one.side_effect = [
            {"count": endpoint_count},
            {"count": test_case_count},
            {"count": recent_executions},
            {"total": total, "passed": passed},
        ]

    def test_basic_question(self):
        self._setup_stats()
        self.provider.generate.return_value = "There are 10 endpoints."

        answer = self.svc.ask_question("How many endpoints?")

        assert answer == "There are 10 endpoints."
        self.provider.generate.assert_called_once()

    def test_with_context(self):
        self._setup_stats()
        self.provider.generate.return_value = "Based on the context..."

        answer = self.svc.ask_question(
            "What's wrong?",
            context={"error": "500 Internal Server Error"},
        )

        prompt_arg = self.provider.generate.call_args[0][0]
        assert "500 Internal Server Error" in prompt_arg

    def test_without_context(self):
        self._setup_stats()
        self.provider.generate.return_value = "No context provided."

        answer = self.svc.ask_question("General question")

        prompt_arg = self.provider.generate.call_args[0][0]
        assert "上下文信息" not in prompt_arg

    def test_stats_included_in_prompt(self):
        self._setup_stats(endpoint_count=42, test_case_count=100)
        self.provider.generate.return_value = "answer"

        self.svc.ask_question("anything")

        prompt_arg = self.provider.generate.call_args[0][0]
        assert "42" in prompt_arg
        assert "100" in prompt_arg


# ============================================================
# _get_system_stats tests
# ============================================================

class TestGetSystemStats:
    def setup_method(self):
        self.db = Mock()
        self.svc = make_service(db_mock=self.db)

    def test_all_stats(self):
        self.db.fetch_one.side_effect = [
            {"count": 25},      # endpoints
            {"count": 100},     # test cases
            {"count": 500},     # recent executions
            {"total": 500, "passed": 450},  # success rate
        ]
        stats = self.svc._get_system_stats()
        assert stats["endpoint_count"] == 25
        assert stats["test_case_count"] == 100
        assert stats["recent_executions"] == 500
        assert stats["avg_success_rate"] == 0.9

    def test_empty_db(self):
        self.db.fetch_one.side_effect = [
            None,  # endpoints
            None,  # test cases
            None,  # recent executions
            None,  # success rate
        ]
        stats = self.svc._get_system_stats()
        assert stats["endpoint_count"] == 0
        assert stats["test_case_count"] == 0
        assert stats["recent_executions"] == 0
        assert stats["avg_success_rate"] == 0

    def test_zero_executions(self):
        self.db.fetch_one.side_effect = [
            {"count": 5},
            {"count": 10},
            {"count": 0},
            {"total": 0, "passed": 0},
        ]
        stats = self.svc._get_system_stats()
        assert stats["avg_success_rate"] == 0


# ============================================================
# Provider lazy loading test
# ============================================================

class TestProviderLazyLoad:
    def test_provider_loaded_on_first_access(self):
        svc = make_service()
        assert svc._provider is None

        mock_provider = Mock()
        with patch("ai_test_tool.services.ai_assistant.get_llm_provider",
                    return_value=mock_provider):
            provider = svc.provider

        assert provider is mock_provider
        assert svc._provider is mock_provider

    def test_provider_reuses_instance(self):
        mock_provider = Mock()
        svc = make_service(provider_mock=mock_provider)
        assert svc.provider is mock_provider
