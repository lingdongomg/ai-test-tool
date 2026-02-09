# 该文件内容使用AI生成，注意识别准确性
"""
AI Assistant API 路由测试
"""

import pytest
from unittest.mock import MagicMock, patch


def _make_model_mock(**fields):
    """创建带属性访问的 Mock 对象，模拟 dataclass 模型"""
    m = MagicMock()
    for k, v in fields.items():
        setattr(m, k, v)
    m.to_dict.return_value = fields
    return m


class TestChatAPI:
    """AI 对话 API 测试"""

    @pytest.fixture
    def mock_service(self):
        """模拟 AIAssistantService"""
        service = MagicMock()
        service.ask_question.return_value = "这是AI的回答"
        return service

    @pytest.fixture
    def mock_session_repo(self):
        """模拟 ChatSessionRepository"""
        repo = MagicMock()
        repo.get_by_id.return_value = None  # 新会话
        repo.create.return_value = 1
        return repo

    @pytest.fixture
    def mock_message_repo(self):
        """模拟 ChatMessageRepository"""
        repo = MagicMock()
        repo.create.return_value = 1
        repo.get_recent_by_session.return_value = []
        return repo

    def test_chat_success(self, mock_service, mock_session_repo, mock_message_repo):
        """测试成功对话"""
        from ai_test_tool.api.routes.ai_assistant import chat_with_ai, ChatRequest
        import asyncio

        request = ChatRequest(
            message="测试问题",
            context={"endpoint": "/api/test"},
            session_id="session_001"
        )

        result = asyncio.run(chat_with_ai(
            request, mock_service, mock_session_repo, mock_message_repo
        ))

        assert result['success'] is True
        assert result['message'] == "测试问题"
        assert result['answer'] == "这是AI的回答"
        assert result['session_id'] == "session_001"

    def test_chat_without_context(self, mock_service, mock_session_repo, mock_message_repo):
        """测试无上下文对话"""
        from ai_test_tool.api.routes.ai_assistant import chat_with_ai, ChatRequest
        import asyncio

        request = ChatRequest(message="简单问题")

        result = asyncio.run(chat_with_ai(
            request, mock_service, mock_session_repo, mock_message_repo
        ))

        assert result['success'] is True
        # 验证 context 被设为空字典
        call_kwargs = mock_service.ask_question.call_args[1]
        assert call_kwargs['context'] == {}

    def test_chat_error_handling(self, mock_service, mock_session_repo, mock_message_repo):
        """测试对话错误处理"""
        mock_service.ask_question.side_effect = Exception("LLM服务不可用")

        from ai_test_tool.api.routes.ai_assistant import chat_with_ai, ChatRequest
        from ai_test_tool.exceptions import LLMError
        import asyncio

        request = ChatRequest(message="测试问题")

        with pytest.raises(LLMError):
            asyncio.run(chat_with_ai(
                request, mock_service, mock_session_repo, mock_message_repo
            ))


