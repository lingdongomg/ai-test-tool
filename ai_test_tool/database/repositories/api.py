"""
API 相关 Repository：标签、端点
"""

from datetime import datetime
from typing import Any

from .base import BaseRepository
from ..models import ApiTag, ApiEndpoint
from ...utils.sql_security import validate_fields_for_update


class ApiTagRepository(BaseRepository[ApiTag]):
    """接口标签仓库"""
    
    table_name = "api_tags"
    model_class = ApiTag
    
    def create(self, tag: ApiTag) -> int:
        """创建标签"""
        data = tag.to_dict()
        sql = """
            INSERT INTO api_tags 
            (name, description, color, parent_id, sort_order, is_system)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            data['name'], data['description'], data['color'],
            data['parent_id'], data['sort_order'], data['is_system']
        )
        return self.db.execute(sql, params)
    
    def get_by_name(self, name: str) -> ApiTag | None:
        """根据名称获取标签"""
        return self._get_by_field("name", name)
    
    def get_by_id(self, tag_id: int) -> ApiTag | None:
        """根据ID获取标签"""
        return self._get_by_field("id", tag_id)
    
    def get_children(self, parent_id: int) -> list[ApiTag]:
        """获取子标签"""
        return self._get_all_by_field("parent_id", parent_id, "sort_order", 1000, 0)


class ApiEndpointRepository(BaseRepository[ApiEndpoint]):
    """接口端点仓库"""
    
    table_name = "api_endpoints"
    model_class = ApiEndpoint
    
    def create(self, endpoint: ApiEndpoint) -> int:
        """创建端点"""
        data = endpoint.to_dict()
        sql = """
            INSERT INTO api_endpoints 
            (endpoint_id, name, description, method, path, summary, parameters,
             request_body, responses, security, source_type, source_file, is_deprecated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['endpoint_id'], data['name'], data['description'], data['method'],
            data['path'], data['summary'], data['parameters'], data['request_body'],
            data['responses'], data['security'], data['source_type'], data['source_file'],
            data['is_deprecated']
        )
        return self.db.execute(sql, params)
    
    def get_by_id(self, endpoint_id: str) -> ApiEndpoint | None:
        """根据ID获取端点"""
        return self._get_by_field("endpoint_id", endpoint_id)
    
    def get_by_method_path(self, method: str, path: str) -> ApiEndpoint | None:
        """根据方法和路径获取端点"""
        sql = "SELECT * FROM api_endpoints WHERE method = %s AND path = %s"
        row = self.db.fetch_one(sql, (method, path))
        return ApiEndpoint.from_dict(row) if row else None
    
    def update(self, endpoint_id: str, updates: dict[str, Any]) -> int:
        """更新端点"""
        if not updates:
            return 0

        updates['updated_at'] = datetime.now().isoformat()
        # 验证字段名
        validated_fields = validate_fields_for_update(updates.keys(), self.table_name)
        set_clauses = [f"{key} = %s" for key in validated_fields]
        params = [updates[key] for key in validated_fields] + [endpoint_id]

        sql = f"UPDATE api_endpoints SET {', '.join(set_clauses)} WHERE endpoint_id = %s"
        return self.db.execute(sql, tuple(params))
    
    def delete(self, endpoint_id: str) -> int:
        """删除端点"""
        return self.delete_by_field("endpoint_id", endpoint_id)
    
    def add_tag(self, endpoint_id: str, tag_id: int) -> int:
        """添加标签关联"""
        sql = "INSERT OR IGNORE INTO api_endpoint_tags (endpoint_id, tag_id) VALUES (%s, %s)"
        return self.db.execute(sql, (endpoint_id, tag_id))
    
    def remove_tag(self, endpoint_id: str, tag_id: int) -> int:
        """移除标签关联"""
        sql = "DELETE FROM api_endpoint_tags WHERE endpoint_id = %s AND tag_id = %s"
        return self.db.execute(sql, (endpoint_id, tag_id))
    
    def get_tags(self, endpoint_id: str) -> list[ApiTag]:
        """获取端点的所有标签"""
        sql = """
            SELECT t.* FROM api_tags t
            JOIN api_endpoint_tags et ON t.id = et.tag_id
            WHERE et.endpoint_id = %s
            ORDER BY t.sort_order
        """
        rows = self.db.fetch_all(sql, (endpoint_id,))
        return [ApiTag.from_dict(row) for row in rows]
    
    def get_by_tag(self, tag_id: int) -> list[ApiEndpoint]:
        """获取标签下的所有端点"""
        sql = """
            SELECT e.* FROM api_endpoints e
            JOIN api_endpoint_tags et ON e.endpoint_id = et.endpoint_id
            WHERE et.tag_id = %s
            ORDER BY e.method, e.path
        """
        rows = self.db.fetch_all(sql, (tag_id,))
        return [ApiEndpoint.from_dict(row) for row in rows]


# =====================================================
# 场景相关仓库（简化版）
# =====================================================

