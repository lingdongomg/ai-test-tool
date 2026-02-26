"""
智能分析模块 API
场景四：智能路由分析（自动场景识别 + 策略匹配 + 执行）
"""

import json
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...services.intelligent_analysis import IntelligentAnalysisService
from ...react.engine import create_react_engine
from ...utils.logger import get_logger
from ..dependencies import get_intelligent_analysis_service

router = APIRouter()
logger = get_logger()


# ==================== 请求/响应模型 ====================

class AnalyzeRequest(BaseModel):
    """智能分析请求"""
    log_content: str | None = Field(default=None, description="日志内容")
    requests: list[dict[str, Any]] | None = Field(default=None, description="解析后的请求列表")
    metrics: dict[str, float] | None = Field(default=None, description="统计指标（如 error_rate, p99_latency_ms）")
    user_hint: str = Field(default="", description="用户提示，如: 分析错误、查看性能")
    task_id: str = Field(default="", description="关联的任务ID")
    options: dict[str, Any] | None = Field(default=None, description="额外选项（execute_all, max_strategies）")


class DetectRequest(BaseModel):
    """场景检测请求"""
    log_content: str | None = Field(default=None, description="日志内容")
    requests: list[dict[str, Any]] | None = Field(default=None, description="解析后的请求列表")
    metrics: dict[str, float] | None = Field(default=None, description="统计指标")
    user_hint: str = Field(default="", description="用户提示")


# ==================== 智能分析 ====================

@router.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    service: IntelligentAnalysisService = Depends(get_intelligent_analysis_service),
):
    """
    智能路由分析入口

    自动识别分析场景并执行匹配的策略。支持的场景包括：
    - 错误分析、性能分析、安全分析、流量分析
    - API覆盖率、健康检查、根因分析、异常检测

    传入 log_content / requests / metrics / user_hint 中的任意组合，
    系统会自动识别最匹配的场景并执行对应策略。
    """
    if not request.log_content and not request.requests and not request.metrics and not request.user_hint:
        raise HTTPException(
            status_code=400,
            detail="请至少提供 log_content、requests、metrics 或 user_hint 中的一个"
        )

    try:
        result = service.analyze(
            log_content=request.log_content or "",
            requests=request.requests,
            metrics=request.metrics,
            user_hint=request.user_hint,
            task_id=request.task_id,
            options=request.options,
        )
        return result
    except Exception as e:
        logger.error(f"智能分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")


# ==================== 场景检测 ====================

@router.post("/detect")
async def detect_scenarios(
    request: DetectRequest,
    service: IntelligentAnalysisService = Depends(get_intelligent_analysis_service),
):
    """
    仅检测分析场景，不执行策略

    返回检测到的场景列表及置信度，用于预览路由器会选择哪些策略。
    """
    if not request.log_content and not request.requests and not request.metrics and not request.user_hint:
        raise HTTPException(
            status_code=400,
            detail="请至少提供 log_content、requests、metrics 或 user_hint 中的一个"
        )

    try:
        scenarios = service.detect_scenarios(
            log_content=request.log_content or "",
            requests=request.requests,
            metrics=request.metrics,
            user_hint=request.user_hint,
        )
        return {
            "total": len(scenarios),
            "scenarios": scenarios,
        }
    except Exception as e:
        logger.error(f"场景检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {e}")


# ==================== 策略查询 ====================

@router.get("/strategies")
async def list_strategies(
    scenario_type: str | None = Query(default=None, description="按场景类型过滤（如 error_analysis, performance, security）"),
    service: IntelligentAnalysisService = Depends(get_intelligent_analysis_service),
):
    """
    查询可用的分析策略列表

    返回所有已注册的策略，支持按场景类型过滤。
    """
    strategies = service.get_available_strategies(scenario_type=scenario_type)
    return {
        "total": len(strategies),
        "strategies": strategies,
    }


# ==================== 路由统计 ====================

@router.get("/statistics")
async def get_statistics(
    service: IntelligentAnalysisService = Depends(get_intelligent_analysis_service),
):
    """
    获取智能路由统计信息

    包含路由执行次数、成功率、回退使用次数、注册表状态等。
    """
    return service.get_statistics()


# ==================== ReAct 流式分析 ====================

class ReactStreamRequest(BaseModel):
    """ReAct 流式分析请求"""
    task: str = Field(..., min_length=1, description="分析任务描述")
    log_content: str | None = Field(default=None, description="日志内容")
    requests: list[dict[str, Any]] | None = Field(default=None, description="请求数据")
    max_iterations: int = Field(default=10, ge=1, le=20, description="最大迭代次数")


@router.post("/react/stream")
async def react_stream(request: ReactStreamRequest):
    """
    ReAct 流式分析

    通过 SSE (Server-Sent Events) 实时推送 ReAct 推理过程，
    包括每一步的思考、行动和观察结果。

    事件类型: started, step_start, thought, action, observation, step_end, finished, error
    """
    from ...react.models import ReActConfig

    config = ReActConfig(max_iterations=request.max_iterations)
    engine = create_react_engine(config=config)

    async def event_generator():
        async for event in engine.run_stream(
            task=request.task,
            log_content=request.log_content or "",
            requests=request.requests,
        ):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
