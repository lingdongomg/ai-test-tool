"""
开发自测模块 - 测试用例管理路由
该文件内容使用AI生成，注意识别准确性
"""

import json
import uuid
import hashlib
import time
from typing import Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends

from ....services import EndpointTestGeneratorService
from ....database import DatabaseManager
from ....database.repository import TaskRepository
from ....database.models.base import TaskStatus
from ....utils.logger import get_logger
from ....utils.sql_security import build_safe_like
from ...dependencies import get_database, get_task_repository
from .schemas import GenerateTestsRequest, UpdateTestCaseRequest

router = APIRouter()
logger = get_logger()


def _run_generate_task(task_id: str, request_data: dict):
    """后台执行测试用例生成任务"""
    task_repo = TaskRepository()

    try:
        # 更新任务状态为运行中
        task_repo.update_status(task_id, TaskStatus.RUNNING)

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
            task_repo.update_counts(
                task_id,
                total_requests=1,
                total_test_cases=len(test_cases)
            )
            task_repo.update_status(task_id, TaskStatus.COMPLETED)
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
            metadata = {
                'total_endpoints': result['total_endpoints'],
                'success_count': result['success_count'],
                'failed_count': result['failed_count'],
                'errors': result.get('errors', [])
            }
            task_repo.update_counts(
                task_id,
                total_requests=result['total_endpoints'],
                total_test_cases=result['total_cases_generated']
            )
            # Update metadata via direct db call since no dedicated method
            task_repo.db.execute(
                "UPDATE analysis_tasks SET metadata = %s WHERE task_id = %s",
                (json.dumps(metadata, ensure_ascii=False), task_id)
            )
            task_repo.update_status(task_id, TaskStatus.COMPLETED)

    except Exception as e:
        logger.error(f"生成任务失败: {e}")
        task_repo.update_status(task_id, TaskStatus.FAILED, error_message=str(e))


