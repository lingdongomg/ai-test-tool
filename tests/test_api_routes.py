"""
API 路由集成测试 - 关键端点验证
验证路由注册、依赖注入、请求/响应格式
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db():
    """模拟数据库管理器"""
    db = MagicMock()
    db.fetch_one.return_value = None
    db.fetch_all.return_value = []
    db.execute.return_value = 1
    return db


@pytest.fixture
def mock_repos(mock_db):
    """模拟所有 Repository"""
    repos = {}
    repo_names = [
        "task_repository", "request_repository", "report_repository",
        "test_case_repository", "test_result_repository",
        "api_endpoint_repository", "api_tag_repository",
        "ai_insight_repository", "production_request_repository",
        "health_check_execution_repository", "health_check_result_repository",
    ]
    for name in repo_names:
        repos[name] = MagicMock()
    return repos


class TestDashboardEndpoints:
    """Dashboard 端点测试"""

    def test_quick_actions_no_db(self):
        """quick-actions 不需要数据库"""
        with patch("ai_test_tool.api.dependencies.get_database") as mock_get_db:
            mock_get_db.return_value = MagicMock()
            from ai_test_tool.api.routes.dashboard import get_quick_actions
            import asyncio

            result = asyncio.run(get_quick_actions())
            assert "actions" in result
            assert len(result["actions"]) > 0
            for action in result["actions"]:
                assert "id" in action
                assert "title" in action
                assert "route" in action

    def test_stats_keys(self, mock_db):
        """验证 stats 返回所有必要 key"""
        # 为 stats 查询提供完整数据
        mock_db.fetch_one.return_value = {
            "endpoint_total": 0, "endpoint_methods": 0,
            "total_cases": 0, "enabled_cases": 0,
            "covered_endpoints": 0,
            "total_monitors": 0, "enabled_monitors": 0,
            "healthy_monitors": 0, "unhealthy_monitors": 0,
            "critical_monitors": 0,
            "total_insights": 0, "unresolved_insights": 0,
            "high_priority_insights": 0,
            "total_reports": 0, "total_anomalies": 0, "critical_count": 0,
        }

        from ai_test_tool.api.routes.dashboard import get_dashboard_stats
        import asyncio

        result = asyncio.run(get_dashboard_stats(mock_db))
        expected_keys = {"endpoints", "test_coverage", "health_status", "recent_anomalies", "ai_insights"}
        assert expected_keys == set(result.keys())


class TestInsightsEndpoints:
    """Insights 端点测试"""

    def test_list_tasks_empty(self, mock_db):
        """空任务列表返回正确结构"""
        mock_db.fetch_one.return_value = {"count": 0}
        mock_db.fetch_all.return_value = []

        from ai_test_tool.api.routes.insights import list_analysis_tasks
        import asyncio

        result = asyncio.run(list_analysis_tasks(page=1, page_size=20, db=mock_db))
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["items"] == []

    def test_get_task_not_found(self, mock_db):
        """不存在的任务返回 404"""
        mock_task_repo = MagicMock()
        mock_task_repo.get_by_id.return_value = None
        mock_report_repo = MagicMock()

        from ai_test_tool.api.routes.insights import get_analysis_task
        from fastapi import HTTPException
        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_analysis_task(
                task_id="nonexistent",
                task_repo=mock_task_repo,
                report_repo=mock_report_repo,
            ))
        assert exc_info.value.status_code == 404

    def test_statistics_structure(self, mock_db):
        """统计端点返回正确结构"""
        mock_db.fetch_one.side_effect = [
            {"total": 10, "completed": 8, "running": 1, "failed": 1},
            {"total_reports": 5, "total_anomalies": 20, "critical_count": 3, "error_count": 7},
            {"tasks_today": 2, "anomalies_today": 5},
        ]

        from ai_test_tool.api.routes.insights import get_insights_statistics
        import asyncio

        result = asyncio.run(get_insights_statistics(db=mock_db))
        assert "tasks" in result
        assert "reports" in result
        assert "today" in result


class TestDevelopmentEndpoints:
    """Development 端点测试"""

    def test_list_endpoints_empty(self, mock_db):
        """空接口列表"""
        mock_db.fetch_one.return_value = {"count": 0}
        mock_db.fetch_all.return_value = []

        from ai_test_tool.api.routes.development.endpoints import list_endpoints
        import asyncio

        result = asyncio.run(list_endpoints(db=mock_db, page=1, page_size=20))
        assert result["total"] == 0
        assert result["items"] == []

    def test_endpoint_not_found(self, mock_db):
        """不存在的接口返回 404"""
        mock_db.fetch_one.return_value = None

        from ai_test_tool.api.routes.development.endpoints import get_endpoint_detail
        from fastapi import HTTPException
        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_endpoint_detail(endpoint_id="nonexistent", db=mock_db))
        assert exc_info.value.status_code == 404

    def test_statistics_structure(self, mock_db):
        """统计端点返回正确结构"""
        mock_db.fetch_one.side_effect = [
            {"total": 5, "methods_count": 3},
            {"total": 20, "enabled": 18, "ai_generated": 15},
            {"cnt": 5},
            {"cnt": 3},
            {"total_executions": 100, "passed": 90, "failed": 10},
        ]

        from ai_test_tool.api.routes.development.executions import get_development_statistics
        import asyncio

        result = asyncio.run(get_development_statistics(db=mock_db))
        assert "endpoints" in result
        assert "test_cases" in result
        assert "coverage" in result
        assert "recent_executions" in result

    def test_delete_test_case_not_found(self, mock_db):
        """删除不存在的测试用例返回 404"""
        mock_db.fetch_one.return_value = None

        from ai_test_tool.api.routes.development.test_cases import delete_test_case
        from fastapi import HTTPException
        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(delete_test_case(test_case_id="nonexistent", db=mock_db))
        assert exc_info.value.status_code == 404


class TestImportsEndpoints:
    """Imports 端点测试"""

    def test_supported_formats(self):
        """支持格式端点不需要数据库"""
        from ai_test_tool.api.routes.imports import get_supported_formats
        import asyncio

        result = asyncio.run(get_supported_formats())
        assert "formats" in result
        assert "update_strategies" in result
        assert len(result["formats"]) >= 2
        format_types = {f["type"] for f in result["formats"]}
        assert "swagger" in format_types
        assert "postman" in format_types


class TestMonitoringEndpoints:
    """Monitoring 端点测试（已是参考实现，验证结构）"""

    def test_environments_endpoint(self):
        """环境列表端点"""
        from ai_test_tool.api.routes.development.executions import list_environments
        import asyncio

        result = asyncio.run(list_environments())
        assert "environments" in result
        env_names = {e["name"] for e in result["environments"]}
        assert "local" in env_names


class TestRouteUtilFunctions:
    """routes/__init__.py 工具函数测试"""

    def test_paginate(self, mock_db):
        """测试通用分页查询"""
        mock_db.fetch_one.return_value = {"count": 50}
        mock_db.fetch_all.return_value = [
            {"id": 1, "name": "item1", "created_at": "2024-01-01"},
        ]

        from ai_test_tool.api.routes import paginate
        result = paginate(
            db=mock_db,
            table="analysis_tasks",
            page=1,
            page_size=10,
        )
        assert result["total"] == 50
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert len(result["items"]) == 1

    def test_build_conditions_empty(self):
        """空过滤条件"""
        from ai_test_tool.api.routes import build_conditions
        conditions, params = build_conditions({})
        assert conditions == []
        assert params == []

    def test_build_conditions_with_search(self):
        """带搜索条件的过滤"""
        from ai_test_tool.api.routes import build_conditions
        conditions, params = build_conditions(
            {"status": "active", "name_search": "test"},
            field_mapping={"status": "t.status"}
        )
        assert len(conditions) == 2
        assert len(params) == 2

    def test_parse_json_fields(self):
        """JSON 字段解析"""
        from ai_test_tool.api.routes import parse_json_fields
        data = {
            "name": "test",
            "metadata": '{"key": "value"}',
            "tags": "not_json_field",
        }
        result = parse_json_fields(data, ["metadata"])
        assert isinstance(result["metadata"], dict)
        assert result["metadata"]["key"] == "value"
        assert result["tags"] == "not_json_field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
