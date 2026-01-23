"""
日志洞察模块 API
场景三：日志分析与异常检测
"""

from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
import uuid

from ...services import LogAnomalyDetectorService, AIAssistantService
from ...database import get_db_manager
from ...database.repository import RequestRepository
from ...database.models import ParsedRequestRecord
from ...parser.log_parser import LogParser
from ...llm.chains import LogAnalysisChain
from ...llm.provider import get_llm_provider
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger()

# 创建线程池用于执行阻塞操作，避免阻塞主事件循环
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="insights_worker")


# ==================== 请求/响应模型 ====================

class AnalyzeLogRequest(BaseModel):
    """分析日志请求"""
    task_id: str | None = Field(default=None, description="已有任务ID")
    log_content: str | None = Field(default=None, description="日志内容（直接粘贴）")
    include_ai_analysis: bool = Field(default=True, description="是否包含AI分析")
    detect_types: list[str] | None = Field(
        default=None,
        description="检测类型: error, warning, exception, performance, security"
    )


class ParseRequestsRequest(BaseModel):
    """解析请求"""
    task_id: str = Field(..., description="任务ID")
    max_lines: int | None = Field(default=None, description="最大处理行数")


class AnomalyReport(BaseModel):
    """异常报告"""
    report_id: str
    title: str
    summary: str
    total_anomalies: int
    critical_count: int
    error_count: int
    warning_count: int
    created_at: str


# ==================== 日志上传与分析 ====================

