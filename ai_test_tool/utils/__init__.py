"""
工具模块
"""

from .logger import AILogger, get_logger
from .sql_security import (
    validate_table_name,
    validate_field_name,
    validate_fields_for_update,
    validate_order_by,
    validate_order_by_multi,
    escape_like_pattern,
    build_safe_like,
    build_safe_update_sql,
    build_safe_in_clause,
    get_allowed_sort_fields,
    ALLOWED_TABLES,
    TABLE_FIELDS,
)

__all__ = [
    "AILogger",
    "get_logger",
    # SQL 安全
    "validate_table_name",
    "validate_field_name",
    "validate_fields_for_update",
    "validate_order_by",
    "validate_order_by_multi",
    "escape_like_pattern",
    "build_safe_like",
    "build_safe_update_sql",
    "build_safe_in_clause",
    "get_allowed_sort_fields",
    "ALLOWED_TABLES",
    "TABLE_FIELDS",
]
