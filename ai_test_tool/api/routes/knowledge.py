# 该文件内容使用AI生成，注意识别准确性
"""
知识库管理API
提供知识的CRUD、检索、审核等接口
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Any

from ...knowledge import (
    KnowledgeStore,
    KnowledgeRetriever,
    RAGContextBuilder,
    KnowledgeLearner
)
from ...knowledge.models import KnowledgeContext
from ...utils.logger import get_logger
from ..dependencies import (
    get_knowledge_store,
    get_knowledge_retriever,
    get_rag_context_builder,
    get_knowledge_learner
)

logger = get_logger()
router = APIRouter(tags=["知识库"])


# ============== 请求/响应模型 ==============

class KnowledgeCreateRequest(BaseModel):
    """创建知识请求"""
    title: str = Field(..., description="知识标题")
    content: str = Field(..., description="知识内容")
    type: str = Field(default="project_config", description="知识类型")
    category: str = Field(default="", description="子分类")
    scope: str = Field(default="", description="适用范围")
    priority: int = Field(default=0, description="优先级")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class KnowledgeUpdateRequest(BaseModel):
    """更新知识请求"""
    title: str | None = None
    content: str | None = None
    category: str | None = None
    scope: str | None = None
    priority: int | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeSearchRequest(BaseModel):
    """知识检索请求"""
    query: str = Field(..., description="查询文本")
    types: list[str] = Field(default_factory=list, description="限制知识类型")
    tags: list[str] = Field(default_factory=list, description="限制标签")
    scope: str = Field(default="", description="限制范围")
    top_k: int = Field(default=5, description="返回数量")
    min_score: float = Field(default=0.3, description="最低相似度阈值")


class BatchReviewRequest(BaseModel):
    """批量审核请求"""
    knowledge_ids: list[str] = Field(..., description="知识ID列表")
    action: str = Field(..., description="操作: approve/reject")


class LearnRequest(BaseModel):
    """知识学习请求"""
    content: str = Field(..., description="要分析的内容")
    source_ref: str = Field(default="", description="来源引用")
    auto_approve: bool = Field(default=False, description="是否自动审核通过")


# ============== 接口实现 ==============

@router.get("")
async def list_knowledge(
    type: str | None = Query(None, description="知识类型"),
    status: str | None = Query(None, description="状态"),
    tags: str | None = Query(None, description="标签(逗号分隔)"),
    scope: str | None = Query(None, description="范围"),
    keyword: str | None = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """获取知识列表"""
    tag_list = tags.split(",") if tags else None

    items, total = store.search_paginated(
        type=type,
        status=status,
        tags=tag_list,
        scope=scope,
        keyword=keyword,
        page=page,
        page_size=page_size
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "knowledge_id": item.knowledge_id,
                "title": item.title,
                "content": item.content,
                "type": item.type,
                "category": item.category,
                "scope": item.scope,
                "priority": item.priority,
                "tags": item.tags,
                "metadata": item.metadata
            }
            for item in items
        ]
    }


@router.get("/pending")
async def list_pending_knowledge(
    limit: int = Query(50, ge=1, le=200),
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """获取待审核知识列表"""
    items = store.get_pending(limit)

    return {
        "total": len(items),
        "items": [
            {
                "knowledge_id": item.knowledge_id,
                "title": item.title,
                "content": item.content,
                "type": item.type,
                "category": item.category,
                "scope": item.scope,
                "tags": item.tags
            }
            for item in items
        ]
    }


@router.get("/statistics")
async def get_statistics(
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """获取知识库统计信息"""
    return store.get_statistics()


@router.get("/{knowledge_id}")
async def get_knowledge(
    knowledge_id: str,
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """获取单个知识详情"""
    item = store.get(knowledge_id)

    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    return {
        "knowledge_id": item.knowledge_id,
        "title": item.title,
        "content": item.content,
        "type": item.type,
        "category": item.category,
        "scope": item.scope,
        "priority": item.priority,
        "tags": item.tags,
        "metadata": item.metadata
    }


@router.post("", status_code=201)
async def create_knowledge(
    request: KnowledgeCreateRequest,
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """创建知识条目"""
    item = store.create(
        title=request.title,
        content=request.content,
        type=request.type,
        category=request.category,
        scope=request.scope,
        priority=request.priority,
        tags=request.tags,
        metadata=request.metadata
    )

    logger.info(f"Created knowledge: {item.knowledge_id}")

    return {
        "knowledge_id": item.knowledge_id,
        "title": item.title,
        "message": "Knowledge created successfully"
    }


@router.put("/{knowledge_id}")
async def update_knowledge(
    knowledge_id: str,
    request: KnowledgeUpdateRequest,
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """更新知识条目"""
    item = store.update(
        knowledge_id=knowledge_id,
        title=request.title,
        content=request.content,
        category=request.category,
        scope=request.scope,
        priority=request.priority,
        tags=request.tags,
        metadata=request.metadata
    )

    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    return {
        "knowledge_id": item.knowledge_id,
        "title": item.title,
        "message": "Knowledge updated successfully"
    }


@router.delete("/{knowledge_id}", status_code=204)
async def delete_knowledge(
    knowledge_id: str,
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> None:
    """删除知识条目（归档）"""
    success = store.archive(knowledge_id)
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge not found")


@router.post("/review")
async def batch_review(
    request: BatchReviewRequest,
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """批量审核知识"""
    if request.action == "approve":
        count = store.approve(request.knowledge_ids)
        message = f"Approved {count} knowledge entries"
    elif request.action == "reject":
        count = store.reject(request.knowledge_ids)
        message = f"Rejected {count} knowledge entries"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    return {
        "action": request.action,
        "count": count,
        "message": message
    }


@router.post("/search")
async def search_knowledge(
    request: KnowledgeSearchRequest,
    retriever: KnowledgeRetriever = Depends(get_knowledge_retriever),
    rag_builder: RAGContextBuilder = Depends(get_rag_context_builder)
) -> dict[str, Any]:
    """语义检索知识"""
    context = KnowledgeContext(
        query=request.query,
        types=request.types,
        tags=request.tags,
        scope=request.scope,
        top_k=request.top_k,
        min_score=request.min_score
    )

    results = retriever.retrieve(context)

    # 构建RAG上下文预览
    rag_context = rag_builder.build(results)

    return {
        "total": len(results),
        "items": [
            {
                "knowledge_id": r.item.knowledge_id,
                "title": r.item.title,
                "content": r.item.content,
                "type": r.item.type,
                "scope": r.item.scope,
                "tags": r.item.tags,
                "score": round(r.score, 4),
                "source": r.source
            }
            for r in results
        ],
        "rag_context_preview": rag_context.context_text[:500] + "..." if len(rag_context.context_text) > 500 else rag_context.context_text,
        "token_count": rag_context.token_count
    }


@router.post("/learn")
async def learn_knowledge(
    request: LearnRequest,
    learner: KnowledgeLearner = Depends(get_knowledge_learner)
) -> dict[str, Any]:
    """从内容中学习知识"""
    created_ids = learner.learn_and_save(
        content=request.content,
        source_ref=request.source_ref,
        auto_approve=request.auto_approve
    )

    return {
        "created_count": len(created_ids),
        "knowledge_ids": created_ids,
        "message": f"Extracted and saved {len(created_ids)} knowledge entries"
    }


@router.post("/rebuild-index")
async def rebuild_vector_index(
    store: KnowledgeStore = Depends(get_knowledge_store)
) -> dict[str, Any]:
    """重建向量索引"""
    count = store.rebuild_vector_index()

    return {
        "indexed_count": count,
        "message": f"Rebuilt vector index for {count} entries"
    }
