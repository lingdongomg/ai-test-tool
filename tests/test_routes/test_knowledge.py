# 该文件内容使用AI生成，注意识别准确性
"""
Knowledge API 路由测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestKnowledgeList:
    """知识列表测试"""

    @pytest.fixture
    def mock_store(self):
        """模拟 KnowledgeStore"""
        store = MagicMock()
        store.search_paginated.return_value = (
            [
                {
                    'knowledge_id': 'k_001',
                    'title': '测试知识1',
                    'content': '知识内容1',
                    'type': 'project_config',
                    'status': 'active',
                    'scope': '/api/test',
                    'priority': 1,
                    'tags': ['tag1', 'tag2'],
                    'created_at': '2024-01-01 12:00:00'
                },
                {
                    'knowledge_id': 'k_002',
                    'title': '测试知识2',
                    'content': '知识内容2',
                    'type': 'business_rule',
                    'status': 'active',
                    'scope': '',
                    'priority': 0,
                    'tags': [],
                    'created_at': '2024-01-02 12:00:00'
                }
            ],
            2
        )
        return store

    def test_list_knowledge_returns_items(self, mock_store):
        """测试列表返回知识条目"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            with patch('ai_test_tool.api.dependencies.get_knowledge_store', return_value=mock_store):
                from ai_test_tool.api.routes.knowledge import list_knowledge
                import asyncio

                result = asyncio.run(list_knowledge(
                    type=None, status=None, tags=None, scope=None,
                    keyword=None, page=1, page_size=20, store=mock_store
                ))

                assert 'items' in result
                assert 'total' in result
                assert len(result['items']) == 2
                assert result['total'] == 2

    def test_list_knowledge_with_filters(self, mock_store):
        """测试带过滤条件的列表查询"""
        mock_store.search_paginated.return_value = ([{'knowledge_id': 'k_001'}], 1)

        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import list_knowledge
            import asyncio

            result = asyncio.run(list_knowledge(
                type='project_config',
                status='active',
                tags='tag1,tag2',
                scope='/api/test',
                keyword='测试',
                page=1,
                page_size=10,
                store=mock_store
            ))

            # 验证过滤条件被正确传递
            mock_store.search_paginated.assert_called_once()
            call_kwargs = mock_store.search_paginated.call_args[1]
            assert call_kwargs['type'] == 'project_config'
            assert call_kwargs['status'] == 'active'
            assert call_kwargs['tags'] == ['tag1', 'tag2']

    def test_list_knowledge_pagination(self, mock_store):
        """测试分页参数"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import list_knowledge
            import asyncio

            asyncio.run(list_knowledge(
                type=None, status=None, tags=None, scope=None,
                keyword=None, page=2, page_size=10, store=mock_store
            ))

            call_kwargs = mock_store.search_paginated.call_args[1]
            assert call_kwargs['page'] == 2
            assert call_kwargs['page_size'] == 10


class TestKnowledgeCreate:
    """知识创建测试"""

    @pytest.fixture
    def mock_store(self):
        """模拟 KnowledgeStore"""
        store = MagicMock()
        store.add.return_value = 'k_new_001'
        return store

    def test_create_knowledge_success(self, mock_store):
        """测试成功创建知识"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import create_knowledge, KnowledgeCreateRequest
            import asyncio

            request = KnowledgeCreateRequest(
                title='新知识',
                content='知识内容',
                type='project_config',
                scope='/api/test',
                tags=['tag1']
            )

            result = asyncio.run(create_knowledge(request, mock_store))

            assert result['knowledge_id'] == 'k_new_001'
            mock_store.add.assert_called_once()

    def test_create_knowledge_with_defaults(self, mock_store):
        """测试使用默认值创建知识"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import create_knowledge, KnowledgeCreateRequest
            import asyncio

            request = KnowledgeCreateRequest(
                title='最小知识',
                content='最小内容'
            )

            result = asyncio.run(create_knowledge(request, mock_store))

            call_args = mock_store.add.call_args
            # 验证默认值
            assert call_args[1]['type'] == 'project_config'
            assert call_args[1]['priority'] == 0


class TestKnowledgeSearch:
    """知识检索测试"""

    @pytest.fixture
    def mock_retriever(self):
        """模拟 KnowledgeRetriever"""
        retriever = MagicMock()
        retriever.retrieve.return_value = [
            MagicMock(
                knowledge_id='k_001',
                title='相关知识',
                content='知识内容',
                type='project_config',
                score=0.85,
                scope='/api/test',
                tags=['tag1']
            )
        ]
        return retriever

    @pytest.fixture
    def mock_rag_builder(self):
        """模拟 RAGContextBuilder"""
        builder = MagicMock()
        builder.build_context.return_value = MagicMock(
            context_text='RAG上下文',
            token_count=100,
            sources=['k_001']
        )
        return builder

    def test_search_knowledge_returns_results(self, mock_retriever, mock_rag_builder):
        """测试知识检索返回结果"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_retriever', return_value=mock_retriever):
            with patch('ai_test_tool.api.routes.knowledge.get_rag_context_builder', return_value=mock_rag_builder):
                from ai_test_tool.api.routes.knowledge import search_knowledge, KnowledgeSearchRequest
                import asyncio

                request = KnowledgeSearchRequest(
                    query='测试查询',
                    top_k=5,
                    min_score=0.3
                )

                result = asyncio.run(search_knowledge(
                    request,
                    retriever=mock_retriever,
                    rag_builder=mock_rag_builder
                ))

                assert 'items' in result
                assert 'total' in result
                assert 'token_count' in result
                mock_retriever.retrieve.assert_called_once()

    def test_search_with_filters(self, mock_retriever, mock_rag_builder):
        """测试带过滤条件的检索"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_retriever', return_value=mock_retriever):
            with patch('ai_test_tool.api.routes.knowledge.get_rag_context_builder', return_value=mock_rag_builder):
                from ai_test_tool.api.routes.knowledge import search_knowledge, KnowledgeSearchRequest
                import asyncio

                request = KnowledgeSearchRequest(
                    query='测试',
                    types=['project_config', 'business_rule'],
                    tags=['tag1'],
                    scope='/api/test',
                    top_k=10,
                    min_score=0.5
                )

                asyncio.run(search_knowledge(
                    request,
                    retriever=mock_retriever,
                    rag_builder=mock_rag_builder
                ))

                call_kwargs = mock_retriever.retrieve.call_args[1]
                assert call_kwargs['top_k'] == 10
                assert call_kwargs['threshold'] == 0.5


class TestKnowledgeStatistics:
    """知识库统计测试"""

    @pytest.fixture
    def mock_store(self):
        """模拟 KnowledgeStore"""
        store = MagicMock()
        store.get_statistics.return_value = {
            'total': 100,
            'by_type': {
                'project_config': 40,
                'business_rule': 30,
                'module_context': 20,
                'test_experience': 10
            },
            'by_status': {
                'active': 85,
                'pending': 10,
                'archived': 5
            }
        }
        return store

    def test_get_statistics(self, mock_store):
        """测试获取统计信息"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import get_statistics
            import asyncio

            result = asyncio.run(get_statistics(mock_store))

            assert result['total'] == 100
            assert 'by_type' in result
            assert 'by_status' in result
            assert result['by_type']['project_config'] == 40


