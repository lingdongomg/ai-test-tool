"""
执行记录 API
"""

import json
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...database import get_db_manager

router = APIRouter()


class StepResultResponse(BaseModel):
    """步骤结果响应"""
    id: int
    step_id: str
    step_order: int
    status: str
    request_url: str
    request_headers: dict[str, str]
    request_body: str
    response_status_code: int
    response_headers: dict[str, str]
    response_body: str
    response_time_ms: float
    extracted_variables: dict[str, Any]
    assertion_results: list[dict[str, Any]]
    error_message: str


class ExecutionResponse(BaseModel):
    """执行记录响应"""
    id: int
    execution_id: str
    scenario_id: str
    scenario_name: str | None = None
    trigger_type: str
    status: str
    base_url: str
    environment: str
    variables: dict[str, Any]
    total_steps: int
    passed_steps: int
    failed_steps: int
    skipped_steps: int
    duration_ms: int
    error_message: str
    started_at: str | None
    completed_at: str | None
    step_results: list[StepResultResponse] = []


class ExecutionListResponse(BaseModel):
    """执行记录列表响应"""
    total: int
    items: list[ExecutionResponse]


class ExecutionStatistics(BaseModel):
    """执行统计"""
    total_executions: int
    passed: int
    failed: int
    cancelled: int
    running: int
    avg_duration_ms: float
    success_rate: float


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    scenario_id: str | None = None,
    status: str | None = None,
    trigger_type: str | None = None,
    environment: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取执行记录列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if scenario_id:
        conditions.append("e.scenario_id = %s")
        params.append(scenario_id)
    
    if status:
        conditions.append("e.status = %s")
        params.append(status)
    
    if trigger_type:
        conditions.append("e.trigger_type = %s")
        params.append(trigger_type)
    
    if environment:
        conditions.append("e.environment = %s")
        params.append(environment)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM scenario_executions e {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT e.*, s.name as scenario_name
        FROM scenario_executions e
        LEFT JOIN test_scenarios s ON e.scenario_id = s.scenario_id
        {where_clause}
        ORDER BY e.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(sql, tuple(params))
    
    items = [_row_to_execution_response(row) for row in rows]
    
    return ExecutionListResponse(total=total, items=items)


@router.get("/statistics", response_model=ExecutionStatistics)
async def get_statistics(
    scenario_id: str | None = None,
    days: int = Query(default=7, ge=1, le=90)
):
    """获取执行统计"""
    db = get_db_manager()
    
    conditions = ["created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"]
    params: list[Any] = [days]
    
    if scenario_id:
        conditions.append("scenario_id = %s")
        params.append(scenario_id)
    
    where_clause = f"WHERE {' AND '.join(conditions)}"
    
    sql = f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
            AVG(duration_ms) as avg_duration
        FROM scenario_executions
        {where_clause}
    """
    
    row = db.fetch_one(sql, tuple(params))
    
    total = row['total'] or 0
    passed = row['passed'] or 0
    
    return ExecutionStatistics(
        total_executions=total,
        passed=passed,
        failed=row['failed'] or 0,
        cancelled=row['cancelled'] or 0,
        running=row['running'] or 0,
        avg_duration_ms=float(row['avg_duration'] or 0),
        success_rate=round(passed / total * 100, 2) if total > 0 else 0
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: str, include_steps: bool = True):
    """获取单个执行记录"""
    db = get_db_manager()
    
    sql = """
        SELECT e.*, s.name as scenario_name
        FROM scenario_executions e
        LEFT JOIN test_scenarios s ON e.scenario_id = s.scenario_id
        WHERE e.execution_id = %s
    """
    row = db.fetch_one(sql, (execution_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    execution = _row_to_execution_response(row)
    
    if include_steps:
        execution.step_results = _get_step_results(db, execution_id)
    
    return execution


@router.get("/{execution_id}/steps", response_model=list[StepResultResponse])
async def get_execution_steps(execution_id: str):
    """获取执行步骤结果"""
    db = get_db_manager()
    
    # 检查执行记录是否存在
    existing = db.fetch_one(
        "SELECT execution_id FROM scenario_executions WHERE execution_id = %s",
        (execution_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    return _get_step_results(db, execution_id)


@router.delete("/{execution_id}")
async def delete_execution(execution_id: str):
    """删除执行记录"""
    db = get_db_manager()
    
    # 检查是否存在
    existing = db.fetch_one(
        "SELECT execution_id FROM scenario_executions WHERE execution_id = %s",
        (execution_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 删除执行记录（步骤结果会级联删除）
    db.execute("DELETE FROM scenario_executions WHERE execution_id = %s", (execution_id,))
    
    return {"message": "删除成功"}


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """取消执行"""
    db = get_db_manager()
    
    # 检查是否存在且正在运行
    existing = db.fetch_one(
        "SELECT status FROM scenario_executions WHERE execution_id = %s",
        (execution_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    if existing['status'] not in ('pending', 'running'):
        raise HTTPException(status_code=400, detail="只能取消待执行或执行中的任务")
    
    # 更新状态
    db.execute(
        "UPDATE scenario_executions SET status = 'cancelled', completed_at = NOW() WHERE execution_id = %s",
        (execution_id,)
    )
    
    return {"message": "已取消"}


def _row_to_execution_response(row: dict[str, Any]) -> ExecutionResponse:
    """转换数据库行为执行响应"""
    variables = row.get('variables', '{}')
    if isinstance(variables, str):
        variables = json.loads(variables) if variables else {}
    
    started_at = row.get('started_at')
    completed_at = row.get('completed_at')
    
    return ExecutionResponse(
        id=row['id'],
        execution_id=row['execution_id'],
        scenario_id=row['scenario_id'],
        scenario_name=row.get('scenario_name'),
        trigger_type=row.get('trigger_type', 'manual'),
        status=row.get('status', 'pending'),
        base_url=row.get('base_url', ''),
        environment=row.get('environment', ''),
        variables=variables,
        total_steps=row.get('total_steps', 0),
        passed_steps=row.get('passed_steps', 0),
        failed_steps=row.get('failed_steps', 0),
        skipped_steps=row.get('skipped_steps', 0),
        duration_ms=row.get('duration_ms', 0),
        error_message=row.get('error_message', ''),
        started_at=str(started_at) if started_at else None,
        completed_at=str(completed_at) if completed_at else None,
        step_results=[]
    )


def _get_step_results(db: Any, execution_id: str) -> list[StepResultResponse]:
    """获取步骤结果"""
    sql = "SELECT * FROM step_results WHERE execution_id = %s ORDER BY step_order"
    rows = db.fetch_all(sql, (execution_id,))
    
    results = []
    for row in rows:
        request_headers = row.get('request_headers', '{}')
        if isinstance(request_headers, str):
            request_headers = json.loads(request_headers) if request_headers else {}
        
        response_headers = row.get('response_headers', '{}')
        if isinstance(response_headers, str):
            response_headers = json.loads(response_headers) if response_headers else {}
        
        extracted_variables = row.get('extracted_variables', '{}')
        if isinstance(extracted_variables, str):
            extracted_variables = json.loads(extracted_variables) if extracted_variables else {}
        
        assertion_results = row.get('assertion_results', '[]')
        if isinstance(assertion_results, str):
            assertion_results = json.loads(assertion_results) if assertion_results else []
        
        results.append(StepResultResponse(
            id=row['id'],
            step_id=row['step_id'],
            step_order=row['step_order'],
            status=row['status'],
            request_url=row.get('request_url', ''),
            request_headers=request_headers,
            request_body=row.get('request_body', ''),
            response_status_code=row.get('response_status_code', 0),
            response_headers=response_headers,
            response_body=row.get('response_body', ''),
            response_time_ms=float(row.get('response_time_ms', 0)),
            extracted_variables=extracted_variables,
            assertion_results=assertion_results,
            error_message=row.get('error_message', '')
        ))
    
    return results
