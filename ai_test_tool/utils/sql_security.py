"""
SQL 安全工具模块

提供 SQL 注入防护功能：
- 表名白名单验证
- 字段名白名单验证
- ORDER BY 子句安全构建
- LIKE 查询参数转义
"""

import re
from typing import Literal

from ..exceptions import ValidationError


# =====================================================
# 白名单定义
# =====================================================

# 允许的表名（从 schema.sql 中提取）
ALLOWED_TABLES: frozenset[str] = frozenset({
    "analysis_tasks",
    "parsed_requests",
    "api_tags",
    "api_endpoints",
    "api_endpoint_tags",
    "test_cases",
    "test_case_history",
    "test_executions",
    "execution_cases",
    "test_results",
    "analysis_reports",
    "test_scenarios",
    "scenario_steps",
    "scenario_executions",
    "step_results",
    "knowledge_entries",
    "knowledge_tags",
    "knowledge_history",
    "knowledge_usage",
    "ai_insights",
    "production_requests",
    "health_check_executions",
    "health_check_results",
})

# 每个表允许的字段（用于 UPDATE/INSERT 操作的字段白名单）
TABLE_FIELDS: dict[str, frozenset[str]] = {
    "analysis_tasks": frozenset({
        "id", "task_id", "name", "description", "task_type", "log_file_path",
        "log_file_size", "status", "total_lines", "processed_lines",
        "total_requests", "total_test_cases", "error_message", "metadata",
        "started_at", "completed_at", "created_at", "updated_at"
    }),
    "parsed_requests": frozenset({
        "id", "task_id", "request_id", "method", "url", "category", "headers",
        "body", "query_params", "http_status", "response_time_ms",
        "response_body", "has_error", "error_message", "has_warning",
        "warning_message", "curl_command", "timestamp", "raw_logs",
        "metadata", "created_at"
    }),
    "api_tags": frozenset({
        "id", "name", "description", "color", "parent_id", "sort_order",
        "is_system", "created_at", "updated_at"
    }),
    "api_endpoints": frozenset({
        "id", "endpoint_id", "name", "description", "method", "path",
        "summary", "parameters", "request_body", "responses", "security",
        "source_type", "source_file", "is_deprecated", "created_at", "updated_at"
    }),
    "api_endpoint_tags": frozenset({
        "endpoint_id", "tag_id", "created_at"
    }),
    "test_cases": frozenset({
        "id", "case_id", "endpoint_id", "name", "description", "category",
        "priority", "method", "url", "headers", "body", "query_params",
        "expected_status_code", "expected_response", "assertions",
        "max_response_time_ms", "tags", "is_enabled", "is_ai_generated",
        "source_task_id", "version", "created_at", "updated_at"
    }),
    "test_case_history": frozenset({
        "id", "case_id", "version", "change_type", "change_summary",
        "snapshot", "changed_fields", "changed_by", "created_at"
    }),
    "test_executions": frozenset({
        "id", "execution_id", "name", "description", "execution_type",
        "trigger_type", "status", "base_url", "environment", "variables",
        "headers", "total_cases", "passed_cases", "failed_cases",
        "error_cases", "skipped_cases", "duration_ms", "error_message",
        "started_at", "completed_at", "created_at"
    }),
    "execution_cases": frozenset({
        "execution_id", "case_id", "order_index", "created_at"
    }),
    "test_results": frozenset({
        "id", "case_id", "execution_id", "result_type", "status",
        "actual_status_code", "actual_response_time_ms", "actual_response_body",
        "actual_headers", "error_message", "assertion_results", "ai_analysis",
        "executed_at", "created_at"
    }),
    "analysis_reports": frozenset({
        "id", "task_id", "report_type", "title", "content", "format",
        "statistics", "issues", "recommendations", "severity", "metadata",
        "created_at"
    }),
    "test_scenarios": frozenset({
        "id", "scenario_id", "name", "description", "tags", "variables",
        "setup_hooks", "teardown_hooks", "retry_on_failure", "max_retries",
        "is_enabled", "created_by", "created_at", "updated_at"
    }),
    "scenario_steps": frozenset({
        "id", "scenario_id", "step_id", "step_order", "name", "description",
        "step_type", "method", "url", "headers", "body", "query_params",
        "extractions", "assertions", "wait_time_ms", "condition",
        "loop_config", "timeout_ms", "continue_on_failure", "is_enabled",
        "created_at", "updated_at"
    }),
    "scenario_executions": frozenset({
        "id", "execution_id", "scenario_id", "trigger_type", "status",
        "base_url", "environment", "variables", "total_steps", "passed_steps",
        "failed_steps", "skipped_steps", "duration_ms", "error_message",
        "started_at", "completed_at", "created_at"
    }),
    "step_results": frozenset({
        "id", "execution_id", "step_id", "step_order", "status",
        "request_url", "request_headers", "request_body",
        "response_status_code", "response_headers", "response_body",
        "response_time_ms", "extracted_variables", "assertion_results",
        "error_message", "executed_at"
    }),
    "knowledge_entries": frozenset({
        "id", "knowledge_id", "type", "category", "title", "content",
        "scope", "priority", "status", "source", "source_ref", "metadata",
        "created_at", "updated_at", "created_by", "version"
    }),
    "knowledge_tags": frozenset({
        "knowledge_id", "tag", "created_at"
    }),
    "knowledge_history": frozenset({
        "id", "knowledge_id", "version", "content", "title", "changed_by",
        "changed_at", "change_type"
    }),
    "knowledge_usage": frozenset({
        "id", "usage_id", "knowledge_id", "used_in", "context", "helpful",
        "used_at"
    }),
    # 监控相关表
    "ai_insights": frozenset({
        "id", "insight_id", "insight_type", "title", "description", "severity",
        "confidence", "details", "recommendations", "is_resolved", "resolved_at",
        "created_at"
    }),
    "production_requests": frozenset({
        "id", "request_id", "method", "url", "headers", "body", "query_params",
        "expected_status_code", "expected_response_pattern", "source",
        "source_task_id", "tags", "is_enabled", "last_check_at",
        "last_check_status", "consecutive_failures", "created_at", "updated_at"
    }),
    "health_check_executions": frozenset({
        "id", "execution_id", "base_url", "total_requests", "healthy_count",
        "unhealthy_count", "status", "trigger_type", "started_at",
        "completed_at", "created_at"
    }),
    "health_check_results": frozenset({
        "id", "execution_id", "request_id", "success", "status_code",
        "response_time_ms", "response_body", "error_message", "ai_analysis",
        "checked_at"
    }),
}

