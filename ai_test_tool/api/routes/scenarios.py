"""
测试场景管理 API
"""

import json
import time
from typing import Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ...database import get_db_manager
from ...database.models import TestScenario, ScenarioStep, StepType

router = APIRouter()


class StepCreate(BaseModel):
    """创建步骤请求"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    step_type: str = Field(default="request")
    method: str = Field(default="GET")
    url: str = Field(default="")
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    query_params: dict[str, str] = Field(default_factory=dict)
    extractions: list[dict[str, Any]] = Field(default_factory=list)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    wait_time_ms: int = Field(default=0)
    timeout_ms: int = Field(default=30000)
    continue_on_failure: bool = Field(default=False)


class ScenarioCreate(BaseModel):
    """创建场景请求"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    retry_on_failure: bool = Field(default=False)
    max_retries: int = Field(default=3)
    steps: list[StepCreate] = Field(default_factory=list)


class ScenarioUpdate(BaseModel):
    """更新场景请求"""
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    variables: dict[str, Any] | None = None
    retry_on_failure: bool | None = None
    max_retries: int | None = None
    is_enabled: bool | None = None


class StepResponse(BaseModel):
    """步骤响应"""
    id: int
    step_id: str
    step_order: int
    name: str
    description: str
    step_type: str
    method: str
    url: str
    headers: dict[str, str]
    body: dict[str, Any] | None
    query_params: dict[str, str]
    extractions: list[dict[str, Any]]
    assertions: list[dict[str, Any]]
    wait_time_ms: int
    timeout_ms: int
    continue_on_failure: bool
    is_enabled: bool


class ScenarioResponse(BaseModel):
    """场景响应"""
    id: int
    scenario_id: str
    name: str
    description: str
    tags: list[str]
    variables: dict[str, Any]
    retry_on_failure: bool
    max_retries: int
    is_enabled: bool
    steps: list[StepResponse]
    
    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """场景列表响应"""
    total: int
    items: list[ScenarioResponse]


class ExecuteRequest(BaseModel):
    """执行请求"""
    base_url: str = Field(..., description="测试目标URL")
    variables: dict[str, Any] = Field(default_factory=dict, description="执行变量")
    environment: str = Field(default="", description="执行环境")


