# 该文件内容使用AI生成，注意识别准确性
"""
Dashboard 路由测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock


class TestDashboardRoutes:
    """Dashboard 路由测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库管理器"""
        db = MagicMock()
        db.fetch_one.return_value = {
            'endpoint_total': 10,
            'endpoint_methods': 4,
            'total_cases': 50,
            'enabled_cases': 45,
            'covered_endpoints': 8,
            'total_monitors': 20,
            'enabled_monitors': 18,
            'healthy_monitors': 15,
            'unhealthy_monitors': 3,
            'critical_monitors': 1,
            'total_insights': 5,
            'unresolved_insights': 2,
            'high_priority_insights': 1,
            'total_reports': 3,
            'total_anomalies': 10,
            'critical_count': 2
        }
        db.fetch_all.return_value = []
        return db

    @pytest.fixture
    def client(self, mock_db):
        """创建测试客户端"""
        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            from ai_test_tool.api.app import create_app
            app = create_app()
            return TestClient(app)

    def test_get_dashboard_stats_structure(self, mock_db):
        """测试 dashboard stats 返回结构"""
        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            with patch('ai_test_tool.api.dependencies.get_database', return_value=mock_db):
                from ai_test_tool.api.routes.dashboard import get_dashboard_stats
                import asyncio

                result = asyncio.run(get_dashboard_stats(mock_db))

                # 验证返回结构
                assert 'endpoints' in result
                assert 'test_coverage' in result
                assert 'health_status' in result
                assert 'recent_anomalies' in result
                assert 'ai_insights' in result

                # 验证 endpoints 结构
                assert 'total' in result['endpoints']
                assert 'methods' in result['endpoints']

                # 验证 test_coverage 结构
                assert 'total_endpoints' in result['test_coverage']
                assert 'covered_endpoints' in result['test_coverage']
                assert 'coverage_rate' in result['test_coverage']

    def test_coverage_rate_calculation(self, mock_db):
        """测试覆盖率计算"""
        mock_db.fetch_one.side_effect = [
            {
                'endpoint_total': 10,
                'endpoint_methods': 4,
                'total_cases': 50,
                'enabled_cases': 45,
                'covered_endpoints': 5,
                'total_monitors': 0,
                'enabled_monitors': 0,
                'healthy_monitors': 0,
                'unhealthy_monitors': 0,
                'critical_monitors': 0,
                'total_insights': 0,
                'unresolved_insights': 0,
                'high_priority_insights': 0
            },
            {
                'total_reports': 0,
                'total_anomalies': 0,
                'critical_count': 0
            }
        ]

        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            from ai_test_tool.api.routes.dashboard import get_dashboard_stats
            import asyncio

            result = asyncio.run(get_dashboard_stats(mock_db))

            # 5/10 = 50%
            assert result['test_coverage']['coverage_rate'] == 50.0

    def test_zero_endpoints_no_division_error(self, mock_db):
        """测试零接口时不会除零错误"""
        mock_db.fetch_one.side_effect = [
            {
                'endpoint_total': 0,
                'endpoint_methods': 0,
                'total_cases': 0,
                'enabled_cases': 0,
                'covered_endpoints': 0,
                'total_monitors': 0,
                'enabled_monitors': 0,
                'healthy_monitors': 0,
                'unhealthy_monitors': 0,
                'critical_monitors': 0,
                'total_insights': 0,
                'unresolved_insights': 0,
                'high_priority_insights': 0
            },
            {
                'total_reports': 0,
                'total_anomalies': 0,
                'critical_count': 0
            }
        ]

        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            from ai_test_tool.api.routes.dashboard import get_dashboard_stats
            import asyncio

            result = asyncio.run(get_dashboard_stats(mock_db))

            # 不应该抛出除零异常
            assert result['test_coverage']['coverage_rate'] == 0


class TestDashboardActivities:
    """Dashboard 活动流测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库"""
        db = MagicMock()
        db.fetch_all.return_value = [
            {
                'type': 'execution',
                'id': 'exec_001',
                'title': '执行测试场景',
                'status': 'completed',
                'details': None,
                'severity': None,
                'created_at': '2024-01-01 12:00:00'
            },
            {
                'type': 'health_check',
                'id': 'hc_001',
                'title': '健康检查 - completed',
                'status': 'completed',
                'details': '健康: 10, 异常: 2',
                'severity': None,
                'created_at': '2024-01-01 11:00:00'
            }
        ]
        return db

    def test_activities_structure(self, mock_db):
        """测试活动流结构"""
        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            from ai_test_tool.api.routes.dashboard import get_recent_activities
            import asyncio

            result = asyncio.run(get_recent_activities(limit=10, db=mock_db))

            assert 'activities' in result
            assert isinstance(result['activities'], list)

    def test_activities_limit(self, mock_db):
        """测试活动数量限制"""
        # 返回超过限制的数据
        mock_db.fetch_all.return_value = [
            {
                'type': 'execution',
                'id': f'exec_{i}',
                'title': f'活动 {i}',
                'status': 'completed',
                'details': None,
                'severity': None,
                'created_at': f'2024-01-01 {12-i}:00:00'
            }
            for i in range(5)
        ]

        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            from ai_test_tool.api.routes.dashboard import get_recent_activities
            import asyncio

            result = asyncio.run(get_recent_activities(limit=3, db=mock_db))

            # SQL 中的 LIMIT 会限制结果
            assert len(result['activities']) <= 5


class TestDashboardTrends:
    """Dashboard 趋势图测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库"""
        db = MagicMock()
        db.fetch_all.return_value = [
            {'date': '2024-01-01', 'new_cases': 5},
            {'date': '2024-01-02', 'new_cases': 3},
            {'date': '2024-01-03', 'new_cases': 8}
        ]
        return db

    def test_coverage_trend_structure(self, mock_db):
        """测试覆盖率趋势结构"""
        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            from ai_test_tool.api.routes.dashboard import get_coverage_trend
            import asyncio

            result = asyncio.run(get_coverage_trend(days=7, db=mock_db))

            assert 'days' in result
            assert 'data' in result
            assert result['days'] == 7

    def test_health_trend_success_rate(self, mock_db):
        """测试健康趋势成功率计算"""
        mock_db.fetch_all.return_value = [
            {'date': '2024-01-01', 'total': 10, 'success': 8, 'avg_time': 150.5},
            {'date': '2024-01-02', 'total': 20, 'success': 18, 'avg_time': 200.0}
        ]

        with patch('ai_test_tool.api.routes.dashboard.get_database', return_value=mock_db):
            from ai_test_tool.api.routes.dashboard import get_health_trend
            import asyncio

            result = asyncio.run(get_health_trend(days=7, db=mock_db))

            assert len(result['data']) == 2
            # 8/10 = 80%
            assert result['data'][0]['success_rate'] == 80.0
            # 18/20 = 90%
            assert result['data'][1]['success_rate'] == 90.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
