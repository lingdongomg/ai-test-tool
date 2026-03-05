# 该文件内容使用AI生成，注意识别准确性
"""
日志洞察服务层

将 routes/insights.py 中的业务逻辑抽取到此处，
路由层仅负责参数校验和响应格式化。

使用方式：在 dependencies.py 中注册为单例，通过 Depends 注入路由。
"""

import logging
from typing import Any

from ..database import DatabaseManager, get_db_manager
from ..database.repositories import TaskRepository, ReportRepository, RequestRepository

logger = logging.getLogger(__name__)


class InsightsService:
    """日志洞察业务服务"""

    def __init__(
        self,
        task_repo: TaskRepository | None = None,
        report_repo: ReportRepository | None = None,
        request_repo: RequestRepository | None = None,
    ) -> None:
        self._task_repo = task_repo or TaskRepository()
        self._report_repo = report_repo or ReportRepository()
        self._request_repo = request_repo or RequestRepository()
        self._db = get_db_manager()

    def get_task_with_requests(self, task_id: str) -> dict[str, Any] | None:
        """获取任务详情及其关联的解析请求"""
        task = self._task_repo.get_by_field("task_id", task_id)
        if not task:
            return None

        requests = self._request_repo.find_by_conditions(
            conditions=["task_id = %s"],
            params=[task_id],
            order_by="created_at DESC"
        )
        result = dict(task)
        result["requests"] = [dict(r) for r in requests] if requests else []
        return result

    def get_statistics(self) -> dict[str, Any]:
        """获取日志洞察统计数据"""
        total_tasks = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM analysis_tasks"
        )
        completed_tasks = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM analysis_tasks WHERE status = 'completed'"
        )
        total_reports = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM analysis_reports"
        )

        return {
            "total_tasks": total_tasks["count"] if total_tasks else 0,
            "completed_tasks": completed_tasks["count"] if completed_tasks else 0,
            "total_reports": total_reports["count"] if total_reports else 0,
        }

    def delete_task(self, task_id: str) -> bool:
        """删除任务及其关联数据"""
        task = self._task_repo.get_by_field("task_id", task_id)
        if not task:
            return False

        # 删除关联的解析请求
        self._db.execute(
            "DELETE FROM parsed_requests WHERE task_id = %s", (task_id,)
        )
        # 删除关联的报告
        self._db.execute(
            "DELETE FROM analysis_reports WHERE task_id = %s", (task_id,)
        )
        # 删除任务本身
        self._task_repo.delete_by_field("task_id", task_id)
        return True
