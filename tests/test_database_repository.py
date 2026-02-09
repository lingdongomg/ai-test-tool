"""
数据库 Repository CRUD 测试 - 核心仓库
测试 TaskRepository, TestCaseRepository, ReportRepository 等
"""

import json
import pytest
from unittest.mock import MagicMock
from datetime import datetime

from ai_test_tool.database.repository import (
    TaskRepository,
    RequestRepository,
    TestCaseRepository,
    TestResultRepository,
    ReportRepository,
    ApiEndpointRepository,
    ApiTagRepository,
)
from ai_test_tool.database.models import (
    AnalysisTask, ParsedRequestRecord, AnalysisReport,
    TestCaseRecord, TestResultRecord, ApiEndpoint, ApiTag,
    TaskStatus, TaskType, ReportType,
    TestCaseCategory, TestCasePriority, TestResultStatus,
    EndpointSourceType,
)


class TestTaskRepository:
    """任务仓库 CRUD 测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        return TaskRepository(mock_db)

    def test_create(self, repo, mock_db):
        mock_db.execute.return_value = 1
        task = AnalysisTask(
            task_id="t_001",
            name="测试任务",
            status=TaskStatus.PENDING,
            task_type=TaskType.LOG_ANALYSIS,
        )
        result = repo.create(task)
        assert result == 1
        mock_db.execute.assert_called_once()

    def test_get_by_id_found(self, repo, mock_db):
        mock_db.fetch_one.return_value = {
            "id": 1,
            "task_id": "t_001",
            "name": "测试任务",
            "description": "",
            "task_type": "log_analysis",
            "log_file_path": "",
            "log_file_size": 0,
            "status": "pending",
            "total_lines": 0,
            "processed_lines": 0,
            "total_requests": 0,
            "total_test_cases": 0,
            "error_message": "",
            "metadata": "{}",
            "started_at": None,
            "completed_at": None,
            "created_at": "2024-01-01 12:00:00",
            "updated_at": None,
        }
        task = repo.get_by_id("t_001")
        assert task is not None
        assert task.task_id == "t_001"
        assert task.status == TaskStatus.PENDING

    def test_get_by_id_not_found(self, repo, mock_db):
        mock_db.fetch_one.return_value = None
        task = repo.get_by_id("nonexistent")
        assert task is None

    def test_update_status_running(self, repo, mock_db):
        mock_db.execute.return_value = 1
        repo.update_status("t_001", TaskStatus.RUNNING)
        call_args = mock_db.execute.call_args[0][0]
        assert "status" in call_args
        assert "started_at" in call_args

    def test_update_status_completed(self, repo, mock_db):
        mock_db.execute.return_value = 1
        repo.update_status("t_001", TaskStatus.COMPLETED)
        call_args = mock_db.execute.call_args[0][0]
        assert "completed_at" in call_args

    def test_update_status_failed_with_error(self, repo, mock_db):
        mock_db.execute.return_value = 1
        repo.update_status("t_001", TaskStatus.FAILED, error_message="boom")
        call_args = mock_db.execute.call_args
        assert "error_message" in call_args[0][0]
        assert "boom" in call_args[0][1]

    def test_update_counts(self, repo, mock_db):
        mock_db.execute.return_value = 1
        repo.update_counts("t_001", total_requests=10, total_test_cases=5)
        call_args = mock_db.execute.call_args[0][0]
        assert "total_requests" in call_args
        assert "total_test_cases" in call_args

    def test_update_progress(self, repo, mock_db):
        mock_db.execute.return_value = 1
        repo.update_progress("t_001", processed_lines=50, total_requests=25)
        call_args = mock_db.execute.call_args[0][0]
        assert "processed_lines" in call_args
        assert "total_requests" in call_args

    def test_delete(self, repo, mock_db):
        mock_db.execute.return_value = 1
        result = repo.delete("t_001")
        assert result == 1


class TestRequestRepository:
    """请求仓库测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        return RequestRepository(mock_db)

    def test_create(self, repo, mock_db):
        mock_db.execute.return_value = 1
        record = ParsedRequestRecord(
            task_id="t1",
            request_id="r1",
            method="GET",
            url="http://api/test",
        )
        result = repo.create(record)
        assert result == 1

    def test_create_batch(self, repo, mock_db):
        mock_db.execute_many.return_value = 3
        records = [
            ParsedRequestRecord(task_id="t1", request_id=f"r{i}", method="GET", url=f"http://api/{i}")
            for i in range(3)
        ]
        result = repo.create_batch(records)
        mock_db.execute_many.assert_called_once()

    def test_count_by_task(self, repo, mock_db):
        mock_db.fetch_one.return_value = {"count": 42}
        count = repo.count_by_task("t1")
        assert count == 42


