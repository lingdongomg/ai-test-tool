# 该文件内容使用AI生成，注意识别准确性
"""
Monitoring API 路由测试
"""

import pytest
from unittest.mock import MagicMock, patch
from unittest.mock import PropertyMock


def _make_model_mock(**fields):
    """创建带 to_dict() 方法的 Mock 对象，模拟 dataclass 模型"""
    m = MagicMock()
    for k, v in fields.items():
        setattr(m, k, v)
    m.to_dict.return_value = fields
    return m


class TestMonitorRequestsAPI:
    """监控请求列表 API 测试"""

    @pytest.fixture
    def mock_request_repo(self):
        """模拟 ProductionRequestRepository"""
        repo = MagicMock()
        repo.search_paginated.return_value = (
            [
                _make_model_mock(
                    request_id='req_001', method='GET', url='/api/health',
                    is_enabled=True, last_status='success',
                    tags=['health', 'critical'], created_at='2024-01-01 12:00:00'
                ),
                _make_model_mock(
                    request_id='req_002', method='POST', url='/api/login',
                    is_enabled=True, last_status='failed',
                    tags=['auth'], created_at='2024-01-02 12:00:00'
                )
            ],
            2
        )
        repo.get_statistics.return_value = {
            'total': 100,
            'enabled': 85,
            'by_status': {'success': 70, 'failed': 10, 'unknown': 5}
        }
        return repo

    def test_list_requests_returns_items(self, mock_request_repo):
        """测试列表返回请求条目"""
        from ai_test_tool.api.routes.monitoring import list_monitor_requests
        import asyncio

        result = asyncio.run(list_monitor_requests(
            tag=None, is_enabled=None, last_status=None,
            search=None, page=1, page_size=20,
            request_repo=mock_request_repo
        ))

        assert 'items' in result
        assert 'total' in result
        assert len(result['items']) == 2
        assert result['total'] == 2

    def test_list_requests_with_filters(self, mock_request_repo):
        """测试带过滤条件的请求列表"""
        mock_request_repo.search_paginated.return_value = (
            [_make_model_mock(request_id='req_001')],
            1
        )

        from ai_test_tool.api.routes.monitoring import list_monitor_requests
        import asyncio

        asyncio.run(list_monitor_requests(
            tag='health',
            is_enabled=True,
            last_status='success',
            search='/api',
            page=1,
            page_size=10,
            request_repo=mock_request_repo
        ))

        call_kwargs = mock_request_repo.search_paginated.call_args[1]
        assert call_kwargs['tag'] == 'health'
        assert call_kwargs['is_enabled'] is True
        assert call_kwargs['last_status'] == 'success'


class TestAddMonitorRequest:
    """添加监控请求 API 测试"""

    @pytest.fixture
    def mock_request_repo(self):
        """模拟 ProductionRequestRepository"""
        repo = MagicMock()
        repo.create.return_value = 1
        return repo

    def test_add_request_success(self, mock_request_repo):
        """测试成功添加监控请求"""
        from ai_test_tool.api.routes.monitoring import add_monitor_request, AddMonitorRequest
        import asyncio

        request = AddMonitorRequest(
            method='GET',
            url='/api/health',
            expected_status_code=200,
            tags=['health']
        )

        result = asyncio.run(add_monitor_request(request, mock_request_repo))

        assert result['success'] is True
        assert 'request_id' in result
        mock_request_repo.create.assert_called_once()

    def test_add_request_creates_production_request_model(self, mock_request_repo):
        """测试添加请求时构建了正确的 ProductionRequest 模型"""
        from ai_test_tool.api.routes.monitoring import add_monitor_request, AddMonitorRequest
        from ai_test_tool.database.models import ProductionRequest
        import asyncio

        request = AddMonitorRequest(
            method='POST',
            url='/api/login',
            headers={'Content-Type': 'application/json'},
            body='{"username": "test"}',
            query_params={'debug': 'true'},
            expected_status_code=200
        )

        asyncio.run(add_monitor_request(request, mock_request_repo))

        # create 的第一个参数是 ProductionRequest 实例
        call_args = mock_request_repo.create.call_args
        prod_request = call_args[0][0]
        assert isinstance(prod_request, ProductionRequest)
        assert prod_request.method == 'POST'
        assert prod_request.url == '/api/login'