@router.get("", response_model=ScenarioListResponse)
async def list_scenarios(
    search: str | None = None,
    tag: str | None = None,
    is_enabled: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取场景列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if search:
        conditions.append("(name LIKE %s OR description LIKE %s)")
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern])
    
    if is_enabled is not None:
        conditions.append("is_enabled = %s")
        params.append(is_enabled)
    
    if tag:
        conditions.append("JSON_CONTAINS(tags, %s)")
        params.append(json.dumps(tag))
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM test_scenarios {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM test_scenarios
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(sql, tuple(params))
    
    items = []
    for row in rows:
        scenario = _row_to_scenario_response(row)
        scenario.steps = _get_scenario_steps(db, row['scenario_id'])
        items.append(scenario)
    
    return ScenarioListResponse(total=total, items=items)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(scenario_id: str):
    """获取单个场景"""
    db = get_db_manager()
    sql = "SELECT * FROM test_scenarios WHERE scenario_id = %s"
    row = db.fetch_one(sql, (scenario_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="场景不存在")
    
    scenario = _row_to_scenario_response(row)
    scenario.steps = _get_scenario_steps(db, scenario_id)
    return scenario


@router.post("", response_model=ScenarioResponse)
async def create_scenario(scenario: ScenarioCreate):
    """创建场景"""
    db = get_db_manager()
    
    # 生成 scenario_id
    scenario_id = f"scenario_{int(time.time() * 1000)}"
    
    # 创建场景
    sql = """
        INSERT INTO test_scenarios 
        (scenario_id, name, description, tags, variables, retry_on_failure, max_retries)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    db.execute(sql, (
        scenario_id,
        scenario.name,
        scenario.description,
        json.dumps(scenario.tags, ensure_ascii=False),
        json.dumps(scenario.variables, ensure_ascii=False),
        scenario.retry_on_failure,
        scenario.max_retries
    ))
    
    # 创建步骤
    for i, step in enumerate(scenario.steps):
        _create_step(db, scenario_id, step, i + 1)
    
    # 返回创建的场景
    row = db.fetch_one("SELECT * FROM test_scenarios WHERE scenario_id = %s", (scenario_id,))
    result = _row_to_scenario_response(row)
    result.steps = _get_scenario_steps(db, scenario_id)
    return result


@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(scenario_id: str, scenario: ScenarioUpdate):
    """更新场景"""
    db = get_db_manager()
    
    # 检查是否存在
    existing = db.fetch_one(
        "SELECT * FROM test_scenarios WHERE scenario_id = %s",
        (scenario_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="场景不存在")
    
    # 构建更新语句
    updates = []
    params: list[Any] = []
    
    if scenario.name is not None:
        updates.append("name = %s")
        params.append(scenario.name)
    
    if scenario.description is not None:
        updates.append("description = %s")
        params.append(scenario.description)
    
    if scenario.tags is not None:
        updates.append("tags = %s")
        params.append(json.dumps(scenario.tags, ensure_ascii=False))
    
    if scenario.variables is not None:
        updates.append("variables = %s")
        params.append(json.dumps(scenario.variables, ensure_ascii=False))
    
    if scenario.retry_on_failure is not None:
        updates.append("retry_on_failure = %s")
        params.append(scenario.retry_on_failure)
    
    if scenario.max_retries is not None:
        updates.append("max_retries = %s")
        params.append(scenario.max_retries)
    
    if scenario.is_enabled is not None:
        updates.append("is_enabled = %s")
        params.append(scenario.is_enabled)
    
    if updates:
        sql = f"UPDATE test_scenarios SET {', '.join(updates)} WHERE scenario_id = %s"
        params.append(scenario_id)
        db.execute(sql, tuple(params))
    
    # 返回更新后的场景
    row = db.fetch_one("SELECT * FROM test_scenarios WHERE scenario_id = %s", (scenario_id,))
    result = _row_to_scenario_response(row)
    result.steps = _get_scenario_steps(db, scenario_id)
    return result


@router.delete("/{scenario_id}")
async def delete_scenario(scenario_id: str):
    """删除场景"""
    db = get_db_manager()
    
    # 检查是否存在
    existing = db.fetch_one(
        "SELECT scenario_id FROM test_scenarios WHERE scenario_id = %s",
        (scenario_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="场景不存在")
    
    # 删除场景（步骤会级联删除）
    db.execute("DELETE FROM test_scenarios WHERE scenario_id = %s", (scenario_id,))
    
    return {"message": "删除成功"}


@router.post("/{scenario_id}/steps", response_model=StepResponse)
async def add_step(scenario_id: str, step: StepCreate):
    """添加步骤"""
    db = get_db_manager()
    
    # 检查场景是否存在
    existing = db.fetch_one(
        "SELECT scenario_id FROM test_scenarios WHERE scenario_id = %s",
        (scenario_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="场景不存在")
    
    # 获取当前最大步骤顺序
    max_order = db.fetch_one(
        "SELECT MAX(step_order) as max_order FROM scenario_steps WHERE scenario_id = %s",
        (scenario_id,)
    )
    next_order = (max_order['max_order'] or 0) + 1 if max_order else 1
    
    # 创建步骤
    step_id = _create_step(db, scenario_id, step, next_order)
    
    # 返回创建的步骤
    row = db.fetch_one("SELECT * FROM scenario_steps WHERE step_id = %s", (step_id,))
    return _row_to_step_response(row)


@router.put("/{scenario_id}/steps/{step_id}", response_model=StepResponse)
async def update_step(scenario_id: str, step_id: str, step: StepCreate):
    """更新步骤"""
    db = get_db_manager()
    
    # 检查步骤是否存在
    existing = db.fetch_one(
        "SELECT * FROM scenario_steps WHERE scenario_id = %s AND step_id = %s",
        (scenario_id, step_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="步骤不存在")
    
    # 更新步骤
    sql = """
        UPDATE scenario_steps SET
            name = %s, description = %s, step_type = %s, method = %s, url = %s,
            headers = %s, body = %s, query_params = %s, extractions = %s,
            assertions = %s, wait_time_ms = %s, timeout_ms = %s, continue_on_failure = %s
        WHERE step_id = %s
    """
    db.execute(sql, (
        step.name,
        step.description,
        step.step_type,
        step.method,
        step.url,
        json.dumps(step.headers, ensure_ascii=False),
        json.dumps(step.body, ensure_ascii=False) if step.body else None,
        json.dumps(step.query_params, ensure_ascii=False),
        json.dumps(step.extractions, ensure_ascii=False),
        json.dumps(step.assertions, ensure_ascii=False),
        step.wait_time_ms,
        step.timeout_ms,
        step.continue_on_failure,
        step_id
    ))
    
    # 返回更新后的步骤
    row = db.fetch_one("SELECT * FROM scenario_steps WHERE step_id = %s", (step_id,))
    return _row_to_step_response(row)


@router.delete("/{scenario_id}/steps/{step_id}")
async def delete_step(scenario_id: str, step_id: str):
    """删除步骤"""
    db = get_db_manager()
    
    # 检查步骤是否存在
    existing = db.fetch_one(
        "SELECT * FROM scenario_steps WHERE scenario_id = %s AND step_id = %s",
        (scenario_id, step_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="步骤不存在")
    
    # 删除步骤
    db.execute("DELETE FROM scenario_steps WHERE step_id = %s", (step_id,))
    
    # 重新排序剩余步骤
    steps = db.fetch_all(
        "SELECT step_id FROM scenario_steps WHERE scenario_id = %s ORDER BY step_order",
        (scenario_id,)
    )
    for i, s in enumerate(steps):
        db.execute(
            "UPDATE scenario_steps SET step_order = %s WHERE step_id = %s",
            (i + 1, s['step_id'])
        )
    
    return {"message": "删除成功"}


@router.post("/{scenario_id}/steps/reorder")
async def reorder_steps(scenario_id: str, step_ids: list[str]):
    """重新排序步骤"""
    db = get_db_manager()
    
    for i, step_id in enumerate(step_ids):
        db.execute(
            "UPDATE scenario_steps SET step_order = %s WHERE scenario_id = %s AND step_id = %s",
            (i + 1, scenario_id, step_id)
        )
    
    return {"message": "排序成功"}


@router.post("/{scenario_id}/execute")
async def execute_scenario(
    scenario_id: str,
    request: ExecuteRequest,
    background_tasks: BackgroundTasks
):
    """执行场景"""
    db = get_db_manager()
    
    # 获取场景
    row = db.fetch_one("SELECT * FROM test_scenarios WHERE scenario_id = %s", (scenario_id,))
    if not row:
        raise HTTPException(status_code=404, detail="场景不存在")
    
    if not row.get('is_enabled'):
        raise HTTPException(status_code=400, detail="场景已禁用")
    
    # 创建执行记录
    execution_id = f"exec_{int(time.time() * 1000)}"
    
    sql = """
        INSERT INTO scenario_executions 
        (execution_id, scenario_id, trigger_type, status, base_url, environment, variables)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    db.execute(sql, (
        execution_id,
        scenario_id,
        'manual',
        'pending',
        request.base_url,
        request.environment,
        json.dumps(request.variables, ensure_ascii=False)
    ))
    
    # 后台执行
    background_tasks.add_task(
        _execute_scenario_background,
        scenario_id,
        execution_id,
        request.base_url,
        request.variables
    )
    
    return {
        "execution_id": execution_id,
        "message": "场景已开始执行"
    }


async def _execute_scenario_background(
    scenario_id: str,
    execution_id: str,
    base_url: str,
    variables: dict[str, Any]
):
    """后台执行场景"""
    from ...scenario import ScenarioExecutor
    from ...database.models import TriggerType
    
    db = get_db_manager()
    
    try:
        # 更新状态为运行中
        db.execute(
            "UPDATE scenario_executions SET status = 'running', started_at = NOW() WHERE execution_id = %s",
            (execution_id,)
        )
        
        # 获取场景和步骤
        row = db.fetch_one("SELECT * FROM test_scenarios WHERE scenario_id = %s", (scenario_id,))
        scenario = TestScenario.from_dict(row)
        
        step_rows = db.fetch_all(
            "SELECT * FROM scenario_steps WHERE scenario_id = %s ORDER BY step_order",
            (scenario_id,)
        )
        scenario.steps = [ScenarioStep.from_dict(r) for r in step_rows]
        
        # 执行场景
        executor = ScenarioExecutor(base_url=base_url)
        result = await executor.execute_scenario(
            scenario=scenario,
            initial_variables=variables,
            trigger_type=TriggerType.MANUAL
        )
        
        # 保存步骤结果
        for sr in result.step_results:
            sql = """
                INSERT INTO step_results 
                (execution_id, step_id, step_order, status, request_url, request_headers,
                 request_body, response_status_code, response_headers, response_body,
                 response_time_ms, extracted_variables, assertion_results, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute(sql, (
                execution_id,
                sr.step_id,
                sr.step_order,
                sr.status.value,
                sr.request_url,
                json.dumps(sr.request_headers, ensure_ascii=False),
                sr.request_body,
                sr.response_status_code,
                json.dumps(sr.response_headers, ensure_ascii=False),
                sr.response_body[:65535] if sr.response_body else '',  # 限制长度
                sr.response_time_ms,
                json.dumps(sr.extracted_variables, ensure_ascii=False),
                json.dumps(sr.assertion_results, ensure_ascii=False),
                sr.error_message
            ))
        
        # 更新执行记录
        db.execute(
            """
            UPDATE scenario_executions SET 
                status = %s, total_steps = %s, passed_steps = %s, failed_steps = %s,
                skipped_steps = %s, duration_ms = %s, error_message = %s,
                variables = %s, completed_at = NOW()
            WHERE execution_id = %s
            """,
            (
                result.status.value,
                result.total_steps,
                result.passed_steps,
                result.failed_steps,
                result.skipped_steps,
                result.duration_ms,
                result.error_message,
                json.dumps(result.final_variables, ensure_ascii=False),
                execution_id
            )
        )
    
    except Exception as e:
        db.execute(
            """
            UPDATE scenario_executions SET 
                status = 'failed', error_message = %s, completed_at = NOW()
            WHERE execution_id = %s
            """,
            (str(e), execution_id)
        )


def _create_step(db: Any, scenario_id: str, step: StepCreate, order: int) -> str:
    """创建步骤"""
    step_id = f"step_{int(time.time() * 1000)}_{order}"
    
    sql = """
        INSERT INTO scenario_steps 
        (scenario_id, step_id, step_order, name, description, step_type, method, url,
         headers, body, query_params, extractions, assertions, wait_time_ms, timeout_ms,
         continue_on_failure)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    db.execute(sql, (
        scenario_id,
        step_id,
        order,
        step.name,
        step.description,
        step.step_type,
        step.method,
        step.url,
        json.dumps(step.headers, ensure_ascii=False),
        json.dumps(step.body, ensure_ascii=False) if step.body else None,
        json.dumps(step.query_params, ensure_ascii=False),
        json.dumps(step.extractions, ensure_ascii=False),
        json.dumps(step.assertions, ensure_ascii=False),
        step.wait_time_ms,
        step.timeout_ms,
        step.continue_on_failure
    ))
    
    return step_id


def _get_scenario_steps(db: Any, scenario_id: str) -> list[StepResponse]:
    """获取场景的步骤"""
    sql = "SELECT * FROM scenario_steps WHERE scenario_id = %s ORDER BY step_order"
    rows = db.fetch_all(sql, (scenario_id,))
    return [_row_to_step_response(row) for row in rows]


def _row_to_scenario_response(row: dict[str, Any]) -> ScenarioResponse:
    """转换数据库行为场景响应"""
    tags = row.get('tags', '[]')
    if isinstance(tags, str):
        tags = json.loads(tags) if tags else []
    
    variables = row.get('variables', '{}')
    if isinstance(variables, str):
        variables = json.loads(variables) if variables else {}
    
    return ScenarioResponse(
        id=row['id'],
        scenario_id=row['scenario_id'],
        name=row['name'],
        description=row.get('description', ''),
        tags=tags,
        variables=variables,
        retry_on_failure=bool(row.get('retry_on_failure', False)),
        max_retries=row.get('max_retries', 3),
        is_enabled=bool(row.get('is_enabled', True)),
        steps=[]
    )


def _row_to_step_response(row: dict[str, Any]) -> StepResponse:
    """转换数据库行为步骤响应"""
    headers = row.get('headers', '{}')
    if isinstance(headers, str):
        headers = json.loads(headers) if headers else {}
    
    body = row.get('body')
    if isinstance(body, str):
        body = json.loads(body) if body else None
    
    query_params = row.get('query_params', '{}')
    if isinstance(query_params, str):
        query_params = json.loads(query_params) if query_params else {}
    
    extractions = row.get('extractions', '[]')
    if isinstance(extractions, str):
        extractions = json.loads(extractions) if extractions else []
    
    assertions = row.get('assertions', '[]')
    if isinstance(assertions, str):
        assertions = json.loads(assertions) if assertions else []
    
    return StepResponse(
        id=row['id'],
        step_id=row['step_id'],
        step_order=row['step_order'],
        name=row['name'],
        description=row.get('description', ''),
        step_type=row.get('step_type', 'request'),
        method=row.get('method', 'GET'),
        url=row.get('url', ''),
        headers=headers,
        body=body,
        query_params=query_params,
        extractions=extractions,
        assertions=assertions,
        wait_time_ms=row.get('wait_time_ms', 0),
        timeout_ms=row.get('timeout_ms', 30000),
        continue_on_failure=bool(row.get('continue_on_failure', False)),
        is_enabled=bool(row.get('is_enabled', True))
    )
