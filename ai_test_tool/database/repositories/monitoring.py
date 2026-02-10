"""
监控相关 Repository：洞察、生产请求、健康检查
"""

from datetime import datetime
from typing import Any

from .base import BaseRepository
from ..models import (
    AIInsight,
    InsightSeverity,
    ProductionRequest,
    RequestSource,
    HealthCheckExecution,
    HealthCheckResult,
    HealthCheckStatus,
)
from ...utils.sql_security import validate_fields_for_update, escape_like_pattern, build_safe_like


class AIInsightRepository(BaseRepository[AIInsight]):
    """AI洞察仓库"""

    table_name = "ai_insights"
    model_class = AIInsight
    allowed_sort_fields = frozenset({"id", "created_at", "severity", "is_resolved"})

    def create(self, insight: AIInsight) -> int:
        """创建AI洞察"""
        data = insight.to_dict()
        sql = """
            INSERT INTO ai_insights
            (insight_id, insight_type, title, description, severity, confidence,
             details, recommendations, is_resolved, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data["insight_id"],
            data["insight_type"],
            data["title"],
            data["description"],
            data["severity"],
            data["confidence"],
            data["details"],
            data["recommendations"],
            data["is_resolved"],
            data["resolved_at"],
        )
        return self.db.execute(sql, params)

    def get_by_id(self, insight_id: str) -> AIInsight | None:
        """根据ID获取洞察"""
        return self._get_by_field("insight_id", insight_id)

    def get_unresolved(
        self,
        severity: InsightSeverity | None = None,
        insight_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AIInsight]:
        """获取未解决的洞察"""
        conditions = ["is_resolved = 0"]
        params: list[Any] = []

        if severity:
            conditions.append("severity = %s")
            params.append(severity.value)

        if insight_type:
            conditions.append("insight_type = %s")
            params.append(insight_type)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT * FROM ai_insights
            WHERE {where_clause}
            ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        rows = self.db.fetch_all(sql, tuple(params))
        return [AIInsight.from_dict(row) for row in rows]

    def resolve(self, insight_id: str) -> int:
        """标记洞察为已解决"""
        sql = """
            UPDATE ai_insights
            SET is_resolved = 1, resolved_at = %s
            WHERE insight_id = %s
        """
        return self.db.execute(sql, (datetime.now().isoformat(), insight_id))

    def delete(self, insight_id: str) -> int:
        """删除洞察"""
        return self.delete_by_field("insight_id", insight_id)

    def count_by_severity(self, unresolved_only: bool = True) -> dict[str, int]:
        """按严重程度统计"""
        condition = "WHERE is_resolved = 0" if unresolved_only else ""
        sql = f"""
            SELECT severity, COUNT(*) as count
            FROM ai_insights {condition}
            GROUP BY severity
        """
        rows = self.db.fetch_all(sql, ())
        return {row["severity"]: row["count"] for row in rows}

    def search(
        self,
        keyword: str | None = None,
        severity: InsightSeverity | None = None,
        insight_type: str | None = None,
        is_resolved: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AIInsight]:
        """搜索洞察"""
        conditions = []
        params: list[Any] = []

        if keyword:
            conditions.append("(title LIKE %s OR description LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if severity:
            conditions.append("severity = %s")
            params.append(severity.value)

        if insight_type:
            conditions.append("insight_type = %s")
            params.append(insight_type)

        if is_resolved is not None:
            conditions.append("is_resolved = %s")
            params.append(1 if is_resolved else 0)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT * FROM ai_insights
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        rows = self.db.fetch_all(sql, tuple(params))
        return [AIInsight.from_dict(row) for row in rows]

    def search_paginated(
        self,
        insight_type: str | None = None,
        severity: str | None = None,
        is_resolved: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AIInsight], int]:
        """
        分页搜索洞察

        Returns:
            元组: (洞察列表, 总数)
        """
        conditions = []
        params: list[Any] = []

        if insight_type:
            conditions.append("insight_type = %s")
            params.append(insight_type)

        if severity:
            conditions.append("severity = %s")
            params.append(severity)

        if is_resolved is not None:
            conditions.append("is_resolved = %s")
            params.append(1 if is_resolved else 0)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 获取总数
        count_sql = f"SELECT COUNT(*) as count FROM ai_insights {where_clause}"
        count_result = self.db.fetch_one(count_sql, tuple(params) if params else None)
        total = count_result["count"] if count_result else 0

        # 获取分页数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM ai_insights
            {where_clause}
            ORDER BY
                CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
                created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        rows = self.db.fetch_all(sql, tuple(params))

        return [AIInsight.from_dict(row) for row in rows], total

    def get_statistics(self) -> dict[str, Any]:
        """获取洞察统计"""
        # 总体统计
        stats = self.db.fetch_one(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) as unresolved,
                SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low
            FROM ai_insights
        """
        )

        # 按类型统计
        type_stats = self.db.fetch_all(
            """
            SELECT
                insight_type,
                COUNT(*) as count
            FROM ai_insights
            GROUP BY insight_type
            ORDER BY count DESC
        """
        )

        return {
            "total": stats["total"] if stats else 0,
            "unresolved": stats["unresolved"] if stats else 0,
            "by_severity": {
                "high": stats["high"] if stats else 0,
                "medium": stats["medium"] if stats else 0,
                "low": stats["low"] if stats else 0,
            },
            "by_type": [
                {"type": t["insight_type"], "count": t["count"]} for t in type_stats
            ],
        }

    def get_by_types(
        self,
        types: list[str],
        is_resolved: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AIInsight], int]:
        """
        按多个类型获取洞察（用于告警列表）

        Args:
            types: 类型列表
            is_resolved: 是否已解决筛选
            page: 页码
            page_size: 每页数量

        Returns:
            元组: (洞察列表, 总数)
        """
        if not types:
            return [], 0

        type_placeholders = ", ".join(["%s"] * len(types))
        conditions = [f"insight_type IN ({type_placeholders})"]
        params: list[Any] = list(types)

        if is_resolved is not None:
            conditions.append("is_resolved = %s")
            params.append(1 if is_resolved else 0)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        # 获取总数
        count_sql = f"SELECT COUNT(*) as count FROM ai_insights {where_clause}"
        count_result = self.db.fetch_one(count_sql, tuple(params))
        total = count_result["count"] if count_result else 0

        # 获取分页数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM ai_insights
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        rows = self.db.fetch_all(sql, tuple(params))

        return [AIInsight.from_dict(row) for row in rows], total