class TestTestCaseRepository:
    """测试用例仓库测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        return TestCaseRepository(mock_db)

    def test_get_by_id(self, repo, mock_db):
        mock_db.fetch_one.return_value = {
            "id": 1,
            "case_id": "tc_001",
            "endpoint_id": "ep_001",
            "name": "测试登录",
            "description": "",
            "category": "normal",
            "priority": "high",
            "method": "POST",
            "url": "http://api/login",
            "headers": "{}",
            "body": None,
            "query_params": "{}",
            "expected_status_code": 200,
            "expected_response": None,
            "assertions": None,
            "max_response_time_ms": 3000,
            "tags": None,
            "is_enabled": 1,
            "is_ai_generated": 0,
            "version": 1,
            "created_at": "2024-01-01",
            "updated_at": None,
        }
        tc = repo.get_by_id("tc_001")
        assert tc is not None
        assert tc.case_id == "tc_001"
        assert tc.category == TestCaseCategory.NORMAL
        assert tc.priority == TestCasePriority.HIGH

    def test_update(self, repo, mock_db):
        mock_db.execute.return_value = 1
        result = repo.update("tc_001", {"name": "新名称", "priority": "low"})
        assert result == 1

    def test_set_enabled(self, repo, mock_db):
        mock_db.execute.return_value = 1
        result = repo.set_enabled("tc_001", False)
        assert result == 1

    def test_delete(self, repo, mock_db):
        mock_db.execute.return_value = 1
        result = repo.delete("tc_001")
        assert result == 1


class TestReportRepository:
    """报告仓库测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        return ReportRepository(mock_db)

    def test_get_by_task(self, repo, mock_db):
        mock_db.fetch_all.return_value = [
            {
                "id": 1,
                "task_id": "t1",
                "title": "报告1",
                "content": "内容",
                "report_type": "anomaly",
                "format": "markdown",
                "statistics": "{}",
                "file_path": None,
                "created_at": "2024-01-01",
            }
        ]
        reports = repo.get_by_task("t1")
        assert len(reports) == 1
        assert reports[0].task_id == "t1"


class TestApiEndpointRepository:
    """接口端点仓库测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        return ApiEndpointRepository(mock_db)

    def test_get_by_id(self, repo, mock_db):
        mock_db.fetch_one.return_value = {
            "id": 1,
            "endpoint_id": "ep_001",
            "name": "获取用户",
            "description": "",
            "method": "GET",
            "path": "/api/users",
            "summary": "",
            "parameters": None,
            "request_body": None,
            "responses": None,
            "source_type": "swagger",
            "source_file": "api.json",
            "is_deprecated": 0,
            "created_at": "2024-01-01",
            "updated_at": None,
        }
        ep = repo.get_by_id("ep_001")
        assert ep is not None
        assert ep.endpoint_id == "ep_001"
        assert ep.source_type == EndpointSourceType.SWAGGER

    def test_get_by_method_path(self, repo, mock_db):
        mock_db.fetch_one.return_value = {
            "id": 1,
            "endpoint_id": "ep_001",
            "name": "获取用户",
            "description": "",
            "method": "GET",
            "path": "/api/users",
            "summary": "",
            "parameters": None,
            "request_body": None,
            "responses": None,
            "source_type": "manual",
            "source_file": None,
            "is_deprecated": 0,
            "created_at": "2024-01-01",
            "updated_at": None,
        }
        ep = repo.get_by_method_path("GET", "/api/users")
        assert ep is not None

    def test_update(self, repo, mock_db):
        mock_db.execute.return_value = 1
        result = repo.update("ep_001", {"name": "新名称"})
        assert result == 1

    def test_delete(self, repo, mock_db):
        mock_db.execute.return_value = 1
        result = repo.delete("ep_001")
        assert result == 1


class TestApiTagRepository:
    """接口标签仓库测试"""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        return ApiTagRepository(mock_db)

    def test_get_by_name(self, repo, mock_db):
        mock_db.fetch_one.return_value = {
            "id": 1,
            "name": "认证",
            "description": "认证接口",
            "color": None,
            "parent_id": None,
            "sort_order": 0,
            "is_system": 0,
            "created_at": "2024-01-01",
        }
        tag = repo.get_by_name("认证")
        assert tag is not None
        assert tag.name == "认证"


class TestBaseRepositoryInheritance:
    """验证所有 Repository 可正常实例化"""

    def test_all_repositories_instantiate(self):
        """验证所有25个 Repository 都能通过兼容层导入和实例化"""
        from ai_test_tool.database.repository import (
            TaskRepository, RequestRepository, ReportRepository,
            TestCaseRepository, TestCaseHistoryRepository,
            TestResultRepository, TestExecutionRepository,
            ExecutionCaseRepository,
            ApiTagRepository, ApiEndpointRepository,
            TestScenarioRepository, ScenarioStepRepository,
            ScenarioExecutionRepository, StepResultRepository,
            KnowledgeRepository, KnowledgeHistoryRepository,
            KnowledgeUsageRepository,
            AIInsightRepository, ProductionRequestRepository,
            HealthCheckExecutionRepository, HealthCheckResultRepository,
            ChatSessionRepository, ChatMessageRepository,
            SystemConfigRepository,
        )

        mock_db = MagicMock()
        repos = [
            TaskRepository(mock_db),
            RequestRepository(mock_db),
            ReportRepository(mock_db),
            TestCaseRepository(mock_db),
            TestCaseHistoryRepository(mock_db),
            TestResultRepository(mock_db),
            TestExecutionRepository(mock_db),
            ExecutionCaseRepository(mock_db),
            ApiTagRepository(mock_db),
            ApiEndpointRepository(mock_db),
            TestScenarioRepository(mock_db),
            ScenarioStepRepository(mock_db),
            ScenarioExecutionRepository(mock_db),
            StepResultRepository(mock_db),
            KnowledgeRepository(mock_db),
            KnowledgeHistoryRepository(mock_db),
            KnowledgeUsageRepository(mock_db),
            AIInsightRepository(mock_db),
            ProductionRequestRepository(mock_db),
            HealthCheckExecutionRepository(mock_db),
            HealthCheckResultRepository(mock_db),
            ChatSessionRepository(mock_db),
            ChatMessageRepository(mock_db),
            SystemConfigRepository(mock_db),
        ]

        assert len(repos) == 24
        for repo in repos:
            assert repo.table_name, f"{type(repo).__name__} missing table_name"
            assert repo.db is mock_db


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
