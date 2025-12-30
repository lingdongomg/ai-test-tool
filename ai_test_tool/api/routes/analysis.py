"""
分析相关API路由
提供接口文档对比分析、RAG增强分析等功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from ...analyzer import ApiKnowledgeBase, RequestAnalyzer
from ...database import get_db_manager, ApiEndpoint, ApiTag
from ...llm.chains import LogAnalysisChain
from ...llm.provider import get_llm_provider


router = APIRouter(prefix="/analysis", tags=["分析"])


class CoverageAnalysisRequest(BaseModel):
    """覆盖分析请求"""
    urls: list[str] = Field(..., description="待分析的URL列表")
    methods: list[str] | None = Field(None, description="对应的HTTP方法列表")


class CoverageAnalysisResponse(BaseModel):
    """覆盖分析响应"""
    total_log_urls: int
    matched_count: int
    unmatched_count: int
    match_rate: str
    total_doc_endpoints: int
    called_endpoints: int
    uncalled_endpoints: int
    doc_coverage: str
    unmatched_urls: list[str]
    uncalled_endpoints_list: list[dict[str, Any]]


class DocComparisonRequest(BaseModel):
    """文档对比请求"""
    urls: list[str] = Field(..., description="待分析的URL列表")
    methods: list[str] | None = Field(None, description="对应的HTTP方法列表")
    include_ai_analysis: bool = Field(True, description="是否包含AI分析")


class TagSuggestionRequest(BaseModel):
    """标签建议请求"""
    url: str = Field(..., description="请求URL")
    method: str = Field("", description="HTTP方法")


class RAGContextRequest(BaseModel):
    """RAG上下文请求"""
    urls: list[str] = Field(..., description="URL列表")
    methods: list[str] | None = Field(None, description="HTTP方法列表")
    max_results: int = Field(20, description="最大结果数")


def _load_knowledge_base() -> ApiKnowledgeBase:
    """加载知识库"""
    kb = ApiKnowledgeBase()
    
    db = get_db_manager()
    
    # 加载所有端点
    sql = "SELECT * FROM api_endpoints"
    rows = db.fetch_all(sql)
    endpoints = [ApiEndpoint.from_dict(row) for row in rows]
    
    # 加载端点标签
    for ep in endpoints:
        tag_sql = """
            SELECT t.name FROM api_tags t
            JOIN api_endpoint_tags et ON t.id = et.tag_id
            WHERE et.endpoint_id = %s
        """
        tag_rows = db.fetch_all(tag_sql, (ep.endpoint_id,))
        ep.tags = [row['name'] for row in tag_rows]
    
    # 加载所有标签
    tag_sql = "SELECT * FROM api_tags"
    tag_rows = db.fetch_all(tag_sql)
    tags = [ApiTag.from_dict(row) for row in tag_rows]
    
    kb.load_from_endpoints(endpoints, tags)
    
    return kb


@router.post("/coverage", response_model=CoverageAnalysisResponse)
async def analyze_coverage(request: CoverageAnalysisRequest):
    """
    分析URL与接口文档的覆盖情况
    
    - 统计日志URL与文档的匹配情况
    - 识别未在文档中的URL（可能是第三方接口或文档遗漏）
    - 识别文档中未被调用的接口
    """
    kb = _load_knowledge_base()
    
    if kb.is_empty:
        raise HTTPException(status_code=400, detail="接口知识库为空，请先导入接口文档")
    
    result = kb.analyze_coverage(request.urls, request.methods)
    return result


@router.post("/doc-comparison")
async def compare_with_doc(request: DocComparisonRequest):
    """
    对比分析接口文档与实际日志
    
    - 分析文档完整性
    - 识别一致性问题
    - 识别第三方依赖
    - 提供改进建议
    """
    kb = _load_knowledge_base()
    
    if kb.is_empty:
        raise HTTPException(status_code=400, detail="接口知识库为空，请先导入接口文档")
    
    # 基础覆盖分析
    coverage_data = kb.analyze_coverage(request.urls, request.methods)
    
    result = {
        "coverage": coverage_data,
        "ai_analysis": None
    }
    
    # AI分析
    if request.include_ai_analysis:
        try:
            provider = get_llm_provider()
            chain = LogAnalysisChain(provider)
            
            api_doc_summary = kb.get_endpoints_summary(max_count=50)
            ai_result = chain.compare_with_api_doc(api_doc_summary, coverage_data)
            result["ai_analysis"] = ai_result
        except Exception as e:
            result["ai_analysis_error"] = str(e)
    
    return result


@router.post("/suggest-tags")
async def suggest_tags(request: TagSuggestionRequest):
    """
    根据URL建议标签
    
    基于接口文档知识库，为URL推荐合适的标签
    """
    kb = _load_knowledge_base()
    
    if kb.is_empty:
        return {"tags": [], "message": "接口知识库为空"}
    
    tags = kb.suggest_tags_for_url(request.url, request.method)
    
    # 同时返回匹配的接口信息
    matches = kb.search_by_url(request.url, request.method)
    matched_endpoints = [
        {
            "path": m.path,
            "method": m.method,
            "name": m.name,
            "tags": m.tags
        }
        for m in matches[:5]
    ]
    
    return {
        "suggested_tags": tags,
        "matched_endpoints": matched_endpoints
    }


@router.post("/rag-context")
async def get_rag_context(request: RAGContextRequest):
    """
    获取RAG上下文
    
    为一组URL构建接口文档上下文，可用于增强AI分析
    """
    kb = _load_knowledge_base()
    
    if kb.is_empty:
        return {"context": "", "message": "接口知识库为空"}
    
    context = kb.build_rag_context(
        request.urls,
        request.methods,
        request.max_results
    )
    
    return {
        "context": context,
        "knowledge_base_size": kb.size
    }


@router.get("/knowledge-base/stats")
async def get_knowledge_base_stats():
    """
    获取知识库统计信息
    """
    kb = _load_knowledge_base()
    
    return {
        "total_endpoints": kb.size,
        "is_empty": kb.is_empty,
        "tags": kb.get_all_tags(),
        "tag_statistics": kb.get_tag_statistics()
    }


@router.get("/knowledge-base/summary")
async def get_knowledge_base_summary(max_count: int = 100):
    """
    获取知识库摘要
    
    返回接口文档的概览信息，按标签分组
    """
    kb = _load_knowledge_base()
    
    if kb.is_empty:
        return {"summary": "接口知识库为空，请先导入接口文档"}
    
    return {
        "summary": kb.get_endpoints_summary(max_count)
    }


@router.post("/batch-categorize")
async def batch_categorize(request: CoverageAnalysisRequest):
    """
    批量分类URL
    
    使用知识库和AI对URL进行智能分类
    """
    kb = _load_knowledge_base()
    
    results = []
    for i, url in enumerate(request.urls):
        method = request.methods[i] if request.methods and i < len(request.methods) else ""
        
        # 从知识库获取建议
        suggested_tags = kb.suggest_tags_for_url(url, method) if not kb.is_empty else []
        matches = kb.search_by_url(url, method) if not kb.is_empty else []
        
        result = {
            "url": url,
            "method": method,
            "suggested_category": suggested_tags[0] if suggested_tags else "其他",
            "all_suggested_tags": suggested_tags,
            "source": "doc" if matches else "inferred",
            "matched_endpoint": {
                "path": matches[0].path,
                "name": matches[0].name
            } if matches else None
        }
        results.append(result)
    
    # 统计分类
    category_stats = {}
    for r in results:
        cat = r["suggested_category"]
        category_stats[cat] = category_stats.get(cat, 0) + 1
    
    return {
        "categorized": results,
        "statistics": category_stats,
        "from_doc_count": sum(1 for r in results if r["source"] == "doc"),
        "inferred_count": sum(1 for r in results if r["source"] == "inferred")
    }