class ProductionRequestRepository(BaseRepository[ProductionRequest]):
    """生产请求监控仓库"""

    table_name = "production_requests"
    model_class = ProductionRequest
    allowed_sort_fields = frozenset(
        {"id", "created_at", "updated_at", "method", "last_check_at"}
    )

    def create(self, request: ProductionRequest) -> int:
        """创建监控请求"""
        data = request.to_dict()
        sql = """
            INSERT INTO production_requests
            (request_id, method, url, headers, body, query_params,
             expected_status_code, expected_response_pattern, source, source_task_id,
             tags, is_enabled, last_check_at, last_check_status, consecutive_failures)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data["request_id"],
            data["method"],
            data["url"],
            data["headers"],
            data["body"],
            data["query_params"],
            data["expected_status_code"],
            data["expected_response_pattern"],
            data["source"],
            data["source_task_id"],
            data["tags"],
            data["is_enabled"],
            data["last_check_at"],
            data["last_check_status"],
            data["consecutive_failures"],
        )
        return self.db.execute(sql, params)

    def get_by_id(self, request_id: str) -> ProductionRequest | None:
        """根据ID获取请求"""
        return self._get_by_field("request_id", request_id)

    def get_enabled(self, limit: int = 1000) -> list[ProductionRequest]:
        """获取启用的监控请求"""
        sql = "SELECT * FROM production_requests WHERE is_enabled = 1 ORDER BY id LIMIT %s"
        rows = self.db.fetch_all(sql, (limit,))
        return [ProductionRequest.from_dict(row) for row in rows]

    def update(self, request_id: str, updates: dict[str, Any]) -> int:
        """更新监控请求"""
        if not updates:
            return 0

        updates["updated_at"] = datetime.now().isoformat()
        validated_fields = validate_fields_for_update(list(updates.keys()), self.table_name)
        set_clauses = [f"{key} = %s" for key in validated_fields]
        params = [updates[key] for key in validated_fields] + [request_id]

        sql = f"UPDATE production_requests SET {', '.join(set_clauses)} WHERE request_id = %s"
        return self.db.execute(sql, tuple(params))

    def update_check_status(
        self, request_id: str, status: str, increment_failures: bool = False
    ) -> int:
        """更新检查状态"""
        now = datetime.now().isoformat()
        if increment_failures:
            sql = """
                UPDATE production_requests
                SET last_check_at = %s, last_check_status = %s,
                    consecutive_failures = consecutive_failures + 1, updated_at = %s
                WHERE request_id = %s
            """
        else:
            sql = """
                UPDATE production_requests
                SET last_check_at = %s, last_check_status = %s,
                    consecutive_failures = 0, updated_at = %s
                WHERE request_id = %s
            """
        return self.db.execute(sql, (now, status, now, request_id))

    def set_enabled(self, request_id: str, enabled: bool) -> int:
        """设置启用状态"""
        return self.update(request_id, {"is_enabled": 1 if enabled else 0})

    def delete(self, request_id: str) -> int:
        """删除监控请求"""
        return self.delete_by_field("request_id", request_id)

    def get_unhealthy(self, min_failures: int = 3) -> list[ProductionRequest]:
        """获取不健康的请求"""
        sql = """
            SELECT * FROM production_requests
            WHERE is_enabled = 1 AND consecutive_failures >= %s
            ORDER BY consecutive_failures DESC
        """
        rows = self.db.fetch_all(sql, (min_failures,))
        return [ProductionRequest.from_dict(row) for row in rows]

    def count_by_status(self) -> dict[str, int]:
        """按状态统计"""
        sql = """
            SELECT last_check_status as status, COUNT(*) as count
            FROM production_requests
            WHERE is_enabled = 1
            GROUP BY last_check_status
        """
        rows = self.db.fetch_all(sql, ())
        return {row["status"] or "unknown": row["count"] for row in rows}

    def search_paginated(
        self,
        tag: str | None = None,
        is_enabled: bool | None = None,
        last_status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProductionRequest], int]:
        """
        分页搜索监控请求

        Returns:
            元组: (请求列表, 总数)
        """

        conditions = []
        params: list[Any] = []

        if is_enabled is not None:
            conditions.append("is_enabled = %s")
            params.append(1 if is_enabled else 0)

        if tag:
            # SQLite JSON 查询
            conditions.append("tags LIKE %s ESCAPE '\\\\'")
            params.append(f'%"{tag}"%')

        if last_status:
            conditions.append("last_check_status = %s")
            params.append(last_status)

        if search:
            conditions.append("url LIKE %s ESCAPE '\\\\'")
            params.append(build_safe_like(search))

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 获取总数
        count_sql = f"SELECT COUNT(*) as count FROM production_requests {where_clause}"
        count_result = self.db.fetch_one(count_sql, tuple(params) if params else None)
        total = count_result["count"] if count_result else 0

        # 获取分页数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM production_requests
            {where_clause}
            ORDER BY CASE WHEN last_check_at IS NULL THEN 1 ELSE 0 END, last_check_at DESC, created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        rows = self.db.fetch_all(sql, tuple(params))

        return [ProductionRequest.from_dict(row) for row in rows], total

    def get_statistics(self) -> dict[str, Any]:
        """获取监控请求统计"""
        stats = self.db.fetch_one(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled,
                SUM(CASE WHEN last_check_status = 'healthy' THEN 1 ELSE 0 END) as healthy,
                SUM(CASE WHEN last_check_status = 'unhealthy' THEN 1 ELSE 0 END) as unhealthy,
                SUM(CASE WHEN consecutive_failures >= 3 THEN 1 ELSE 0 END) as critical
            FROM production_requests
        """
        )

        total = stats["total"] if stats else 0
        healthy = stats["healthy"] if stats else 0

        return {
            "total": total,
            "enabled": stats["enabled"] if stats else 0,
            "healthy": healthy,
            "unhealthy": stats["unhealthy"] if stats else 0,
            "critical": stats["critical"] if stats else 0,
            "health_rate": round(healthy / total * 100, 2) if total > 0 else 0,
        }


