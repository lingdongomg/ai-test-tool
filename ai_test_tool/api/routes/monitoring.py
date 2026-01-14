"""
线上监控模块 API
场景二：线上质量巡检
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import json

from ...services import ProductionMonitorService, AIAssistantService
from ...database import get_db_manager
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger()


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
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取监控请求列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if is_enabled is not None:
        conditions.append("is_enabled = %s")
        params.append(is_enabled)
    
    if tag:
        conditions.append("JSON_CONTAINS(tags, %s)")
        params.append(json.dumps(tag))
    
    if last_status:
        conditions.append("last_check_status = %s")
        params.append(last_status)
    
    if search:
        conditions.append("url LIKE %s")
        params.append(f"%{search}%")
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM production_requests {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM production_requests
        {where_clause}
        ORDER BY CASE WHEN last_check_at IS NULL THEN 1 ELSE 0 END, last_check_at DESC, created_at DESC
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


@router.get("/requests/{request_id}")
async def get_monitor_request(request_id: str):
    """获取监控请求详情"""
    db = get_db_manager()
    
    sql = "SELECT * FROM production_requests WHERE request_id = %s"
    row = db.fetch_one(sql, (request_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="监控请求不存在")
    
    # 获取最近检查记录
    history_sql = """
        SELECT * FROM health_check_results
        WHERE request_id = %s
        ORDER BY checked_at DESC
        LIMIT 50
    """
    history = db.fetch_all(history_sql, (request_id,))
    
    return {
        "request": dict(row),
        "check_history": [dict(h) for h in history]
    }


@router.post("/requests")
async def add_monitor_request(request: AddMonitorRequest):
    """手动添加监控请求"""
    import uuid
    
    db = get_db_manager()
    request_id = str(uuid.uuid4())[:8]
    
    sql = """
        INSERT INTO production_requests 
        (request_id, method, url, headers, body, query_params, 
         expected_status_code, expected_response_pattern, tags, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'manual')
    """
    
    db.execute(sql, (
        request_id,
        request.method.upper(),
        request.url,
        json.dumps(request.headers) if request.headers else None,
        request.body,
        json.dumps(request.query_params) if request.query_params else None,
        request.expected_status_code,
        request.expected_response_pattern,
        json.dumps(request.tags) if request.tags else None
    ))
    
    return {
        "success": True,
        "request_id": request_id,
        "message": "监控请求添加成功"
    }


@router.post("/requests/extract")
async def extract_from_log(request: ExtractRequestsRequest):
    """从日志分析任务中提取请求到监控库"""
    try:
        service = ProductionMonitorService(verbose=True)
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提取请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/requests/{request_id}")
async def update_monitor_request(request_id: str, request: AddMonitorRequest):
    """更新监控请求"""
    db = get_db_manager()
    
    sql = """
        UPDATE production_requests SET
            method = %s,
            url = %s,
            headers = %s,
            body = %s,
            query_params = %s,
            expected_status_code = %s,
            expected_response_pattern = %s,
            tags = %s,
            updated_at = NOW()
        WHERE request_id = %s
    """
    
    affected = db.execute(sql, (
        request.method.upper(),
        request.url,
        json.dumps(request.headers) if request.headers else None,
        request.body,
        json.dumps(request.query_params) if request.query_params else None,
        request.expected_status_code,
        request.expected_response_pattern,
        json.dumps(request.tags) if request.tags else None,
        request_id
    ))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="监控请求不存在")
    
    return {"success": True, "message": "更新成功"}


@router.delete("/requests/{request_id}")
async def delete_monitor_request(request_id: str):
    """删除监控请求"""
    db = get_db_manager()
    
    sql = "DELETE FROM production_requests WHERE request_id = %s"
    affected = db.execute(sql, (request_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="监控请求不存在")
    
    return {"success": True, "message": "删除成功"}


@router.patch("/requests/{request_id}/toggle")
async def toggle_monitor_request(request_id: str, is_enabled: bool):
    """启用/禁用监控请求"""
    db = get_db_manager()
    
    sql = "UPDATE production_requests SET is_enabled = %s WHERE request_id = %s"
    affected = db.execute(sql, (is_enabled, request_id))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="监控请求不存在")
    
    return {"success": True, "is_enabled": is_enabled}


# ==================== 健康检查执行 ====================

@router.post("/health-check")
async def run_health_check(request: HealthCheckRequest, background_tasks: BackgroundTasks):
    """执行健康检查"""
    try:
        service = ProductionMonitorService(verbose=True)
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
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取健康检查执行记录"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if status:
        conditions.append("status = %s")
        params.append(status)
    
    if trigger_type:
        conditions.append("trigger_type = %s")
        params.append(trigger_type)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM health_check_executions {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM health_check_executions
        {where_clause}
        ORDER BY created_at DESC
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


@router.get("/health-check/executions/{execution_id}")
async def get_health_check_execution(execution_id: str):
    """获取健康检查执行详情"""
    db = get_db_manager()
    
    # 获取执行记录
    execution_sql = "SELECT * FROM health_check_executions WHERE execution_id = %s"
    execution = db.fetch_one(execution_sql, (execution_id,))
    
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 获取详细结果
    results_sql = """
        SELECT r.*, p.url, p.method
        FROM health_check_results r
        JOIN production_requests p ON r.request_id = p.request_id
        WHERE r.execution_id = %s
        ORDER BY r.success ASC, r.response_time_ms DESC
    """
    results = db.fetch_all(results_sql, (execution_id,))
    
    return {
        "execution": dict(execution),
        "results": [dict(r) for r in results]
    }


# ==================== 健康状态概览 ====================

@router.get("/summary")
async def get_health_summary(days: int = Query(default=7, ge=1, le=30)):
    """获取健康状态摘要"""
    try:
        service = ProductionMonitorService(verbose=True)
        return service.get_health_summary(days=days)
    except Exception as e:
        logger.error(f"获取健康摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_monitoring_statistics():
    """获取监控统计数据"""
    db = get_db_manager()
    
    # 监控请求统计
    request_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled,
            SUM(CASE WHEN last_check_status = 'healthy' THEN 1 ELSE 0 END) as healthy,
            SUM(CASE WHEN last_check_status = 'unhealthy' THEN 1 ELSE 0 END) as unhealthy,
            SUM(CASE WHEN consecutive_failures >= 3 THEN 1 ELSE 0 END) as critical
        FROM production_requests
    """)
    
    # 今日检查统计
    today_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total_checks,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
            AVG(response_time_ms) as avg_response_time
        FROM health_check_results
        WHERE DATE(checked_at) = CURDATE()
    """)
    
    # 近7天趋势
    trend_sql = """
        SELECT 
            DATE(checked_at) as date,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
            AVG(response_time_ms) as avg_time
        FROM health_check_results
        WHERE checked_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(checked_at)
        ORDER BY date
    """
    trend = db.fetch_all(trend_sql)
    
    total_requests = request_stats['total'] if request_stats else 0
    healthy_requests = request_stats['healthy'] if request_stats else 0
    
    return {
        "requests": {
            "total": total_requests,
            "enabled": request_stats['enabled'] if request_stats else 0,
            "healthy": healthy_requests,
            "unhealthy": request_stats['unhealthy'] if request_stats else 0,
            "critical": request_stats['critical'] if request_stats else 0,
            "health_rate": round(healthy_requests / total_requests * 100, 2) if total_requests > 0 else 0
        },
        "today": {
            "total_checks": today_stats['total_checks'] if today_stats else 0,
            "success_count": today_stats['success_count'] if today_stats else 0,
            "avg_response_time": round(today_stats['avg_response_time'] or 0, 2) if today_stats else 0
        },
        "trend": [
            {
                "date": str(t['date']),
                "total": t['total'],
                "success": t['success'],
                "success_rate": round(t['success'] / t['total'] * 100, 2) if t['total'] > 0 else 0,
                "avg_time": round(t['avg_time'] or 0, 2)
            }
            for t in trend
        ]
    }


# ==================== 定时任务配置 ====================

@router.get("/schedule")
async def get_schedule_config():
    """获取定时巡检配置"""
    # 暂时返回默认配置，后续可扩展为数据库存储
    return {
        "enabled": False,
        "cron": "0 */1 * * *",
        "base_url": "",
        "use_ai_validation": True,
        "alert_on_failure": True,
        "alert_threshold": 3,
        "last_run": None,
        "next_run": None
    }


@router.put("/schedule")
async def update_schedule_config(config: ScheduleConfig):
    """更新定时巡检配置"""
    # TODO: 保存到数据库并更新调度器
    return {
        "success": True,
        "message": "配置已更新",
        "config": config.model_dump()
    }


# ==================== 告警配置 ====================

@router.get("/alerts")
async def list_alerts(
    is_resolved: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取告警列表"""
    db = get_db_manager()
    
    # 从 ai_insights 表获取告警类型的洞察
    conditions = ["insight_type IN ('health_alert', 'consecutive_failure')"]
    params: list[Any] = []
    
    if is_resolved is not None:
        conditions.append("is_resolved = %s")
        params.append(is_resolved)
    
    where_clause = f"WHERE {' AND '.join(conditions)}"
    
    count_sql = f"SELECT COUNT(*) as count FROM ai_insights {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM ai_insights
        {where_clause}
        ORDER BY created_at DESC
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


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """标记告警为已解决"""
    db = get_db_manager()
    
    sql = """
        UPDATE ai_insights 
        SET is_resolved = 1, resolved_at = NOW() 
        WHERE insight_id = %s
    """
    affected = db.execute(sql, (alert_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="告警不存在")
    
    return {"success": True, "message": "告警已标记为解决"}
