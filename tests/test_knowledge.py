# 该文件内容使用AI生成，注意识别准确性
"""
知识库模块单元测试
"""

import pytest
from unittest.mock import Mock, patch

# 知识库模块
from ai_test_tool.knowledge.models import (
    KnowledgeItem, KnowledgeSearchResult, KnowledgeContext, RAGContext
)
from ai_test_tool.knowledge.store import KnowledgeStore
from ai_test_tool.knowledge.retriever import KnowledgeRetriever
from ai_test_tool.knowledge.rag_builder import RAGContextBuilder
from ai_test_tool.knowledge.embeddings import EmbeddingProvider, TFIDFEmbeddingProvider

# 数据库模型
from ai_test_tool.database.models import (
    KnowledgeEntry, KnowledgeType, KnowledgeStatus, KnowledgeSource
)


class TestKnowledgeModels:
    """知识领域模型测试"""
    
    def test_knowledge_item_creation(self):
        """测试知识条目创建"""
        item = KnowledgeItem(
            knowledge_id="test_001",
            title="测试知识",
            content="这是测试内容",
            type=KnowledgeType.PROJECT_CONFIG,
            category="auth",
            scope="/api/*",
            tags=["test", "auth"],
            priority=10
        )
        
        assert item.knowledge_id == "test_001"
        assert item.title == "测试知识"
        assert item.type == KnowledgeType.PROJECT_CONFIG
        assert item.priority == 10
        assert "test" in item.tags
    
    def test_knowledge_item_to_text(self):
        """测试知识条目转文本"""
        item = KnowledgeItem(
            knowledge_id="test_002",
            title="测试",
            content="内容",
            type=KnowledgeType.BUSINESS_RULE,
            tags=["tag1"]
        )
        
        result = item.to_text()
        
        assert isinstance(result, str)
        assert "测试" in result
        assert "内容" in result
    
    def test_knowledge_search_result(self):
        """测试搜索结果"""
        item = KnowledgeItem(
            knowledge_id="test_003",
            title="搜索结果",
            content="匹配内容",
            type=KnowledgeType.MODULE_CONTEXT
        )
        
        result = KnowledgeSearchResult(
            item=item,
            score=0.85
        )
        
        assert result.score == 0.85
        assert result.item.title == "搜索结果"
    
    def test_knowledge_context(self):
        """测试知识上下文"""
        context = KnowledgeContext(
            query="测试查询",
            scope="/api/test"
        )
        
        assert context.query == "测试查询"
        assert context.scope == "/api/test"
    
    def test_rag_context(self):
        """测试RAG上下文"""
        items = [
            KnowledgeItem(
                knowledge_id=f"rag_{i}",
                title=f"知识{i}",
                content=f"内容{i}",
                type=KnowledgeType.PROJECT_CONFIG
            )
            for i in range(3)
        ]
        
        context = RAGContext(
            knowledge_items=items,
            context_text="格式化的上下文"
        )
        
        assert len(context.knowledge_items) == 3
        assert context.context_text == "格式化的上下文"


class TestTFIDFEmbedding:
    """TF-IDF向量化测试"""
    
    def test_provider_name(self):
        """测试提供商名称"""
        embedder = TFIDFEmbeddingProvider()
        assert embedder.name == "tfidf"
    
    def test_dimension(self):
        """测试向量维度"""
        embedder = TFIDFEmbeddingProvider()
        assert embedder.dimension >= 100


class TestKnowledgeStore:
    """知识存储测试"""
    
    @pytest.fixture
    def mock_repository(self):
        """模拟仓库"""
        repo = Mock()
        repo.create.return_value = 1
        repo.get_by_id.return_value = None
        repo.search.return_value = []
        repo.update.return_value = 1
        repo.archive.return_value = 1
        return repo
    
    @pytest.fixture
    def store(self, mock_repository):
        """创建测试用存储"""
        with patch('ai_test_tool.knowledge.store.KnowledgeRepository', return_value=mock_repository):
            with patch('ai_test_tool.knowledge.store.KnowledgeHistoryRepository'):
                with patch('ai_test_tool.knowledge.store.KnowledgeUsageRepository'):
                    with patch('ai_test_tool.knowledge.store.get_db_manager'):
                        store = KnowledgeStore()
                        store._repository = mock_repository
                        return store
    
    def test_create_knowledge(self, store, mock_repository):
        """测试创建知识"""
        knowledge_id = store.create(
            title="测试标题",
            content="测试内容",
            type=KnowledgeType.PROJECT_CONFIG,
            tags=["test"]
        )
        
        assert knowledge_id is not None
        assert mock_repository.create.called
    
    def test_search_knowledge(self, store, mock_repository):
        """测试搜索知识"""
        mock_entry = KnowledgeEntry(
            knowledge_id="search_001",
            title="搜索结果",
            content="匹配内容",
            type=KnowledgeType.PROJECT_CONFIG,
            tags=["api"]
        )
        mock_repository.search.return_value = [mock_entry]
        
        results = store.search(keyword="匹配")
        
        assert mock_repository.search.called


