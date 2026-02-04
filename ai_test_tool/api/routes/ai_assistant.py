"""
AI 助手 API
统一的 AI 能力入口
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services import AIAssistantService
from ...database import get_db_manager
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger()


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    context: dict[str, Any] | None = Field(default=None, description="上下文信息")
    session_id: str | None = Field(default=None, description="会话ID")


class GenerateMockRequest(BaseModel):
    """生成Mock数据请求"""
    endpoint_id: str = Field(..., description="接口ID")
    count: int = Field(default=5, ge=1, le=20, description="生成数量")
    scenario: str | None = Field(default=None, description="场景描述")


class GenerateCodeRequest(BaseModel):
    """生成测试代码请求"""
    endpoint_id: str = Field(..., description="接口ID")
    language: str = Field(default="python", description="编程语言: python, javascript, java")
    framework: str = Field(default="pytest", description="测试框架")
    include_comments: bool = Field(default=True, description="是否包含注释")


class AnalyzeRequest(BaseModel):
    """分析请求"""
    type: str = Field(..., description="分析类型: performance, coverage, risk")
    target_id: str | None = Field(default=None, description="目标ID")
    days: int = Field(default=7, ge=1, le=30, description="时间范围")


# ==================== 智能对话 ====================

@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """
    与 AI 助手对话
    
    支持的问题类型：
    - 接口相关问题
    - 测试建议
    - 异常分析
    - 性能优化建议
    """
    try:
        service = AIAssistantService(verbose=True)
        
        # 构建上下文
        context = request.context or {}
        
        # 如果有 session_id，获取历史对话
        if request.session_id:
            # TODO: 实现对话历史存储
            pass
        
        answer = service.ask_question(
            question=request.message,
            context=context
        )
        
        return {
            "success": True,
            "message": request.message,
            "answer": answer,
            "session_id": request.session_id
        }
    
    except Exception as e:
        logger.error(f"AI对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Mock 数据生成 ====================

@router.post("/generate/mock")
async def generate_mock_data(request: GenerateMockRequest):
    """为接口生成 Mock 数据"""
    try:
        service = AIAssistantService(verbose=True)
        result = service.generate_mock_data(
            endpoint_id=request.endpoint_id,
            count=request.count,
            scenario=request.scenario
        )
        return {
            "success": True,
            "endpoint_id": request.endpoint_id,
            "count": request.count,
            "data": result.get('mock_data', []),
            "schema": result.get('schema')
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"生成Mock数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 测试代码生成 ====================

@router.post("/generate/code")
async def generate_test_code(request: GenerateCodeRequest):
    """为接口生成测试代码"""
    try:
        service = AIAssistantService(verbose=True)
        code = service.generate_test_code(
            endpoint_id=request.endpoint_id,
            language=request.language,
            framework=request.framework,
            include_comments=request.include_comments
        )
        return {
            "success": True,
            "endpoint_id": request.endpoint_id,
            "language": request.language,
            "framework": request.framework,
            "code": code
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"生成测试代码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 智能分析 ====================

@router.post("/analyze/performance")
async def analyze_performance(request: AnalyzeRequest):
    """分析性能趋势"""
    try:
        service = AIAssistantService(verbose=True)
        insights = service.analyze_performance_trend(
            endpoint_id=request.target_id,
            days=request.days
        )
        return {
            "success": True,
            "type": "performance",
            "insights": [
                {
                    "id": i.insight_id,
                    "type": i.insight_type.value if hasattr(i.insight_type, 'value') else i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "confidence": i.confidence,
                    "details": i.details,
                    "recommendations": i.recommendations
                }
                for i in insights
            ]
        }
    except Exception as e:
        logger.error(f"性能分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/coverage")
async def analyze_coverage():
    """分析测试覆盖率缺口"""
    try:
        service = AIAssistantService(verbose=True)
        insights = service.analyze_coverage_gaps()
        return {
            "success": True,
            "type": "coverage",
            "insights": [
                {
                    "id": i.insight_id,
                    "type": i.insight_type.value if hasattr(i.insight_type, 'value') else i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "details": i.details,
                    "recommendations": i.recommendations
                }
                for i in insights
            ]
        }
    except Exception as e:
        logger.error(f"覆盖率分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/risk")
async def analyze_risk():
    """分析高风险接口"""
    try:
        service = AIAssistantService(verbose=True)
        insights = service.identify_high_risk_endpoints()
        return {
            "success": True,
            "type": "risk",
            "insights": [
                {
                    "id": i.insight_id,
                    "type": i.insight_type.value if hasattr(i.insight_type, 'value') else i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "details": i.details,
                    "recommendations": i.recommendations
                }
                for i in insights
            ]
        }
    except Exception as e:
        logger.error(f"风险分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 智能建议 ====================

@router.get("/recommendations")
async def get_recommendations(
    type: str | None = Query(default=None, description="建议类型: test, monitor, fix"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """获取智能建议"""
    try:
        service = AIAssistantService(verbose=True)
        insights = service.get_test_recommendations()
        
        # 按类型筛选
        if type:
            insights = [i for i in insights if type in i.insight_type.value]
        
        return {
            "success": True,
            "recommendations": [
                {
                    "id": i.insight_id,
                    "type": i.insight_type.value if hasattr(i.insight_type, 'value') else i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "confidence": i.confidence,
                    "details": i.details,
                    "recommendations": i.recommendations
                }
                for i in insights[:limit]
            ]
        }
    except Exception as e:
        logger.error(f"获取建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI 洞察管理 ====================

@router.get("/insights")
async def list_insights(
    type: str | None = None,
    severity: str | None = None,
    is_resolved: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取 AI 洞察列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if type:
        conditions.append("insight_type = %s")
        params.append(type)
    
    if severity:
        conditions.append("severity = %s")
        params.append(severity)
    
    if is_resolved is not None:
        conditions.append("is_resolved = %s")
        params.append(is_resolved)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    count_sql = f"SELECT COUNT(*) as count FROM ai_insights {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM ai_insights
        {where_clause}
        ORDER BY 
            CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
            created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(sql, tuple(params))
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [dict(row) for row in rows]
    }


@router.get("/insights/{insight_id}")
async def get_insight(insight_id: str):
    """获取洞察详情"""
    db = get_db_manager()
    
    sql = "SELECT * FROM ai_insights WHERE insight_id = %s"
    row = db.fetch_one(sql, (insight_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="洞察不存在")
    
    return dict(row)


@router.patch("/insights/{insight_id}/resolve")
async def resolve_insight(insight_id: str):
    """标记洞察为已解决"""
    db = get_db_manager()
    
    sql = """
        UPDATE ai_insights 
        SET is_resolved = 1, resolved_at = datetime('now') 
        WHERE insight_id = %s
    """
    affected = db.execute(sql, (insight_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="洞察不存在")
    
    return {"success": True, "message": "已标记为解决"}


@router.delete("/insights/{insight_id}")
async def delete_insight(insight_id: str):
    """删除洞察"""
    db = get_db_manager()
    
    sql = "DELETE FROM ai_insights WHERE insight_id = %s"
    affected = db.execute(sql, (insight_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="洞察不存在")
    
    return {"success": True, "message": "删除成功"}


# ==================== 统计 ====================

@router.get("/statistics")
async def get_ai_statistics():
    """获取 AI 功能统计"""
    db = get_db_manager()
    
    # 洞察统计
    insight_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) as unresolved,
            SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low
        FROM ai_insights
    """)
    
    # 按类型统计
    type_stats = db.fetch_all("""
        SELECT 
            insight_type,
            COUNT(*) as count
        FROM ai_insights
        GROUP BY insight_type
        ORDER BY count DESC
    """)
    
    # AI 生成的测试用例统计（test_cases 表没有 is_ai_generated 列）
    ai_cases = db.fetch_one("""
        SELECT COUNT(*) as count FROM test_cases WHERE JSON_CONTAINS(tags, '"ai-generated"')
    """)
    
    return {
        "insights": {
            "total": insight_stats['total'] if insight_stats else 0,
            "unresolved": insight_stats['unresolved'] if insight_stats else 0,
            "by_severity": {
                "high": insight_stats['high'] if insight_stats else 0,
                "medium": insight_stats['medium'] if insight_stats else 0,
                "low": insight_stats['low'] if insight_stats else 0
            }
        },
        "by_type": [
            {"type": t['insight_type'], "count": t['count']}
            for t in type_stats
        ],
        "ai_generated_cases": ai_cases['count'] if ai_cases else 0
    }
