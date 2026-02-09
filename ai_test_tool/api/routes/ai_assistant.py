"""
AI 助手 API
统一的 AI 能力入口
"""

import uuid
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ...services import AIAssistantService
from ...database.repository import AIInsightRepository, TestCaseRepository, ChatSessionRepository, ChatMessageRepository
from ...utils.logger import get_logger
from ...exceptions import NotFoundError, LLMError
from ..dependencies import (
    get_ai_assistant_service,
    get_database,
    get_ai_insight_repository,
    get_test_case_repository,
    get_chat_session_repository,
    get_chat_message_repository,
)

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
async def chat_with_ai(
    request: ChatRequest,
    service: AIAssistantService = Depends(get_ai_assistant_service),
    session_repo: ChatSessionRepository = Depends(get_chat_session_repository),
    message_repo: ChatMessageRepository = Depends(get_chat_message_repository)
):
    """
    与 AI 助手对话

    支持的问题类型：
    - 接口相关问题
    - 测试建议
    - 异常分析
    - 性能优化建议
    """
    try:
        # 构建上下文
        context = request.context or {}
        session_id = request.session_id
        history_messages: list[dict] = []

        # 如果有 session_id，获取历史对话
        if session_id:
            session = session_repo.get_by_id(session_id)
            if session:
                # 获取最近的历史消息
                history_messages = message_repo.get_recent_by_session(session_id, limit=10)
            else:
                # 创建新会话
                session_repo.create(session_id, title=request.message[:50])
        else:
            # 生成新的会话ID
            session_id = f"chat_{uuid.uuid4().hex[:12]}"
            session_repo.create(session_id, title=request.message[:50])

        # 将历史消息添加到上下文
        if history_messages:
            context['chat_history'] = [
                {'role': msg['role'], 'content': msg['content']}
                for msg in history_messages
            ]

        # 保存用户消息
        user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        message_repo.create(user_msg_id, session_id, 'user', request.message)

        # 调用 AI 服务
        answer = service.ask_question(
            question=request.message,
            context=context
        )

        # 保存 AI 回复
        assistant_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        message_repo.create(assistant_msg_id, session_id, 'assistant', answer)

        # 更新会话消息计数
        session_repo.increment_message_count(session_id)
        session_repo.increment_message_count(session_id)

        return {
            "success": True,
            "message": request.message,
            "answer": answer,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"AI对话失败: {e}")
        raise LLMError(f"AI对话失败: {e}")


# ==================== 会话管理 ====================

@router.get("/sessions")
async def list_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    session_repo: ChatSessionRepository = Depends(get_chat_session_repository)
):
    """获取会话列表"""
    sessions = session_repo.list_recent(limit)
    return {
        "items": sessions,
        "total": len(sessions)
    }


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    session_repo: ChatSessionRepository = Depends(get_chat_session_repository),
    message_repo: ChatMessageRepository = Depends(get_chat_message_repository)
):
    """获取会话详情及消息历史"""
    session = session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError("会话", session_id)

    messages = message_repo.get_by_session(session_id, limit=100)
    return {
        "session": session,
        "messages": messages
    }


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    session_repo: ChatSessionRepository = Depends(get_chat_session_repository),
    message_repo: ChatMessageRepository = Depends(get_chat_message_repository)
):
    """删除会话"""
    session = session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError("会话", session_id)

    # 删除消息（外键级联删除也会处理，但显式删除更安全）
    message_repo.delete_by_session(session_id)
    session_repo.delete(session_id)

    return {"success": True, "message": "会话已删除"}


# ==================== Mock 数据生成 ====================

@router.post("/generate/mock")
async def generate_mock_data(
    request: GenerateMockRequest,
    service: AIAssistantService = Depends(get_ai_assistant_service)
):
    """为接口生成 Mock 数据"""
    try:
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
        raise NotFoundError("接口", request.endpoint_id)
    except Exception as e:
        logger.error(f"生成Mock数据失败: {e}")
        raise LLMError(f"生成Mock数据失败: {e}")


# ==================== 测试代码生成 ====================

@router.post("/generate/code")
async def generate_test_code(
    request: GenerateCodeRequest,
    service: AIAssistantService = Depends(get_ai_assistant_service)
):
    """为接口生成测试代码"""
    try:
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
        raise NotFoundError("接口", request.endpoint_id)
    except Exception as e:
        logger.error(f"生成测试代码失败: {e}")
        raise LLMError(f"生成测试代码失败: {e}")


# ==================== 智能分析 ====================