class TestInsightAPI:
    """AI 洞察 API 测试"""

    @pytest.fixture
    def mock_repository(self):
        """模拟 AIInsightRepository"""
        repo = MagicMock()
        repo.search_paginated.return_value = (
            [
                _make_model_mock(
                    id=1, insight_id='ins_001', insight_type='anomaly',
                    severity=MagicMock(value='high'),
                    title='异常洞察1', description='描述内容',
                    confidence=0.9, details=None, recommendations=None,
                    is_resolved=False, resolved_at=None, created_at=None
                )
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
        from ai_test_tool.api.routes.ai_assistant import list_insights
        import asyncio

        result = asyncio.run(list_insights(
            type=None, severity=None, is_resolved=None,
            page=1, page_size=20, insight_repo=mock_repository
        ))

        assert 'items' in result
        assert 'total' in result
        assert len(result['items']) == 1

    def test_list_insights_with_filters(self, mock_repository):
        """测试带过滤条件的洞察列表"""
        from ai_test_tool.api.routes.ai_assistant import list_insights
        import asyncio

        asyncio.run(list_insights(
            type='anomaly',
            severity='high',
            is_resolved=False,
            page=1,
            page_size=10,
            insight_repo=mock_repository
        ))

        call_kwargs = mock_repository.search_paginated.call_args[1]
        assert call_kwargs['insight_type'] == 'anomaly'
        assert call_kwargs['severity'] == 'high'
        assert call_kwargs['is_resolved'] is False

    def test_get_ai_statistics(self, mock_repository):
        """测试获取 AI 统计"""
        mock_case_repo = MagicMock()
        mock_case_repo.count.return_value = 42

        from ai_test_tool.api.routes.ai_assistant import get_ai_statistics
        import asyncio

        result = asyncio.run(get_ai_statistics(mock_repository, mock_case_repo))

        assert 'insights' in result
        assert result['insights']['total'] == 50
        assert result['insights']['unresolved'] == 10
        assert result['ai_generated_cases'] == 42


class TestMockDataGeneration:
    """Mock 数据生成 API 测试"""

    @pytest.fixture
    def mock_service(self):
        """模拟 AIAssistantService"""
        service = MagicMock()
        service.generate_mock_data.return_value = {
            'mock_data': [
                {"id": 1, "name": "测试数据1"},
                {"id": 2, "name": "测试数据2"}
            ],
            'schema': {'type': 'object'}
        }
        return service

    def test_generate_mock_data_success(self, mock_service):
        """测试成功生成 Mock 数据"""
        from ai_test_tool.api.routes.ai_assistant import generate_mock_data, GenerateMockRequest
        import asyncio

        request = GenerateMockRequest(
            endpoint_id='ep_001',
            count=5
        )

        result = asyncio.run(generate_mock_data(request, mock_service))

        assert result['endpoint_id'] == 'ep_001'
        assert 'data' in result
        assert len(result['data']) == 2

    def test_generate_mock_data_endpoint_not_found(self, mock_service):
        """测试接口不存在时的处理"""
        mock_service.generate_mock_data.side_effect = ValueError("Endpoint not found")

        from ai_test_tool.api.routes.ai_assistant import generate_mock_data, GenerateMockRequest
        from ai_test_tool.exceptions import NotFoundError
        import asyncio

        request = GenerateMockRequest(
            endpoint_id='ep_not_exist',
            count=5
        )

        with pytest.raises(NotFoundError):
            asyncio.run(generate_mock_data(request, mock_service))


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

    def test_generate_code_success(self, mock_service):
        """测试成功生成测试代码"""
        from ai_test_tool.api.routes.ai_assistant import generate_test_code, GenerateCodeRequest
        import asyncio

        request = GenerateCodeRequest(
            endpoint_id='ep_001',
            language='python',
            framework='pytest'
        )

        result = asyncio.run(generate_test_code(request, mock_service))

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
        # analyze_performance_trend 返回 AIInsight 对象列表
        service.analyze_performance_trend.return_value = [
            _make_model_mock(
                insight_id='perf_001',
                insight_type=MagicMock(value='performance'),
                title='性能问题', description='响应时间过长',
                severity='high', confidence=0.9,
                details={'avg_time': 500}, recommendations=['优化查询']
            )
        ]
        service.analyze_coverage_gaps.return_value = [
            _make_model_mock(
                insight_id='cov_001',
                insight_type=MagicMock(value='coverage'),
                title='覆盖率不足', description='3个接口未覆盖',
                severity='medium',
                details={'uncovered': 3}, recommendations=['添加测试']
            )
        ]
        return service

    def test_analyze_performance(self, mock_service):
        """测试性能分析"""
        from ai_test_tool.api.routes.ai_assistant import analyze_performance, AnalyzeRequest
        import asyncio

        request = AnalyzeRequest(
            type='performance',
            days=7
        )

        result = asyncio.run(analyze_performance(request, mock_service))

        assert result['success'] is True
        assert result['type'] == 'performance'
        assert 'insights' in result
        mock_service.analyze_performance_trend.assert_called_once()

    def test_analyze_coverage(self, mock_service):
        """测试覆盖率分析"""
        from ai_test_tool.api.routes.ai_assistant import analyze_coverage
        import asyncio

        result = asyncio.run(analyze_coverage(mock_service))

        assert result['success'] is True
        assert result['type'] == 'coverage'
        mock_service.analyze_coverage_gaps.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
