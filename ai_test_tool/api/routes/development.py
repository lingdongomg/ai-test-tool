"""
开发自测模块 API
场景一：开发阶段的接口测试
"""

import json
import uuid
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ...services import EndpointTestGeneratorService, AIAssistantService
from ...database import get_db_manager
from ...utils.logger import get_logger

router = APIRouter()
logger = get_logger()


# ==================== 请求/响应模型 ====================

class GenerateTestsRequest(BaseModel):
    """生成测试用例请求"""
    endpoint_ids: list[str] | None = Field(default=None, description="接口ID列表，为空则全部")
    tag_filter: str | None = Field(default=None, description="按标签筛选")
    test_types: list[str] | None = Field(
        default=None,
        description="测试类型: normal, boundary, exception, security"
    )
    use_ai: bool = Field(default=True, description="是否使用AI增强生成")
    skip_existing: bool = Field(default=True, description="跳过已有测试用例的接口")


class ExecuteTestsRequest(BaseModel):
    """执行测试请求"""
    test_case_ids: list[str] | None = Field(default=None, description="测试用例ID列表")
    endpoint_id: str | None = Field(default=None, description="按接口筛选")
    tag_filter: str | None = Field(default=None, description="按标签筛选")
    base_url: str = Field(..., description="目标服务器URL")
    environment: str = Field(default="local", description="环境: local/test/staging/production")


class TestExecutionResult(BaseModel):
    """测试执行结果"""
    execution_id: str
    total: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    duration_ms: float


class UpdateTestCaseRequest(BaseModel):
    """更新测试用例请求"""
    name: str | None = Field(default=None, description="用例名称")
    description: str | None = Field(default=None, description="用例描述")
    category: str | None = Field(default=None, description="用例类别: normal, boundary, exception, performance, security")
    priority: str | None = Field(default=None, description="优先级: high, medium, low")
    method: str | None = Field(default=None, description="HTTP方法")
    url: str | None = Field(default=None, description="请求URL")
    headers: dict | None = Field(default=None, description="请求头")
    body: dict | None = Field(default=None, description="请求体")
    query_params: dict | None = Field(default=None, description="查询参数")
    expected_status_code: int | None = Field(default=None, description="期望状态码")
    expected_response: dict | None = Field(default=None, description="期望响应")
    assertions: list | None = Field(default=None, description="断言规则")
    max_response_time_ms: int | None = Field(default=None, description="最大响应时间(ms)")
    is_enabled: bool | None = Field(default=None, description="是否启用")


# ==================== 接口管理 ====================

@router.get("/endpoints")
async def list_endpoints(
    search: str | None = None,
    method: str | None = None,
    tag_id: str | None = None,
    has_tests: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """
    获取接口列表
    
    - search: 搜索关键词（路径、描述）
    - method: HTTP方法筛选
    - tag_id: 标签筛选
    - has_tests: 是否有测试用例
    """
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if search:
        conditions.append("(e.path LIKE %s OR e.description LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    if method:
        conditions.append("e.method = %s")
        params.append(method.upper())
    
    if tag_id:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM api_endpoint_tags et 
                WHERE et.endpoint_id = e.endpoint_id AND et.tag_id = %s
            )
        """)
        params.append(tag_id)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM api_endpoints e {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据（包含测试用例数量）
    offset = (page - 1) * page_size
    sql = f"""
        SELECT 
            e.*,
            COALESCE((SELECT COUNT(*) FROM test_cases WHERE case_id LIKE CONCAT(e.endpoint_id, '%%')), 0) as test_case_count,
            (SELECT GROUP_CONCAT(t.name) FROM api_tags t 
             JOIN api_endpoint_tags et ON t.id = et.tag_id 
             WHERE et.endpoint_id = e.endpoint_id) as tag_names
        FROM api_endpoints e
        {where_clause}
        ORDER BY e.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(sql, tuple(params))
    
    # 如果需要筛选有/无测试用例
    items = [dict(row) for row in rows]
    if has_tests is not None:
        items = [
            item for item in items 
            if (item['test_case_count'] > 0) == has_tests
        ]
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }


