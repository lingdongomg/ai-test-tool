"""
开发自测模块 - 测试执行和统计路由
该文件内容使用AI生成，注意识别准确性
"""

import json
import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Depends

from ....database import DatabaseManager
from ....utils.logger import get_logger
from ...dependencies import get_database
from .schemas import ExecuteTestsRequest

router = APIRouter()
logger = get_logger()


@router.post("/tests/execute")
async def execute_tests(
    request: ExecuteTestsRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    执行测试用例

    支持：
    - 执行指定用例
    - 执行某接口的所有用例
    - 按标签执行
    """
    from ....testing import TestExecutor, TestCase
    from ....testing.test_case_generator import ExpectedResult
    from ....database.models.base import TestCaseCategory, TestCasePriority
    from ....config import TestConfig

    # 构建查询条件
    conditions = ["is_enabled = 1"]
    params: list[Any] = []

    if request.test_case_ids:
        placeholders = ','.join(['%s'] * len(request.test_case_ids))
        conditions.append(f"case_id IN ({placeholders})")
        params.extend(request.test_case_ids)

    if request.endpoint_id:
        conditions.append("endpoint_id = %s")
        params.append(request.endpoint_id)

    if request.tag_filter:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM api_endpoints e
                JOIN api_endpoint_tags et ON e.endpoint_id = et.endpoint_id
                JOIN api_tags t ON et.tag_id = t.id
                WHERE t.name = %s AND test_cases.endpoint_id = e.endpoint_id
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
    started_at = datetime.now().isoformat()

    # 写入 test_executions 表（状态: running）
    db.execute("""
        INSERT INTO test_executions
        (execution_id, name, execution_type, trigger_type, status,
         base_url, environment, total_cases, started_at)
        VALUES (%s, %s, 'test', 'manual', 'running', %s, %s, %s, %s)
    """, (
        execution_id,
        f"手动执行 ({len(cases)} 个用例)",
        request.base_url,
        request.environment,
        len(cases),
        started_at
    ))

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
        completed_at = datetime.now().isoformat()

        # 持久化每条用例的执行结果到 test_results 表
        for r in results:
            db.execute("""
                INSERT INTO test_results
                (case_id, execution_id, result_type, status,
                 actual_status_code, actual_response_time_ms,
                 actual_response_body, actual_headers,
                 error_message, assertion_results, executed_at)
                VALUES (%s, %s, 'test', %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                r.test_case_id,
                execution_id,
                r.status.value,
                r.actual_status_code,
                r.actual_response_time_ms,
                (r.actual_response_body or '')[:5000],
                json.dumps(r.actual_headers, ensure_ascii=False) if r.actual_headers else None,
                r.error_message or None,
                json.dumps(r.validation_results, ensure_ascii=False) if r.validation_results else None,
                completed_at
            ))

        # 更新 test_executions 表状态为 completed
        db.execute("""
            UPDATE test_executions SET
                status = 'completed',
                passed_cases = %s,
                failed_cases = %s,
                error_cases = %s,
                skipped_cases = %s,
                duration_ms = %s,
                completed_at = %s
            WHERE execution_id = %s
        """, (passed, failed, error, skipped, int(total_duration), completed_at, execution_id))

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
        # 更新执行记录为失败
        db.execute("""
            UPDATE test_executions SET status = 'failed', error_message = %s,
            completed_at = %s WHERE execution_id = %s
        """, (str(e), datetime.now().isoformat(), execution_id))
        logger.error(f"执行测试失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions")
async def list_executions(
    endpoint_id: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DatabaseManager = Depends(get_database)
):
    """获取执行记录列表"""
    conditions = []
    params: list[Any] = []

    if status:
        conditions.append("e.status = %s")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM test_executions e {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0

    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT
            e.*,
            CASE WHEN e.total_cases > 0
                THEN ROUND(e.passed_cases * 100.0 / e.total_cases, 2)
                ELSE 0
            END as pass_rate
        FROM test_executions e
        {where_clause}
        ORDER BY e.created_at DESC
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


@router.get("/executions/{execution_id}")
async def get_execution_detail(
    execution_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """获取执行记录详情，包含每条用例的执行结果"""
    # 获取执行批次信息
    execution = db.fetch_one(
        "SELECT * FROM test_executions WHERE execution_id = %s",
        (execution_id,)
    )
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # 获取该批次下所有用例的执行结果
    results = db.fetch_all("""
        SELECT tr.*, tc.name as case_name, tc.method, tc.url, tc.category
        FROM test_results tr
        LEFT JOIN test_cases tc ON tr.case_id = tc.case_id
        WHERE tr.execution_id = %s
        ORDER BY tr.id
    """, (execution_id,))

    result_items = []
    for r in results:
        item = dict(r)
        # 解析 assertion_results JSON
        if item.get('assertion_results') and isinstance(item['assertion_results'], str):
            try:
                item['assertion_results'] = json.loads(item['assertion_results'])
            except (json.JSONDecodeError, ValueError):
                pass
        result_items.append(item)

    exec_dict = dict(execution)
    exec_dict['pass_rate'] = round(
        exec_dict.get('passed_cases', 0) / exec_dict.get('total_cases', 1) * 100, 2
    ) if exec_dict.get('total_cases') else 0

    return {
        "execution": exec_dict,
        "results": result_items
    }


# ==================== 环境配置 ====================

@router.get("/environments")
async def list_environments():
    """获取环境配置列表"""
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
async def get_development_statistics(db: DatabaseManager = Depends(get_database)):
    """获取开发自测统计数据"""
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
            SUM(CASE WHEN is_ai_generated = 1 THEN 1 ELSE 0 END) as ai_generated
        FROM test_cases
    """)

    # 覆盖率统计
    total_endpoints_result = db.fetch_one("SELECT COUNT(*) as cnt FROM api_endpoints")
    covered_result = db.fetch_one("""
        SELECT COUNT(*) as cnt FROM api_endpoints e
        WHERE EXISTS (SELECT 1 FROM test_cases tc WHERE tc.endpoint_id = e.endpoint_id)
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
        WHERE executed_at >= datetime('now', '-7 days')
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