@router.post("/upload")
async def upload_log_file(
    file: UploadFile = File(...),
    analysis_type: str = Form(default="anomaly", description="分析类型: anomaly(异常检测) 或 request(请求提取)"),
    detect_types: str | None = Form(default=None),
    include_ai_analysis: bool = Form(default=True),
    max_lines: int | None = Form(default=None, description="最大处理行数"),
    background_tasks: BackgroundTasks = None
):
    """
    上传日志文件进行分析
    
    支持格式：.log, .txt, .json
    分析类型：
    - anomaly: 异常检测（检测错误、警告等）
    - request: 请求提取（解析HTTP请求，用于提取监控用例）
    """
    # 验证文件类型
    allowed_extensions = {'.log', '.txt', '.json'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型，支持: {', '.join(allowed_extensions)}"
        )
    
    # 验证分析类型
    if analysis_type not in ('anomaly', 'request'):
        raise HTTPException(
            status_code=400,
            detail="分析类型必须是 anomaly 或 request"
        )
    
    # 保存文件
    task_id = str(uuid.uuid4())[:8]
    upload_dir = os.path.join(os.getcwd(), 'uploads', 'logs')
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")
    
    try:
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # 创建分析任务
        db = get_db_manager()
        task_name = f"日志分析-{file.filename}" if analysis_type == "anomaly" else f"请求提取-{file.filename}"
        db.execute("""
            INSERT INTO analysis_tasks 
            (task_id, name, log_file_path, log_file_size, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (task_id, task_name, file_path, len(content)))
        
        # 后台执行分析
        if background_tasks:
            if analysis_type == "anomaly":
                types_list = detect_types.split(',') if detect_types else None
                background_tasks.add_task(
                    _analyze_log_task, 
                    task_id, 
                    file_path, 
                    types_list,
                    include_ai_analysis
                )
            else:
                background_tasks.add_task(
                    _parse_requests_task,
                    task_id,
                    file_path,
                    max_lines
                )
        
        return {
            "success": True,
            "task_id": task_id,
            "file_name": file.filename,
            "file_size": len(content),
            "analysis_type": analysis_type,
            "message": f"文件上传成功，正在后台{'解析请求' if analysis_type == 'request' else '检测异常'}"
        }
    
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_log(request: AnalyzeLogRequest, background_tasks: BackgroundTasks):
    """
    分析日志（支持已有任务或直接粘贴内容）
    """
    db = get_db_manager()
    
    if request.task_id:
        # 分析已有任务
        task = db.fetch_one(
            "SELECT * FROM analysis_tasks WHERE task_id = %s",
            (request.task_id,)
        )
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        file_path = task['log_file_path']
    
    elif request.log_content:
        # 直接分析粘贴的内容
        task_id = str(uuid.uuid4())[:8]
        upload_dir = os.path.join(os.getcwd(), 'uploads', 'logs')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{task_id}_pasted.log")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.log_content)
        
        db.execute("""
            INSERT INTO analysis_tasks 
            (task_id, name, log_file_path, log_file_size, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (task_id, "日志分析-粘贴内容", file_path, len(request.log_content)))
        
        request.task_id = task_id
    
    else:
        raise HTTPException(status_code=400, detail="请提供 task_id 或 log_content")
    
    # 后台执行分析
    background_tasks.add_task(
        _analyze_log_task,
        request.task_id,
        file_path,
        request.detect_types,
        request.include_ai_analysis
    )
    
    return {
        "success": True,
        "task_id": request.task_id,
        "message": "分析任务已启动"
    }


def _analyze_log_task_sync(
    task_id: str, 
    file_path: str, 
    detect_types: list[str] | None,
    include_ai_analysis: bool
):
    """后台分析任务 - 同步版本，在线程池中执行"""
    import traceback
    db = get_db_manager()
    
    try:
        # 更新状态为运行中
        db.execute(
            "UPDATE analysis_tasks SET status = 'running', started_at = datetime('now') WHERE task_id = %s",
            (task_id,)
        )
        
        service = LogAnomalyDetectorService(verbose=True)
        report = service.detect_anomalies_from_file(
            file_path=file_path,
            task_id=task_id,
            detect_types=detect_types,
            include_ai_analysis=include_ai_analysis
        )
        
        # 更新状态为完成
        db.execute("""
            UPDATE analysis_tasks 
            SET status = 'completed', completed_at = datetime('now')
            WHERE task_id = %s
        """, (task_id,))
        
    except Exception as e:
        # 记录详细错误信息，包含堆栈追踪
        error_detail = f"{type(e).__name__}: {str(e)}\n\n堆栈追踪:\n{traceback.format_exc()}"
        logger.error(f"分析任务失败 [{task_id}]: {error_detail}")
        db.execute("""
            UPDATE analysis_tasks 
            SET status = 'failed', error_message = %s, completed_at = datetime('now')
            WHERE task_id = %s
        """, (error_detail, task_id))


async def _analyze_log_task(
    task_id: str, 
    file_path: str, 
    detect_types: list[str] | None,
    include_ai_analysis: bool
):
    """后台分析任务 - 在线程池中执行，避免阻塞主事件循环"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor,
        _analyze_log_task_sync,
        task_id,
        file_path,
        detect_types,
        include_ai_analysis
    )


def _parse_requests_task_sync(
    task_id: str,
    file_path: str,
    max_lines: int | None
):
    """后台解析请求任务 - 同步版本，在线程池中执行"""
    import traceback as tb
    db = get_db_manager()
    task_logger = get_logger(verbose=True)
    
    try:
        # 更新状态为运行中
        db.execute(
            "UPDATE analysis_tasks SET status = 'running', started_at = datetime('now') WHERE task_id = %s",
            (task_id,)
        )
        
        # 初始化解析器
        try:
            provider = get_llm_provider()
            llm_chain = LogAnalysisChain(provider, verbose=True)
        except Exception as e:
            task_logger.warn(f"无法初始化AI，使用基础解析: {e}")
            llm_chain = None
        
        parser = LogParser(llm_chain=llm_chain, verbose=True)
        request_repo = RequestRepository()
        
        total_requests = 0
        total_lines = 0
        
        # 计算总行数
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            total_lines = sum(1 for _ in f)
        
        db.execute(
            "UPDATE analysis_tasks SET total_lines = %s WHERE task_id = %s",
            (total_lines, task_id)
        )
        
        # 解析日志文件
        for batch_requests in parser.parse_file(file_path, max_lines=max_lines):
            # 转换为数据库记录
            records = []
            for req in batch_requests:
                record = ParsedRequestRecord(
                    task_id=task_id,
                    request_id=req.request_id or str(uuid.uuid4())[:16],
                    method=req.method,
                    url=req.url,
                    category=req.category,
                    headers=req.headers or {},
                    body=req.body,
                    query_params=req.query_params or {},
                    http_status=req.http_status,
                    response_time_ms=req.response_time_ms,
                    response_body=req.response_body,
                    has_error=req.has_error,
                    error_message=req.error_message,
                    has_warning=req.has_warning,
                    warning_message=req.warning_message,
                    curl_command=req.curl_command,
                    timestamp=req.timestamp,
                    raw_logs='\n'.join(req.raw_logs) if req.raw_logs else '',
                    metadata=req.metadata or {}
                )
                records.append(record)
            
            # 批量保存
            if records:
                request_repo.create_batch(records)
                total_requests += len(records)
                
                # 更新进度
                db.execute(
                    "UPDATE analysis_tasks SET total_requests = %s WHERE task_id = %s",
                    (total_requests, task_id)
                )
        
        # 更新状态为完成
        db.execute("""
            UPDATE analysis_tasks 
            SET status = 'completed', 
                total_requests = %s,
                completed_at = datetime('now')
            WHERE task_id = %s
        """, (total_requests, task_id))
        
        task_logger.info(f"请求解析完成: 共提取 {total_requests} 个请求")
        
    except Exception as e:
        # 记录详细错误信息，包含堆栈追踪
        error_detail = f"{type(e).__name__}: {str(e)}\n\n堆栈追踪:\n{tb.format_exc()}"
        logger.error(f"请求解析任务失败 [{task_id}]: {error_detail}")
        db.execute("""
            UPDATE analysis_tasks 
            SET status = 'failed', error_message = %s, completed_at = datetime('now')
            WHERE task_id = %s
        """, (error_detail, task_id))


async def _parse_requests_task(
    task_id: str,
    file_path: str,
    max_lines: int | None
):
    """后台解析请求任务 - 在线程池中执行，避免阻塞主事件循环"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        _executor,
        _parse_requests_task_sync,
        task_id,
        file_path,
        max_lines
    )


