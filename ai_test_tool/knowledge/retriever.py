"""
知识检索器
该文件内容使用AI生成，注意识别准确性

提供混合检索策略：关键词匹配 + 语义相似度 + 上下文重排序
"""

import logging
from typing import Any

from .models import KnowledgeItem, KnowledgeSearchResult, KnowledgeContext
from .store import KnowledgeStore
from .embeddings import cosine_similarity

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    知识检索器
    
    采用三阶段检索策略：
    1. 关键词预筛选：基于类型、标签、范围快速过滤
    2. 语义排序：计算查询与知识的向量相似度
    3. 上下文重排序：根据当前场景调整排名
    """
    
    def __init__(self, store: KnowledgeStore):
        self.store = store
        
        # 知识类型权重（用于重排序）
        self.type_weights = {
            "project_config": 1.2,    # 项目配置最重要
            "business_rule": 1.1,     # 业务规则次之
            "module_context": 1.0,    # 模块上下文
            "test_experience": 0.9    # 测试经验
        }
    
    def retrieve(self, context: KnowledgeContext) -> list[KnowledgeSearchResult]:
        """
        检索相关知识
        
        Args:
            context: 检索上下文
        
        Returns:
            按相关度排序的知识结果列表
        """
        results: list[KnowledgeSearchResult] = []
        
        # 1. 关键词预筛选
        candidates = self._keyword_filter(context)
        
        if not candidates:
            logger.debug(f"No candidates found for query: {context.query[:50]}...")
            return []
        
        # 2. 语义排序
        if self.store.use_vector_store:
            results = self._semantic_rank(context.query, candidates, context.min_score)
        else:
            # 无向量存储时使用简单的关键词匹配分数
            results = self._keyword_rank(context.query, candidates)
        
        # 3. 上下文重排序
        results = self._context_rerank(results, context)
        
        # 4. 截取top_k
        results = results[:context.top_k]
        
        logger.debug(f"Retrieved {len(results)} knowledge items for query: {context.query[:50]}...")
        return results
    
    def _keyword_filter(self, context: KnowledgeContext) -> list[KnowledgeItem]:
        """
        关键词预筛选
        
        基于类型、标签、范围进行快速过滤
        """
        # 构建搜索条件
        type_filter = context.types[0] if len(context.types) == 1 else None
        
        # 搜索
        items = self.store.search(
            type=type_filter,
            tags=context.tags if context.tags else None,
            scope=context.scope if context.scope else None,
            status="active",
            limit=100  # 预筛选获取较多候选
        )
        
        # 如果指定了多个类型，进一步过滤
        if len(context.types) > 1:
            items = [item for item in items if item.type in context.types]
        
        return items
    
    def _semantic_rank(
        self,
        query: str,
        candidates: list[KnowledgeItem],
        min_score: float
    ) -> list[KnowledgeSearchResult]:
        """
        语义相似度排序
        """
        # 获取候选ID
        candidate_ids = [item.knowledge_id for item in candidates]
        
        # 向量搜索
        vector_results = self.store.vector_search(
            query=query,
            top_k=len(candidates),
            filter_ids=candidate_ids
        )
        
        # 构建ID到分数的映射
        score_map = {kid: score for kid, score in vector_results}
        
        # 构建结果
        results = []
        for item in candidates:
            score = score_map.get(item.knowledge_id, 0.0)
            if score >= min_score:
                results.append(KnowledgeSearchResult(
                    item=item,
                    score=score,
                    source="semantic"
                ))
        
        # 按分数排序
        results.sort(reverse=True)
        return results
    
    def _keyword_rank(
        self,
        query: str,
        candidates: list[KnowledgeItem]
    ) -> list[KnowledgeSearchResult]:
        """
        关键词匹配排序（降级方案）
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        for item in candidates:
            # 计算简单的关键词匹配分数
            text = f"{item.title} {item.content}".lower()
            text_words = set(text.split())
            
            # 词重叠度
            overlap = len(query_words & text_words)
            max_words = max(len(query_words), 1)
            score = overlap / max_words
            
            # 标题匹配加分
            if query_lower in item.title.lower():
                score += 0.3
            
            if score > 0:
                results.append(KnowledgeSearchResult(
                    item=item,
                    score=min(score, 1.0),
                    source="keyword"
                ))
        
        results.sort(reverse=True)
        return results
    
    def _context_rerank(
        self,
        results: list[KnowledgeSearchResult],
        context: KnowledgeContext
    ) -> list[KnowledgeSearchResult]:
        """
        上下文重排序
        
        根据知识类型、范围匹配度等因素调整排名
        """
        for result in results:
            item = result.item
            
            # 1. 类型权重
            type_weight = self.type_weights.get(item.type, 1.0)
            
            # 2. 范围匹配加权
            scope_weight = 1.0
            if context.scope and item.scope:
                if context.scope == item.scope:
                    scope_weight = 1.3  # 精确匹配
                elif context.scope.startswith(item.scope):
                    scope_weight = 1.2  # 前缀匹配
                elif item.scope.startswith(context.scope):
                    scope_weight = 1.1  # 包含匹配
            
            # 3. 优先级加权
            priority_weight = 1 + item.priority * 0.05
            
            # 计算最终分数
            result.score = result.score * type_weight * scope_weight * priority_weight
        
        # 重新排序
        results.sort(reverse=True)
        return results
    
    def retrieve_for_test_generation(
        self,
        api_path: str,
        method: str = "",
        module: str = "",
        additional_context: str = ""
    ) -> list[KnowledgeSearchResult]:
        """
        为测试生成检索知识
        
        专门针对测试用例生成场景优化的检索方法
        """
        # 构建查询
        query_parts = [f"API接口 {method} {api_path}"]
        if module:
            query_parts.append(f"模块: {module}")
        if additional_context:
            query_parts.append(additional_context)
        query = " ".join(query_parts)
        
        # 构建标签
        tags = []
        if module:
            tags.append(module)
        
        # 从路径提取可能的标签
        path_parts = api_path.strip("/").split("/")
        for part in path_parts[:2]:  # 取前两级
            if part and not part.startswith("{"):  # 排除路径参数
                tags.append(part)
        
        # 检索
        context = KnowledgeContext(
            query=query,
            types=["project_config", "business_rule", "module_context"],
            tags=tags,
            scope=api_path,
            top_k=10,
            min_score=0.2
        )
        
        return self.retrieve(context)
    
    def retrieve_for_log_analysis(
        self,
        urls: list[str],
        error_messages: list[str] | None = None
    ) -> list[KnowledgeSearchResult]:
        """
        为日志分析检索知识
        """
        # 构建查询
        query_parts = []
        
        # 从URL提取关键信息
        for url in urls[:5]:  # 限制数量
            path = url.split("?")[0]
            query_parts.append(path)
        
        if error_messages:
            query_parts.extend(error_messages[:3])
        
        query = " ".join(query_parts)
        
        # 检索
        context = KnowledgeContext(
            query=query,
            types=["project_config", "business_rule", "test_experience"],
            top_k=8,
            min_score=0.25
        )
        
        return self.retrieve(context)
    
    def get_all_by_scope(self, scope: str) -> list[KnowledgeItem]:
        """
        获取指定范围的所有知识（不做相似度过滤）
        """
        return self.store.search(scope=scope, status="active", limit=50)
