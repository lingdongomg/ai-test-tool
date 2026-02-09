"""
数据库模型测试 - to_dict / from_dict 序列化
"""

import json
import pytest
from datetime import datetime

from ai_test_tool.database.models import (
    AnalysisTask, ParsedRequestRecord, AnalysisReport,
    TestCaseRecord, ApiTag, ApiEndpoint,
    AIInsight, ProductionRequest,
    KnowledgeEntry,
    TaskStatus, TaskType, TestCaseCategory, TestCasePriority,
    ReportType, EndpointSourceType, KnowledgeType, KnowledgeStatus, KnowledgeSource,
)
from ai_test_tool.database.models.monitoring import InsightSeverity, RequestSource


class TestAnalysisTaskModel:
    """AnalysisTask 序列化测试"""

    def test_to_dict_basic(self):
        task = AnalysisTask(
            task_id="test_001",
            name="测试任务",
            status=TaskStatus.PENDING,
            task_type=TaskType.LOG_ANALYSIS,
        )
        d = task.to_dict()
        assert d["task_id"] == "test_001"
        assert d["name"] == "测试任务"
        assert d["status"] == "pending"
        assert d["task_type"] == "log_analysis"

    def test_to_dict_enum_serialization(self):
        task = AnalysisTask(
            task_id="t1",
            name="t",
            status=TaskStatus.RUNNING,
            task_type=TaskType.TEST_GENERATION,
        )
        d = task.to_dict()
        assert d["status"] == "running"
        assert d["task_type"] == "test_generation"

    def test_to_dict_json_fields(self):
        task = AnalysisTask(
            task_id="t2",
            name="t",
            metadata={"key": "value", "count": 3},
        )
        d = task.to_dict()
        # metadata 应被序列化为 JSON 字符串
        assert isinstance(d["metadata"], str)
        parsed = json.loads(d["metadata"])
        assert parsed["key"] == "value"
        assert parsed["count"] == 3

    def test_from_dict_basic(self):
        data = {
            "task_id": "test_002",
            "name": "从字典创建",
            "status": "completed",
            "task_type": "log_analysis",
        }
        task = AnalysisTask.from_dict(data)
        assert task.task_id == "test_002"
        assert task.status == TaskStatus.COMPLETED
        assert task.task_type == TaskType.LOG_ANALYSIS

    def test_from_dict_json_fields(self):
        data = {
            "task_id": "t3",
            "name": "t",
            "metadata": '{"key": "value"}',
        }
        task = AnalysisTask.from_dict(data)
        assert isinstance(task.metadata, dict)
        assert task.metadata["key"] == "value"

    def test_from_dict_ignores_unknown_fields(self):
        data = {
            "task_id": "t4",
            "name": "t",
            "unknown_field": "should_be_ignored",
        }
        task = AnalysisTask.from_dict(data)
        assert task.task_id == "t4"
        assert not hasattr(task, "unknown_field")

    def test_roundtrip(self):
        original = AnalysisTask(
            task_id="rt_001",
            name="Roundtrip 测试",
            status=TaskStatus.FAILED,
            task_type=TaskType.TEST_GENERATION,
            total_lines=100,
            total_requests=50,
            error_message="测试错误",
            metadata={"errors": [1, 2, 3]},
        )
        d = original.to_dict()
        restored = AnalysisTask.from_dict(d)
        assert restored.task_id == original.task_id
        assert restored.status == original.status
        assert restored.total_lines == original.total_lines
        assert restored.error_message == original.error_message