# ==================== 分析任务管理 ====================

@router.get("/tasks")
async def list_analysis_tasks(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取分析任务列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if status:
        conditions.append("status = %s")
        params.append(status)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    count_sql = f"SELECT COUNT(*) as count FROM analysis_tasks {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM analysis_tasks
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


@router.get("/tasks/{task_id}")
async def get_analysis_task(task_id: str):
    """获取分析任务详情"""
    db = get_db_manager()
    
    task = db.fetch_one(
        "SELECT * FROM analysis_tasks WHERE task_id = %s",
        (task_id,)
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取关联的报告
    reports = db.fetch_all(
        "SELECT * FROM analysis_reports WHERE task_id = %s ORDER BY created_at DESC",
        (task_id,)
    )
    
    return {
        "task": dict(task),
        "reports": [dict(r) for r in reports]
    }


@router.delete("/tasks/{task_id}")
async def delete_analysis_task(task_id: str):
    """删除分析任务"""
    db = get_db_manager()
    
    # 检查任务是否存在
    task = db.fetch_one(
        "SELECT * FROM analysis_tasks WHERE task_id = %s",
        (task_id,)
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 删除关联的报告
    db.execute("DELETE FROM analysis_reports WHERE task_id = %s", (task_id,))
    
    # 删除关联的解析请求
    db.execute("DELETE FROM parsed_requests WHERE task_id = %s", (task_id,))
    
    # 删除任务
    db.execute("DELETE FROM analysis_tasks WHERE task_id = %s", (task_id,))
    
    # 删除上传的文件
    if task.get('log_file_path'):
        import os
        try:
            if os.path.exists(task['log_file_path']):
                os.remove(task['log_file_path'])
        except Exception as e:
            logger.warn(f"删除文件失败: {e}")
    
    return {"success": True, "message": "删除成功"}


# ==================== 异常报告管理 ====================

@router.get("/reports")
async def list_anomaly_reports(
    task_id: str | None = None,
    severity: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取异常报告列表"""
    db = get_db_manager()
    
    conditions = ["report_type = 'anomaly'"]
    params: list[Any] = []
    
    if task_id:
        conditions.append("task_id = %s")
        params.append(task_id)
    
    where_clause = f"WHERE {' AND '.join(conditions)}"
    
    count_sql = f"SELECT COUNT(*) as count FROM analysis_reports {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    offset = (page - 1) * page_size
    sql = f"""
        SELECT id, task_id, title, format, statistics, created_at
        FROM analysis_reports
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


@router.get("/reports/{report_id}")
async def get_anomaly_report(report_id: int):
    """获取异常报告详情"""
    db = get_db_manager()
    
    sql = "SELECT * FROM analysis_reports WHERE id = %s"
    row = db.fetch_one(sql, (report_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    return dict(row)


@router.get("/reports/{report_id}/download")
async def download_report(report_id: int, format: str = Query(default="markdown")):
    """下载报告"""
    from fastapi.responses import PlainTextResponse
    
    db = get_db_manager()
    
    sql = "SELECT * FROM analysis_reports WHERE id = %s"
    row = db.fetch_one(sql, (report_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    content = row['content']
    filename = f"anomaly_report_{report_id}.md"
    
    return PlainTextResponse(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 异常检测 ====================

@router.post("/detect")
async def detect_anomalies(request: AnalyzeLogRequest):
    """直接检测异常（同步返回结果）"""
    try:
        service = LogAnomalyDetectorService(verbose=True)
        
        if request.task_id:
            report = service.detect_anomalies_from_task(
                task_id=request.task_id,
                detect_types=request.detect_types,
                include_ai_analysis=request.include_ai_analysis
            )
        elif request.log_content:
            report = service.detect_anomalies_from_content(
                content=request.log_content,
                detect_types=request.detect_types,
                include_ai_analysis=request.include_ai_analysis
            )
        else:
            raise HTTPException(status_code=400, detail="请提供 task_id 或 log_content")
        
        return {
            "success": True,
            "report_id": report.report_id,
            "title": report.title,
            "summary": report.summary,
            "total_anomalies": report.total_anomalies,
            "critical_count": report.critical_count,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "anomalies": [
                {
                    "type": a.type,
                    "severity": a.severity,
                    "message": a.message,
                    "line_number": a.line_number,
                    "context": a.context,
                    "ai_analysis": a.ai_analysis
                }
                for a in report.anomalies[:50]  # 限制返回数量
            ]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"异常检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 趋势分析 ====================

@router.get("/trends")
async def get_anomaly_trends(days: int = Query(default=7, ge=1, le=30)):
    """获取异常趋势"""
    db = get_db_manager()
    
    # 按天统计异常数量
    sql = """
        SELECT 
            DATE(created_at) as date,
            JSON_EXTRACT(statistics, '$.critical_count') as critical,
            JSON_EXTRACT(statistics, '$.error_count') as error,
            JSON_EXTRACT(statistics, '$.warning_count') as warning,
            JSON_EXTRACT(statistics, '$.total_anomalies') as total
        FROM analysis_reports
        WHERE report_type = 'anomaly' 
        AND created_at >= datetime('now', '-' || %s || ' days')
        ORDER BY date
    """
    rows = db.fetch_all(sql, (days,))
    
    return {
        "days": days,
        "trends": [
            {
                "date": str(row['date']),
                "critical": int(row['critical'] or 0),
                "error": int(row['error'] or 0),
                "warning": int(row['warning'] or 0),
                "total": int(row['total'] or 0)
            }
            for row in rows
        ]
    }


# ==================== 统计概览 ====================

@router.get("/statistics")
async def get_insights_statistics():
    """获取日志洞察统计"""
    db = get_db_manager()
    
    # 任务统计
    task_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM analysis_tasks
    """)
    
    # 报告统计
    report_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total_reports,
            SUM(JSON_EXTRACT(statistics, '$.total_anomalies')) as total_anomalies,
            SUM(JSON_EXTRACT(statistics, '$.critical_count')) as critical_count,
            SUM(JSON_EXTRACT(statistics, '$.error_count')) as error_count
        FROM analysis_reports
        WHERE report_type = 'anomaly'
    """)
    
    # 今日统计
    today_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as tasks_today,
            SUM(JSON_EXTRACT(statistics, '$.total_anomalies')) as anomalies_today
        FROM analysis_reports
        WHERE report_type = 'anomaly' AND DATE(created_at) = DATE('now')
    """)
    
    return {
        "tasks": {
            "total": task_stats['total'] if task_stats else 0,
            "completed": task_stats['completed'] if task_stats else 0,
            "running": task_stats['running'] if task_stats else 0,
            "failed": task_stats['failed'] if task_stats else 0
        },
        "reports": {
            "total": report_stats['total_reports'] if report_stats else 0,
            "total_anomalies": int(report_stats['total_anomalies'] or 0) if report_stats else 0,
            "critical_count": int(report_stats['critical_count'] or 0) if report_stats else 0,
            "error_count": int(report_stats['error_count'] or 0) if report_stats else 0
        },
        "today": {
            "tasks": today_stats['tasks_today'] if today_stats else 0,
            "anomalies": int(today_stats['anomalies_today'] or 0) if today_stats else 0
        }
    }
