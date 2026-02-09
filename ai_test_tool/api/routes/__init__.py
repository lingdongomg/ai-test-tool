# 该文件内容使用AI生成，注意识别准确性
"""
API 路由模块

提供通用的路由工具函数，减少重复代码
"""

import json
from typing import Any, Callable, TypeVar
from functools import wraps

from ...database import DatabaseManager
from ...utils.logger import get_logger
from ...utils.sql_security import (
    validate_table_name,
    validate_field_name,
    validate_order_by_multi,
    validate_fields_for_update,
    escape_like_pattern,
    build_safe_like,
    get_allowed_sort_fields,
)

logger = get_logger()
T = TypeVar('T')


def paginate(
    db: DatabaseManager,
    table: str,
    conditions: list[str] | None = None,
    params: list[Any] | None = None,
    page: int = 1,
    page_size: int = 20,
    order_by: str = "created_at DESC",
    select_fields: str = "*",
    joins: str = ""
) -> dict[str, Any]:
    """
    通用分页查询

    Args:
        db: 数据库管理器（通过依赖注入获取）
        table: 表名
        conditions: WHERE条件列表（不含WHERE关键字）
        params: 查询参数
        page: 页码
        page_size: 每页数量
        order_by: 排序字段
        select_fields: 查询字段
        joins: JOIN子句

    Returns:
        包含 total, page, page_size, items 的字典
    """
    conditions = conditions or []
    params = params or []

    # SQL 安全验证
    validate_table_name(table)
    allowed_sort = get_allowed_sort_fields(table)
    order_by = validate_order_by_multi(order_by, allowed_sort)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM {table} {joins} {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0

    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT {select_fields} FROM {table} {joins}
        {where_clause}
        ORDER BY {order_by}
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


def parse_json_fields(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """解析字典中的JSON字符串字段"""
    result = dict(data)
    for field in fields:
        if result.get(field) and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except json.JSONDecodeError:
                pass
    return result


def update_task_status(
    db: DatabaseManager,
    table: str,
    id_field: str,
    task_id: str,
    status: str,
    extra_fields: dict[str, Any] | None = None
) -> None:
    """更新任务状态"""

    # SQL 安全验证
    validate_table_name(table)
    validate_field_name(id_field, table, allow_qualified=False)

    fields = ["status = %s"]
    params: list[Any] = [status]

    if status == "running":
        fields.append("started_at = datetime('now')")
    elif status in ("completed", "failed"):
        fields.append("completed_at = datetime('now')")

    if extra_fields:
        # 验证额外字段
        validated_fields = validate_fields_for_update(extra_fields.keys(), table)
        for key in validated_fields:
            fields.append(f"{key} = %s")
            params.append(extra_fields[key])

    params.append(task_id)
    sql = f"UPDATE {table} SET {', '.join(fields)} WHERE {id_field} = %s"
    db.execute(sql, tuple(params))


def build_conditions(
    filters: dict[str, Any],
    field_mapping: dict[str, str] | None = None
) -> tuple[list[str], list[Any]]:
    """
    根据过滤条件构建WHERE子句

    Args:
        filters: 过滤条件字典 {field: value}
        field_mapping: 字段映射 {param_name: sql_field}

    Returns:
        (conditions, params) 元组
    """
    conditions: list[str] = []
    params: list[Any] = []
    field_mapping = field_mapping or {}

    for key, value in filters.items():
        if value is None:
            continue

        field = field_mapping.get(key, key)

        if key.endswith("_search"):
            # 模糊搜索 - 使用安全的 LIKE 参数构建
            base_field = field_mapping.get(key, key.replace("_search", ""))
            conditions.append(f"({base_field} LIKE %s ESCAPE '\\\\')")
            params.append(build_safe_like(str(value)))
        elif isinstance(value, bool):
            conditions.append(f"{field} = %s")
            params.append(1 if value else 0)
        else:
            conditions.append(f"{field} = %s")
            params.append(value)

    return conditions, params


# 核心路由
from . import dashboard
from . import development
from . import monitoring
from . import insights
from . import ai_assistant
from . import imports
from . import tasks
from . import knowledge

# 任务取消检查函数
from .tasks import is_task_cancelled

__all__ = [
    "dashboard",
    "development",
    "monitoring",
    "insights",
    "ai_assistant",
    "imports",
    "tasks",
    "knowledge",
    "is_task_cancelled",
    # 工具函数
    "paginate",
    "parse_json_fields",
    "update_task_status",
    "build_conditions"
]
