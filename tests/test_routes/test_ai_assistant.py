# 该文件内容使用AI生成，注意识别准确性
"""
AI Assistant API 路由测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestChatAPI:
    """AI 对话 API 测试"""

    @pytest.fixture
    def mock_service(self):
        """模拟 AIAssistantService"""
        service = MagicMock()
        service.ask_question.return_value = "这是AI的回答"
        return service

    def test_chat_success(self, mock_service):
        """测试成功对话"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            from ai_test_tool.api.routes.ai_assistant import chat_with_ai, ChatRequest
            import asyncio

            request = ChatRequest(
                message="测试问题",
                context={"endpoint": "/api/test"},
                session_id="session_001"
            )

            result = asyncio.run(chat_with_ai(request, mock_service))

            assert result['success'] is True
            assert result['message'] == "测试问题"
            assert result['answer'] == "这是AI的回答"
            assert result['session_id'] == "session_001"

    def test_chat_without_context(self, mock_service):
        """测试无上下文对话"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            from ai_test_tool.api.routes.ai_assistant import chat_with_ai, ChatRequest
            import asyncio

            request = ChatRequest(message="简单问题")

            result = asyncio.run(chat_with_ai(request, mock_service))

            assert result['success'] is True
            # 验证 context 被设为空字典
            call_kwargs = mock_service.ask_question.call_args[1]
            assert call_kwargs['context'] == {}

    def test_chat_error_handling(self, mock_service):
        """测试对话错误处理"""
        mock_service.ask_question.side_effect = Exception("LLM服务不可用")

        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            from ai_test_tool.api.routes.ai_assistant import chat_with_ai, ChatRequest
            from ai_test_tool.exceptions import LLMError
            import asyncio

            request = ChatRequest(message="测试问题")

            with pytest.raises(LLMError):
                asyncio.run(chat_with_ai(request, mock_service))


class TestInsightAPI:
    """AI 洞察 API 测试"""

    @pytest.fixture
    def mock_repository(self):
        """模拟 AIInsightRepository"""
        repo = MagicMock()
        repo.search_paginated.return_value = (
            [
                {
                    'insight_id': 'ins_001',
                    'type': 'anomaly',
                    'severity': 'high',
                    'title': '异常洞察1',
                    'description': '描述内容',
                    'is_resolved': False,
                    'created_at': '2024-01-01 12:00:00'
                }
            ],
            1
        )
        repo.get_statistics.return_value = {
            'total': 50,
            'unresolved': 10,
            'by_type': {'anomaly': 30, 'suggestion': 20},
            'by_severity': {'high': 5, 'medium': 25, 'low': 20}
        }
        return repo

    def test_list_insights(self, mock_repository):
        """测试获取洞察列表"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_insight_repository', return_value=mock_repository):
            from ai_test_tool.api.routes.ai_assistant import list_insights
            import asyncio

            result = asyncio.run(list_insights(
                type=None, severity=None, is_resolved=None,
                page=1, page_size=20, repo=mock_repository
            ))

            assert 'items' in result
            assert 'total' in result
            assert len(result['items']) == 1

    def test_list_insights_with_filters(self, mock_repository):
        """测试带过滤条件的洞察列表"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_insight_repository', return_value=mock_repository):
            from ai_test_tool.api.routes.ai_assistant import list_insights
            import asyncio

            asyncio.run(list_insights(
                type='anomaly',
                severity='high',
                is_resolved=False,
                page=1,
                page_size=10,
                repo=mock_repository
            ))

            call_kwargs = mock_repository.search_paginated.call_args[1]
            assert call_kwargs['type'] == 'anomaly'
            assert call_kwargs['severity'] == 'high'
            assert call_kwargs['is_resolved'] is False

    def test_get_insight_statistics(self, mock_repository):
        """测试获取洞察统计"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_insight_repository', return_value=mock_repository):
            from ai_test_tool.api.routes.ai_assistant import get_insight_statistics
            import asyncio

            result = asyncio.run(get_insight_statistics(mock_repository))

            assert result['total'] == 50
            assert result['unresolved'] == 10
            assert 'by_type' in result
            assert 'by_severity' in result