@router.get("/endpoints/{endpoint_id}")
async def get_endpoint_detail(endpoint_id: str):
    """获取接口详情（包含测试用例）"""
    db = get_db_manager()
    
    # 获取接口信息
    endpoint_sql = "SELECT * FROM api_endpoints WHERE endpoint_id = %s"
    endpoint = db.fetch_one(endpoint_sql, (endpoint_id,))
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    
    # 获取关联的测试用例（通过 case_id 前缀匹配 endpoint_id）
    cases_sql = """
        SELECT * FROM test_cases 
        WHERE case_id LIKE %s 
        ORDER BY priority, created_at DESC
    """
    cases = db.fetch_all(cases_sql, (f"{endpoint_id}%",))
    
    # 获取关联的标签
    tags_sql = """
        SELECT t.* FROM api_tags t
        JOIN api_endpoint_tags et ON t.id = et.tag_id
        WHERE et.endpoint_id = %s
    """
    tags = db.fetch_all(tags_sql, (endpoint_id,))
    
    # 获取最近执行记录（基于已获取的 case_id 列表）
    recent_executions = []
    if cases:
        case_ids = [c['case_id'] for c in cases]
        placeholders = ','.join(['%s'] * len(case_ids))
        recent_executions_sql = f"""
            SELECT tr.* FROM test_results tr
            WHERE tr.case_id IN ({placeholders})
            ORDER BY tr.executed_at DESC
            LIMIT 10
        """
        recent_executions = db.fetch_all(recent_executions_sql, tuple(case_ids))
    
    return {
        "endpoint": dict(endpoint),
        "test_cases": [dict(c) for c in cases],
        "tags": [dict(t) for t in tags],
        "recent_executions": [dict(e) for e in recent_executions],
        "statistics": {
            "total_cases": len(cases),
            "recent_pass_rate": _calculate_pass_rate(recent_executions)
        }
    }


def _calculate_pass_rate(executions) -> float:
    """计算通过率"""
    if not executions:
        return 0.0
    passed = sum(1 for e in executions if e.get('status') == 'passed')
    return round(passed / len(executions) * 100, 2)


# ==================== 测试用例生成 ====================

def _run_generate_task(task_id: str, request_data: dict):
    """后台执行测试用例生成任务"""
    db = get_db_manager()
    
    try:
        # 更新任务状态为运行中
        db.execute("""
            UPDATE test_generation_tasks 
            SET status = 'running', started_at = NOW() 
            WHERE task_id = %s
        """, (task_id,))
        
        service = EndpointTestGeneratorService(verbose=True)
        endpoint_ids = request_data.get('endpoint_ids')
        tag_filter = request_data.get('tag_filter')
        test_types = request_data.get('test_types')
        use_ai = request_data.get('use_ai', True)
        skip_existing = request_data.get('skip_existing', True)
        
        if endpoint_ids and len(endpoint_ids) == 1:
            # 单个接口
            test_cases = service.generate_for_endpoint(
                endpoint_id=endpoint_ids[0],
                test_types=test_types,
                use_ai=use_ai,
                save_to_db=True
            )
            db.execute("""
                UPDATE test_generation_tasks 
                SET status = 'completed', 
                    total_endpoints = 1,
                    processed_endpoints = 1,
                    success_count = 1,
                    total_cases_generated = %s,
                    completed_at = NOW()
                WHERE task_id = %s
            """, (len(test_cases), task_id))
        else:
            # 批量生成
            result = service.generate_for_all_endpoints(
                endpoint_ids=endpoint_ids,
                tag_filter=tag_filter,
                test_types=test_types,
                use_ai=use_ai,
                skip_existing=skip_existing,
                save_to_db=True
            )
            db.execute("""
                UPDATE test_generation_tasks 
                SET status = 'completed',
                    total_endpoints = %s,
                    processed_endpoints = %s,
                    success_count = %s,
                    failed_count = %s,
                    total_cases_generated = %s,
                    errors = %s,
                    completed_at = NOW()
                WHERE task_id = %s
            """, (
                result['total_endpoints'],
                result['total_endpoints'],
                result['success_count'],
                result['failed_count'],
                result['total_cases_generated'],
                json.dumps(result.get('errors', []), ensure_ascii=False),
                task_id
            ))
    
    except Exception as e:
        logger.error(f"生成任务失败: {e}")
        db.execute("""
            UPDATE test_generation_tasks 
            SET status = 'failed', 
                error_message = %s,
                completed_at = NOW()
            WHERE task_id = %s
        """, (str(e), task_id))


