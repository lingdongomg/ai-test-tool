"""
知识存储层
该文件内容使用AI生成，注意识别准确性

提供知识的持久化存储，结合SQLite（元数据）和ChromaDB（向量索引）
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from ..database.connection import get_db_manager
from ..database.repository import (
    KnowledgeRepository,
    KnowledgeHistoryRepository,
    KnowledgeUsageRepository
)
from ..database.models import (
    KnowledgeEntry,
    KnowledgeHistory,
    KnowledgeUsage,
    KnowledgeType,
    KnowledgeStatus,
    KnowledgeSource,
    ChangeType
)
from .models import KnowledgeItem, KnowledgeSuggestion
from .embeddings import EmbeddingProvider, get_embedding_provider
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """
    知识存储层
    
    结合SQLite和向量索引（可选ChromaDB）的混合存储方案
    """
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        use_vector_store: bool = True,
        vector_store_path: str = "./data/knowledge_vectors"
    ):
        self.db = get_db_manager()
        self.knowledge_repo = KnowledgeRepository(self.db)
        self.history_repo = KnowledgeHistoryRepository(self.db)
        self.usage_repo = KnowledgeUsageRepository(self.db)
        
        self.use_vector_store = use_vector_store
        self.vector_store_path = vector_store_path
        self._embedding_provider = embedding_provider
        self._vector_collection = None
        self._chroma_client = None
    
    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """懒加载embedding提供商"""
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider("auto")
        return self._embedding_provider
    
    def _get_vector_collection(self):
        """获取ChromaDB collection"""
        if not self.use_vector_store:
            return None
        
        if self._vector_collection is not None:
            return self._vector_collection
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            self._chroma_client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.vector_store_path,
                anonymized_telemetry=False
            ))
            
            self._vector_collection = self._chroma_client.get_or_create_collection(
                name="knowledge_embeddings",
                metadata={"description": "Knowledge base embeddings"}
            )
            
            logger.info(f"ChromaDB collection initialized at {self.vector_store_path}")
            return self._vector_collection
            
        except ImportError:
            logger.warning("ChromaDB not installed, vector search disabled")
            self.use_vector_store = False
            return None
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.use_vector_store = False
            return None
    
    def create(
        self,
        title: str,
        content: str,
        type: str = "project_config",
        category: str = "",
        scope: str = "",
        priority: int = 0,
        tags: list[str] | None = None,
        source: str = "manual",
        source_ref: str = "",
        metadata: dict[str, Any] | None = None,
        status: str = "active",
        created_by: str = ""
    ) -> KnowledgeItem:
        """
        创建知识条目
        
        Args:
            title: 标题
            content: 内容
            type: 知识类型
            category: 子分类
            scope: 适用范围
            priority: 优先级
            tags: 标签列表
            source: 来源
            source_ref: 来源引用
            metadata: 额外元数据
            status: 状态
            created_by: 创建者
        
        Returns:
            创建的知识条目
        """
        knowledge_id = f"kb_{uuid.uuid4().hex[:12]}"
        
        # 创建数据库记录
        entry = KnowledgeEntry(
            knowledge_id=knowledge_id,
            title=title,
            content=content,
            type=KnowledgeType(type),
            category=category,
            scope=scope,
            priority=priority,
            status=KnowledgeStatus(status),
            source=KnowledgeSource(source),
            source_ref=source_ref,
            metadata=metadata or {},
            tags=tags or [],
            created_by=created_by,
            version=1
        )
        
        self.knowledge_repo.create(entry)
        
        # 创建历史记录
        history = KnowledgeHistory(
            knowledge_id=knowledge_id,
            version=1,
            title=title,
            content=content,
            change_type=ChangeType.CREATE,
            changed_by=created_by
        )
        self.history_repo.create(history)
        
        # 添加向量索引
        if self.use_vector_store:
            self._add_to_vector_store(knowledge_id, title, content, tags or [])
        
        logger.info(f"Created knowledge: {knowledge_id} - {title}")
        
        return KnowledgeItem(
            knowledge_id=knowledge_id,
            title=title,
            content=content,
            type=type,
            category=category,
            scope=scope,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {}
        )
    
    def _add_to_vector_store(
        self,
        knowledge_id: str,
        title: str,
        content: str,
        tags: list[str]
    ) -> None:
        """添加到向量存储"""
        collection = self._get_vector_collection()
        if collection is None:
            return
        
        try:
            # 构建要embedding的文本
            text = f"{title}\n{content}"
            if tags:
                text += f"\n标签: {', '.join(tags)}"
            
            # 生成embedding
            embedding = self.embedding_provider.embed(text)
            
            # 存储到ChromaDB
            collection.add(
                ids=[knowledge_id],
                embeddings=[embedding],
                metadatas=[{"title": title}],
                documents=[text]
            )
            
        except Exception as e:
            logger.error(f"Failed to add to vector store: {e}")
    
    def update(
        self,
        knowledge_id: str,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        scope: str | None = None,
        priority: int | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        updated_by: str = ""
    ) -> KnowledgeItem | None:
        """
        更新知识条目
        """
        entry = self.knowledge_repo.get_by_id(knowledge_id)
        if not entry:
            return None
        
        updates: dict[str, Any] = {}
        if title is not None:
            updates['title'] = title
        if content is not None:
            updates['content'] = content
        if category is not None:
            updates['category'] = category
        if scope is not None:
            updates['scope'] = scope
        if priority is not None:
            updates['priority'] = priority
        if tags is not None:
            updates['tags'] = tags
        if metadata is not None:
            updates['metadata'] = metadata
        
        if not updates:
            return self._entry_to_item(entry)
        
        # 更新数据库
        self.knowledge_repo.update(knowledge_id, updates)
        
        # 创建历史记录
        new_title = updates.get('title', entry.title)
        new_content = updates.get('content', entry.content)
        
        history = KnowledgeHistory(
            knowledge_id=knowledge_id,
            version=entry.version + 1,
            title=new_title,
            content=new_content,
            change_type=ChangeType.UPDATE,
            changed_by=updated_by
        )
        self.history_repo.create(history)
        
        # 更新向量索引
        if self.use_vector_store and ('title' in updates or 'content' in updates or 'tags' in updates):
            new_tags = updates.get('tags', entry.tags)
            self._update_vector_store(knowledge_id, new_title, new_content, new_tags)
        
        # 获取更新后的记录
        updated_entry = self.knowledge_repo.get_by_id(knowledge_id)
        return self._entry_to_item(updated_entry) if updated_entry else None
    
    def _update_vector_store(
        self,
        knowledge_id: str,
        title: str,
        content: str,
        tags: list[str]
    ) -> None:
        """更新向量存储"""
        collection = self._get_vector_collection()
        if collection is None:
            return
        
        try:
            # 删除旧的
            collection.delete(ids=[knowledge_id])
            
            # 添加新的
            self._add_to_vector_store(knowledge_id, title, content, tags)
            
        except Exception as e:
            logger.error(f"Failed to update vector store: {e}")
    
    def delete(self, knowledge_id: str) -> bool:
        """
        删除知识条目（硬删除）
        """
        entry = self.knowledge_repo.get_by_id(knowledge_id)
        if not entry:
            return False
        
        # 从向量存储删除
        if self.use_vector_store:
            collection = self._get_vector_collection()
            if collection:
                try:
                    collection.delete(ids=[knowledge_id])
                except Exception as e:
                    logger.error(f"Failed to delete from vector store: {e}")
        
        # 从数据库删除
        self.knowledge_repo.delete(knowledge_id)
        
        logger.info(f"Deleted knowledge: {knowledge_id}")
        return True
    
    def archive(self, knowledge_id: str, archived_by: str = "") -> bool:
        """
        归档知识条目（软删除）
        """
        entry = self.knowledge_repo.get_by_id(knowledge_id)
        if not entry:
            return False
        
        # 更新状态
        self.knowledge_repo.archive(knowledge_id)
        
        # 创建历史记录
        history = KnowledgeHistory(
            knowledge_id=knowledge_id,
            version=entry.version + 1,
            title=entry.title,
            content=entry.content,
            change_type=ChangeType.ARCHIVE,
            changed_by=archived_by
        )
        self.history_repo.create(history)
        
        # 从向量存储删除（归档后不参与检索）
        if self.use_vector_store:
            collection = self._get_vector_collection()
            if collection:
                try:
                    collection.delete(ids=[knowledge_id])
                except Exception:
                    pass
        
        logger.info(f"Archived knowledge: {knowledge_id}")
        return True
    
    def get(self, knowledge_id: str) -> KnowledgeItem | None:
        """获取单个知识条目"""
        entry = self.knowledge_repo.get_by_id(knowledge_id)
        return self._entry_to_item(entry) if entry else None
    
    def search(
        self,
        type: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        scope: str | None = None,
        keyword: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[KnowledgeItem]:
        """
        搜索知识条目
        """
        entries = self.knowledge_repo.search(
            type=KnowledgeType(type) if type else None,
            status=KnowledgeStatus(status) if status else None,
            tags=tags,
            scope=scope,
            keyword=keyword,
            limit=limit,
            offset=offset
        )
        return [self._entry_to_item(e) for e in entries]

    def search_paginated(
        self,
        type: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        scope: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[KnowledgeItem], int]:
        """
        分页搜索知识条目

        Returns:
            元组: (知识条目列表, 总数)
        """
        entries, total = self.knowledge_repo.search_paginated(
            type=KnowledgeType(type) if type else None,
            status=KnowledgeStatus(status) if status else None,
            tags=tags,
            scope=scope,
            keyword=keyword,
            page=page,
            page_size=page_size
        )
        return [self._entry_to_item(e) for e in entries], total
    
    def get_pending(self, limit: int = 100) -> list[KnowledgeItem]:
        """获取待审核的知识"""
        entries = self.knowledge_repo.get_pending(limit)
        return [self._entry_to_item(e) for e in entries]
    
    def approve(self, knowledge_ids: list[str]) -> int:
        """批量审核通过"""
        return self.knowledge_repo.batch_update_status(
            knowledge_ids,
            KnowledgeStatus.ACTIVE
        )
    
    def reject(self, knowledge_ids: list[str]) -> int:
        """批量拒绝（归档）"""
        # 从向量存储删除
        if self.use_vector_store:
            collection = self._get_vector_collection()
            if collection:
                try:
                    collection.delete(ids=knowledge_ids)
                except Exception:
                    pass
        
        return self.knowledge_repo.batch_update_status(
            knowledge_ids,
            KnowledgeStatus.ARCHIVED
        )
    
    def create_from_suggestion(
        self,
        suggestion: KnowledgeSuggestion,
        created_by: str = ""
    ) -> KnowledgeItem:
        """从知识建议创建条目"""
        # 确定来源
        source_ref_lower = suggestion.source_ref.lower()
        if "rule_engine" in source_ref_lower:
            source = "rule_engine"
        elif "log" in source_ref_lower:
            source = "log_learning"
        elif "test" in source_ref_lower:
            source = "test_learning"
        elif "api_doc" in source_ref_lower:
            source = "api_doc_sync"
        else:
            source = "log_learning"

        # 将 evidence 和 related_urls 存入 metadata
        metadata: dict[str, Any] = {}
        if hasattr(suggestion, 'related_urls') and suggestion.related_urls:
            metadata['related_urls'] = suggestion.related_urls

        return self.create(
            title=suggestion.title,
            content=suggestion.content,
            type=suggestion.type,
            category=suggestion.category,
            scope=suggestion.scope,
            tags=suggestion.tags,
            source=source,
            source_ref=suggestion.source_ref,
            metadata=metadata,
            status="pending",  # 建议的知识需要审核
            created_by=created_by
        )
    
    def record_usage(
        self,
        knowledge_id: str,
        used_in: str,
        context: str = ""
    ) -> str:
        """记录知识使用"""
        usage_id = f"usage_{uuid.uuid4().hex[:12]}"
        
        usage = KnowledgeUsage(
            usage_id=usage_id,
            knowledge_id=knowledge_id,
            used_in=used_in,
            context=context,
            helpful=0
        )
        
        self.usage_repo.create(usage)
        return usage_id
    
    def feedback_usage(self, usage_id: str, helpful: bool) -> None:
        """反馈知识使用效果"""
        self.usage_repo.update_helpful(usage_id, 1 if helpful else -1)
    
    def get_statistics(self) -> dict[str, Any]:
        """获取知识库统计"""
        status_counts = self.knowledge_repo.count_by_status()
        return {
            "total": sum(status_counts.values()),
            "by_status": status_counts
        }
    
    def vector_search(
        self,
        query: str,
        top_k: int = 10,
        filter_ids: list[str] | None = None
    ) -> list[tuple[str, float]]:
        """
        向量相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            filter_ids: 限制在这些ID中搜索
        
        Returns:
            (knowledge_id, similarity_score) 列表
        """
        collection = self._get_vector_collection()
        if collection is None:
            return []
        
        try:
            # 生成查询向量
            query_embedding = self.embedding_provider.embed(query)
            
            # 搜索
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"$in": filter_ids} if filter_ids else None
            )
            
            if not results['ids'] or not results['ids'][0]:
                return []
            
            # 组装结果
            ids = results['ids'][0]
            distances = results['distances'][0] if results.get('distances') else [0.0] * len(ids)
            
            # ChromaDB返回的是距离，转换为相似度
            # 余弦距离: similarity = 1 - distance/2
            similarities = [1 - d / 2 for d in distances]
            
            return list(zip(ids, similarities))
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def find_similar(
        self,
        title: str,
        content: str,
        scope: str = "",
        type: str = "",
        threshold: float = 0.85
    ) -> KnowledgeItem | None:
        """
        查找与给定标题/内容语义相似的已有知识

        两阶段去重策略:
        1. 精确匹配: 相同 scope + type → 直接返回
        2. 语义匹配: 向量相似度 > threshold → 返回最相似的

        Args:
            title: 新知识标题
            content: 新知识内容
            scope: 适用范围
            type: 知识类型
            threshold: 语义相似度阈值

        Returns:
            找到的相似知识条目，未找到返回 None
        """
        # 1. 精确去重：同 scope + type 下搜索关键词匹配
        if scope and type:
            existing = self.search(
                type=type, scope=scope, status="active", limit=10
            )
            for item in existing:
                # 标题高度相似（包含关系）
                if (title.lower() in item.title.lower() or
                    item.title.lower() in title.lower()):
                    return item

        # 2. 语义去重：向量相似度
        if self.use_vector_store:
            query_text = f"{title}\n{content}"
            results = self.vector_search(query=query_text, top_k=3)
            for kid, score in results:
                if score >= threshold:
                    item = self.get(kid)
                    if item and (not type or item.type == type):
                        return item

        return None

    def create_or_merge(
        self,
        suggestion: KnowledgeSuggestion,
        created_by: str = ""
    ) -> tuple[KnowledgeItem, bool]:
        """
        创建知识或与已有知识合并（去重）

        Returns:
            (item, is_new): 知识条目 + 是否新建
        """
        existing = self.find_similar(
            title=suggestion.title,
            content=suggestion.content,
            scope=suggestion.scope,
            type=suggestion.type,
            threshold=0.85
        )

        if existing:
            # 合并：如果新内容更详细，更新 content
            new_content = suggestion.content
            if len(new_content) > len(existing.content):
                self.update(
                    knowledge_id=existing.knowledge_id,
                    content=new_content,
                    updated_by=created_by
                )
            logger.info(f"知识去重合并: {existing.knowledge_id} ← '{suggestion.title[:30]}'")
            return existing, False

        # 新建
        item = self.create_from_suggestion(suggestion, created_by)
        return item, True

    def rebuild_vector_index(self) -> int:
        """重建向量索引"""
        if not self.use_vector_store:
            return 0
        
        collection = self._get_vector_collection()
        if collection is None:
            return 0
        
        # 清空现有索引
        try:
            # 删除并重建collection
            if self._chroma_client:
                self._chroma_client.delete_collection("knowledge_embeddings")
                self._vector_collection = None
                collection = self._get_vector_collection()
        except Exception:
            pass
        
        # 重新索引所有活跃知识
        entries = self.knowledge_repo.search(
            status=KnowledgeStatus.ACTIVE,
            limit=10000
        )
        
        count = 0
        for entry in entries:
            try:
                self._add_to_vector_store(
                    entry.knowledge_id,
                    entry.title,
                    entry.content,
                    entry.tags
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to index {entry.knowledge_id}: {e}")
        
        logger.info(f"Rebuilt vector index for {count} entries")
        return count
    
    def _entry_to_item(self, entry: KnowledgeEntry) -> KnowledgeItem:
        """将数据库模型转换为DTO"""
        return KnowledgeItem(
            knowledge_id=entry.knowledge_id,
            title=entry.title,
            content=entry.content,
            type=entry.type.value if isinstance(entry.type, KnowledgeType) else entry.type,
            category=entry.category,
            sub_category=getattr(entry, 'sub_category', ''),
            scope=entry.scope,
            priority=entry.priority,
            tags=entry.tags,
            metadata=entry.metadata,
            evidence=getattr(entry, 'evidence', ''),
        )