@router.post("/analyze/performance")
async def analyze_performance(
    request: AnalyzeRequest,
    service: AIAssistantService = Depends(get_ai_assistant_service)
):
    """分析性能趋势"""
    try:
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
        raise LLMError(f"性能分析失败: {e}")


@router.post("/analyze/coverage")
async def analyze_coverage(
    service: AIAssistantService = Depends(get_ai_assistant_service)
):
    """分析测试覆盖率缺口"""
    try:
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
        raise LLMError(f"覆盖率分析失败: {e}")


@router.post("/analyze/risk")
async def analyze_risk(
    service: AIAssistantService = Depends(get_ai_assistant_service)
):
    """分析高风险接口"""
    try:
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
        raise LLMError(f"风险分析失败: {e}")


# ==================== 智能建议 ====================

@router.get("/recommendations")
async def get_recommendations(
    type: str | None = Query(default=None, description="建议类型: test, monitor, fix"),
    limit: int = Query(default=10, ge=1, le=50),
    service: AIAssistantService = Depends(get_ai_assistant_service)
):
    """获取智能建议"""
    try:
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
        raise LLMError(f"获取建议失败: {e}")


# ==================== AI 洞察管理 ====================

@router.get("/insights")
async def list_insights(
    type: str | None = None,
    severity: str | None = None,
    is_resolved: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    insight_repo: AIInsightRepository = Depends(get_ai_insight_repository)
):
    """获取 AI 洞察列表"""
    insights, total = insight_repo.search_paginated(
        insight_type=type,
        severity=severity,
        is_resolved=is_resolved,
        page=page,
        page_size=page_size
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                'id': i.id,
                'insight_id': i.insight_id,
                'insight_type': i.insight_type,
                'title': i.title,
                'description': i.description,
                'severity': i.severity.value if hasattr(i.severity, 'value') else i.severity,
                'confidence': i.confidence,
                'details': i.details,
                'recommendations': i.recommendations,
                'is_resolved': i.is_resolved,
                'resolved_at': i.resolved_at,
                'created_at': i.created_at.isoformat() if i.created_at else None
            }
            for i in insights
        ]
    }


@router.get("/insights/{insight_id}")
async def get_insight(
    insight_id: str,
    insight_repo: AIInsightRepository = Depends(get_ai_insight_repository)
):
    """获取洞察详情"""
    insight = insight_repo.get_by_id(insight_id)

    if not insight:
        raise NotFoundError("洞察", insight_id)

    return {
        'id': insight.id,
        'insight_id': insight.insight_id,
        'insight_type': insight.insight_type,
        'title': insight.title,
        'description': insight.description,
        'severity': insight.severity.value if hasattr(insight.severity, 'value') else insight.severity,
        'confidence': insight.confidence,
        'details': insight.details,
        'recommendations': insight.recommendations,
        'is_resolved': insight.is_resolved,
        'resolved_at': insight.resolved_at,
        'created_at': insight.created_at.isoformat() if insight.created_at else None
    }


@router.patch("/insights/{insight_id}/resolve")
async def resolve_insight(
    insight_id: str,
    insight_repo: AIInsightRepository = Depends(get_ai_insight_repository)
):
    """标记洞察为已解决"""
    affected = insight_repo.resolve(insight_id)

    if affected == 0:
        raise NotFoundError("洞察", insight_id)

    return {"success": True, "message": "已标记为解决"}


@router.delete("/insights/{insight_id}")
async def delete_insight(
    insight_id: str,
    insight_repo: AIInsightRepository = Depends(get_ai_insight_repository)
):
    """删除洞察"""
    affected = insight_repo.delete(insight_id)

    if affected == 0:
        raise NotFoundError("洞察", insight_id)

    return {"success": True, "message": "删除成功"}


# ==================== 统计 ====================

@router.get("/statistics")
async def get_ai_statistics(
    insight_repo: AIInsightRepository = Depends(get_ai_insight_repository),
    test_case_repo: TestCaseRepository = Depends(get_test_case_repository)
):
    """获取 AI 功能统计"""
    # 洞察统计
    insight_stats = insight_repo.get_statistics()

    # AI 生成的测试用例统计
    ai_cases_count = test_case_repo.count("is_ai_generated = 1")

    return {
        "insights": {
            "total": insight_stats['total'],
            "unresolved": insight_stats['unresolved'],
            "by_severity": insight_stats['by_severity']
        },
        "by_type": insight_stats['by_type'],
        "ai_generated_cases": ai_cases_count
    }
