"""
测试用例管理路由
提供测试用例的CRUD、执行、定时任务等功能
"""

import json
import uuid
import asyncio
import httpx
from datetime import datetime
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field

from ...database.connection import get_db_manager
from ...database.models import (
    TestCaseRecord, TestCaseCategory, TestCasePriority,
    TestResultRecord, TestResultStatus,
    TestExecution, ExecutionStatus, TriggerType,
    ScheduledTask
)
from ...utils.logger import get_logger
from ...config import get_config

router = APIRouter(prefix="/api/v1/test-cases", tags=["测试用例管理"])
logger = get_logger("test_cases")


# =====================================================
# 请求/响应模型
# =====================================================

class TestCaseCreate(BaseModel):
    """创建测试用例请求"""
    endpoint_id: str = Field(..., description="关联接口ID")
    name: str = Field(..., description="用例名称")
    description: str = Field("", description="用例描述")
    category: str = Field("normal", description="用例类别")
    priority: str = Field("medium", description="优先级")
    method: str = Field(..., description="HTTP方法")
    url: str = Field(..., description="请求URL")
    headers: dict[str, str] = Field(default_factory=dict, description="请求头")
    body: dict[str, Any] | None = Field(None, description="请求体")
    query_params: dict[str, str] = Field(default_factory=dict, description="查询参数")
    expected_status_code: int = Field(200, description="期望状态码")
    expected_response: dict[str, Any] = Field(default_factory=dict, description="期望响应")
    assertions: list[dict[str, Any]] = Field(default_factory=list, description="断言规则")
    max_response_time_ms: int = Field(3000, description="最大响应时间")
    tags: list[str] = Field(default_factory=list, description="标签")


class TestCaseUpdate(BaseModel):
    """更新测试用例请求"""
    name: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    method: str | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    body: dict[str, Any] | None = None
    query_params: dict[str, str] | None = None
    expected_status_code: int | None = None
    expected_response: dict[str, Any] | None = None
    assertions: list[dict[str, Any]] | None = None
    max_response_time_ms: int | None = None
    tags: list[str] | None = None
    is_enabled: bool | None = None


class ExecuteRequest(BaseModel):
    """执行测试请求"""
    case_ids: list[str] = Field(default_factory=list, description="要执行的用例ID列表")
    endpoint_ids: list[str] = Field(default_factory=list, description="要执行的接口ID列表（执行该接口下所有用例）")
    base_url: str = Field(..., description="测试目标URL")
    environment: str = Field("", description="执行环境")
    variables: dict[str, Any] = Field(default_factory=dict, description="全局变量")
    headers: dict[str, str] = Field(default_factory=dict, description="全局请求头")


class ScheduledTaskCreate(BaseModel):
    """创建定时任务请求"""
    name: str = Field(..., description="任务名称")
    description: str = Field("", description="任务描述")
    cron_expression: str = Field(..., description="Cron表达式")
    case_ids: list[str] = Field(default_factory=list, description="要执行的用例ID")
    endpoint_ids: list[str] = Field(default_factory=list, description="要执行的接口ID")
    tag_names: list[str] = Field(default_factory=list, description="按标签筛选")
    base_url: str = Field(..., description="测试目标URL")
    environment: str = Field("", description="执行环境")
    variables: dict[str, Any] = Field(default_factory=dict, description="执行变量")
    headers: dict[str, str] = Field(default_factory=dict, description="全局请求头")
    notify_on_failure: bool = Field(True, description="失败时是否通知")
    notify_channels: list[str] = Field(default_factory=list, description="通知渠道")
    notify_config: dict[str, Any] = Field(default_factory=dict, description="通知配置")


# =====================================================
# 测试用例 CRUD
# =====================================================