class TestKnowledgeReview:
    """知识审核测试"""

    @pytest.fixture
    def mock_store(self):
        """模拟 KnowledgeStore"""
        store = MagicMock()
        store.batch_review.return_value = 3
        store.get_pending.return_value = [
            {'knowledge_id': 'k_001', 'title': '待审核1'},
            {'knowledge_id': 'k_002', 'title': '待审核2'}
        ]
        return store

    def test_batch_approve(self, mock_store):
        """测试批量通过审核"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import batch_review, BatchReviewRequest
            import asyncio

            request = BatchReviewRequest(
                knowledge_ids=['k_001', 'k_002', 'k_003'],
                action='approve'
            )

            result = asyncio.run(batch_review(request, mock_store))

            assert result['count'] == 3
            mock_store.batch_review.assert_called_once_with(
                ['k_001', 'k_002', 'k_003'], 'approve'
            )

    def test_batch_reject(self, mock_store):
        """测试批量拒绝审核"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import batch_review, BatchReviewRequest
            import asyncio

            request = BatchReviewRequest(
                knowledge_ids=['k_001'],
                action='reject'
            )

            asyncio.run(batch_review(request, mock_store))

            mock_store.batch_review.assert_called_once_with(
                ['k_001'], 'reject'
            )

    def test_get_pending_list(self, mock_store):
        """测试获取待审核列表"""
        with patch('ai_test_tool.api.routes.knowledge.get_knowledge_store', return_value=mock_store):
            from ai_test_tool.api.routes.knowledge import list_pending
            import asyncio

            result = asyncio.run(list_pending(limit=100, store=mock_store))

            assert 'items' in result
            assert len(result['items']) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