# 排序方向
SORT_DIRECTIONS: frozenset[str] = frozenset({"ASC", "DESC", "asc", "desc"})

# 标识符合法字符模式（只允许字母、数字、下划线，且不以数字开头）
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


# =====================================================
# 验证函数
# =====================================================

def validate_table_name(table: str) -> str:
    """
    验证表名是否在白名单中

    Args:
        table: 表名

    Returns:
        验证通过的表名

    Raises:
        ValidationError: 表名不在白名单中
    """
    # 处理带别名的表名，如 "test_cases tc"
    base_table = table.split()[0].strip()

    if base_table not in ALLOWED_TABLES:
        raise ValidationError(f"无效的表名: {base_table}", field="table")
    return table


def validate_field_name(
    field: str,
    table: str | None = None,
    allow_qualified: bool = True
) -> str:
    """
    验证字段名是否合法

    Args:
        field: 字段名（可能包含表别名，如 "t.name"）
        table: 表名（用于字段白名单验证）
        allow_qualified: 是否允许带表别名的字段名

    Returns:
        验证通过的字段名

    Raises:
        ValidationError: 字段名不合法
    """
    # 处理带表别名的字段名
    if "." in field and allow_qualified:
        parts = field.split(".", 1)
        if len(parts) == 2:
            alias, col = parts
            if not IDENTIFIER_PATTERN.match(alias):
                raise ValidationError(f"无效的表别名: {alias}", field="field")
            field_to_check = col
        else:
            field_to_check = field
    else:
        field_to_check = field

    # 检查标识符格式
    if not IDENTIFIER_PATTERN.match(field_to_check):
        raise ValidationError(f"无效的字段名格式: {field_to_check}", field="field")

    # 如果提供了表名，检查字段是否在该表的白名单中
    if table:
        base_table = table.split()[0].strip()
        allowed_fields = TABLE_FIELDS.get(base_table, frozenset())
        if allowed_fields and field_to_check not in allowed_fields:
            raise ValidationError(
                f"字段 {field_to_check} 不属于表 {base_table}",
                field="field"
            )

    return field


def validate_fields_for_update(
    fields: list[str] | set[str] | frozenset[str],
    table: str
) -> list[str]:
    """
    验证用于 UPDATE 操作的字段列表

    Args:
        fields: 字段名列表
        table: 表名

    Returns:
        验证通过的字段列表

    Raises:
        ValidationError: 包含无效字段
    """
    base_table = table.split()[0].strip()
    allowed_fields = TABLE_FIELDS.get(base_table)

    if not allowed_fields:
        raise ValidationError(f"未知的表: {base_table}", field="table")

    validated = []
    for field in fields:
        if not IDENTIFIER_PATTERN.match(field):
            raise ValidationError(f"无效的字段名格式: {field}", field="field")
        if field not in allowed_fields:
            raise ValidationError(
                f"字段 {field} 不允许在表 {base_table} 中更新",
                field="field"
            )
        validated.append(field)

    return validated


def validate_order_by(
    order_by: str,
    allowed_fields: set[str] | frozenset[str] | None = None
) -> str:
    """
    验证 ORDER BY 子句

    Args:
        order_by: ORDER BY 表达式（如 "created_at DESC" 或 "id"）
        allowed_fields: 允许排序的字段集合（可选）

    Returns:
        验证通过的 ORDER BY 表达式

    Raises:
        ValidationError: ORDER BY 表达式不合法
    """
    # 解析 ORDER BY 表达式
    parts = order_by.strip().split()

    if not parts:
        raise ValidationError("ORDER BY 不能为空", field="order_by")

    field = parts[0]
    direction = parts[1].upper() if len(parts) > 1 else "ASC"

    # 验证字段名
    if not IDENTIFIER_PATTERN.match(field.split(".")[-1]):  # 处理带别名的情况
        raise ValidationError(f"无效的排序字段: {field}", field="order_by")

    # 如果提供了白名单，检查字段
    if allowed_fields:
        base_field = field.split(".")[-1]
        if base_field not in allowed_fields:
            raise ValidationError(
                f"不允许按字段 {base_field} 排序",
                field="order_by"
            )

    # 验证排序方向
    if direction not in {"ASC", "DESC"}:
        raise ValidationError(f"无效的排序方向: {direction}", field="order_by")

    return f"{field} {direction}"


