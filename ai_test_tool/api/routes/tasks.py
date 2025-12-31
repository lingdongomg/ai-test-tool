"""
分析任务 API 路由
提供日志分析、测试用例生成、测试执行等功能
替代原有的 run.py 命令行工具
"""

import os
import uuid
import asyncio
from datetime import datetime
from typing import Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from ...core import AITestTool
from ...config import AppConfig, LLMConfig, TestConfig
from ...database import (
    get_db_manager,
    TaskRepository,
    RequestRepository,
    TestCaseRepository,
    TestResultRepository,
    ReportRepository,
    AnalysisTask,
    TaskStatus
)

router = APIRouter()


# ==================== 请求/响应模型 ====================

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    name: str | None = Field(default=None, description="任务名称")
    max_lines: int | None = Field(default=None, description="最大处理行数")
    test_strategy: str = Field(default="comprehensive", description="测试策略: comprehensive/quick/security")
    run_tests: bool = Field(default=False, description="是否执行测试")
    base_url: str | None = Field(default=None, description="测试目标URL")
    concurrent: int = Field(default=5, description="并发请求数")
    verbose: bool = Field(default=False, description="是否显示详细日志")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    name: str
    status: str
    log_file_path: str | None = None
    log_file_size: int | None = None
    total_lines: int | None = None
    processed_lines: int | None = None
    total_requests: int | None = None
    total_test_cases: int | None = None
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    items: list[TaskResponse]


class TaskResultResponse(BaseModel):
    """任务结果响应"""
    task_id: str
    status: str
    parsed_requests: int = 0
    test_cases: int = 0
    test_results: int = 0
    analysis: dict[str, Any] = {}
    validation: dict[str, Any] | None = None
    reports_saved: list[str] = []
    error_message: str | None = None


class RunTestsRequest(BaseModel):
    """执行测试请求"""
    base_url: str = Field(..., description="测试目标URL")
    concurrent: int = Field(default=5, description="并发请求数")


class ParseLogRequest(BaseModel):
    """解析日志请求 (JSON内容)"""
    log_content: str = Field(..., description="日志内容 (JSON格式)")
    name: str | None = Field(default=None, description="任务名称")
    max_lines: int | None = Field(default=None, description="最大处理行数")


class GenerateTestCasesRequest(BaseModel):
    """生成测试用例请求"""
    test_strategy: str = Field(default="comprehensive", description="测试策略")


# ==================== 后台任务存储 ====================

# 存储正在运行的任务
_running_tasks: dict[str, dict[str, Any]] = {}


def _get_task_repo() -> TaskRepository:
    """获取任务仓库"""
    return TaskRepository(get_db_manager())


def _get_request_repo() -> RequestRepository:
    """获取请求仓库"""
    return RequestRepository(get_db_manager())


def _get_test_case_repo() -> TestCaseRepository:
    """获取测试用例仓库"""
    return TestCaseRepository(get_db_manager())


def _get_test_result_repo() -> TestResultRepository:
    """获取测试结果仓库"""
    return TestResultRepository(get_db_manager())


def _get_report_repo() -> ReportRepository:
    """获取报告仓库"""
    return ReportRepository(get_db_manager())


# ==================== API 端点 ====================

