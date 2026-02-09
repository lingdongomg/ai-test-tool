"""
线上监控模块 API
场景二：线上质量巡检
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import json
import uuid

from ...services import ProductionMonitorService, AIAssistantService
from ...database.repository import (
    ProductionRequestRepository,
    HealthCheckExecutionRepository,
    HealthCheckResultRepository,
    AIInsightRepository,
    SystemConfigRepository,
)
from ...database.models import ProductionRequest
from ...utils.logger import get_logger
from ...utils.sql_security import build_safe_like
from ...exceptions import NotFoundError, ExternalServiceError
from ..dependencies import (
    get_production_monitor_service,
    get_database,
    get_production_request_repository,
    get_health_check_execution_repository,
    get_health_check_result_repository,
    get_ai_insight_repository,
    get_system_config_repository,
)

router = APIRouter()
logger = get_logger()

# 配置键常量
SCHEDULE_CONFIG_KEY = "health_check_schedule"


# ==================== 请求/响应模型 ====================

class ExtractRequestsRequest(BaseModel):
    """从日志提取请求"""
    task_id: str = Field(..., description="日志分析任务ID")
    min_success_rate: float = Field(default=0.9, ge=0, le=1, description="最小成功率过滤")
    max_requests_per_endpoint: int = Field(default=5, ge=1, le=20, description="每接口最大请求数")
    tags: list[str] | None = Field(default=None, description="添加的标签")


class AddMonitorRequest(BaseModel):
    """手动添加监控请求"""
    method: str = Field(..., description="HTTP方法")
    url: str = Field(..., description="请求URL")
    headers: dict | None = Field(default=None, description="请求头")
    body: str | None = Field(default=None, description="请求体")
    query_params: dict | None = Field(default=None, description="查询参数")
    expected_status_code: int = Field(default=200, description="期望状态码")
    expected_response_pattern: str | None = Field(default=None, description="期望响应正则")
    tags: list[str] | None = Field(default=None, description="标签")
    description: str | None = Field(default=None, description="描述")


class HealthCheckRequest(BaseModel):
    """执行健康检查"""
    base_url: str = Field(..., description="目标服务器URL")
    request_ids: list[str] | None = Field(default=None, description="指定请求ID列表")
    tag_filter: str | None = Field(default=None, description="按标签筛选")
    use_ai_validation: bool = Field(default=True, description="是否使用AI验证返回结果")
    timeout_seconds: int = Field(default=30, ge=5, le=120, description="超时时间")
    parallel: int = Field(default=5, ge=1, le=20, description="并发数")


class ScheduleConfig(BaseModel):
    """定时任务配置"""
    enabled: bool = Field(default=True, description="是否启用")
    cron: str = Field(default="0 */1 * * *", description="Cron表达式")
    base_url: str = Field(..., description="目标服务器URL")
    use_ai_validation: bool = Field(default=True, description="是否使用AI验证")
    alert_on_failure: bool = Field(default=True, description="失败时告警")
    alert_threshold: int = Field(default=3, ge=1, description="连续失败告警阈值")


# ==================== 监控用例库管理 ====================

@router.get("/requests")
async def list_monitor_requests(
    tag: str | None = None,
    is_enabled: bool | None = None,
    last_status: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    request_repo: ProductionRequestRepository = Depends(get_production_request_repository)
):
    """获取监控请求列表"""
    requests, total = request_repo.search_paginated(
        tag=tag,
        is_enabled=is_enabled,
        last_status=last_status,
        search=search,
        page=page,
        page_size=page_size
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [r.to_dict() for r in requests]
    }


@router.get("/requests/{request_id}")
async def get_monitor_request(
    request_id: str,
    request_repo: ProductionRequestRepository = Depends(get_production_request_repository),
    result_repo: HealthCheckResultRepository = Depends(get_health_check_result_repository)
):
    """获取监控请求详情"""
    request = request_repo.get_by_id(request_id)

    if not request:
        raise NotFoundError("监控请求", request_id)

    # 获取最近检查记录
    history = result_repo.get_by_request(request_id, limit=50)

    return {
        "request": request.to_dict(),
        "check_history": [h.to_dict() for h in history]
    }


@router.post("/requests")
async def add_monitor_request(
    request: AddMonitorRequest,
    request_repo: ProductionRequestRepository = Depends(get_production_request_repository)
):
    """手动添加监控请求"""
    request_id = str(uuid.uuid4())[:8]

    prod_request = ProductionRequest(
        request_id=request_id,
        method=request.method.upper(),
        url=request.url,
        headers=json.dumps(request.headers) if request.headers else None,
        body=request.body,
        query_params=json.dumps(request.query_params) if request.query_params else None,
        expected_status_code=request.expected_status_code,
        expected_response_pattern=request.expected_response_pattern,
        tags=json.dumps(request.tags) if request.tags else None,
        source="manual"
    )

    request_repo.create(prod_request)

    return {
        "success": True,
        "request_id": request_id,
        "message": "监控请求添加成功"
    }


@router.post("/requests/extract")
async def extract_from_log(
    request: ExtractRequestsRequest,
    service: ProductionMonitorService = Depends(get_production_monitor_service)
):
    """从日志分析任务中提取请求到监控库"""
    try:
        result = service.extract_requests_from_log(
            task_id=request.task_id,
            min_success_rate=request.min_success_rate,
            max_requests_per_endpoint=request.max_requests_per_endpoint,
            tags=request.tags
        )
        return {
            "success": True,
            "message": f"成功提取 {result['saved']} 个请求到监控库",
            "total": result['total'],
            "saved": result['saved'],
            "skipped": result['skipped'],
            "details": result.get('details', [])
        }
    except ValueError as e:
        raise NotFoundError("任务", request.task_id)
    except Exception as e:
        logger.error(f"提取请求失败: {e}")
        raise ExternalServiceError(f"提取请求失败: {e}")


@router.put("/requests/{request_id}")
async def update_monitor_request(
    request_id: str,
    request: AddMonitorRequest,
    request_repo: ProductionRequestRepository = Depends(get_production_request_repository)
):
    """更新监控请求"""
    updates = {
        'method': request.method.upper(),
        'url': request.url,
        'headers': json.dumps(request.headers) if request.headers else None,
        'body': request.body,
        'query_params': json.dumps(request.query_params) if request.query_params else None,
        'expected_status_code': request.expected_status_code,
        'expected_response_pattern': request.expected_response_pattern,
        'tags': json.dumps(request.tags) if request.tags else None,
    }

    affected = request_repo.update(request_id, updates)

    if affected == 0:
        raise NotFoundError("监控请求", request_id)

    return {"success": True, "message": "更新成功"}


@router.delete("/requests/{request_id}")
async def delete_monitor_request(
    request_id: str,
    request_repo: ProductionRequestRepository = Depends(get_production_request_repository)
):
    """删除监控请求"""
    affected = request_repo.delete(request_id)

    if affected == 0:
        raise NotFoundError("监控请求", request_id)

    return {"success": True, "message": "删除成功"}


@router.patch("/requests/{request_id}/toggle")
async def toggle_monitor_request(
    request_id: str,
    is_enabled: bool,
    request_repo: ProductionRequestRepository = Depends(get_production_request_repository)
):
    """启用/禁用监控请求"""
    affected = request_repo.set_enabled(request_id, is_enabled)

    if affected == 0:
        raise NotFoundError("监控请求", request_id)

    return {"success": True, "is_enabled": is_enabled}


# ==================== 健康检查执行 ====================

@router.post("/health-check")
async def run_health_check(
    request: HealthCheckRequest,
    background_tasks: BackgroundTasks,
    service: ProductionMonitorService = Depends(get_production_monitor_service)
):
    """执行健康检查"""
    try:
        result = service.run_health_check(
            base_url=request.base_url,
            request_ids=request.request_ids,
            tag_filter=request.tag_filter,
            use_ai_validation=request.use_ai_validation,
            timeout_seconds=request.timeout_seconds,
            parallel=request.parallel
        )
        return {
            "success": True,
            "execution_id": result['execution_id'],
            "total": result['total'],
            "healthy": result['healthy'],
            "unhealthy": result['unhealthy'],
            "health_rate": result['health_rate'],
            "duration_ms": result.get('duration_ms', 0),
            "status": result['status'],
            "results": result.get('results', [])
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check/executions")
async def list_health_check_executions(
    status: str | None = None,
    trigger_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    execution_repo: HealthCheckExecutionRepository = Depends(get_health_check_execution_repository)
):
    """获取健康检查执行记录"""
    executions, total = execution_repo.search_paginated(
        status=status,
        trigger_type=trigger_type,
        page=page,
        page_size=page_size
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [e.to_dict() for e in executions]
    }


@router.get("/health-check/executions/{execution_id}")
async def get_health_check_execution(
    execution_id: str,
    execution_repo: HealthCheckExecutionRepository = Depends(get_health_check_execution_repository),
    result_repo: HealthCheckResultRepository = Depends(get_health_check_result_repository)
):
    """获取健康检查执行详情"""
    execution = execution_repo.get_by_id(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # 获取详细结果（包含请求信息）
    results = result_repo.get_by_execution_with_request_details(execution_id)

    return {
        "execution": execution.to_dict(),
        "results": results
    }


# ==================== 健康状态概览 ====================

@router.get("/summary")
async def get_health_summary(
    days: int = Query(default=7, ge=1, le=30),
    service: ProductionMonitorService = Depends(get_production_monitor_service)
):
    """获取健康状态摘要"""
    try:
        return service.get_health_summary(days=days)
    except Exception as e:
        logger.error(f"获取健康摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_monitoring_statistics(
    request_repo: ProductionRequestRepository = Depends(get_production_request_repository),
    result_repo: HealthCheckResultRepository = Depends(get_health_check_result_repository)
):
    """获取监控统计数据"""
    # 监控请求统计
    request_stats = request_repo.get_statistics()

    # 今日检查统计
    today_stats = result_repo.get_today_statistics()

    # 近7天趋势
    trend = result_repo.get_trend(days=7)

    return {
        "requests": request_stats,
        "today": today_stats,
        "trend": trend
    }


# ==================== 定时任务配置 ====================

@router.get("/schedule")
async def get_schedule_config(
    config_repo: SystemConfigRepository = Depends(get_system_config_repository)
):
    """获取定时巡检配置"""
    default_config = {
        "enabled": False,
        "cron": "0 */1 * * *",
        "base_url": "",
        "use_ai_validation": True,
        "alert_on_failure": True,
        "alert_threshold": 3,
        "last_run": None,
        "next_run": None
    }
    saved_config = config_repo.get(SCHEDULE_CONFIG_KEY, default_config)
    # 合并默认配置（确保新字段有值）
    return {**default_config, **saved_config}


@router.put("/schedule")
async def update_schedule_config(
    config: ScheduleConfig,
    config_repo: SystemConfigRepository = Depends(get_system_config_repository)
):
    """更新定时巡检配置"""
    config_data = config.model_dump()

    # 保存到数据库
    config_repo.set(
        SCHEDULE_CONFIG_KEY,
        config_data,
        description="健康检查定时任务配置"
    )

    logger.info(f"定时巡检配置已更新: enabled={config.enabled}, cron={config.cron}")

    return {
        "success": True,
        "message": "配置已更新",
        "config": config_data
    }


# ==================== 告警配置 ====================

@router.get("/alerts")
async def list_alerts(
    is_resolved: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    insight_repo: AIInsightRepository = Depends(get_ai_insight_repository)
):
    """获取告警列表"""
    # 从 ai_insights 表获取告警类型的洞察
    alert_types = ['health_alert', 'consecutive_failure']
    insights, total = insight_repo.get_by_types(
        types=alert_types,
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


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    insight_repo: AIInsightRepository = Depends(get_ai_insight_repository)
):
    """标记告警为已解决"""
    affected = insight_repo.resolve(alert_id)

    if affected == 0:
        raise HTTPException(status_code=404, detail="告警不存在")

    return {"success": True, "message": "告警已标记为解决"}