@router.post("/tests/generate")
async def generate_tests(request: GenerateTestsRequest, background_tasks: BackgroundTasks):
    """
    为接口生成测试用例（异步任务）
    
    支持：
    - 为指定接口生成
    - 按标签批量生成
    - 为所有接口生成
    
    返回任务ID，可通过 GET /tests/generate/{task_id} 查询进度
    """
    db = get_db_manager()
    task_id = str(uuid.uuid4())[:16]
    task_type = 'single' if request.endpoint_ids and len(request.endpoint_ids) == 1 else 'batch'
    
    # 创建任务记录
    db.execute("""
        INSERT INTO test_generation_tasks 
        (task_id, task_type, status, endpoint_ids, tag_filter, test_types, use_ai, skip_existing)
        VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s)
    """, (
        task_id,
        task_type,
        json.dumps(request.endpoint_ids, ensure_ascii=False) if request.endpoint_ids else None,
        request.tag_filter,
        json.dumps(request.test_types, ensure_ascii=False) if request.test_types else None,
        1 if request.use_ai else 0,
        1 if request.skip_existing else 0
    ))
    
    # 添加后台任务
    request_data = {
        'endpoint_ids': request.endpoint_ids,
        'tag_filter': request.tag_filter,
        'test_types': request.test_types,
        'use_ai': request.use_ai,
        'skip_existing': request.skip_existing
    }
    background_tasks.add_task(_run_generate_task, task_id, request_data)
    
    return {
        "success": True,
        "message": "测试用例生成任务已创建，正在后台执行",
        "task_id": task_id,
        "task_type": task_type,
        "status": "pending"
    }


@router.get("/tests/generate/{task_id}")
async def get_generate_task_status(task_id: str):
    """查询测试用例生成任务状态"""
    db = get_db_manager()
    
    task = db.fetch_one("""
        SELECT * FROM test_generation_tasks WHERE task_id = %s
    """, (task_id,))
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    result = dict(task)
    # 解析 JSON 字段
    for field in ['endpoint_ids', 'test_types', 'errors']:
        if result.get(field) and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except:
                pass
    
    return result