class TestParsedRequestRecordModel:
    """ParsedRequestRecord 序列化测试"""

    def test_to_dict_json_fields(self):
        record = ParsedRequestRecord(
            task_id="t1",
            request_id="r1",
            method="POST",
            url="http://api/test",
            headers={"Content-Type": "application/json"},
            query_params={"page": "1"},
            metadata={"source": "log"},
        )
        d = record.to_dict()
        assert isinstance(d["headers"], str)
        assert isinstance(d["query_params"], str)
        assert isinstance(d["metadata"], str)

    def test_from_dict_json_fields(self):
        data = {
            "task_id": "t1",
            "request_id": "r1",
            "method": "GET",
            "url": "http://api/test",
            "headers": '{"Auth": "Bearer token"}',
            "query_params": '{"limit": 10}',
            "metadata": "{}",
        }
        record = ParsedRequestRecord.from_dict(data)
        assert isinstance(record.headers, dict)
        assert record.headers["Auth"] == "Bearer token"
        assert record.query_params["limit"] == 10


class TestAIInsightModel:
    """AIInsight 序列化测试"""

    def test_enum_serialization(self):
        insight = AIInsight(
            insight_id="ins_001",
            insight_type="performance",
            title="性能问题",
            severity=InsightSeverity.HIGH,
        )
        d = insight.to_dict()
        assert d["severity"] == "high"

    def test_from_dict_enum(self):
        data = {
            "insight_id": "ins_002",
            "insight_type": "coverage",
            "title": "覆盖率不足",
            "severity": "medium",
            "confidence": 0.85,
        }
        insight = AIInsight.from_dict(data)
        assert insight.severity == InsightSeverity.MEDIUM
        assert insight.confidence == 0.85


class TestProductionRequestModel:
    """ProductionRequest 序列化测试"""

    def test_enum_serialization(self):
        req = ProductionRequest(
            request_id="pr_001",
            method="GET",
            url="http://api/health",
            source=RequestSource.MANUAL,
        )
        d = req.to_dict()
        assert d["source"] == "manual"

    def test_from_dict(self):
        data = {
            "request_id": "pr_002",
            "method": "POST",
            "url": "http://api/data",
            "source": "log_parse",
            "is_enabled": 1,
            "consecutive_failures": 3,
        }
        req = ProductionRequest.from_dict(data)
        assert req.source == RequestSource.LOG_PARSE
        assert req.consecutive_failures == 3


class TestApiEndpointModel:
    """ApiEndpoint 序列化测试"""

    def test_json_fields(self):
        ep = ApiEndpoint(
            endpoint_id="ep_001",
            name="获取用户",
            method="GET",
            path="/api/users",
            parameters=[{"name": "id", "type": "string"}],
            responses={"200": {"description": "OK"}},
        )
        d = ep.to_dict()
        assert isinstance(d["parameters"], str)
        assert isinstance(d["responses"], str)

    def test_from_dict_json_fields(self):
        data = {
            "endpoint_id": "ep_002",
            "name": "创建用户",
            "method": "POST",
            "path": "/api/users",
            "parameters": '[{"name": "body", "in": "body"}]',
            "responses": '{"201": {"description": "Created"}}',
            "source_type": "swagger",
        }
        ep = ApiEndpoint.from_dict(data)
        assert isinstance(ep.parameters, list)
        assert isinstance(ep.responses, dict)
        assert ep.source_type == EndpointSourceType.SWAGGER


class TestKnowledgeEntryModel:
    """KnowledgeEntry 序列化测试"""

    def test_roundtrip(self):
        entry = KnowledgeEntry(
            knowledge_id="kb_001",
            type=KnowledgeType.BUSINESS_RULE,
            category="auth",
            title="认证规则",
            content="必须使用 Bearer Token",
            status=KnowledgeStatus.ACTIVE,
            source=KnowledgeSource.MANUAL,
            metadata={"author": "admin"},
        )
        d = entry.to_dict()
        restored = KnowledgeEntry.from_dict(d)
        assert restored.knowledge_id == entry.knowledge_id
        assert restored.type == entry.type
        assert restored.status == entry.status


class TestApiTagModel:
    """ApiTag 序列化测试"""

    def test_basic(self):
        tag = ApiTag(name="认证", description="认证相关接口")
        d = tag.to_dict()
        assert d["name"] == "认证"
        assert d["description"] == "认证相关接口"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