def validate_order_by_multi(
    order_by: str,
    allowed_fields: set[str] | frozenset[str] | None = None
) -> str:
    """
    验证多字段 ORDER BY 子句

    Args:
        order_by: 多字段 ORDER BY 表达式（如 "created_at DESC, id ASC"）
        allowed_fields: 允许排序的字段集合（可选）

    Returns:
        验证通过的 ORDER BY 表达式

    Raises:
        ValidationError: ORDER BY 表达式不合法
    """
    if not order_by.strip():
        raise ValidationError("ORDER BY 不能为空", field="order_by")

    validated_parts = []
    for part in order_by.split(","):
        validated_part = validate_order_by(part.strip(), allowed_fields)
        validated_parts.append(validated_part)

    return ", ".join(validated_parts)


# =====================================================
# 安全构建函数
# =====================================================

def escape_like_pattern(value: str) -> str:
    """
    转义 LIKE 模式中的特殊字符

    防止通过特殊字符进行模式搜索攻击

    Args:
        value: 原始搜索值

    Returns:
        转义后的值
    """
    # 转义 SQL LIKE 的特殊字符
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_safe_like(value: str, position: Literal["start", "end", "both"] = "both") -> str:
    """
    构建安全的 LIKE 参数

    Args:
        value: 搜索值
        position: 通配符位置 - start: %value, end: value%, both: %value%

    Returns:
        带通配符的安全 LIKE 参数
    """
    escaped = escape_like_pattern(value)
    if position == "start":
        return f"%{escaped}"
    elif position == "end":
        return f"{escaped}%"
    return f"%{escaped}%"


def build_safe_update_sql(
    table: str,
    updates: dict[str, any],
    id_field: str,
    id_value: any
) -> tuple[str, tuple]:
    """
    构建安全的 UPDATE SQL 语句

    Args:
        table: 表名
        updates: 要更新的字段和值
        id_field: ID 字段名
        id_value: ID 值

    Returns:
        (SQL语句, 参数元组)

    Raises:
        ValidationError: 表名或字段名无效
    """
    # 验证表名
    validate_table_name(table)

    # 验证并获取字段列表
    fields = validate_fields_for_update(updates.keys(), table)

    # 验证 ID 字段
    validate_field_name(id_field, table, allow_qualified=False)

    # 构建 SET 子句
    set_clauses = [f"{field} = %s" for field in fields]
    params = [updates[field] for field in fields]
    params.append(id_value)

    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {id_field} = %s"
    return sql, tuple(params)


def build_safe_in_clause(
    values: list,
    field: str,
    table: str | None = None
) -> tuple[str, list]:
    """
    构建安全的 IN 子句

    Args:
        values: 值列表
        field: 字段名
        table: 表名（可选，用于字段验证）

    Returns:
        (IN子句, 参数列表)

    Raises:
        ValidationError: 字段名无效或值列表为空
    """
    if not values:
        raise ValidationError("IN 子句值列表不能为空", field="values")

    # 验证字段名
    validate_field_name(field, table)

    placeholders = ", ".join(["%s"] * len(values))
    return f"{field} IN ({placeholders})", list(values)


# =====================================================
# 常用排序字段白名单
# =====================================================

# 通用排序字段（大多数表都有）
COMMON_SORT_FIELDS: frozenset[str] = frozenset({
    "id", "created_at", "updated_at", "name", "status"
})

# 特定表的排序字段白名单
SORT_FIELD_WHITELIST: dict[str, frozenset[str]] = {
    "analysis_tasks": COMMON_SORT_FIELDS | {"task_type", "started_at", "completed_at"},
    "test_cases": COMMON_SORT_FIELDS | {"case_id", "endpoint_id", "category", "priority"},
    "test_executions": COMMON_SORT_FIELDS | {"execution_id", "started_at", "completed_at"},
    "test_results": frozenset({"id", "executed_at", "status", "case_id"}),
    "api_endpoints": COMMON_SORT_FIELDS | {"endpoint_id", "method", "path"},
    "knowledge_entries": COMMON_SORT_FIELDS | {"knowledge_id", "type", "priority", "scope"},
    "scenario_executions": COMMON_SORT_FIELDS | {"execution_id", "scenario_id", "started_at"},
}


def get_allowed_sort_fields(table: str) -> frozenset[str]:
    """获取表允许的排序字段"""
    base_table = table.split()[0].strip()
    return SORT_FIELD_WHITELIST.get(base_table, COMMON_SORT_FIELDS)