class TestMockDataGeneration:
    """Mock 数据生成 API 测试"""

    @pytest.fixture
    def mock_service(self):
        """模拟 AIAssistantService"""
        service = MagicMock()
        service.generate_mock_data.return_value = [
            {"id": 1, "name": "测试数据1"},
            {"id": 2, "name": "测试数据2"}
        ]
        return service

    @pytest.fixture
    def mock_db(self):
        """模拟数据库"""
        db = MagicMock()
        db.fetch_one.return_value = {
            'endpoint_id': 'ep_001',
            'name': '测试接口',
            'method': 'POST',
            'path': '/api/test'
        }
        return db

    def test_generate_mock_data_success(self, mock_service, mock_db):
        """测试成功生成 Mock 数据"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            with patch('ai_test_tool.api.routes.ai_assistant.get_database', return_value=mock_db):
                from ai_test_tool.api.routes.ai_assistant import generate_mock_data, GenerateMockRequest
                import asyncio

                request = GenerateMockRequest(
                    endpoint_id='ep_001',
                    count=5
                )

                result = asyncio.run(generate_mock_data(request, mock_service, mock_db))

                assert result['endpoint_id'] == 'ep_001'
                assert 'mock_data' in result
                assert len(result['mock_data']) == 2

    def test_generate_mock_data_endpoint_not_found(self, mock_service, mock_db):
        """测试接口不存在时的处理"""
        mock_db.fetch_one.return_value = None

        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            with patch('ai_test_tool.api.routes.ai_assistant.get_database', return_value=mock_db):
                from ai_test_tool.api.routes.ai_assistant import generate_mock_data, GenerateMockRequest
                from ai_test_tool.exceptions import NotFoundError
                import asyncio

                request = GenerateMockRequest(
                    endpoint_id='ep_not_exist',
                    count=5
                )

                with pytest.raises(NotFoundError):
                    asyncio.run(generate_mock_data(request, mock_service, mock_db))


class TestCodeGeneration:
    """测试代码生成 API 测试"""

    @pytest.fixture
    def mock_service(self):
        """模拟 AIAssistantService"""
        service = MagicMock()
        service.generate_test_code.return_value = '''
import pytest

def test_example():
    assert True
'''
        return service

    @pytest.fixture
    def mock_case_repo(self):
        """模拟 TestCaseRepository"""
        repo = MagicMock()
        repo.get_by_endpoint.return_value = [
            {
                'case_id': 'case_001',
                'name': '正常测试',
                'method': 'POST',
                'url': '/api/test'
            }
        ]
        return repo

    def test_generate_code_success(self, mock_service, mock_case_repo):
        """测试成功生成测试代码"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            with patch('ai_test_tool.api.routes.ai_assistant.get_test_case_repository', return_value=mock_case_repo):
                from ai_test_tool.api.routes.ai_assistant import generate_test_code, GenerateCodeRequest
                import asyncio

                request = GenerateCodeRequest(
                    endpoint_id='ep_001',
                    language='python',
                    framework='pytest'
                )

                result = asyncio.run(generate_test_code(request, mock_service, mock_case_repo))

                assert result['endpoint_id'] == 'ep_001'
                assert result['language'] == 'python'
                assert 'code' in result
                assert 'pytest' in result['code']


class TestAnalysisAPI:
    """分析 API 测试"""

    @pytest.fixture
    def mock_service(self):
        """模拟 AIAssistantService"""
        service = MagicMock()
        service.analyze_performance.return_value = {
            'summary': '性能分析摘要',
            'issues': [],
            'recommendations': ['建议1', '建议2']
        }
        service.analyze_coverage.return_value = {
            'coverage_rate': 75.5,
            'uncovered_endpoints': [],
            'suggestions': []
        }
        return service

    def test_analyze_performance(self, mock_service):
        """测试性能分析"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            from ai_test_tool.api.routes.ai_assistant import run_analysis, AnalyzeRequest
            import asyncio

            request = AnalyzeRequest(
                type='performance',
                days=7
            )

            result = asyncio.run(run_analysis(request, mock_service))

            assert result['type'] == 'performance'
            assert 'result' in result
            mock_service.analyze_performance.assert_called_once()

    def test_analyze_coverage(self, mock_service):
        """测试覆盖率分析"""
        with patch('ai_test_tool.api.routes.ai_assistant.get_ai_assistant_service', return_value=mock_service):
            from ai_test_tool.api.routes.ai_assistant import run_analysis, AnalyzeRequest
            import asyncio

            request = AnalyzeRequest(
                type='coverage',
                target_id='ep_001'
            )

            result = asyncio.run(run_analysis(request, mock_service))

            assert result['type'] == 'coverage'
            mock_service.analyze_coverage.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