@router.get("/tests/generate-tasks")
async def list_generate_tasks(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取测试用例生成任务列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if status:
        conditions.append("status = %s")
        params.append(status)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM test_generation_tasks {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM test_generation_tasks
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(sql, tuple(params))
    
    items = []
    for row in rows:
        item = dict(row)
        for field in ['endpoint_ids', 'test_types', 'errors']:
            if item.get(field) and isinstance(item[field], str):
                try:
                    item[field] = json.loads(item[field])
                except:
                    pass
        items.append(item)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }


@router.post("/tests/generate/{endpoint_id}")
async def generate_tests_for_endpoint(
    endpoint_id: str,
    background_tasks: BackgroundTasks,
    test_types: list[str] | None = Query(default=None),
    use_ai: bool = Query(default=True)
):
    """为单个接口生成测试用例（异步任务，快捷接口）"""
    db = get_db_manager()
    task_id = str(uuid.uuid4())[:16]
    
    # 创建任务记录
    db.execute("""
        INSERT INTO test_generation_tasks 
        (task_id, task_type, status, endpoint_ids, test_types, use_ai, skip_existing)
        VALUES (%s, 'single', 'pending', %s, %s, %s, 0)
    """, (
        task_id,
        json.dumps([endpoint_id], ensure_ascii=False),
        json.dumps(test_types, ensure_ascii=False) if test_types else None,
        1 if use_ai else 0
    ))
    
    # 添加后台任务
    request_data = {
        'endpoint_ids': [endpoint_id],
        'test_types': test_types,
        'use_ai': use_ai,
        'skip_existing': False
    }
    background_tasks.add_task(_run_generate_task, task_id, request_data)
    
    return {
        "success": True,
        "message": "测试用例生成任务已创建",
        "task_id": task_id,
        "endpoint_id": endpoint_id,
        "status": "pending"
    }


# ==================== 测试用例管理 ====================

@router.get("/tests")
async def list_test_cases(
    endpoint_id: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    is_enabled: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取测试用例列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if endpoint_id:
        # test_cases 表没有 endpoint_id 列，通过 case_id 前缀匹配
        conditions.append("tc.case_id LIKE %s")
        params.append(f"{endpoint_id}%")
    
    if category:
        conditions.append("tc.category = %s")
        params.append(category)
    
    if priority:
        conditions.append("tc.priority = %s")
        params.append(priority)
    
    if is_enabled is not None:
        conditions.append("tc.is_enabled = %s")
        params.append(is_enabled)
    
    if search:
        conditions.append("(tc.name LIKE %s OR tc.description LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM test_cases tc {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据，关联 api_endpoints 表获取接口信息
    # 注意：test_cases.task_id 实际存储的是 endpoint_id
    offset = (page - 1) * page_size
    sql = f"""
        SELECT 
            tc.*,
            e.method as endpoint_method,
            e.path as endpoint_path
        FROM test_cases tc
        LEFT JOIN api_endpoints e ON tc.task_id = e.endpoint_id
        {where_clause}
        ORDER BY tc.priority, tc.created_at DESC
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


@router.get("/tests/{test_case_id}")
async def get_test_case(test_case_id: str):
    """获取测试用例详情"""
    db = get_db_manager()
    
    # 直接查询 test_cases 表，不做 JOIN
    sql = "SELECT * FROM test_cases WHERE case_id = %s"
    row = db.fetch_one(sql, (test_case_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    # 获取最近执行记录
    executions_sql = """
        SELECT * FROM test_results 
        WHERE case_id = %s
        ORDER BY executed_at DESC
        LIMIT 20
    """
    executions = db.fetch_all(executions_sql, (test_case_id,))
    
    return {
        "test_case": dict(row),
        "executions": [dict(e) for e in executions]
    }


@router.put("/tests/{test_case_id}")
async def update_test_case(test_case_id: str, request: UpdateTestCaseRequest):
    """更新测试用例"""
    import json
    db = get_db_manager()
    
    # 检查用例是否存在
    existing = db.fetch_one("SELECT * FROM test_cases WHERE case_id = %s", (test_case_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    # 构建更新字段
    updates = []
    params: list[Any] = []
    
    if request.name is not None:
        updates.append("name = %s")
        params.append(request.name)
    
    if request.description is not None:
        updates.append("description = %s")
        params.append(request.description)
    
    if request.category is not None:
        updates.append("category = %s")
        params.append(request.category)
    
    if request.priority is not None:
        updates.append("priority = %s")
        params.append(request.priority)
    
    if request.method is not None:
        updates.append("method = %s")
        params.append(request.method)
    
    if request.url is not None:
        updates.append("url = %s")
        params.append(request.url)
    
    if request.headers is not None:
        updates.append("headers = %s")
        params.append(json.dumps(request.headers))
    
    if request.body is not None:
        updates.append("body = %s")
        params.append(json.dumps(request.body))
    
    if request.query_params is not None:
        updates.append("query_params = %s")
        params.append(json.dumps(request.query_params))
    
    if request.expected_status_code is not None:
        updates.append("expected_status_code = %s")
        params.append(request.expected_status_code)
    
    if request.expected_response is not None:
        updates.append("expected_response = %s")
        params.append(json.dumps(request.expected_response))
    
    if request.assertions is not None:
        updates.append("assertions = %s")
        params.append(json.dumps(request.assertions))
    
    if request.max_response_time_ms is not None:
        updates.append("max_response_time_ms = %s")
        params.append(request.max_response_time_ms)
    
    if request.is_enabled is not None:
        updates.append("is_enabled = %s")
        params.append(1 if request.is_enabled else 0)
    
    if not updates:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    
    # 执行更新
    params.append(test_case_id)
    sql = f"UPDATE test_cases SET {', '.join(updates)} WHERE case_id = %s"
    db.execute(sql, tuple(params))
    
    # 返回更新后的数据
    updated = db.fetch_one("SELECT * FROM test_cases WHERE case_id = %s", (test_case_id,))
    return {
        "success": True,
        "message": "测试用例更新成功",
        "test_case": dict(updated)
    }


@router.post("/tests/{test_case_id}/copy")
async def copy_test_case(test_case_id: str, request: Optional[UpdateTestCaseRequest] = None):
    """复制测试用例"""
    import hashlib
    
    db = get_db_manager()
    
    # 获取原始用例
    original = db.fetch_one("SELECT * FROM test_cases WHERE case_id = %s", (test_case_id,))
    if not original:
        raise HTTPException(status_code=404, detail="原始测试用例不存在")
    
    original = dict(original)
    
    # 生成新的 case_id
    task_id = original['task_id']  # endpoint_id
    timestamp = str(int(__import__('time').time() * 1000))
    hash_str = hashlib.md5(timestamp.encode()).hexdigest()[:8]
    new_case_id = f"{task_id}_{hash_str}"
    
    # 准备新用例数据，优先使用请求中的数据
    new_data = {
        'case_id': new_case_id,
        'task_id': task_id,
        'name': request.name if request and request.name else original['name'] + ' (副本)',
        'description': request.description if request and request.description is not None else original.get('description'),
        'category': request.category if request and request.category else original.get('category', 'normal'),
        'priority': request.priority if request and request.priority else original.get('priority', 'medium'),
        'method': request.method if request and hasattr(request, 'method') and request.method else original['method'],
        'url': request.url if request and hasattr(request, 'url') and request.url else original['url'],
        'headers': json.dumps(request.headers) if request and request.headers is not None else original.get('headers'),
        'body': json.dumps(request.body) if request and request.body is not None else original.get('body'),
        'query_params': json.dumps(request.query_params) if request and request.query_params is not None else original.get('query_params'),
        'expected_status_code': request.expected_status_code if request and request.expected_status_code else original.get('expected_status_code', 200),
        'max_response_time_ms': request.max_response_time_ms if request and request.max_response_time_ms else original.get('max_response_time_ms', 3000),
        'expected_response': original.get('expected_response'),
        'tags': original.get('tags'),
        'group_name': original.get('group_name'),
        'is_enabled': 1
    }
    
    # 插入新用例
    sql = """
        INSERT INTO test_cases (
            case_id, task_id, name, description, category, priority, 
            method, url, headers, body, query_params, 
            expected_status_code, max_response_time_ms, expected_response, 
            tags, group_name, is_enabled
        ) VALUES (
            %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, 
            %s, %s, %s, 
            %s, %s, %s
        )
    """
    db.execute(sql, (
        new_data['case_id'], new_data['task_id'], new_data['name'], 
        new_data['description'], new_data['category'], new_data['priority'],
        new_data['method'], new_data['url'], new_data['headers'], 
        new_data['body'], new_data['query_params'],
        new_data['expected_status_code'], new_data['max_response_time_ms'], 
        new_data['expected_response'],
        new_data['tags'], new_data['group_name'], new_data['is_enabled']
    ))
    
    # 返回新用例
    new_case = db.fetch_one("SELECT * FROM test_cases WHERE case_id = %s", (new_case_id,))
    
    return {
        "success": True,
        "message": "测试用例复制成功",
        "test_case": dict(new_case)
    }


@router.delete("/tests/{test_case_id}")
async def delete_test_case(test_case_id: str):
    """删除测试用例"""
    db = get_db_manager()
    
    # 检查用例是否存在
    existing = db.fetch_one("SELECT * FROM test_cases WHERE case_id = %s", (test_case_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    # 删除相关的执行记录
    db.execute("DELETE FROM test_results WHERE case_id = %s", (test_case_id,))
    
    # 删除用例
    db.execute("DELETE FROM test_cases WHERE case_id = %s", (test_case_id,))
    
    return {
        "success": True,
        "message": "测试用例删除成功"
    }


# ==================== 测试执行 ====================

@router.post("/tests/execute")
async def execute_tests(request: ExecuteTestsRequest):
    """
    执行测试用例
    
    支持：
    - 执行指定用例
    - 执行某接口的所有用例
    - 按标签执行
    """
    from ...testing import TestExecutor, TestCase
    from ...testing.test_case_generator import TestCaseCategory, TestCasePriority, ExpectedResult
    from ...config import TestConfig
    import uuid
    
    db = get_db_manager()
    
    # 构建查询条件
    conditions = ["is_enabled = 1"]
    params: list[Any] = []
    
    if request.test_case_ids:
        placeholders = ','.join(['%s'] * len(request.test_case_ids))
        conditions.append(f"case_id IN ({placeholders})")
        params.extend(request.test_case_ids)
    
    if request.endpoint_id:
        # test_cases 表没有 endpoint_id 列，通过 task_id 匹配
        conditions.append("task_id = %s")
        params.append(request.endpoint_id)
    
    if request.tag_filter:
        # 通过 task_id (endpoint_id) 关联查询
        conditions.append("""
            EXISTS (
                SELECT 1 FROM api_endpoints e
                JOIN api_endpoint_tags et ON e.endpoint_id = et.endpoint_id
                JOIN api_tags t ON et.tag_id = t.id
                WHERE t.name = %s AND test_cases.task_id = e.endpoint_id
            )
        """)
        params.append(request.tag_filter)
    
    where_clause = f"WHERE {' AND '.join(conditions)}"
    
    # 获取要执行的测试用例
    sql = f"SELECT * FROM test_cases {where_clause}"
    cases = db.fetch_all(sql, tuple(params) if params else None)
    
    if not cases:
        raise HTTPException(status_code=400, detail="没有找到可执行的测试用例")
    
    # 创建执行记录
    execution_id = str(uuid.uuid4())[:8]
    
    try:
        # 转换数据库记录为 TestCase 对象
        test_cases: list[TestCase] = []
        for c in cases:
            case_dict = dict(c)
            
            # 解析 JSON 字段
            headers = case_dict.get('headers') or {}
            if isinstance(headers, str):
                headers = json.loads(headers) if headers else {}
            
            body = case_dict.get('body')
            if isinstance(body, str):
                body = json.loads(body) if body else None
            
            query_params = case_dict.get('query_params') or {}
            if isinstance(query_params, str):
                query_params = json.loads(query_params) if query_params else {}
            
            # 转换枚举
            category_str = case_dict.get('category', 'normal')
            priority_str = case_dict.get('priority', 'medium')
            
            try:
                category = TestCaseCategory(category_str)
            except ValueError:
                category = TestCaseCategory.NORMAL
            
            try:
                priority = TestCasePriority(priority_str)
            except ValueError:
                priority = TestCasePriority.MEDIUM
            
            # 创建 ExpectedResult
            expected = ExpectedResult(
                status_code=case_dict.get('expected_status_code', 200),
                max_response_time_ms=case_dict.get('max_response_time_ms', 3000)
            )
            
            test_case = TestCase(
                id=case_dict['case_id'],
                name=case_dict['name'],
                description=case_dict.get('description', ''),
                category=category,
                priority=priority,
                method=case_dict['method'],
                url=case_dict['url'],
                headers=headers,
                body=body,
                query_params=query_params,
                expected=expected
            )
            test_cases.append(test_case)
        
        # 配置执行器
        config = TestConfig(base_url=request.base_url)
        executor = TestExecutor(config=config)
        
        # 执行测试
        results = await executor.execute_test_suite(test_cases)
        
        # 统计结果
        passed = sum(1 for r in results if r.status.value == 'passed')
        failed = sum(1 for r in results if r.status.value == 'failed')
        error = sum(1 for r in results if r.status.value == 'error')
        skipped = sum(1 for r in results if r.status.value == 'skipped')
        total_duration = sum(r.actual_response_time_ms for r in results)
        
        # 转换结果为字典
        result_dicts = [r.to_dict() for r in results]
        
        return {
            "success": True,
            "execution_id": execution_id,
            "environment": request.environment,
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "error": error,
            "skipped": skipped,
            "pass_rate": round(passed / len(results) * 100, 2) if results else 0,
            "duration_ms": total_duration,
            "results": result_dicts
        }
    
    except Exception as e:
        logger.error(f"执行测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions")
async def list_executions(
    endpoint_id: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取执行记录列表"""
    db = get_db_manager()
    
    conditions = []
    params: list[Any] = []
    
    if status:
        conditions.append("status = %s")
        params.append(status)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM scenario_executions {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM scenario_executions
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


# ==================== 环境配置 ====================

@router.get("/environments")
async def list_environments():
    """获取环境配置列表"""
    # 暂时返回默认配置，后续可扩展为数据库存储
    return {
        "environments": [
            {"name": "local", "label": "本地环境", "base_url": "http://localhost:8080"},
            {"name": "test", "label": "测试环境", "base_url": ""},
            {"name": "staging", "label": "预发环境", "base_url": ""},
            {"name": "production", "label": "生产环境", "base_url": ""}
        ]
    }


# ==================== 统计概览 ====================

@router.get("/statistics")
async def get_development_statistics():
    """获取开发自测统计数据"""
    db = get_db_manager()
    
    # 接口统计
    endpoint_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT method) as methods_count
        FROM api_endpoints
    """)
    
    # 测试用例统计
    case_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled,
            0 as ai_generated
        FROM test_cases
    """)
    
    # 覆盖率统计：统计有测试用例覆盖的接口数量
    total_endpoints_result = db.fetch_one("SELECT COUNT(*) as cnt FROM api_endpoints")
    # 统计有测试用例的接口数量（通过检查是否存在匹配的 case_id）
    covered_result = db.fetch_one("""
        SELECT COUNT(*) as cnt FROM api_endpoints e
        WHERE EXISTS (SELECT 1 FROM test_cases tc WHERE tc.case_id LIKE CONCAT(e.endpoint_id, '%'))
    """)
    coverage_stats = {
        'total_endpoints': total_endpoints_result['cnt'] if total_endpoints_result else 0,
        'covered_endpoints': covered_result['cnt'] if covered_result else 0
    }
    
    # 近7天执行统计
    recent_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total_executions,
            SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM test_results
        WHERE executed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)
    
    total_endpoints = coverage_stats['total_endpoints'] if coverage_stats else 0
    covered_endpoints = coverage_stats['covered_endpoints'] if coverage_stats else 0
    
    return {
        "endpoints": {
            "total": endpoint_stats['total'] if endpoint_stats else 0,
            "methods_count": endpoint_stats['methods_count'] if endpoint_stats else 0
        },
        "test_cases": {
            "total": case_stats['total'] if case_stats else 0,
            "enabled": case_stats['enabled'] if case_stats else 0,
            "ai_generated": case_stats['ai_generated'] if case_stats else 0
        },
        "coverage": {
            "total_endpoints": total_endpoints,
            "covered_endpoints": covered_endpoints,
            "coverage_rate": round(covered_endpoints / total_endpoints * 100, 2) if total_endpoints > 0 else 0
        },
        "recent_executions": {
            "total": recent_stats['total_executions'] if recent_stats else 0,
            "passed": recent_stats['passed'] if recent_stats else 0,
            "failed": recent_stats['failed'] if recent_stats else 0,
            "pass_rate": round(
                (recent_stats['passed'] or 0) / (recent_stats['total_executions'] or 1) * 100, 2
            ) if recent_stats and recent_stats['total_executions'] else 0
        }
    }