@router.get("")
async def list_test_cases(
    endpoint_id: str | None = Query(None, description="按接口ID筛选"),
    category: str | None = Query(None, description="按类别筛选"),
    priority: str | None = Query(None, description="按优先级筛选"),
    is_enabled: bool | None = Query(None, description="按启用状态筛选"),
    tag: str | None = Query(None, description="按标签筛选"),
    search: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取测试用例列表"""
    db = get_db_manager()
    
    # 构建查询条件
    conditions = []
    params: list[Any] = []
    
    if endpoint_id:
        conditions.append("endpoint_id = %s")
        params.append(endpoint_id)
    if category:
        conditions.append("category = %s")
        params.append(category)
    if priority:
        conditions.append("priority = %s")
        params.append(priority)
    if is_enabled is not None:
        conditions.append("is_enabled = %s")
        params.append(is_enabled)
    if search:
        conditions.append("(name LIKE %s OR description LIKE %s OR url LIKE %s)")
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # 查询总数
    count_sql = f"SELECT COUNT(*) as total FROM test_cases WHERE {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params))
    total = count_result['total'] if count_result else 0
    
    # 查询数据
    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT tc.*, 
               (SELECT COUNT(*) FROM test_results tr WHERE tr.case_id = tc.case_id) as execution_count,
               (SELECT status FROM test_results tr WHERE tr.case_id = tc.case_id ORDER BY executed_at DESC LIMIT 1) as last_status
        FROM test_cases tc
        WHERE {where_clause}
        ORDER BY tc.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(data_sql, tuple(params))
    
    # 转换数据
    items = []
    for row in rows:
        item = TestCaseRecord.from_dict(row)
        items.append({
            **item.to_dict(),
            "execution_count": row.get('execution_count', 0),
            "last_status": row.get('last_status')
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/by-endpoint/{endpoint_id}")
async def get_test_cases_by_endpoint(
    endpoint_id: str,
    enabled_only: bool = Query(False, description="仅返回启用的用例")
):
    """获取接口的所有测试用例"""
    db = get_db_manager()
    
    if enabled_only:
        sql = "SELECT * FROM test_cases WHERE endpoint_id = %s AND is_enabled = 1 ORDER BY created_at"
    else:
        sql = "SELECT * FROM test_cases WHERE endpoint_id = %s ORDER BY created_at"
    
    rows = db.fetch_all(sql, (endpoint_id,))
    items = [TestCaseRecord.from_dict(row) for row in rows]
    
    return {
        "endpoint_id": endpoint_id,
        "total": len(items),
        "items": [item.to_dict() for item in items]
    }


@router.get("/{case_id}")
async def get_test_case(case_id: str):
    """获取单个测试用例详情"""
    db = get_db_manager()
    
    sql = "SELECT * FROM test_cases WHERE case_id = %s"
    row = db.fetch_one(sql, (case_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    item = TestCaseRecord.from_dict(row)
    
    # 获取最近执行记录
    result_sql = """
        SELECT * FROM test_results 
        WHERE case_id = %s 
        ORDER BY executed_at DESC 
        LIMIT 10
    """
    results = db.fetch_all(result_sql, (case_id,))
    
    return {
        **item.to_dict(),
        "recent_results": results
    }


@router.post("")
async def create_test_case(data: TestCaseCreate):
    """创建测试用例"""
    db = get_db_manager()
    
    case_id = f"tc_{uuid.uuid4().hex[:12]}"
    
    test_case = TestCaseRecord(
        case_id=case_id,
        endpoint_id=data.endpoint_id,
        name=data.name,
        description=data.description,
        category=TestCaseCategory(data.category),
        priority=TestCasePriority(data.priority),
        method=data.method,
        url=data.url,
        headers=data.headers,
        body=data.body,
        query_params=data.query_params,
        expected_status_code=data.expected_status_code,
        expected_response=data.expected_response,
        assertions=data.assertions,
        max_response_time_ms=data.max_response_time_ms,
        tags=data.tags
    )
    
    tc_data = test_case.to_dict()
    sql = """
        INSERT INTO test_cases 
        (case_id, endpoint_id, name, description, category, priority, method, url,
         headers, body, query_params, expected_status_code, expected_response,
         assertions, max_response_time_ms, tags, is_enabled, is_ai_generated, source_task_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        tc_data['case_id'], tc_data['endpoint_id'], tc_data['name'], tc_data['description'],
        tc_data['category'], tc_data['priority'], tc_data['method'], tc_data['url'],
        tc_data['headers'], tc_data['body'], tc_data['query_params'],
        tc_data['expected_status_code'], tc_data['expected_response'],
        tc_data['assertions'], tc_data['max_response_time_ms'], tc_data['tags'],
        tc_data['is_enabled'], tc_data['is_ai_generated'], tc_data['source_task_id']
    )
    db.execute(sql, params)
    
    return {"case_id": case_id, "message": "创建成功"}


@router.put("/{case_id}")
async def update_test_case(case_id: str, data: TestCaseUpdate):
    """更新测试用例"""
    db = get_db_manager()
    
    # 检查是否存在
    check_sql = "SELECT case_id FROM test_cases WHERE case_id = %s"
    if not db.fetch_one(check_sql, (case_id,)):
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    # 构建更新语句
    updates = []
    params: list[Any] = []
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            if key in ('headers', 'body', 'query_params', 'expected_response', 'assertions', 'tags'):
                value = json.dumps(value, ensure_ascii=False)
            updates.append(f"{key} = %s")
            params.append(value)
    
    if not updates:
        return {"message": "没有需要更新的字段"}
    
    sql = f"UPDATE test_cases SET {', '.join(updates)} WHERE case_id = %s"
    params.append(case_id)
    db.execute(sql, tuple(params))
    
    return {"message": "更新成功"}


@router.delete("/{case_id}")
async def delete_test_case(case_id: str):
    """删除测试用例"""
    db = get_db_manager()
    
    sql = "DELETE FROM test_cases WHERE case_id = %s"
    affected = db.execute(sql, (case_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    return {"message": "删除成功"}


@router.post("/{case_id}/toggle")
async def toggle_test_case(case_id: str):
    """切换测试用例启用状态"""
    db = get_db_manager()
    
    sql = "UPDATE test_cases SET is_enabled = NOT is_enabled WHERE case_id = %s"
    affected = db.execute(sql, (case_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    # 获取当前状态
    status_sql = "SELECT is_enabled FROM test_cases WHERE case_id = %s"
    row = db.fetch_one(status_sql, (case_id,))
    
    return {"is_enabled": row['is_enabled'] if row else False}


# =====================================================
# 测试执行
# =====================================================

async def execute_single_case(
    case: TestCaseRecord,
    execution_id: str,
    base_url: str,
    global_headers: dict[str, str],
    global_variables: dict[str, Any]
) -> TestResultRecord:
    """执行单个测试用例"""
    start_time = datetime.now()
    
    # 合并请求头
    headers = {**global_headers, **case.headers}
    
    # 构建完整URL
    url = case.url
    if not url.startswith("http"):
        url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
    
    # 添加查询参数
    if case.query_params:
        query_string = "&".join(f"{k}={v}" for k, v in case.query_params.items())
        url = f"{url}?{query_string}" if "?" not in url else f"{url}&{query_string}"
    
    try:
        async with httpx.AsyncClient(timeout=case.max_response_time_ms / 1000) as client:
            response = await client.request(
                method=case.method,
                url=url,
                headers=headers,
                json=case.body if case.body else None
            )
            
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # 执行断言
            assertion_results = []
            all_passed = True
            
            # 状态码断言
            status_passed = response.status_code == case.expected_status_code
            assertion_results.append({
                "type": "status_code",
                "expected": case.expected_status_code,
                "actual": response.status_code,
                "passed": status_passed
            })
            if not status_passed:
                all_passed = False
            
            # 响应时间断言
            time_passed = response_time_ms <= case.max_response_time_ms
            assertion_results.append({
                "type": "response_time",
                "expected": f"<= {case.max_response_time_ms}ms",
                "actual": f"{response_time_ms:.2f}ms",
                "passed": time_passed
            })
            if not time_passed:
                all_passed = False
            
            # 自定义断言
            for assertion in case.assertions:
                # TODO: 实现更复杂的断言逻辑
                pass
            
            status = TestResultStatus.PASSED if all_passed else TestResultStatus.FAILED
            
            return TestResultRecord(
                case_id=case.case_id,
                execution_id=execution_id,
                status=status,
                actual_status_code=response.status_code,
                actual_response_time_ms=response_time_ms,
                actual_response_body=response.text[:10000],  # 限制长度
                actual_headers=dict(response.headers),
                assertion_results=assertion_results,
                executed_at=end_time
            )
            
    except httpx.TimeoutException:
        return TestResultRecord(
            case_id=case.case_id,
            execution_id=execution_id,
            status=TestResultStatus.ERROR,
            error_message="请求超时",
            executed_at=datetime.now()
        )
    except Exception as e:
        return TestResultRecord(
            case_id=case.case_id,
            execution_id=execution_id,
            status=TestResultStatus.ERROR,
            error_message=str(e),
            executed_at=datetime.now()
        )


async def run_execution(execution_id: str, cases: list[TestCaseRecord], request: ExecuteRequest):
    """后台执行测试"""
    db = get_db_manager()
    
    # 更新执行状态为运行中
    db.execute(
        "UPDATE test_executions SET status = %s, started_at = %s WHERE execution_id = %s",
        (ExecutionStatus.RUNNING.value, datetime.now(), execution_id)
    )
    
    passed = 0
    failed = 0
    error = 0
    
    for case in cases:
        result = await execute_single_case(
            case=case,
            execution_id=execution_id,
            base_url=request.base_url,
            global_headers=request.headers,
            global_variables=request.variables
        )
        
        # 保存结果
        result_data = result.to_dict()
        db.execute("""
            INSERT INTO test_results 
            (case_id, execution_id, status, actual_status_code, actual_response_time_ms,
             actual_response_body, actual_headers, error_message, assertion_results, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            result_data['case_id'], result_data['execution_id'], result_data['status'],
            result_data['actual_status_code'], result_data['actual_response_time_ms'],
            result_data['actual_response_body'], result_data['actual_headers'],
            result_data['error_message'], result_data['assertion_results'], result_data['executed_at']
        ))
        
        if result.status == TestResultStatus.PASSED:
            passed += 1
        elif result.status == TestResultStatus.FAILED:
            failed += 1
        else:
            error += 1
    
    # 更新执行状态为完成
    db.execute("""
        UPDATE test_executions 
        SET status = %s, completed_at = %s, passed_cases = %s, failed_cases = %s, error_cases = %s
        WHERE execution_id = %s
    """, (ExecutionStatus.COMPLETED.value, datetime.now(), passed, failed, error, execution_id))


@router.post("/execute")
async def execute_test_cases(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """执行测试用例"""
    db = get_db_manager()
    
    # 收集要执行的用例
    cases: list[TestCaseRecord] = []
    
    if request.case_ids:
        placeholders = ",".join(["%s"] * len(request.case_ids))
        sql = f"SELECT * FROM test_cases WHERE case_id IN ({placeholders}) AND is_enabled = 1"
        rows = db.fetch_all(sql, tuple(request.case_ids))
        cases.extend([TestCaseRecord.from_dict(row) for row in rows])
    
    if request.endpoint_ids:
        placeholders = ",".join(["%s"] * len(request.endpoint_ids))
        sql = f"SELECT * FROM test_cases WHERE endpoint_id IN ({placeholders}) AND is_enabled = 1"
        rows = db.fetch_all(sql, tuple(request.endpoint_ids))
        cases.extend([TestCaseRecord.from_dict(row) for row in rows])
    
    if not cases:
        raise HTTPException(status_code=400, detail="没有找到可执行的测试用例")
    
    # 去重
    seen = set()
    unique_cases = []
    for case in cases:
        if case.case_id not in seen:
            seen.add(case.case_id)
            unique_cases.append(case)
    cases = unique_cases
    
    # 创建执行记录
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    execution = TestExecution(
        execution_id=execution_id,
        name=f"执行 {len(cases)} 个测试用例",
        trigger_type=TriggerType.MANUAL,
        status=ExecutionStatus.PENDING,
        base_url=request.base_url,
        environment=request.environment,
        variables=request.variables,
        headers=request.headers,
        total_cases=len(cases)
    )
    
    exec_data = execution.to_dict()
    db.execute("""
        INSERT INTO test_executions 
        (execution_id, name, description, trigger_type, status, base_url, environment,
         variables, headers, total_cases, passed_cases, failed_cases, error_cases, skipped_cases)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        exec_data['execution_id'], exec_data['name'], exec_data['description'],
        exec_data['trigger_type'], exec_data['status'], exec_data['base_url'],
        exec_data['environment'], exec_data['variables'], exec_data['headers'],
        exec_data['total_cases'], 0, 0, 0, 0
    ))
    
    # 后台执行
    background_tasks.add_task(run_execution, execution_id, cases, request)
    
    return {
        "execution_id": execution_id,
        "total_cases": len(cases),
        "message": "测试执行已启动"
    }


@router.get("/executions")
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取执行记录列表"""
    db = get_db_manager()
    
    # 查询总数
    count_sql = "SELECT COUNT(*) as total FROM test_executions"
    count_result = db.fetch_one(count_sql)
    total = count_result['total'] if count_result else 0
    
    # 查询数据
    offset = (page - 1) * page_size
    sql = """
        SELECT * FROM test_executions 
        ORDER BY created_at DESC 
        LIMIT %s OFFSET %s
    """
    rows = db.fetch_all(sql, (page_size, offset))
    
    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """获取执行详情"""
    db = get_db_manager()
    
    # 获取执行记录
    exec_sql = "SELECT * FROM test_executions WHERE execution_id = %s"
    execution = db.fetch_one(exec_sql, (execution_id,))
    
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 获取执行结果
    results_sql = """
        SELECT tr.*, tc.name as case_name, tc.url as case_url
        FROM test_results tr
        LEFT JOIN test_cases tc ON tr.case_id = tc.case_id
        WHERE tr.execution_id = %s
        ORDER BY tr.executed_at
    """
    results = db.fetch_all(results_sql, (execution_id,))
    
    return {
        "execution": execution,
        "results": results
    }


# =====================================================
# 定时任务
# =====================================================

@router.get("/scheduled-tasks")
async def list_scheduled_tasks():
    """获取定时任务列表"""
    db = get_db_manager()
    
    sql = "SELECT * FROM scheduled_tasks ORDER BY created_at DESC"
    rows = db.fetch_all(sql)
    
    return {"items": rows}


@router.post("/scheduled-tasks")
async def create_scheduled_task(data: ScheduledTaskCreate):
    """创建定时任务"""
    db = get_db_manager()
    
    task_id = f"sched_{uuid.uuid4().hex[:12]}"
    
    task = ScheduledTask(
        task_id=task_id,
        name=data.name,
        description=data.description,
        cron_expression=data.cron_expression,
        case_ids=data.case_ids,
        endpoint_ids=data.endpoint_ids,
        tag_names=data.tag_names,
        base_url=data.base_url,
        environment=data.environment,
        variables=data.variables,
        headers=data.headers,
        notify_on_failure=data.notify_on_failure,
        notify_channels=data.notify_channels,
        notify_config=data.notify_config
    )
    
    task_data = task.to_dict()
    sql = """
        INSERT INTO scheduled_tasks 
        (task_id, name, description, cron_expression, case_ids, endpoint_ids, tag_names,
         base_url, environment, variables, headers, notify_on_failure, notify_channels,
         notify_config, is_enabled)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        task_data['task_id'], task_data['name'], task_data['description'],
        task_data['cron_expression'], task_data['case_ids'], task_data['endpoint_ids'],
        task_data['tag_names'], task_data['base_url'], task_data['environment'],
        task_data['variables'], task_data['headers'], task_data['notify_on_failure'],
        task_data['notify_channels'], task_data['notify_config'], task_data['is_enabled']
    )
    db.execute(sql, params)
    
    return {"task_id": task_id, "message": "创建成功"}


@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: str):
    """删除定时任务"""
    db = get_db_manager()
    
    sql = "DELETE FROM scheduled_tasks WHERE task_id = %s"
    affected = db.execute(sql, (task_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    return {"message": "删除成功"}


@router.post("/scheduled-tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str):
    """切换定时任务启用状态"""
    db = get_db_manager()
    
    sql = "UPDATE scheduled_tasks SET is_enabled = NOT is_enabled WHERE task_id = %s"
    affected = db.execute(sql, (task_id,))
    
    if affected == 0:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    # 获取当前状态
    status_sql = "SELECT is_enabled FROM scheduled_tasks WHERE task_id = %s"
    row = db.fetch_one(status_sql, (task_id,))
    
    return {"is_enabled": row['is_enabled'] if row else False}


# =====================================================
# 统计接口
# =====================================================

@router.get("/statistics")
async def get_statistics():
    """获取测试用例统计信息"""
    db = get_db_manager()
    
    # 用例统计
    case_stats_sql = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled,
            SUM(CASE WHEN is_ai_generated = 1 THEN 1 ELSE 0 END) as ai_generated
        FROM test_cases
    """
    case_stats = db.fetch_one(case_stats_sql)
    
    # 按类别统计
    category_stats_sql = """
        SELECT category, COUNT(*) as count 
        FROM test_cases 
        GROUP BY category
    """
    category_stats = db.fetch_all(category_stats_sql)
    
    # 按优先级统计
    priority_stats_sql = """
        SELECT priority, COUNT(*) as count 
        FROM test_cases 
        GROUP BY priority
    """
    priority_stats = db.fetch_all(priority_stats_sql)
    
    # 最近执行统计
    recent_exec_sql = """
        SELECT 
            COUNT(*) as total_executions,
            SUM(passed_cases) as total_passed,
            SUM(failed_cases) as total_failed,
            SUM(error_cases) as total_error
        FROM test_executions
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """
    recent_exec = db.fetch_one(recent_exec_sql)
    
    return {
        "cases": case_stats,
        "by_category": {row['category']: row['count'] for row in category_stats},
        "by_priority": {row['priority']: row['count'] for row in priority_stats},
        "recent_executions": recent_exec
    }


@router.get("/endpoint-summary")
async def get_endpoint_summary():
    """获取按接口分组的测试用例统计"""
    db = get_db_manager()
    
    sql = """
        SELECT 
            ae.endpoint_id,
            ae.name as endpoint_name,
            ae.method,
            ae.path,
            COUNT(tc.case_id) as case_count,
            SUM(CASE WHEN tc.is_enabled = 1 THEN 1 ELSE 0 END) as enabled_count
        FROM api_endpoints ae
        LEFT JOIN test_cases tc ON ae.endpoint_id = tc.endpoint_id
        GROUP BY ae.endpoint_id, ae.name, ae.method, ae.path
        ORDER BY case_count DESC
    """
    rows = db.fetch_all(sql)
    
    return {"items": rows}
