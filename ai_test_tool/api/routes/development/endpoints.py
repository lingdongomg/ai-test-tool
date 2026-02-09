"""
开发自测模块 - 接口管理路由
该文件内容使用AI生成，注意识别准确性
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Depends

from ....database import DatabaseManager
from ....utils.logger import get_logger
from ....utils.sql_security import build_safe_like
from ...dependencies import get_database

router = APIRouter()
logger = get_logger()


def _calculate_pass_rate(executions) -> float:
    """计算通过率"""
    if not executions:
        return 0.0
    passed = sum(1 for e in executions if e.get('status') == 'passed')
    return round(passed / len(executions) * 100, 2)


@router.get("/endpoints")
async def list_endpoints(
    search: str | None = None,
    method: str | None = None,
    tag_id: str | None = None,
    has_tests: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取接口列表

    - search: 搜索关键词（路径、描述）
    - method: HTTP方法筛选
    - tag_id: 标签筛选
    - has_tests: 是否有测试用例
    """
    conditions = []
    params: list[Any] = []

    if search:
        safe_search = build_safe_like(search)
        conditions.append("(e.path LIKE %s ESCAPE '\\\\' OR e.description LIKE %s ESCAPE '\\\\')")
        params.extend([safe_search, safe_search])

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
            COALESCE((SELECT COUNT(*) FROM test_cases WHERE case_id LIKE (e.endpoint_id || '%')), 0) as test_case_count,
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
async def get_endpoint_detail(endpoint_id: str, db: DatabaseManager = Depends(get_database)):
    """获取接口详情（包含测试用例）"""
    # 获取接口信息
    endpoint_sql = "SELECT * FROM api_endpoints WHERE endpoint_id = %s"
    endpoint = db.fetch_one(endpoint_sql, (endpoint_id,))

    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")

    # 获取关联的测试用例（通过 case_id 前缀匹配 endpoint_id）
    # 注：这里的 endpoint_id 来自数据库验证后的记录，是安全的
    cases_sql = """
        SELECT * FROM test_cases
        WHERE case_id LIKE %s ESCAPE '\\\\'
        ORDER BY priority, created_at DESC
    """
    cases = db.fetch_all(cases_sql, (build_safe_like(endpoint_id, "end"),))

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
