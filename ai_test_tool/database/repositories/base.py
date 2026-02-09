"""
Repository 基类
提供泛型 CRUD 操作
"""

from typing import Any, Generic, TypeVar

from ..connection import DatabaseManager, get_db_manager
from ..models import BaseModel
from ...utils.sql_security import (
    validate_table_name,
    validate_field_name,
    validate_fields_for_update,
    validate_order_by,
    get_allowed_sort_fields,
    ALLOWED_TABLES,
)

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """
    泛型仓库基类
    提供通用的 CRUD 操作
    """

    table_name: str = ""
    model_class: type[T] = BaseModel  # type: ignore
    id_field: str = "id"

    # 子类可覆盖：允许的字段名集合（用于动态查询验证）
    allowed_fields: frozenset[str] = frozenset()
    # 子类可覆盖：允许的排序字段
    allowed_sort_fields: frozenset[str] = frozenset({"id", "created_at"})

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        self.db = db_manager or get_db_manager()
        # 验证表名（类初始化时验证）
        if self.table_name and self.table_name not in ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {self.table_name}")

    def _validate_field(self, field: str) -> str:
        """验证字段名"""
        return validate_field_name(field, self.table_name, allow_qualified=True)

    def _validate_order_by(self, order_by: str) -> str:
        """验证排序字段"""
        allowed = self.allowed_sort_fields or get_allowed_sort_fields(self.table_name)
        return validate_order_by(order_by, allowed)

    def _get_by_field(self, field: str, value: Any) -> T | None:
        """根据字段获取单条记录"""
        self._validate_field(field)
        sql = f"SELECT * FROM {self.table_name} WHERE {field} = %s"
        row = self.db.fetch_one(sql, (value,))
        return self.model_class.from_dict(row) if row else None

    def _get_all_by_field(
        self,
        field: str,
        value: Any,
        order_by: str = "id",
        limit: int = 1000,
        offset: int = 0
    ) -> list[T]:
        """根据字段获取多条记录"""
        self._validate_field(field)
        validated_order = self._validate_order_by(order_by)
        sql = f"SELECT * FROM {self.table_name} WHERE {field} = %s ORDER BY {validated_order} LIMIT %s OFFSET %s"
        rows = self.db.fetch_all(sql, (value, limit, offset))
        return [self.model_class.from_dict(row) for row in rows]

    def get_all(
        self,
        order_by: str = "created_at DESC",
        limit: int = 100,
        offset: int = 0
    ) -> list[T]:
        """获取所有记录"""
        validated_order = self._validate_order_by(order_by)
        sql = f"SELECT * FROM {self.table_name} ORDER BY {validated_order} LIMIT %s OFFSET %s"
        rows = self.db.fetch_all(sql, (limit, offset))
        return [self.model_class.from_dict(row) for row in rows]

    def count(self, where: str = "", params: tuple = ()) -> int:
        """
        统计记录数

        注意：where 参数应该是由内部构建的安全条件，不应直接使用外部输入
        """
        sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
        if where:
            sql += f" WHERE {where}"
        result = self.db.fetch_one(sql, params)
        return result['count'] if result else 0

    def delete_by_field(self, field: str, value: Any) -> int:
        """根据字段删除记录"""
        self._validate_field(field)
        sql = f"DELETE FROM {self.table_name} WHERE {field} = %s"
        return self.db.execute(sql, (value,))