class HealthCheckExecutionRepository(BaseRepository[HealthCheckExecution]):
    """健康检查执行仓库"""

    table_name = "health_check_executions"
    model_class = HealthCheckExecution
    allowed_sort_fields = frozenset({"id", "created_at", "status"})

    def create(self, execution: HealthCheckExecution) -> int:
        """创建执行记录"""
        data = execution.to_dict()
        sql = """
            INSERT INTO health_check_executions
            (execution_id, base_url, total_requests, healthy_count, unhealthy_count,
             status, trigger_type, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data["execution_id"],
            data["base_url"],
            data["total_requests"],
            data["healthy_count"],
            data["unhealthy_count"],
            data["status"],
            data["trigger_type"],
            data["started_at"],
            data["completed_at"],
        )
        return self.db.execute(sql, params)

    def get_by_id(self, execution_id: str) -> HealthCheckExecution | None:
        """根据ID获取执行记录"""
        return self._get_by_field("execution_id", execution_id)

    def update_status(
        self,
        execution_id: str,
        status: HealthCheckStatus,
        healthy_count: int | None = None,
        unhealthy_count: int | None = None,
    ) -> int:
        """更新执行状态"""
        now = datetime.now().isoformat()
        updates = ["status = %s"]
        params: list[Any] = [status.value]

        if status == HealthCheckStatus.RUNNING:
            updates.append("started_at = %s")
            params.append(now)
        elif status in (HealthCheckStatus.COMPLETED, HealthCheckStatus.FAILED):
            updates.append("completed_at = %s")
            params.append(now)

        if healthy_count is not None:
            updates.append("healthy_count = %s")
            params.append(healthy_count)

        if unhealthy_count is not None:
            updates.append("unhealthy_count = %s")
            params.append(unhealthy_count)

        params.append(execution_id)
        sql = f"UPDATE health_check_executions SET {', '.join(updates)} WHERE execution_id = %s"
        return self.db.execute(sql, tuple(params))

    def get_latest(self, limit: int = 10) -> list[HealthCheckExecution]:
        """获取最近的执行记录"""
        sql = "SELECT * FROM health_check_executions ORDER BY created_at DESC LIMIT %s"
        rows = self.db.fetch_all(sql, (limit,))
        return [HealthCheckExecution.from_dict(row) for row in rows]

    def search_paginated(
        self,
        status: str | None = None,
        trigger_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[HealthCheckExecution], int]:
        """
        分页搜索执行记录

        Returns:
            元组: (执行记录列表, 总数)
        """
        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("status = %s")
            params.append(status)

        if trigger_type:
            conditions.append("trigger_type = %s")
            params.append(trigger_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 获取总数
        count_sql = (
            f"SELECT COUNT(*) as count FROM health_check_executions {where_clause}"
        )
        count_result = self.db.fetch_one(count_sql, tuple(params) if params else None)
        total = count_result["count"] if count_result else 0

        # 获取分页数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM health_check_executions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        rows = self.db.fetch_all(sql, tuple(params))

        return [HealthCheckExecution.from_dict(row) for row in rows], total


class HealthCheckResultRepository(BaseRepository[HealthCheckResult]):
    """健康检查结果仓库"""

    table_name = "health_check_results"
    model_class = HealthCheckResult
    allowed_sort_fields = frozenset({"id", "checked_at", "success"})

    def create(self, result: HealthCheckResult) -> int:
        """创建检查结果"""
        data = result.to_dict()
        sql = """
            INSERT INTO health_check_results
            (execution_id, request_id, success, status_code, response_time_ms,
             response_body, error_message, ai_analysis, checked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data["execution_id"],
            data["request_id"],
            data["success"],
            data["status_code"],
            data["response_time_ms"],
            data["response_body"],
            data["error_message"],
            data["ai_analysis"],
            data["checked_at"],
        )
        return self.db.execute(sql, params)

    def create_batch(self, results: list[HealthCheckResult]) -> int:
        """批量创建检查结果"""
        if not results:
            return 0

        sql = """
            INSERT INTO health_check_results
            (execution_id, request_id, success, status_code, response_time_ms,
             response_body, error_message, ai_analysis, checked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_list = []
        for r in results:
            data = r.to_dict()
            params_list.append(
                (
                    data["execution_id"],
                    data["request_id"],
                    data["success"],
                    data["status_code"],
                    data["response_time_ms"],
                    data["response_body"],
                    data["error_message"],
                    data["ai_analysis"],
                    data["checked_at"],
                )
            )
        return self.db.execute_many(sql, params_list)

    def get_by_execution(self, execution_id: str) -> list[HealthCheckResult]:
        """获取执行批次的所有结果"""
        sql = "SELECT * FROM health_check_results WHERE execution_id = %s ORDER BY id"
        rows = self.db.fetch_all(sql, (execution_id,))
        return [HealthCheckResult.from_dict(row) for row in rows]

    def get_by_request(
        self, request_id: str, limit: int = 100
    ) -> list[HealthCheckResult]:
        """获取请求的检查历史"""
        sql = """
            SELECT * FROM health_check_results
            WHERE request_id = %s
            ORDER BY checked_at DESC
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (request_id, limit))
        return [HealthCheckResult.from_dict(row) for row in rows]

    def get_statistics(self, execution_id: str) -> dict[str, Any]:
        """获取执行统计"""
        sql = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(response_time_ms) as avg_response_time
            FROM health_check_results
            WHERE execution_id = %s
        """
        row = self.db.fetch_one(sql, (execution_id,))
        return row if row else {"total": 0, "success_count": 0, "avg_response_time": 0}

    def delete_by_execution(self, execution_id: str) -> int:
        """删除执行批次的所有结果"""
        return self.delete_by_field("execution_id", execution_id)

    def get_by_execution_with_request_details(
        self, execution_id: str
    ) -> list[dict[str, Any]]:
        """
        获取执行批次结果（含请求详情）

        Returns:
            包含结果和请求URL/method的字典列表
        """
        sql = """
            SELECT r.*, p.url, p.method
            FROM health_check_results r
            JOIN production_requests p ON r.request_id = p.request_id
            WHERE r.execution_id = %s
            ORDER BY r.success ASC, r.response_time_ms DESC
        """
        rows = self.db.fetch_all(sql, (execution_id,))
        return [dict(r) for r in rows]

    def get_today_statistics(self) -> dict[str, Any]:
        """获取今日检查统计"""
        stats = self.db.fetch_one(
            """
            SELECT
                COUNT(*) as total_checks,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(response_time_ms) as avg_response_time
            FROM health_check_results
            WHERE DATE(checked_at) = DATE('now')
        """
        )

        return {
            "total_checks": stats["total_checks"] if stats else 0,
            "success_count": stats["success_count"] if stats else 0,
            "avg_response_time": (
                round(stats["avg_response_time"] or 0, 2) if stats else 0
            ),
        }

    def get_trend(self, days: int = 7) -> list[dict[str, Any]]:
        """获取近N天的检查趋势"""
        sql = """
            SELECT
                DATE(checked_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                AVG(response_time_ms) as avg_time
            FROM health_check_results
            WHERE checked_at >= datetime('now', %s)
            GROUP BY DATE(checked_at)
            ORDER BY date
        """
        rows = self.db.fetch_all(sql, (f"-{days} days",))
        return [
            {
                "date": str(t["date"]),
                "total": t["total"],
                "success": t["success"],
                "success_rate": (
                    round(t["success"] / t["total"] * 100, 2) if t["total"] > 0 else 0
                ),
                "avg_time": round(t["avg_time"] or 0, 2),
            }
            for t in rows
        ]


# =====================================================
# 对话会话仓库
# 该文件内容使用AI生成，注意识别准确性
# =====================================================
