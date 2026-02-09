# 该文件内容使用AI生成，注意识别准确性
"""
Repository 层测试 - AIInsightRepository
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from ai_test_tool.database.repository import (
    AIInsightRepository,
    ProductionRequestRepository,
    HealthCheckResultRepository,
    KnowledgeRepository
)
from ai_test_tool.database.models import (
    AIInsight,
    ProductionRequest,
    HealthCheckResult,
    KnowledgeEntry,
    KnowledgeType,
    KnowledgeStatus
)
from ai_test_tool.database.models.monitoring import InsightSeverity


class TestAIInsightRepository:
    """AI洞察仓库测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库管理器"""
        db = MagicMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """创建测试用仓库"""
        return AIInsightRepository(mock_db)

    def test_create_insight(self, repo, mock_db):
        """测试创建洞察"""
        mock_db.execute.return_value = 1

        insight = AIInsight(
            insight_id='ins_001',
            insight_type='performance',
            title='性能问题',
            description='响应时间过长',
            severity=InsightSeverity.HIGH
        )

        result = repo.create(insight)

        assert result == 1
        mock_db.execute.assert_called_once()

    def test_get_by_id(self, repo, mock_db):
        """测试根据ID获取洞察"""
        mock_db.fetch_one.return_value = {
            'id': 1,
            'insight_id': 'ins_001',
            'insight_type': 'performance',
            'title': '性能问题',
            'description': '响应时间过长',
            'severity': 'high',
            'confidence': 0.9,
            'details': None,
            'recommendations': None,
            'is_resolved': 0,
            'resolved_at': None,
            'created_at': '2024-01-01 12:00:00'
        }

        insight = repo.get_by_id('ins_001')

        assert insight is not None
        assert insight.insight_id == 'ins_001'
        assert insight.severity == InsightSeverity.HIGH

    def test_get_by_id_not_found(self, repo, mock_db):
        """测试获取不存在的洞察"""
        mock_db.fetch_one.return_value = None

        insight = repo.get_by_id('nonexistent')

        assert insight is None

    def test_resolve_insight(self, repo, mock_db):
        """测试解决洞察"""
        mock_db.execute.return_value = 1

        result = repo.resolve('ins_001')

        assert result == 1
        mock_db.execute.assert_called_once()
        # 检查SQL中是否设置了is_resolved = 1
        call_args = mock_db.execute.call_args
        assert 'is_resolved = 1' in call_args[0][0]

    def test_search_paginated(self, repo, mock_db):
        """测试分页搜索"""
        mock_db.fetch_one.return_value = {'count': 10}
        mock_db.fetch_all.return_value = [
            {
                'id': i,
                'insight_id': f'ins_{i:03d}',
                'insight_type': 'performance',
                'title': f'洞察 {i}',
                'description': None,
                'severity': 'medium',
                'confidence': 0.8,
                'details': None,
                'recommendations': None,
                'is_resolved': 0,
                'resolved_at': None,
                'created_at': '2024-01-01 12:00:00'
            }
            for i in range(5)
        ]

        insights, total = repo.search_paginated(page=1, page_size=5)

        assert total == 10
        assert len(insights) == 5
        mock_db.fetch_one.assert_called()
        mock_db.fetch_all.assert_called()

    def test_get_statistics(self, repo, mock_db):
        """测试获取统计"""
        mock_db.fetch_one.return_value = {
            'total': 100,
            'unresolved': 30,
            'high': 10,
            'medium': 15,
            'low': 5
        }
        mock_db.fetch_all.return_value = [
            {'insight_type': 'performance', 'count': 40},
            {'insight_type': 'coverage', 'count': 35},
            {'insight_type': 'risk', 'count': 25}
        ]

        stats = repo.get_statistics()

        assert stats['total'] == 100
        assert stats['unresolved'] == 30
        assert stats['by_severity']['high'] == 10
        assert len(stats['by_type']) == 3


class TestProductionRequestRepository:
    """生产请求仓库测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库"""
        db = MagicMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """创建测试用仓库"""
        return ProductionRequestRepository(mock_db)

    def test_get_enabled(self, repo, mock_db):
        """测试获取启用的请求"""
        mock_db.fetch_all.return_value = [
            {
                'id': 1,
                'request_id': 'req_001',
                'method': 'GET',
                'url': 'http://api/test',
                'headers': None,
                'body': None,
                'query_params': None,
                'expected_status_code': 200,
                'expected_response_pattern': None,
                'source': 'manual',
                'source_task_id': None,
                'tags': None,
                'is_enabled': 1,
                'last_check_at': None,
                'last_check_status': None,
                'consecutive_failures': 0,
                'created_at': '2024-01-01 12:00:00',
                'updated_at': None
            }
        ]

        requests = repo.get_enabled()

        assert len(requests) == 1
        assert requests[0].is_enabled

    def test_update_check_status_success(self, repo, mock_db):
        """测试更新成功状态"""
        mock_db.execute.return_value = 1

        result = repo.update_check_status('req_001', 'healthy')

        assert result == 1
        # 检查连续失败次数被重置
        call_args = mock_db.execute.call_args
        assert 'consecutive_failures = 0' in call_args[0][0]

    def test_update_check_status_failure(self, repo, mock_db):
        """测试更新失败状态"""
        mock_db.execute.return_value = 1

        result = repo.update_check_status('req_001', 'unhealthy', increment_failures=True)

        assert result == 1
        # 检查连续失败次数被增加
        call_args = mock_db.execute.call_args
        assert 'consecutive_failures + 1' in call_args[0][0]

    def test_get_statistics(self, repo, mock_db):
        """测试获取统计"""
        mock_db.fetch_one.return_value = {
            'total': 50,
            'enabled': 45,
            'healthy': 40,
            'unhealthy': 5,
            'critical': 2
        }

        stats = repo.get_statistics()

        assert stats['total'] == 50
        assert stats['enabled'] == 45
        assert stats['health_rate'] == 80.0  # 40/50 * 100


class TestKnowledgeRepository:
    """知识库仓库测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库"""
        db = MagicMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """创建测试用仓库"""
        return KnowledgeRepository(mock_db)

    def test_search_paginated_with_keyword(self, repo, mock_db):
        """测试关键词搜索"""
        mock_db.fetch_one.return_value = {'count': 5}
        # First fetch_all returns search results, subsequent calls return empty tags
        mock_db.fetch_all.side_effect = [
            [
                {
                    'id': 1,
                    'knowledge_id': 'kb_001',
                    'type': 'project_config',
                    'category': 'auth',
                    'title': '认证配置',
                    'content': 'Bearer Token认证',
                    'scope': '/api/*',
                    'priority': 10,
                    'status': 'active',
                    'source': 'manual',
                    'source_ref': '',
                    'metadata': '{}',
                    'created_by': '',
                    'version': 1,
                    'created_at': '2024-01-01 12:00:00',
                    'updated_at': None
                }
            ],
            [],  # tags for kb_001
        ]

        entries, total = repo.search_paginated(keyword='认证', page=1, page_size=10)

        assert total == 5
        # 验证关键词被包含在查询中（第一次 fetch_all 调用是搜索查询）
        search_call = mock_db.fetch_all.call_args_list[0]
        assert any('LIKE' in str(arg) for arg in search_call[0])

    def test_count_by_type(self, repo, mock_db):
        """测试按类型统计"""
        mock_db.fetch_all.return_value = [
            {'type': 'project_config', 'count': 20},
            {'type': 'business_rule', 'count': 15},
            {'type': 'module_context', 'count': 10}
        ]

        result = repo.count_by_type()

        assert result['project_config'] == 20
        assert result['business_rule'] == 15
        assert result['module_context'] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
