"""
知识库相关 Repository
"""

from datetime import datetime
from typing import Any

from .base import BaseRepository
from ..models import (
    KnowledgeEntry, KnowledgeHistory, KnowledgeUsage,
    KnowledgeType, KnowledgeStatus, KnowledgeSource,
)
from ...utils.sql_security import validate_fields_for_update, escape_like_pattern


class KnowledgeRepository(BaseRepository[KnowledgeEntry]):
    """知识库仓库"""
    
    table_name = "knowledge_entries"
    model_class = KnowledgeEntry
    
    def create(self, entry: KnowledgeEntry) -> int:
        """创建知识条目"""
        data = entry.to_dict()
        sql = """
            INSERT INTO knowledge_entries 
            (knowledge_id, type, category, title, content, scope, priority,
             status, source, source_ref, metadata, created_by, version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['knowledge_id'], data['type'], data['category'], data['title'],
            data['content'], data['scope'], data['priority'], data['status'],
            data['source'], data['source_ref'], data['metadata'],
            data['created_by'], data['version']
        )
        result = self.db.execute(sql, params)
        
        # 保存标签
        if entry.tags:
            self._save_tags(entry.knowledge_id, entry.tags)
        
        return result
    
    def _save_tags(self, knowledge_id: str, tags: list[str]) -> None:
        """保存知识标签"""
        # 先删除旧标签
        self.db.execute("DELETE FROM knowledge_tags WHERE knowledge_id = %s", (knowledge_id,))
        
        # 插入新标签
        if tags:
            sql = "INSERT INTO knowledge_tags (knowledge_id, tag) VALUES (%s, %s)"
            params_list = [(knowledge_id, tag) for tag in tags]
            self.db.execute_many(sql, params_list)
    
    def get_by_id(self, knowledge_id: str) -> KnowledgeEntry | None:
        """根据ID获取知识"""
        entry = self._get_by_field("knowledge_id", knowledge_id)
        if entry:
            entry.tags = self._get_tags(knowledge_id)
        return entry
    
    def _get_tags(self, knowledge_id: str) -> list[str]:
        """获取知识标签"""
        sql = "SELECT tag FROM knowledge_tags WHERE knowledge_id = %s"
        rows = self.db.fetch_all(sql, (knowledge_id,))
        return [row['tag'] for row in rows]
    
    def update(self, knowledge_id: str, updates: dict[str, Any]) -> int:
        """更新知识条目"""
        if not updates:
            return 0

        # 提取标签更新
        tags = updates.pop('tags', None)

        updates['updated_at'] = datetime.now().isoformat()
        updates['version'] = self._get_next_version(knowledge_id)

        # 验证字段名
        validated_fields = validate_fields_for_update(updates.keys(), self.table_name)
        set_clauses = [f"{key} = %s" for key in validated_fields]
        params = [updates[key] for key in validated_fields] + [knowledge_id]

        sql = f"UPDATE knowledge_entries SET {', '.join(set_clauses)} WHERE knowledge_id = %s"
        result = self.db.execute(sql, tuple(params))

        # 更新标签
        if tags is not None:
            self._save_tags(knowledge_id, tags)

        return result
    
    def _get_next_version(self, knowledge_id: str) -> int:
        """获取下一个版本号"""
        sql = "SELECT version FROM knowledge_entries WHERE knowledge_id = %s"
        row = self.db.fetch_one(sql, (knowledge_id,))
        return (row['version'] + 1) if row else 1
    
    def archive(self, knowledge_id: str) -> int:
        """归档知识（软删除）"""
        return self.update(knowledge_id, {'status': KnowledgeStatus.ARCHIVED.value})
    
    def delete(self, knowledge_id: str) -> int:
        """删除知识"""
        return self.delete_by_field("knowledge_id", knowledge_id)
    
    def search(
        self,
        type: KnowledgeType | None = None,
        status: KnowledgeStatus | None = None,
        tags: list[str] | None = None,
        scope: str | None = None,
        keyword: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[KnowledgeEntry]:
        """搜索知识条目"""
        conditions = []
        params: list[Any] = []
        
        if type:
            conditions.append("type = %s")
            params.append(type.value)
        
        if status:
            conditions.append("status = %s")
            params.append(status.value)
        else:
            # 默认不返回已归档
            conditions.append("status != %s")
            params.append(KnowledgeStatus.ARCHIVED.value)
        
        if scope:
            conditions.append("(scope = %s OR scope = '' OR scope LIKE %s)")
            params.extend([scope, f"{scope}%"])
        
        if keyword:
            conditions.append("(title LIKE %s OR content LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 如果有标签筛选，使用子查询
        if tags:
            tag_placeholders = ", ".join(["%s"] * len(tags))
            sql = f"""
                SELECT DISTINCT e.* FROM knowledge_entries e
                JOIN knowledge_tags t ON e.knowledge_id = t.knowledge_id
                WHERE {where_clause} AND t.tag IN ({tag_placeholders})
                ORDER BY e.priority DESC, e.updated_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend(tags)
        else:
            sql = f"""
                SELECT * FROM knowledge_entries
                WHERE {where_clause}
                ORDER BY priority DESC, updated_at DESC
                LIMIT %s OFFSET %s
            """
        
        params.extend([limit, offset])
        rows = self.db.fetch_all(sql, tuple(params))
        
        entries = []
        for row in rows:
            entry = KnowledgeEntry.from_dict(row)
            entry.tags = self._get_tags(entry.knowledge_id)
            entries.append(entry)
        
        return entries
    
    def get_by_scope(self, scope: str, type: KnowledgeType | None = None) -> list[KnowledgeEntry]:
        """获取指定范围的知识"""
        return self.search(type=type, scope=scope, status=KnowledgeStatus.ACTIVE)
    
    def get_pending(self, limit: int = 100) -> list[KnowledgeEntry]:
        """获取待审核的知识"""
        return self.search(status=KnowledgeStatus.PENDING, limit=limit)
    
    def batch_update_status(self, knowledge_ids: list[str], status: KnowledgeStatus) -> int:
        """批量更新状态"""
        if not knowledge_ids:
            return 0

        placeholders = ", ".join(["%s"] * len(knowledge_ids))
        sql = f"""
            UPDATE knowledge_entries
            SET status = %s, updated_at = %s
            WHERE knowledge_id IN ({placeholders})
        """
        params = [status.value, datetime.now().isoformat()] + knowledge_ids
        return self.db.execute(sql, tuple(params))

    def search_paginated(
        self,
        type: KnowledgeType | None = None,
        status: KnowledgeStatus | None = None,
        tags: list[str] | None = None,
        scope: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[KnowledgeEntry], int]:
        """
        分页搜索知识条目

        Returns:
            元组: (知识条目列表, 总数)
        """
        conditions = []
        params: list[Any] = []

        if type:
            conditions.append("type = %s")
            params.append(type.value)

        if status:
            conditions.append("status = %s")
            params.append(status.value)
        else:
            conditions.append("status != %s")
            params.append(KnowledgeStatus.ARCHIVED.value)

        if scope:
            conditions.append("(scope = %s OR scope = '' OR scope LIKE %s)")
            params.extend([scope, f"{scope}%"])

        if keyword:
            conditions.append("(title LIKE %s OR content LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 处理标签筛选
        if tags:
            tag_placeholders = ", ".join(["%s"] * len(tags))
            count_sql = f"""
                SELECT COUNT(DISTINCT e.knowledge_id) as count
                FROM knowledge_entries e
                JOIN knowledge_tags t ON e.knowledge_id = t.knowledge_id
                WHERE {where_clause} AND t.tag IN ({tag_placeholders})
            """
            count_params = list(params) + tags
            count_result = self.db.fetch_one(count_sql, tuple(count_params))

            offset = (page - 1) * page_size
            sql = f"""
                SELECT DISTINCT e.* FROM knowledge_entries e
                JOIN knowledge_tags t ON e.knowledge_id = t.knowledge_id
                WHERE {where_clause} AND t.tag IN ({tag_placeholders})
                ORDER BY e.priority DESC, e.updated_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend(tags)
            params.extend([page_size, offset])
        else:
            count_sql = f"SELECT COUNT(*) as count FROM knowledge_entries WHERE {where_clause}"
            count_result = self.db.fetch_one(count_sql, tuple(params) if params else None)

            offset = (page - 1) * page_size
            sql = f"""
                SELECT * FROM knowledge_entries
                WHERE {where_clause}
                ORDER BY priority DESC, updated_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

        total = count_result['count'] if count_result else 0
        rows = self.db.fetch_all(sql, tuple(params))

        entries = []
        for row in rows:
            entry = KnowledgeEntry.from_dict(row)
            entry.tags = self._get_tags(entry.knowledge_id)
            entries.append(entry)

        return entries, total

    def count_by_type(self) -> dict[str, int]:
        """按类型统计知识数量"""
        sql = """
            SELECT type, COUNT(*) as count
            FROM knowledge_entries
            WHERE status != %s
            GROUP BY type
        """
        rows = self.db.fetch_all(sql, (KnowledgeStatus.ARCHIVED.value,))
        return {row['type']: row['count'] for row in rows}

    def get_statistics(self) -> dict[str, Any]:
        """获取知识库统计"""
        stats = self.db.fetch_one("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) as archived
            FROM knowledge_entries
        """)

        type_stats = self.db.fetch_all("""
            SELECT type, COUNT(*) as count
            FROM knowledge_entries
            WHERE status != 'archived'
            GROUP BY type
            ORDER BY count DESC
        """)

        return {
            'total': stats['total'] if stats else 0,
            'active': stats['active'] if stats else 0,
            'pending': stats['pending'] if stats else 0,
            'archived': stats['archived'] if stats else 0,
            'by_type': [
                {'type': t['type'], 'count': t['count']}
                for t in type_stats
            ]
        }
    
    def count_by_status(self) -> dict[str, int]:
        """按状态统计数量"""
        sql = "SELECT status, COUNT(*) as count FROM knowledge_entries GROUP BY status"
        rows = self.db.fetch_all(sql, ())
        return {row['status']: row['count'] for row in rows}


class KnowledgeHistoryRepository(BaseRepository[KnowledgeHistory]):
    """知识历史仓库"""
    
    table_name = "knowledge_history"
    model_class = KnowledgeHistory
    
    def create(self, history: KnowledgeHistory) -> int:
        """创建历史记录"""
        data = history.to_dict()
        sql = """
            INSERT INTO knowledge_history 
            (knowledge_id, version, content, title, changed_by, change_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            data['knowledge_id'], data['version'], data['content'],
            data['title'], data['changed_by'], data['change_type']
        )
        return self.db.execute(sql, params)
    
    def get_by_knowledge(self, knowledge_id: str, limit: int = 50) -> list[KnowledgeHistory]:
        """获取知识的历史记录"""
        sql = """
            SELECT * FROM knowledge_history 
            WHERE knowledge_id = %s 
            ORDER BY version DESC 
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (knowledge_id, limit))
        return [KnowledgeHistory.from_dict(row) for row in rows]
    
    def get_version(self, knowledge_id: str, version: int) -> KnowledgeHistory | None:
        """获取指定版本"""
        sql = "SELECT * FROM knowledge_history WHERE knowledge_id = %s AND version = %s"
        row = self.db.fetch_one(sql, (knowledge_id, version))
        return KnowledgeHistory.from_dict(row) if row else None


class KnowledgeUsageRepository(BaseRepository[KnowledgeUsage]):
    """知识使用记录仓库"""

    table_name = "knowledge_usage"
    model_class = KnowledgeUsage

    def create(self, usage: KnowledgeUsage) -> int:
        """创建使用记录"""
        data = usage.to_dict()
        sql = """
            INSERT INTO knowledge_usage
            (usage_id, knowledge_id, used_in, context, helpful)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            data['usage_id'], data['knowledge_id'], data['used_in'],
            data['context'], data['helpful']
        )
        return self.db.execute(sql, params)

    def update_helpful(self, usage_id: str, helpful: int) -> int:
        """更新帮助评价"""
        sql = "UPDATE knowledge_usage SET helpful = %s WHERE usage_id = %s"
        return self.db.execute(sql, (helpful, usage_id))

    def get_by_knowledge(self, knowledge_id: str, limit: int = 100) -> list[KnowledgeUsage]:
        """获取知识的使用记录"""
        sql = """
            SELECT * FROM knowledge_usage
            WHERE knowledge_id = %s
            ORDER BY used_at DESC
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (knowledge_id, limit))
        return [KnowledgeUsage.from_dict(row) for row in rows]

    def get_statistics(self, knowledge_id: str) -> dict[str, Any]:
        """获取知识使用统计"""
        sql = """
            SELECT
                COUNT(*) as total_usage,
                SUM(CASE WHEN helpful = 1 THEN 1 ELSE 0 END) as helpful_count,
                SUM(CASE WHEN helpful = -1 THEN 1 ELSE 0 END) as unhelpful_count
            FROM knowledge_usage
            WHERE knowledge_id = %s
        """
        row = self.db.fetch_one(sql, (knowledge_id,))
        return row if row else {'total_usage': 0, 'helpful_count': 0, 'unhelpful_count': 0}


# =====================================================
# 监控相关仓库
# 该文件内容使用AI生成，注意识别准确性
# =====================================================