@router.get("", response_model=TaskListResponse, summary="获取任务列表")
async def list_tasks(
    status: str | None = None,
    offset: int = 0,
    limit: int = 20
):
    """
    获取分析任务列表
    
    - **status**: 筛选状态 (pending/running/completed/failed)
    - **offset**: 分页偏移
    - **limit**: 每页数量
    """
    try:
        repo = _get_task_repo()
        
        # 获取任务列表
        tasks = repo.get_all(limit=limit, offset=offset)
        
        # 如果有状态筛选，在内存中过滤
        if status:
            try:
                status_enum = TaskStatus(status)
                tasks = [t for t in tasks if t.status == status_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
        
        # 获取总数
        all_tasks = repo.get_all(limit=10000, offset=0)
        total = len([t for t in all_tasks if not status or t.status.value == status])
        
        items = []
        for task in tasks:
            items.append(TaskResponse(
                task_id=task.task_id,
                name=task.name,
                status=task.status.value,
                log_file_path=task.log_file_path,
                log_file_size=task.log_file_size,
                total_lines=task.total_lines,
                processed_lines=task.processed_lines,
                total_requests=task.total_requests,
                total_test_cases=task.total_test_cases,
                error_message=task.error_message,
                created_at=task.created_at.isoformat() if task.created_at else None,
                started_at=task.started_at.isoformat() if task.started_at else None,
                completed_at=task.completed_at.isoformat() if task.completed_at else None
            ))
        
        return TaskListResponse(total=total, items=items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
async def get_task(task_id: str):
    """获取单个任务详情"""
    try:
        repo = _get_task_repo()
        task = repo.get_by_id(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
        return TaskResponse(
            task_id=task.task_id,
            name=task.name,
            status=task.status.value,
            log_file_path=task.log_file_path,
            log_file_size=task.log_file_size,
            total_lines=task.total_lines,
            processed_lines=task.processed_lines,
            total_requests=task.total_requests,
            total_test_cases=task.total_test_cases,
            error_message=task.error_message,
            created_at=task.created_at.isoformat() if task.created_at else None,
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")


@router.post("/upload", response_model=TaskResultResponse, summary="上传日志文件并分析")
async def upload_and_analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="日志文件"),
    name: str | None = Form(default=None, description="任务名称"),
    max_lines: int | None = Form(default=None, description="最大处理行数"),
    test_strategy: str = Form(default="comprehensive", description="测试策略"),
    run_tests: bool = Form(default=False, description="是否执行测试"),
    base_url: str | None = Form(default=None, description="测试目标URL"),
    concurrent: int = Form(default=5, description="并发请求数"),
    async_mode: bool = Form(default=True, description="是否异步执行")
):
    """
    上传日志文件并执行分析
    
    支持的文件格式: JSON, JSONL, 文本日志
    
    - **file**: 日志文件
    - **name**: 任务名称 (可选)
    - **max_lines**: 最大处理行数 (可选)
    - **test_strategy**: 测试策略 (comprehensive/quick/security)
    - **run_tests**: 是否执行测试
    - **base_url**: 测试目标URL (run_tests=true时需要)
    - **concurrent**: 并发请求数
    - **async_mode**: 是否异步执行 (默认true，后台执行)
    """
    # 保存上传的文件
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = Path(file.filename or "log.json").suffix or ".json"
    saved_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = upload_dir / saved_filename
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
    
    task_name = name or f"分析任务 - {file.filename}"
    
    if async_mode:
        # 异步执行
        task_id = f"task_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        # 创建初始任务记录
        repo = _get_task_repo()
        task = AnalysisTask(
            task_id=task_id,
            name=task_name,
            log_file_path=str(file_path),
            log_file_size=len(content),
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        repo.create(task)
        
        # 添加后台任务
        background_tasks.add_task(
            _run_analysis_task,
            task_id=task_id,
            file_path=str(file_path),
            max_lines=max_lines,
            test_strategy=test_strategy,
            run_tests=run_tests,
            base_url=base_url,
            concurrent=concurrent
        )
        
        return TaskResultResponse(
            task_id=task_id,
            status="pending",
            error_message=None
        )
    else:
        # 同步执行
        try:
            result = await _execute_analysis(
                file_path=str(file_path),
                name=task_name,
                max_lines=max_lines,
                test_strategy=test_strategy,
                run_tests=run_tests,
                base_url=base_url,
                concurrent=concurrent
            )
            return TaskResultResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze-content", response_model=TaskResultResponse, summary="分析日志内容")
async def analyze_content(
    request: ParseLogRequest,
    background_tasks: BackgroundTasks,
    test_strategy: str = "comprehensive",
    run_tests: bool = False,
    base_url: str | None = None,
    async_mode: bool = True
):
    """
    直接分析日志内容 (无需上传文件)
    
    - **log_content**: JSON格式的日志内容
    - **name**: 任务名称 (可选)
    - **max_lines**: 最大处理行数 (可选)
    """
    # 保存内容到临时文件
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.json"
    file_path = upload_dir / saved_filename
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.log_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存内容失败: {str(e)}")
    
    task_name = request.name or f"分析任务 - {timestamp}"
    
    if async_mode:
        task_id = f"task_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        repo = _get_task_repo()
        task = AnalysisTask(
            task_id=task_id,
            name=task_name,
            log_file_path=str(file_path),
            log_file_size=len(request.log_content.encode()),
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        repo.create(task)
        
        background_tasks.add_task(
            _run_analysis_task,
            task_id=task_id,
            file_path=str(file_path),
            max_lines=request.max_lines,
            test_strategy=test_strategy,
            run_tests=run_tests,
            base_url=base_url,
            concurrent=5
        )
        
        return TaskResultResponse(
            task_id=task_id,
            status="pending"
        )
    else:
        try:
            result = await _execute_analysis(
                file_path=str(file_path),
                name=task_name,
                max_lines=request.max_lines,
                test_strategy=test_strategy,
                run_tests=run_tests,
                base_url=base_url,
                concurrent=5
            )
            return TaskResultResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/{task_id}/run-tests", response_model=TaskResultResponse, summary="执行测试")
async def run_tests_for_task(
    task_id: str,
    request: RunTestsRequest,
    background_tasks: BackgroundTasks,
    async_mode: bool = True
):
    """
    对已有任务执行测试
    
    - **task_id**: 任务ID
    - **base_url**: 测试目标URL
    - **concurrent**: 并发请求数
    """
    repo = _get_task_repo()
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    if task.status not in [TaskStatus.COMPLETED, TaskStatus.RUNNING]:
        raise HTTPException(status_code=400, detail=f"任务状态不允许执行测试: {task.status.value}")
    
    # 检查是否有测试用例
    test_case_repo = _get_test_case_repo()
    test_cases = test_case_repo.get_by_task(task_id)
    
    if not test_cases:
        raise HTTPException(status_code=400, detail="任务没有测试用例，请先生成测试用例")
    
    if async_mode:
        background_tasks.add_task(
            _run_tests_task,
            task_id=task_id,
            base_url=request.base_url,
            concurrent=request.concurrent
        )
        
        return TaskResultResponse(
            task_id=task_id,
            status="running",
            test_cases=len(test_cases)
        )
    else:
        try:
            result = await _execute_tests(
                task_id=task_id,
                base_url=request.base_url,
                concurrent=request.concurrent
            )
            return TaskResultResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"执行测试失败: {str(e)}")


@router.post("/{task_id}/generate-cases", response_model=TaskResultResponse, summary="生成测试用例")
async def generate_test_cases(
    task_id: str,
    request: GenerateTestCasesRequest,
    background_tasks: BackgroundTasks,
    async_mode: bool = True
):
    """
    为已有任务生成测试用例
    
    - **task_id**: 任务ID
    - **test_strategy**: 测试策略 (comprehensive/quick/security)
    """
    repo = _get_task_repo()
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    # 检查是否有解析的请求
    request_repo = _get_request_repo()
    requests = request_repo.get_by_task(task_id)
    
    if not requests:
        raise HTTPException(status_code=400, detail="任务没有解析的请求，请先解析日志")
    
    if async_mode:
        background_tasks.add_task(
            _generate_cases_task,
            task_id=task_id,
            test_strategy=request.test_strategy
        )
        
        return TaskResultResponse(
            task_id=task_id,
            status="running",
            parsed_requests=len(requests)
        )
    else:
        try:
            result = await _execute_generate_cases(
                task_id=task_id,
                test_strategy=request.test_strategy
            )
            return TaskResultResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"生成测试用例失败: {str(e)}")


@router.get("/{task_id}/result", response_model=TaskResultResponse, summary="获取任务结果")
async def get_task_result(task_id: str):
    """获取任务执行结果"""
    repo = _get_task_repo()
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    # 获取相关数据
    request_repo = _get_request_repo()
    test_case_repo = _get_test_case_repo()
    test_result_repo = _get_test_result_repo()
    report_repo = _get_report_repo()
    
    requests = request_repo.get_by_task(task_id)
    test_cases = test_case_repo.get_by_task(task_id)
    test_results = test_result_repo.get_by_task(task_id)
    reports = report_repo.get_by_task(task_id)
    
    # 统计分析
    analysis = {}
    if requests:
        success_count = sum(1 for r in requests if not r.has_error)
        analysis = {
            "total_requests": len(requests),
            "success_count": success_count,
            "error_count": len(requests) - success_count,
            "success_rate": f"{success_count / len(requests) * 100:.1f}%" if requests else "0%"
        }
    
    # 验证结果
    validation = None
    if test_results:
        passed = sum(1 for r in test_results if r.status.value == "passed")
        failed = sum(1 for r in test_results if r.status.value == "failed")
        errors = sum(1 for r in test_results if r.status.value == "error")
        validation = {
            "total": len(test_results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": f"{passed / len(test_results) * 100:.1f}%" if test_results else "0%"
        }
    
    return TaskResultResponse(
        task_id=task_id,
        status=task.status.value,
        parsed_requests=len(requests),
        test_cases=len(test_cases),
        test_results=len(test_results),
        analysis=analysis,
        validation=validation,
        reports_saved=[r.title for r in reports],
        error_message=task.error_message
    )


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(task_id: str):
    """删除任务及其所有相关数据"""
    repo = _get_task_repo()
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    try:
        # 删除任务（级联删除相关数据）
        repo.delete(task_id)
        
        return {"message": f"任务 {task_id} 已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(task_id: str):
    """取消正在运行的任务"""
    repo = _get_task_repo()
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    if task.status != TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail=f"只能取消运行中的任务，当前状态: {task.status.value}")
    
    try:
        repo.update_status(task_id, TaskStatus.FAILED, "用户取消")
        
        # 标记任务为取消
        if task_id in _running_tasks:
            _running_tasks[task_id]["cancelled"] = True
        
        return {"message": f"任务 {task_id} 已取消"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


# ==================== 后台任务函数 ====================

async def _run_analysis_task(
    task_id: str,
    file_path: str,
    max_lines: int | None,
    test_strategy: str,
    run_tests: bool,
    base_url: str | None,
    concurrent: int
) -> None:
    """后台执行分析任务"""
    _running_tasks[task_id] = {"cancelled": False}
    repo = _get_task_repo()
    
    try:
        repo.update_status(task_id, TaskStatus.RUNNING)
        
        # 创建 AITestTool 实例
        config = AppConfig(
            test=TestConfig(
                base_url=base_url or "http://localhost:8080",
                concurrent_requests=concurrent
            )
        )
        
        tool = AITestTool(config=config, verbose=False)
        tool.task_id = task_id  # 使用已创建的任务ID
        
        try:
            # 检查是否取消
            if _running_tasks.get(task_id, {}).get("cancelled"):
                return
            
            # 解析日志
            tool.parse_log_file(file_path, max_lines)
            
            if _running_tasks.get(task_id, {}).get("cancelled"):
                return
            
            # 分析请求
            tool.analyze_requests()
            
            if _running_tasks.get(task_id, {}).get("cancelled"):
                return
            
            # 生成测试用例
            tool.generate_test_cases(test_strategy)
            
            # 执行测试
            if run_tests and base_url:
                if _running_tasks.get(task_id, {}).get("cancelled"):
                    return
                tool.run_tests(base_url, concurrent)
                tool.validate_results()
            
            # 导出结果
            tool.export_all()
            
            repo.update_status(task_id, TaskStatus.COMPLETED)
        finally:
            tool.close()
            
    except Exception as e:
        repo.update_status(task_id, TaskStatus.FAILED, str(e))
    finally:
        _running_tasks.pop(task_id, None)


async def _execute_analysis(
    file_path: str,
    name: str,
    max_lines: int | None,
    test_strategy: str,
    run_tests: bool,
    base_url: str | None,
    concurrent: int
) -> dict[str, Any]:
    """同步执行分析"""
    config = AppConfig(
        test=TestConfig(
            base_url=base_url or "http://localhost:8080",
            concurrent_requests=concurrent
        )
    )
    
    tool = AITestTool(config=config, verbose=False)
    
    try:
        result = tool.run_full_pipeline(
            log_file=file_path,
            max_lines=max_lines,
            test_strategy=test_strategy,
            run_tests=run_tests,
            base_url=base_url
        )
        
        return {
            "task_id": result["task_id"],
            "status": "completed",
            "parsed_requests": result["parsed_requests"],
            "test_cases": result["test_cases"],
            "test_results": result.get("test_results", 0),
            "analysis": result.get("analysis", {}),
            "validation": result.get("validation"),
            "reports_saved": result.get("reports_saved", [])
        }
    finally:
        tool.close()


async def _run_tests_task(
    task_id: str,
    base_url: str,
    concurrent: int
) -> None:
    """后台执行测试任务"""
    # TODO: 实现从数据库加载测试用例并执行
    pass


async def _execute_tests(
    task_id: str,
    base_url: str,
    concurrent: int
) -> dict[str, Any]:
    """同步执行测试"""
    # TODO: 实现从数据库加载测试用例并执行
    return {
        "task_id": task_id,
        "status": "completed",
        "test_results": 0
    }


async def _generate_cases_task(
    task_id: str,
    test_strategy: str
) -> None:
    """后台生成测试用例"""
    # TODO: 实现从数据库加载请求并生成测试用例
    pass


async def _execute_generate_cases(
    task_id: str,
    test_strategy: str
) -> dict[str, Any]:
    """同步生成测试用例"""
    # TODO: 实现从数据库加载请求并生成测试用例
    return {
        "task_id": task_id,
        "status": "completed",
        "test_cases": 0
    }
