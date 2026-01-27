"""
知识库模块
该文件内容使用AI生成，注意识别准确性

提供项目知识的存储、检索、学习能力，用于增强AI生成测试用例的质量
"""

from .models import (
    KnowledgeItem,
    KnowledgeSearchResult,
    KnowledgeContext,
    RAGContext
)
from .store import KnowledgeStore
from .retriever import KnowledgeRetriever
from .embeddings import EmbeddingProvider, get_embedding_provider
from .rag_builder import RAGContextBuilder
from .learner import KnowledgeLearner

# 全局知识库存储实例
_knowledge_store: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    """获取全局知识库存储实例（单例）"""
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = KnowledgeStore()
    return _knowledge_store


__all__ = [
    # 数据模型
    'KnowledgeItem',
    'KnowledgeSearchResult', 
    'KnowledgeContext',
    'RAGContext',
    # 核心组件
    'KnowledgeStore',
    'KnowledgeRetriever',
    'EmbeddingProvider',
    'get_embedding_provider',
    'RAGContextBuilder',
    'KnowledgeLearner',
    # 工厂函数
    'get_knowledge_store',
]