@router.post("/tests/generate")
async def generate_tests(
    request: GenerateTestsRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_database)
):
    """
    为接口生成测试用例（异步任务）

    支持：
    - 为指定接口生成
    - 按标签批量生成
    - 为所有接口生成

    返回任务ID，可通过 GET /tests/generate/{task_id} 查询进度
    """
    task_id = str(uuid.uuid4())[:16]
    task_type = 'single' if request.endpoint_ids and len(request.endpoint_ids) == 1 else 'batch'

    # 使用 analysis_tasks 表，task_type='test_generation'
    metadata = {
        'generation_type': task_type,
        'endpoint_ids': request.endpoint_ids,
        'tag_filter': request.tag_filter,
        'test_types': request.test_types,
        'use_ai': request.use_ai,
        'skip_existing': request.skip_existing
    }
    db.execute("""
        INSERT INTO analysis_tasks
        (task_id, name, description, task_type, status, metadata)
        VALUES (%s, %s, %s, 'test_generation', 'pending', %s)
    """, (
        task_id,
        f"测试用例生成任务 ({task_type})",
        f"为接口生成测试用例",
        json.dumps(metadata, ensure_ascii=False)
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
async def get_generate_task_status(
    task_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """查询测试用例生成任务状态"""
    task = db.fetch_one("""
        SELECT * FROM analysis_tasks WHERE task_id = %s AND task_type = 'test_generation'
    """, (task_id,))

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = dict(task)
    # 解析 metadata JSON 字段
    if result.get('metadata') and isinstance(result['metadata'], str):
        try:
            result['metadata'] = json.loads(result['metadata'])
        except (json.JSONDecodeError, ValueError):
            pass

    return result


@router.get("/tests/generate-tasks")
async def list_generate_tasks(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DatabaseManager = Depends(get_database)
):
    """获取测试用例生成任务列表"""
    conditions = ["task_type = 'test_generation'"]
    params: list[Any] = []

    if status:
        conditions.append("status = %s")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}"

    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM analysis_tasks {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0

    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM analysis_tasks
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(sql, tuple(params))

    items = []
    for row in rows:
        item = dict(row)
        if item.get('metadata') and isinstance(item['metadata'], str):
            try:
                item['metadata'] = json.loads(item['metadata'])
            except (json.JSONDecodeError, ValueError):
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
    use_ai: bool = Query(default=True),
    db: DatabaseManager = Depends(get_database)
):
    """为单个接口生成测试用例（异步任务，快捷接口）"""
    task_id = str(uuid.uuid4())[:16]

    # 使用 analysis_tasks 表
    metadata = {
        'generation_type': 'single',
        'endpoint_ids': [endpoint_id],
        'test_types': test_types,
        'use_ai': use_ai,
        'skip_existing': False
    }
    db.execute("""
        INSERT INTO analysis_tasks
        (task_id, name, description, task_type, status, metadata)
        VALUES (%s, %s, %s, 'test_generation', 'pending', %s)
    """, (
        task_id,
        f"测试用例生成 - {endpoint_id}",
        f"为接口 {endpoint_id} 生成测试用例",
        json.dumps(metadata, ensure_ascii=False)
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
    page_size: int = Query(default=20, ge=1, le=100),
    db: DatabaseManager = Depends(get_database)
):
    """获取测试用例列表"""
    conditions = []
    params: list[Any] = []

    if endpoint_id:
        # test_cases 表没有 endpoint_id 列，通过 case_id 前缀匹配
        conditions.append("tc.case_id LIKE %s ESCAPE '\\\\'")
        params.append(build_safe_like(endpoint_id, "end"))

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
        safe_search = build_safe_like(search)
        conditions.append("(tc.name LIKE %s ESCAPE '\\\\' OR tc.description LIKE %s ESCAPE '\\\\')")
        params.extend([safe_search, safe_search])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM test_cases tc {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0

    # 获取分页数据，关联 api_endpoints 表获取接口信息
    offset = (page - 1) * page_size
    sql = f"""
        SELECT
            tc.*,
            e.method as endpoint_method,
            e.path as endpoint_path
        FROM test_cases tc
        LEFT JOIN api_endpoints e ON tc.endpoint_id = e.endpoint_id
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
async def get_test_case(test_case_id: str, db: DatabaseManager = Depends(get_database)):
    """获取测试用例详情"""
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
async def update_test_case(
    test_case_id: str,
    request: UpdateTestCaseRequest,
    db: DatabaseManager = Depends(get_database)
):
    """更新测试用例"""
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
async def copy_test_case(
    test_case_id: str,
    request: UpdateTestCaseRequest | None = None,
    db: DatabaseManager = Depends(get_database)
):
    """复制测试用例"""
    # 获取原始用例
    original = db.fetch_one("SELECT * FROM test_cases WHERE case_id = %s", (test_case_id,))
    if not original:
        raise HTTPException(status_code=404, detail="原始测试用例不存在")

    original = dict(original)

    # 生成新的 case_id
    endpoint_id = original['endpoint_id']
    timestamp = str(int(time.time() * 1000))
    hash_str = hashlib.md5(timestamp.encode()).hexdigest()[:8]
    new_case_id = f"{endpoint_id}_{hash_str}"

    # 准备新用例数据，优先使用请求中的数据
    new_data = {
        'case_id': new_case_id,
        'endpoint_id': endpoint_id,
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
        'is_enabled': 1
    }

    # 插入新用例
    sql = """
        INSERT INTO test_cases (
            case_id, endpoint_id, name, description, category, priority,
            method, url, headers, body, query_params,
            expected_status_code, max_response_time_ms, expected_response,
            tags, is_enabled
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s
        )
    """
    db.execute(sql, (
        new_data['case_id'], new_data['endpoint_id'], new_data['name'],
        new_data['description'], new_data['category'], new_data['priority'],
        new_data['method'], new_data['url'], new_data['headers'],
        new_data['body'], new_data['query_params'],
        new_data['expected_status_code'], new_data['max_response_time_ms'],
        new_data['expected_response'],
        new_data['tags'], new_data['is_enabled']
    ))

    # 返回新用例
    new_case = db.fetch_one("SELECT * FROM test_cases WHERE case_id = %s", (new_case_id,))

    return {
        "success": True,
        "message": "测试用例复制成功",
        "test_case": dict(new_case)
    }


@router.delete("/tests/{test_case_id}")
async def delete_test_case(
    test_case_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """删除测试用例"""
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