class TestHealthCheckAPI:
    """健康检查 API 测试"""

    @pytest.fixture
    def mock_monitor_service(self):
        """模拟 ProductionMonitorService"""
        service = MagicMock()
        service.run_health_check.return_value = {
            'execution_id': 'exec_001',
            'total': 10,
            'healthy': 8,
            'unhealthy': 2,
            'health_rate': 80.0,
            'duration_ms': 1500,
            'status': 'completed',
            'results': []
        }
        return service

    @pytest.fixture
    def mock_execution_repo(self):
        """模拟 HealthCheckExecutionRepository"""
        repo = MagicMock()
        repo.search_paginated.return_value = (
            [
                _make_model_mock(
                    execution_id='exec_001', status='completed',
                    total_requests=10, success_count=8, failed_count=2,
                    started_at='2024-01-01 12:00:00',
                    completed_at='2024-01-01 12:05:00'
                )
            ],
            1
        )
        return repo

    @pytest.fixture
    def mock_result_repo(self):
        """模拟 HealthCheckResultRepository"""
        repo = MagicMock()
        repo.get_by_execution_with_request_details.return_value = [
            {
                'result_id': 'res_001',
                'request_id': 'req_001',
                'status': 'success',
                'response_time_ms': 150,
                'url': '/api/health'
            }
        ]
        repo.get_today_statistics.return_value = {
            'total': 100, 'success': 90, 'failed': 10, 'success_rate': 90.0
        }
        repo.get_trend.return_value = [
            {'date': '2024-01-01', 'total': 50, 'success': 45},
            {'date': '2024-01-02', 'total': 50, 'success': 48}
        ]
        return repo

    def test_run_health_check_success(self, mock_monitor_service):
        """测试成功执行健康检查"""
        from ai_test_tool.api.routes.monitoring import run_health_check, HealthCheckRequest
        from fastapi import BackgroundTasks
        import asyncio

        request = HealthCheckRequest(
            base_url='http://localhost:8000',
            use_ai_validation=True,
            timeout_seconds=30,
            parallel=5
        )

        background_tasks = BackgroundTasks()

        result = asyncio.run(run_health_check(request, background_tasks, mock_monitor_service))

        assert result['execution_id'] == 'exec_001'
        assert result['total'] == 10
        assert result['healthy'] == 8
        mock_monitor_service.run_health_check.assert_called_once()

    def test_run_health_check_with_filters(self, mock_monitor_service):
        """测试带过滤条件的健康检查"""
        from ai_test_tool.api.routes.monitoring import run_health_check, HealthCheckRequest
        from fastapi import BackgroundTasks
        import asyncio

        request = HealthCheckRequest(
            base_url='http://localhost:8000',
            request_ids=['req_001', 'req_002'],
            tag_filter='critical'
        )

        background_tasks = BackgroundTasks()

        asyncio.run(run_health_check(request, background_tasks, mock_monitor_service))

        call_kwargs = mock_monitor_service.run_health_check.call_args[1]
        assert call_kwargs['request_ids'] == ['req_001', 'req_002']
        assert call_kwargs['tag_filter'] == 'critical'

    def test_list_health_check_executions(self, mock_execution_repo):
        """测试获取执行历史列表"""
        from ai_test_tool.api.routes.monitoring import list_health_check_executions
        import asyncio

        result = asyncio.run(list_health_check_executions(
            status=None, trigger_type=None, page=1, page_size=20,
            execution_repo=mock_execution_repo
        ))

        assert 'items' in result
        assert 'total' in result
        assert len(result['items']) == 1

    def test_get_health_check_execution_detail(self, mock_execution_repo, mock_result_repo):
        """测试获取执行详情"""
        mock_execution_repo.get_by_id.return_value = _make_model_mock(
            execution_id='exec_001', status='completed'
        )

        from ai_test_tool.api.routes.monitoring import get_health_check_execution
        import asyncio

        result = asyncio.run(get_health_check_execution(
            'exec_001',
            execution_repo=mock_execution_repo,
            result_repo=mock_result_repo
        ))

        assert result['execution']['execution_id'] == 'exec_001'
        assert 'results' in result

    def test_get_health_check_execution_not_found(self, mock_execution_repo, mock_result_repo):
        """测试执行不存在时的处理"""
        mock_execution_repo.get_by_id.return_value = None

        from ai_test_tool.api.routes.monitoring import get_health_check_execution
        from fastapi import HTTPException
        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_health_check_execution(
                'exec_not_exist',
                execution_repo=mock_execution_repo,
                result_repo=mock_result_repo
            ))
        assert exc_info.value.status_code == 404


class TestMonitorStatistics:
    """监控统计 API 测试"""

    @pytest.fixture
    def mock_request_repo(self):
        """模拟 ProductionRequestRepository"""
        repo = MagicMock()
        repo.get_statistics.return_value = {
            'total': 100,
            'enabled': 85,
            'by_status': {
                'success': 70,
                'failed': 10,
                'unknown': 5
            }
        }
        return repo

    @pytest.fixture
    def mock_result_repo(self):
        """模拟 HealthCheckResultRepository"""
        repo = MagicMock()
        repo.get_today_statistics.return_value = {
            'total_checks': 500,
            'success': 450,
            'failed': 50,
            'success_rate': 90.0,
            'avg_response_time': 200.5
        }
        repo.get_trend.return_value = [
            {'date': '2024-01-01', 'total': 100, 'success': 90, 'avg_time': 180.0},
            {'date': '2024-01-02', 'total': 100, 'success': 95, 'avg_time': 150.0}
        ]
        return repo

    def test_get_monitoring_statistics(self, mock_request_repo, mock_result_repo):
        """测试获取监控统计"""
        from ai_test_tool.api.routes.monitoring import get_monitoring_statistics
        import asyncio

        result = asyncio.run(get_monitoring_statistics(mock_request_repo, mock_result_repo))

        assert 'requests' in result
        assert 'today' in result
        assert 'trend' in result
        assert result['requests']['total'] == 100


class TestToggleMonitorRequest:
    """切换监控状态 API 测试"""

    @pytest.fixture
    def mock_request_repo(self):
        """模拟 ProductionRequestRepository"""
        repo = MagicMock()
        repo.set_enabled.return_value = 1
        return repo

    def test_toggle_enable_success(self, mock_request_repo):
        """测试成功切换启用状态"""
        from ai_test_tool.api.routes.monitoring import toggle_monitor_request
        import asyncio

        result = asyncio.run(toggle_monitor_request(
            'req_001',
            is_enabled=False,
            request_repo=mock_request_repo
        ))

        assert result['success'] is True
        assert result['is_enabled'] is False
        mock_request_repo.set_enabled.assert_called_once_with('req_001', False)

    def test_toggle_not_found(self, mock_request_repo):
        """测试请求不存在时的处理"""
        mock_request_repo.set_enabled.return_value = 0

        from ai_test_tool.api.routes.monitoring import toggle_monitor_request
        from ai_test_tool.exceptions import NotFoundError
        import asyncio

        with pytest.raises(NotFoundError):
            asyncio.run(toggle_monitor_request(
                'req_not_exist',
                is_enabled=True,
                request_repo=mock_request_repo
            ))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
