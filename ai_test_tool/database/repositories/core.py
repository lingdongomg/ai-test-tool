"""
核心业务 Repository：任务、请求、报告
"""

from datetime import datetime
from typing import Any

from .base import BaseRepository
from ..models import (
    AnalysisTask, TaskStatus, TaskType,
    ParsedRequestRecord,
    AnalysisReport, ReportType,
)


class TaskRepository(BaseRepository[AnalysisTask]):
    """任务仓库"""
    
    table_name = "analysis_tasks"
    model_class = AnalysisTask
    
    def create(self, task: AnalysisTask) -> int:
        """创建任务"""
        sql = """
            INSERT INTO analysis_tasks 
            (task_id, name, description, task_type, log_file_path, log_file_size, 
             status, total_lines, processed_lines, total_requests, total_test_cases,
             error_message, metadata, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = task.to_dict()
        params = (
            data['task_id'], data['name'], data['description'], data['task_type'],
            data['log_file_path'], data['log_file_size'], data['status'],
            data['total_lines'], data['processed_lines'], data['total_requests'],
            data['total_test_cases'], data['error_message'], data['metadata'],
            data['started_at'], data['completed_at']
        )
        return self.db.execute(sql, params)
    
    def get_by_id(self, task_id: str) -> AnalysisTask | None:
        """根据ID获取任务"""
        return self._get_by_field("task_id", task_id)
    
    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: str | None = None
    ) -> None:
        """更新任务状态"""
        now = datetime.now().isoformat()
        if status == TaskStatus.RUNNING:
            sql = "UPDATE analysis_tasks SET status = %s, started_at = %s, updated_at = %s WHERE task_id = %s"
            self.db.execute(sql, (status.value, now, now, task_id))
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            sql = "UPDATE analysis_tasks SET status = %s, error_message = %s, completed_at = %s, updated_at = %s WHERE task_id = %s"
            self.db.execute(sql, (status.value, error_message, now, now, task_id))
        else:
            sql = "UPDATE analysis_tasks SET status = %s, updated_at = %s WHERE task_id = %s"
            self.db.execute(sql, (status.value, now, task_id))
    
    def update_progress(
        self,
        task_id: str,
        processed_lines: int,
        total_requests: int | None = None
    ) -> None:
        """更新处理进度"""
        now = datetime.now().isoformat()
        if total_requests is not None:
            sql = "UPDATE analysis_tasks SET processed_lines = %s, total_requests = %s, updated_at = %s WHERE task_id = %s"
            self.db.execute(sql, (processed_lines, total_requests, now, task_id))
        else:
            sql = "UPDATE analysis_tasks SET processed_lines = %s, updated_at = %s WHERE task_id = %s"
            self.db.execute(sql, (processed_lines, now, task_id))
    
    def update_counts(
        self,
        task_id: str,
        total_requests: int | None = None,
        total_test_cases: int | None = None
    ) -> None:
        """更新计数"""
        updates, params = [], []
        if total_requests is not None:
            updates.append("total_requests = %s")
            params.append(total_requests)
        if total_test_cases is not None:
            updates.append("total_test_cases = %s")
            params.append(total_test_cases)
        
        if updates:
            updates.append("updated_at = %s")
            params.append(datetime.now().isoformat())
            sql = f"UPDATE analysis_tasks SET {', '.join(updates)} WHERE task_id = %s"
            params.append(task_id)
            self.db.execute(sql, tuple(params))
    
    def delete(self, task_id: str) -> int:
        """删除任务"""
        return self.delete_by_field("task_id", task_id)


class RequestRepository(BaseRepository[ParsedRequestRecord]):
    """请求仓库"""
    
    table_name = "parsed_requests"
    model_class = ParsedRequestRecord
    
    def create(self, request: ParsedRequestRecord) -> int:
        """创建请求记录"""
        data = request.to_dict()
        sql = """
            INSERT INTO parsed_requests 
            (task_id, request_id, method, url, category, headers, body, query_params,
             http_status, response_time_ms, response_body, has_error, error_message,
             has_warning, warning_message, curl_command, timestamp, raw_logs, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['task_id'], data['request_id'], data['method'], data['url'],
            data['category'], data['headers'], data['body'], data['query_params'],
            data['http_status'], data['response_time_ms'], data['response_body'],
            data['has_error'], data['error_message'], data['has_warning'],
            data['warning_message'], data['curl_command'], data['timestamp'],
            data['raw_logs'], data['metadata']
        )
        return self.db.execute(sql, params)
    
    def create_batch(self, requests: list[ParsedRequestRecord]) -> int:
        """批量创建请求记录"""
        if not requests:
            return 0
        
        sql = """
            INSERT INTO parsed_requests 
            (task_id, request_id, method, url, category, headers, body, query_params,
             http_status, response_time_ms, response_body, has_error, error_message,
             has_warning, warning_message, curl_command, timestamp, raw_logs, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_list = []
        for req in requests:
            data = req.to_dict()
            params_list.append((
                data['task_id'], data['request_id'], data['method'], data['url'],
                data['category'], data['headers'], data['body'], data['query_params'],
                data['http_status'], data['response_time_ms'], data['response_body'],
                data['has_error'], data['error_message'], data['has_warning'],
                data['warning_message'], data['curl_command'], data['timestamp'],
                data['raw_logs'], data['metadata']
            ))
        
        return self.db.execute_many(sql, params_list)
    
    def get_by_task(self, task_id: str, limit: int = 1000, offset: int = 0) -> list[ParsedRequestRecord]:
        """获取任务的所有请求"""
        return self._get_all_by_field("task_id", task_id, "id", limit, offset)
    
    def get_by_category(self, task_id: str, category: str) -> list[ParsedRequestRecord]:
        """按分类获取请求"""
        sql = "SELECT * FROM parsed_requests WHERE task_id = %s AND category = %s"
        rows = self.db.fetch_all(sql, (task_id, category))
        return [ParsedRequestRecord.from_dict(row) for row in rows]
    
    def get_errors(self, task_id: str) -> list[ParsedRequestRecord]:
        """获取错误请求"""
        sql = "SELECT * FROM parsed_requests WHERE task_id = %s AND has_error = 1"
        rows = self.db.fetch_all(sql, (task_id,))
        return [ParsedRequestRecord.from_dict(row) for row in rows]
    
    def count_by_task(self, task_id: str) -> int:
        """统计任务的请求数"""
        return self.count("task_id = %s", (task_id,))


class ReportRepository(BaseRepository[AnalysisReport]):
    """报告仓库"""
    
    table_name = "analysis_reports"
    model_class = AnalysisReport
    
    def create(self, report: AnalysisReport) -> int:
        """创建报告"""
        data = report.to_dict()
        sql = """
            INSERT INTO analysis_reports 
            (task_id, report_type, title, content, format, statistics, 
             issues, recommendations, severity, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['task_id'], data['report_type'], data['title'], data['content'],
            data['format'], data['statistics'], data['issues'], data['recommendations'],
            data['severity'], data['metadata']
        )
        return self.db.execute(sql, params)
    
    def get_by_task(self, task_id: str, report_type: ReportType | None = None) -> list[AnalysisReport]:
        """获取任务的报告"""
        if report_type:
            sql = "SELECT * FROM analysis_reports WHERE task_id = %s AND report_type = %s ORDER BY created_at DESC"
            rows = self.db.fetch_all(sql, (task_id, report_type.value))
        else:
            sql = "SELECT * FROM analysis_reports WHERE task_id = %s ORDER BY created_at DESC"
            rows = self.db.fetch_all(sql, (task_id,))
        return [AnalysisReport.from_dict(row) for row in rows]
    
    def get_latest(self, task_id: str, report_type: ReportType) -> AnalysisReport | None:
        """获取最新报告"""
        sql = """
            SELECT * FROM analysis_reports 
            WHERE task_id = %s AND report_type = %s 
            ORDER BY created_at DESC LIMIT 1
        """
        row = self.db.fetch_one(sql, (task_id, report_type.value))
        return AnalysisReport.from_dict(row) if row else None


