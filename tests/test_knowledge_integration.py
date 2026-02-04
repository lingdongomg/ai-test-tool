# 该文件内容使用AI生成，注意识别准确性
"""
知识库集成测试
测试完整的知识学习→检索→应用流程
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from ai_test_tool.knowledge.models import KnowledgeItem, KnowledgeSearchResult, KnowledgeContext
from ai_test_tool.knowledge.store import KnowledgeStore
from ai_test_tool.knowledge.retriever import KnowledgeRetriever
from ai_test_tool.knowledge.rag_builder import RAGContextBuilder
from ai_test_tool.knowledge.learner import KnowledgeLearner
from ai_test_tool.database.models import KnowledgeType, KnowledgeStatus, KnowledgeEntry


class TestKnowledgeLearningFlow:
    """知识学习流程测试"""
    
    @pytest.fixture
    def mock_store(self):
        """模拟知识存储"""
        store = Mock(spec=KnowledgeStore)
        store.create.return_value = "learned_001"
        store.create_from_suggestion.return_value = "pending_001"
        return store
    
    def test_learner_initialization(self, mock_store):
        """测试学习器初始化"""
        learner = KnowledgeLearner(mock_store)
        assert learner.store == mock_store
    
    def test_learner_with_mock_chain(self, mock_store):
        """测试学习器使用模拟Chain"""
        learner = KnowledgeLearner(mock_store)
        
        # 验证学习器有正确的属性
        assert hasattr(learner, 'store')
        assert learner.store == mock_store
        
        # 验证学习器有正确的方法
        assert hasattr(learner, 'extract_from_log_analysis')
        assert hasattr(learner, 'extract_from_test_results')


class TestKnowledgeRetrievalFlow:
    """知识检索流程测试"""
    
    @pytest.fixture
    def sample_knowledge(self):
        """样本知识数据"""
        return [
            KnowledgeItem(
                knowledge_id="k001",
                title="API认证Token",
                content="所有API请求必须在header中传入 Authorization: Bearer {token}",
                type=KnowledgeType.PROJECT_CONFIG,
                category="auth",
                scope="/api/*",
                tags=["auth", "token", "header"],
                priority=10
            ),
            KnowledgeItem(
                knowledge_id="k002",
                title="直播模块game-id",
                content="直播电商接口需要header传入game-id，测试环境demo游戏ID为123456",
                type=KnowledgeType.BUSINESS_RULE,
                category="live",
                scope="/api/live/*",
                tags=["live", "game-id", "电商"],
                priority=8
            )
        ]
    
    def test_retrieve_with_context(self, sample_knowledge):
        """测试使用上下文检索"""
        mock_store = Mock(spec=KnowledgeStore)
        mock_store.search.return_value = sample_knowledge
        mock_store.use_vector_store = False
        
        retriever = KnowledgeRetriever(mock_store)
        
        context = KnowledgeContext(
            query="API认证",
            scope="/api/*"
        )
        results = retriever.retrieve(context)
        
        assert mock_store.search.called
    
    def test_retrieve_for_test_generation(self, sample_knowledge):
        """测试为测试生成检索"""
        mock_store = Mock(spec=KnowledgeStore)
        mock_store.search.return_value = [sample_knowledge[1]]
        mock_store.use_vector_store = False
        
        retriever = KnowledgeRetriever(mock_store)
        results = retriever.retrieve_for_test_generation(
            api_path="/api/live/room",
            method="POST"
        )
        
        assert mock_store.search.called


class TestRAGApplicationFlow:
    """RAG应用流程测试"""
    
    def test_build_test_generation_context(self):
        """测试为测试生成构建上下文"""
        mock_items = [
            KnowledgeItem(
                knowledge_id="rag001",
                title="API认证",
                content="需要Bearer Token认证",
                type=KnowledgeType.PROJECT_CONFIG,
                tags=["auth"]
            ),
            KnowledgeItem(
                knowledge_id="rag002",
                title="game-id规则",
                content="直播接口需要game-id: 123456",
                type=KnowledgeType.BUSINESS_RULE,
                tags=["live"]
            )
        ]
        
        mock_results = [
            KnowledgeSearchResult(item=item, score=0.9-i*0.1)
            for i, item in enumerate(mock_items)
        ]
        
        mock_retriever = Mock(spec=KnowledgeRetriever)
        mock_retriever.retrieve_for_test_generation.return_value = mock_results
        
        builder = RAGContextBuilder(mock_retriever)
        builder.max_tokens = 4000  # 设置实际值
        
        # 使用正确的方法签名
        context = builder.build_test_generation_context(results=mock_results)
        
        assert isinstance(context, str)


class TestEndToEndFlow:
    """端到端流程测试"""
    
    def test_knowledge_lifecycle(self):
        """测试知识生命周期：创建→存储→检索→应用"""
        
        with patch('ai_test_tool.knowledge.store.KnowledgeRepository') as MockRepo:
            with patch('ai_test_tool.knowledge.store.KnowledgeHistoryRepository'):
                with patch('ai_test_tool.knowledge.store.KnowledgeUsageRepository'):
                    with patch('ai_test_tool.knowledge.store.get_db_manager'):
                        mock_repo = Mock()
                        mock_repo.create.return_value = 1
                        mock_repo.get_by_id.return_value = KnowledgeEntry(
                            knowledge_id="lifecycle_001",
                            title="测试环境配置",
                            content="测试环境base_url为http://test.example.com",
                            type=KnowledgeType.PROJECT_CONFIG,
                            tags=["env", "test"]
                        )
                        mock_repo.search.return_value = [mock_repo.get_by_id.return_value]
                        MockRepo.return_value = mock_repo
                        
                        # 1. 创建存储
                        store = KnowledgeStore()
                        store._repository = mock_repo
                        store.use_vector_store = False
                        
                        # 2. 添加知识
                        knowledge_id = store.create(
                            title="测试环境配置",
                            content="测试环境base_url为http://test.example.com",
                            type=KnowledgeType.PROJECT_CONFIG,
                            tags=["env", "test"]
                        )
                        
                        # 3. 检索知识
                        retriever = KnowledgeRetriever(store)
                        
                        # 4. 构建RAG上下文
                        builder = RAGContextBuilder(retriever)
                        
                        # 先检索
                        results = retriever.retrieve_for_test_generation(
                            api_path="/api/test",
                            method="GET"
                        )
                        
                        # 再构建上下文
                        context = builder.build_test_generation_context(results=results)
                        
                        # 5. 验证流程
                        assert mock_repo.create.called
                        print(f"✅ 知识创建成功")
                        print(f"✅ 知识检索完成")
                        print(f"✅ RAG上下文构建完成")


class TestTestGeneratorIntegration:
    """测试生成器集成测试"""
    
    def test_knowledge_enhanced_generation_mock(self):
        """测试知识增强的测试用例生成（Mock模式）"""
        from ai_test_tool.testing.test_case_generator import TestCaseGenerator
        
        generator = TestCaseGenerator(
            llm_chain=None,
            verbose=False,
            enable_knowledge=False
        )
        
        assert generator is not None
        assert generator._knowledge_enabled == False
    
    def test_generator_with_knowledge_enabled_flag(self):
        """测试生成器知识启用标志"""
        from ai_test_tool.testing.test_case_generator import KNOWLEDGE_ENABLED
        
        assert KNOWLEDGE_ENABLED == True


# 运行测试的入口
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