class TestKnowledgeRetriever:
    """知识检索器测试"""
    
    @pytest.fixture
    def mock_store(self):
        """模拟存储"""
        store = Mock(spec=KnowledgeStore)
        store.search.return_value = []
        store.vector_search.return_value = []
        store.use_vector_store = False
        return store
    
    @pytest.fixture
    def retriever(self, mock_store):
        """创建测试用检索器"""
        return KnowledgeRetriever(mock_store)
    
    def test_retrieve(self, retriever, mock_store):
        """测试检索"""
        mock_store.search.return_value = [
            KnowledgeItem(
                knowledge_id="ret_001",
                title="关键词匹配",
                content="包含关键词的内容",
                type=KnowledgeType.PROJECT_CONFIG
            )
        ]
        
        context = KnowledgeContext(query="关键词")
        results = retriever.retrieve(context)
        
        assert mock_store.search.called
    
    def test_retrieve_for_test_generation(self, retriever, mock_store):
        """测试为测试生成检索"""
        mock_store.search.return_value = [
            KnowledgeItem(
                knowledge_id="gen_001",
                title="API认证",
                content="需要Bearer Token",
                type=KnowledgeType.PROJECT_CONFIG
            )
        ]
        
        # 使用正确的参数名
        results = retriever.retrieve_for_test_generation(
            api_path="/api/test",
            method="GET"
        )
        
        assert mock_store.search.called


class TestRAGContextBuilder:
    """RAG上下文构建器测试"""
    
    @pytest.fixture
    def mock_retriever(self):
        """模拟检索器"""
        retriever = Mock(spec=KnowledgeRetriever)
        retriever.retrieve.return_value = []
        retriever.retrieve_for_test_generation.return_value = []
        return retriever
    
    @pytest.fixture
    def builder(self, mock_retriever):
        """创建测试用构建器"""
        b = RAGContextBuilder(mock_retriever)
        b.max_tokens = 4000  # 设置实际值避免Mock问题
        return b
    
    def test_build_empty_context(self, builder):
        """测试构建空上下文"""
        results: list[KnowledgeSearchResult] = []
        context = builder.build(results)
        
        assert context.is_empty
    
    def test_build_context_with_results(self, builder):
        """测试构建带结果的上下文"""
        items = [
            KnowledgeItem(
                knowledge_id="ctx_001",
                title="认证配置",
                content="所有API需要Bearer Token认证",
                type=KnowledgeType.PROJECT_CONFIG,
                tags=["auth"]
            ),
            KnowledgeItem(
                knowledge_id="ctx_002",
                title="直播模块",
                content="需要game-id header",
                type=KnowledgeType.BUSINESS_RULE,
                tags=["live"]
            )
        ]
        
        results = [
            KnowledgeSearchResult(item=item, score=0.9-i*0.1)
            for i, item in enumerate(items)
        ]
        
        context = builder.build(results)
        
        assert not context.is_empty
        assert len(context.knowledge_items) == 2
    
    def test_build_test_generation_context(self, builder):
        """测试构建测试生成上下文"""
        items = [
            KnowledgeItem(
                knowledge_id="tg_001",
                title="测试配置",
                content="测试内容",
                type=KnowledgeType.PROJECT_CONFIG
            )
        ]
        
        results = [
            KnowledgeSearchResult(item=item, score=0.9)
            for item in items
        ]
        
        # 使用正确的签名
        context = builder.build_test_generation_context(results=results)
        
        assert isinstance(context, str)


class TestKnowledgeIntegration:
    """知识库集成测试"""
    
    def test_store_and_retrieve_mock(self):
        """测试存储和检索流程（Mock模式）"""
        with patch('ai_test_tool.knowledge.store.KnowledgeRepository') as MockRepo:
            with patch('ai_test_tool.knowledge.store.KnowledgeHistoryRepository'):
                with patch('ai_test_tool.knowledge.store.KnowledgeUsageRepository'):
                    with patch('ai_test_tool.knowledge.store.get_db_manager'):
                        mock_repo = Mock()
                        mock_repo.create.return_value = 1
                        mock_repo.search.return_value = [
                            KnowledgeEntry(
                                knowledge_id="int_001",
                                title="测试知识",
                                content="测试内容",
                                type=KnowledgeType.PROJECT_CONFIG,
                                tags=["test"]
                            )
                        ]
                        MockRepo.return_value = mock_repo
                        
                        # 1. 创建存储
                        store = KnowledgeStore()
                        store._repository = mock_repo
                        
                        # 2. 创建知识
                        kid = store.create(
                            title="测试知识",
                            content="测试内容",
                            type=KnowledgeType.PROJECT_CONFIG,
                            tags=["test"]
                        )
                        
                        # 3. 检索知识
                        results = store.search(keyword="测试")
                        
                        # 4. 验证
                        assert mock_repo.create.called
                        assert mock_repo.search.called


# 运行测试的入口
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
