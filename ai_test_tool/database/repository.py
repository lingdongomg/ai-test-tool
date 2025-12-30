"""
数据仓库层
提供数据的CRUD操作
"""

from datetime import datetime
from typing import Any

from .connection import DatabaseManager, get_db_manager
from .models import (
    AnalysisTask, TaskStatus,
    ParsedRequestRecord,
    TestCaseRecord,
    TestResultRecord,
    AnalysisReport, ReportType,
    TestCaseVersion, TestCaseChangeLog, ChangeType
)


class BaseRepository:
    """仓库基类"""
    
    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        self.db = db_manager or get_db_manager()


class TaskRepository(BaseRepository):
    """任务仓库"""
    
    def create(self, task: AnalysisTask) -> int:
        """创建任务"""
        sql = """
            INSERT INTO analysis_tasks 
            (task_id, name, description, log_file_path, log_file_size, status, 
             total_lines, processed_lines, total_requests, total_test_cases,
             error_message, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            task.task_id, task.name, task.description, task.log_file_path,
            task.log_file_size, task.status.value, task.total_lines,
            task.processed_lines, task.total_requests, task.total_test_cases,
            task.error_message, task.started_at, task.completed_at
        )
        return self.db.execute(sql, params)
    
    def get_by_id(self, task_id: str) -> AnalysisTask | None:
        """根据ID获取任务"""
        sql = "SELECT * FROM analysis_tasks WHERE task_id = %s"
        row = self.db.fetch_one(sql, (task_id,))
        return AnalysisTask.from_dict(row) if row else None
    
    def get_all(self, limit: int = 100, offset: int = 0) -> list[AnalysisTask]:
        """获取所有任务"""
        sql = "SELECT * FROM analysis_tasks ORDER BY created_at DESC LIMIT %s OFFSET %s"
        rows = self.db.fetch_all(sql, (limit, offset))
        return [AnalysisTask.from_dict(row) for row in rows]
    
    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: str | None = None
    ) -> None:
        """更新任务状态"""
        if status == TaskStatus.RUNNING:
            sql = "UPDATE analysis_tasks SET status = %s, started_at = %s WHERE task_id = %s"
            self.db.execute(sql, (status.value, datetime.now(), task_id))
        elif status == TaskStatus.COMPLETED:
            sql = "UPDATE analysis_tasks SET status = %s, completed_at = %s WHERE task_id = %s"
            self.db.execute(sql, (status.value, datetime.now(), task_id))
        elif status == TaskStatus.FAILED:
            sql = "UPDATE analysis_tasks SET status = %s, error_message = %s, completed_at = %s WHERE task_id = %s"
            self.db.execute(sql, (status.value, error_message, datetime.now(), task_id))
        else:
            sql = "UPDATE analysis_tasks SET status = %s WHERE task_id = %s"
            self.db.execute(sql, (status.value, task_id))
    
    def update_progress(
        self,
        task_id: str,
        processed_lines: int,
        total_requests: int | None = None
    ) -> None:
        """更新处理进度"""
        if total_requests is not None:
            sql = "UPDATE analysis_tasks SET processed_lines = %s, total_requests = %s WHERE task_id = %s"
            self.db.execute(sql, (processed_lines, total_requests, task_id))
        else:
            sql = "UPDATE analysis_tasks SET processed_lines = %s WHERE task_id = %s"
            self.db.execute(sql, (processed_lines, task_id))
    
    def update_counts(
        self,
        task_id: str,
        total_requests: int | None = None,
        total_test_cases: int | None = None
    ) -> None:
        """更新计数"""
        updates: list[str] = []
        params: list[Any] = []
        if total_requests is not None:
            updates.append("total_requests = %s")
            params.append(total_requests)
        if total_test_cases is not None:
            updates.append("total_test_cases = %s")
            params.append(total_test_cases)
        
        if updates:
            sql = f"UPDATE analysis_tasks SET {', '.join(updates)} WHERE task_id = %s"
            params.append(task_id)
            self.db.execute(sql, tuple(params))
    
    def delete(self, task_id: str) -> None:
        """删除任务（级联删除相关数据）"""
        sql = "DELETE FROM analysis_tasks WHERE task_id = %s"
        self.db.execute(sql, (task_id,))


class RequestRepository(BaseRepository):
    """请求仓库"""
    
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
        params_list: list[tuple[Any, ...]] = []
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
    
    def get_by_task(
        self,
        task_id: str,
        limit: int = 1000,
        offset: int = 0
    ) -> list[ParsedRequestRecord]:
        """获取任务的所有请求"""
        sql = "SELECT * FROM parsed_requests WHERE task_id = %s ORDER BY id LIMIT %s OFFSET %s"
        rows = self.db.fetch_all(sql, (task_id, limit, offset))
        return [ParsedRequestRecord.from_dict(row) for row in rows]
    
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
        sql = "SELECT COUNT(*) as count FROM parsed_requests WHERE task_id = %s"
        result = self.db.fetch_one(sql, (task_id,))
        return result['count'] if result else 0


class TestCaseRepository(BaseRepository):
    """测试用例仓库"""
    
    def create(self, test_case: TestCaseRecord) -> int:
        """创建测试用例"""
        data = test_case.to_dict()
        sql = """
            INSERT INTO test_cases 
            (task_id, case_id, name, description, category, priority, method, url,
             headers, body, query_params, expected_status_code, expected_response,
             max_response_time_ms, tags, group_name, dependencies, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['task_id'], data['case_id'], data['name'], data['description'],
            data['category'], data['priority'], data['method'], data['url'],
            data['headers'], data['body'], data['query_params'],
            data['expected_status_code'], data['expected_response'],
            data['max_response_time_ms'], data['tags'], data['group_name'],
            data['dependencies'], data['is_enabled']
        )
        return self.db.execute(sql, params)
    
    def create_batch(self, test_cases: list[TestCaseRecord]) -> int:
        """批量创建测试用例"""
        if not test_cases:
            return 0
        
        sql = """
            INSERT INTO test_cases 
            (task_id, case_id, name, description, category, priority, method, url,
             headers, body, query_params, expected_status_code, expected_response,
             max_response_time_ms, tags, group_name, dependencies, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_list: list[tuple[Any, ...]] = []
        for tc in test_cases:
            data = tc.to_dict()
            params_list.append((
                data['task_id'], data['case_id'], data['name'], data['description'],
                data['category'], data['priority'], data['method'], data['url'],
                data['headers'], data['body'], data['query_params'],
                data['expected_status_code'], data['expected_response'],
                data['max_response_time_ms'], data['tags'], data['group_name'],
                data['dependencies'], data['is_enabled']
            ))
        
        return self.db.execute_many(sql, params_list)
    
    def get_by_task(
        self,
        task_id: str,
        enabled_only: bool = False
    ) -> list[TestCaseRecord]:
        """获取任务的所有测试用例"""
        if enabled_only:
            sql = "SELECT * FROM test_cases WHERE task_id = %s AND is_enabled = 1 ORDER BY id"
        else:
            sql = "SELECT * FROM test_cases WHERE task_id = %s ORDER BY id"
        rows = self.db.fetch_all(sql, (task_id,))
        return [TestCaseRecord.from_dict(row) for row in rows]
    
    def get_by_id(self, task_id: str, case_id: str) -> TestCaseRecord | None:
        """获取单个测试用例"""
        sql = "SELECT * FROM test_cases WHERE task_id = %s AND case_id = %s"
        row = self.db.fetch_one(sql, (task_id, case_id))
        return TestCaseRecord.from_dict(row) if row else None
    
    def get_by_group(self, task_id: str, group_name: str) -> list[TestCaseRecord]:
        """按分组获取测试用例"""
        sql = "SELECT * FROM test_cases WHERE task_id = %s AND group_name = %s ORDER BY id"
        rows = self.db.fetch_all(sql, (task_id, group_name))
        return [TestCaseRecord.from_dict(row) for row in rows]
    
    def get_by_tag(self, task_id: str, tag_name: str) -> list[TestCaseRecord]:
        """按标签获取测试用例"""
        sql = """
            SELECT tc.* FROM test_cases tc
            JOIN test_case_tags tct ON tc.task_id = tct.task_id AND tc.case_id = tct.case_id
            WHERE tc.task_id = %s AND tct.tag_name = %s
            ORDER BY tc.id
        """
        rows = self.db.fetch_all(sql, (task_id, tag_name))
        return [TestCaseRecord.from_dict(row) for row in rows]
    
    def update(self, task_id: str, case_id: str, updates: dict[str, Any]) -> int:
        """更新测试用例"""
        if not updates:
            return 0
        
        set_clauses: list[str] = []
        params: list[Any] = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            params.append(value)
        
        sql = f"UPDATE test_cases SET {', '.join(set_clauses)} WHERE task_id = %s AND case_id = %s"
        params.extend([task_id, case_id])
        return self.db.execute(sql, tuple(params))
    
    def set_enabled(self, task_id: str, case_id: str, enabled: bool) -> int:
        """设置用例启用状态"""
        sql = "UPDATE test_cases SET is_enabled = %s WHERE task_id = %s AND case_id = %s"
        return self.db.execute(sql, (enabled, task_id, case_id))
    
    def set_group(self, task_id: str, case_id: str, group_name: str) -> int:
        """设置用例分组"""
        sql = "UPDATE test_cases SET group_name = %s WHERE task_id = %s AND case_id = %s"
        return self.db.execute(sql, (group_name, task_id, case_id))
    
    def add_tag(self, task_id: str, case_id: str, tag_name: str) -> int:
        """添加标签"""
        sql = "INSERT IGNORE INTO test_case_tags (task_id, case_id, tag_name) VALUES (%s, %s, %s)"
        return self.db.execute(sql, (task_id, case_id, tag_name))
    
    def remove_tag(self, task_id: str, case_id: str, tag_name: str) -> int:
        """移除标签"""
        sql = "DELETE FROM test_case_tags WHERE task_id = %s AND case_id = %s AND tag_name = %s"
        return self.db.execute(sql, (task_id, case_id, tag_name))
    
    def get_tags(self, task_id: str, case_id: str) -> list[str]:
        """获取用例的所有标签"""
        sql = "SELECT tag_name FROM test_case_tags WHERE task_id = %s AND case_id = %s"
        rows = self.db.fetch_all(sql, (task_id, case_id))
        return [row['tag_name'] for row in rows]
    
    def delete(self, task_id: str, case_id: str) -> int:
        """删除测试用例"""
        sql = "DELETE FROM test_cases WHERE task_id = %s AND case_id = %s"
        return self.db.execute(sql, (task_id, case_id))


class TestResultRepository(BaseRepository):
    """测试结果仓库"""
    
    def create(self, result: TestResultRecord) -> int:
        """创建测试结果"""
        data = result.to_dict()
        sql = """
            INSERT INTO test_results 
            (task_id, case_id, execution_id, status, actual_status_code,
             actual_response_time_ms, actual_response_body, actual_headers,
             error_message, validation_results, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['task_id'], data['case_id'], data['execution_id'], data['status'],
            data['actual_status_code'], data['actual_response_time_ms'],
            data['actual_response_body'], data['actual_headers'],
            data['error_message'], data['validation_results'], data['executed_at']
        )
        return self.db.execute(sql, params)
    
    def create_batch(self, results: list[TestResultRecord]) -> int:
        """批量创建测试结果"""
        if not results:
            return 0
        
        sql = """
            INSERT INTO test_results 
            (task_id, case_id, execution_id, status, actual_status_code,
             actual_response_time_ms, actual_response_body, actual_headers,
             error_message, validation_results, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_list: list[tuple[Any, ...]] = []
        for r in results:
            data = r.to_dict()
            params_list.append((
                data['task_id'], data['case_id'], data['execution_id'], data['status'],
                data['actual_status_code'], data['actual_response_time_ms'],
                data['actual_response_body'], data['actual_headers'],
                data['error_message'], data['validation_results'], data['executed_at']
            ))
        
        return self.db.execute_many(sql, params_list)
    
    def get_by_execution(self, execution_id: str) -> list[TestResultRecord]:
        """获取执行批次的所有结果"""
        sql = "SELECT * FROM test_results WHERE execution_id = %s ORDER BY id"
        rows = self.db.fetch_all(sql, (execution_id,))
        return [TestResultRecord.from_dict(row) for row in rows]
    
    def get_by_task(self, task_id: str, limit: int = 1000) -> list[TestResultRecord]:
        """获取任务的所有结果"""
        sql = "SELECT * FROM test_results WHERE task_id = %s ORDER BY executed_at DESC LIMIT %s"
        rows = self.db.fetch_all(sql, (task_id, limit))
        return [TestResultRecord.from_dict(row) for row in rows]
    
    def get_latest_by_case(
        self,
        task_id: str,
        case_id: str
    ) -> TestResultRecord | None:
        """获取用例的最新结果"""
        sql = """
            SELECT * FROM test_results 
            WHERE task_id = %s AND case_id = %s 
            ORDER BY executed_at DESC LIMIT 1
        """
        row = self.db.fetch_one(sql, (task_id, case_id))
        return TestResultRecord.from_dict(row) if row else None
    
    def get_statistics(self, execution_id: str) -> dict[str, int]:
        """获取执行统计"""
        sql = """
            SELECT status, COUNT(*) as count 
            FROM test_results 
            WHERE execution_id = %s 
            GROUP BY status
        """
        rows = self.db.fetch_all(sql, (execution_id,))
        return {row['status']: row['count'] for row in rows}


class ReportRepository(BaseRepository):
    """报告仓库"""
    
    def create(self, report: AnalysisReport) -> int:
        """创建报告"""
        data = report.to_dict()
        sql = """
            INSERT INTO analysis_reports 
            (task_id, report_type, title, content, format, statistics, issues, recommendations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['task_id'], data['report_type'], data['title'], data['content'],
            data['format'], data['statistics'], data['issues'], data['recommendations']
        )
        return self.db.execute(sql, params)
    
    def get_by_task(
        self,
        task_id: str,
        report_type: ReportType | None = None
    ) -> list[AnalysisReport]:
        """获取任务的报告"""
        if report_type:
            sql = "SELECT * FROM analysis_reports WHERE task_id = %s AND report_type = %s ORDER BY created_at DESC"
            rows = self.db.fetch_all(sql, (task_id, report_type.value))
        else:
            sql = "SELECT * FROM analysis_reports WHERE task_id = %s ORDER BY created_at DESC"
            rows = self.db.fetch_all(sql, (task_id,))
        return [AnalysisReport.from_dict(row) for row in rows]
    
    def get_latest(
        self,
        task_id: str,
        report_type: ReportType
    ) -> AnalysisReport | None:
        """获取最新报告"""
        sql = """
            SELECT * FROM analysis_reports 
            WHERE task_id = %s AND report_type = %s 
            ORDER BY created_at DESC LIMIT 1
        """
        row = self.db.fetch_one(sql, (task_id, report_type.value))
        return AnalysisReport.from_dict(row) if row else None


class TestCaseVersionRepository(BaseRepository):
    """测试用例版本仓库"""
    
    def create(self, version: TestCaseVersion) -> int:
        """创建版本记录"""
        data = version.to_dict()
        sql = """
            INSERT INTO test_case_versions 
            (version_id, task_id, case_id, version_number, name, description,
             category, priority, method, url, headers, body, query_params,
             expected_status_code, expected_response, max_response_time_ms,
             tags, group_name, dependencies, change_type, change_summary,
             changed_fields, changed_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['version_id'], data['task_id'], data['case_id'], data['version_number'],
            data['name'], data['description'], data['category'], data['priority'],
            data['method'], data['url'], data['headers'], data['body'], data['query_params'],
            data['expected_status_code'], data['expected_response'], data['max_response_time_ms'],
            data['tags'], data['group_name'], data['dependencies'], data['change_type'],
            data['change_summary'], data['changed_fields'], data['changed_by']
        )
        return self.db.execute(sql, params)
    
    def get_by_case(
        self,
        task_id: str,
        case_id: str,
        limit: int = 50
    ) -> list[TestCaseVersion]:
        """获取用例的所有版本"""
        sql = """
            SELECT * FROM test_case_versions 
            WHERE task_id = %s AND case_id = %s 
            ORDER BY version_number DESC 
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (task_id, case_id, limit))
        return [TestCaseVersion.from_dict(row) for row in rows]
    
    def get_version(
        self,
        task_id: str,
        case_id: str,
        version_number: int
    ) -> TestCaseVersion | None:
        """获取指定版本"""
        sql = """
            SELECT * FROM test_case_versions 
            WHERE task_id = %s AND case_id = %s AND version_number = %s
        """
        row = self.db.fetch_one(sql, (task_id, case_id, version_number))
        return TestCaseVersion.from_dict(row) if row else None
    
    def get_by_version_id(self, version_id: str) -> TestCaseVersion | None:
        """根据版本ID获取版本"""
        sql = "SELECT * FROM test_case_versions WHERE version_id = %s"
        row = self.db.fetch_one(sql, (version_id,))
        return TestCaseVersion.from_dict(row) if row else None
    
    def get_latest_version_number(self, task_id: str, case_id: str) -> int:
        """获取最新版本号"""
        sql = """
            SELECT MAX(version_number) as max_version 
            FROM test_case_versions 
            WHERE task_id = %s AND case_id = %s
        """
        row = self.db.fetch_one(sql, (task_id, case_id))
        return row['max_version'] if row and row['max_version'] else 0
    
    def get_versions_count(self, task_id: str, case_id: str) -> int:
        """获取版本数量"""
        sql = """
            SELECT COUNT(*) as count FROM test_case_versions 
            WHERE task_id = %s AND case_id = %s
        """
        row = self.db.fetch_one(sql, (task_id, case_id))
        return row['count'] if row else 0
    
    def compare_versions(
        self,
        task_id: str,
        case_id: str,
        version1: int,
        version2: int
    ) -> dict[str, Any]:
        """比较两个版本的差异"""
        v1 = self.get_version(task_id, case_id, version1)
        v2 = self.get_version(task_id, case_id, version2)
        
        if not v1 or not v2:
            return {"error": "版本不存在"}
        
        # 比较字段
        fields_to_compare = [
            'name', 'description', 'category', 'priority', 'method', 'url',
            'headers', 'body', 'query_params', 'expected_status_code',
            'expected_response', 'max_response_time_ms', 'tags', 'group_name', 'dependencies'
        ]
        
        differences: list[dict[str, Any]] = []
        for field in fields_to_compare:
            val1 = getattr(v1, field)
            val2 = getattr(v2, field)
            
            # 枚举类型转换为值
            if hasattr(val1, 'value'):
                val1 = val1.value
            if hasattr(val2, 'value'):
                val2 = val2.value
            
            if val1 != val2:
                differences.append({
                    "field": field,
                    "version1_value": val1,
                    "version2_value": val2
                })
        
        return {
            "version1": version1,
            "version2": version2,
            "differences": differences,
            "has_changes": len(differences) > 0
        }


class TestCaseChangeLogRepository(BaseRepository):
    """测试用例变更日志仓库"""
    
    def create(self, log: TestCaseChangeLog) -> int:
        """创建变更日志"""
        data = log.to_dict()
        sql = """
            INSERT INTO test_case_change_logs 
            (task_id, case_id, version_id, change_type, change_summary,
             old_value, new_value, changed_by, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['task_id'], data['case_id'], data['version_id'], data['change_type'],
            data['change_summary'], data['old_value'], data['new_value'],
            data['changed_by'], data['ip_address'], data['user_agent']
        )
        return self.db.execute(sql, params)
    
    def get_by_case(
        self,
        task_id: str,
        case_id: str,
        limit: int = 100
    ) -> list[TestCaseChangeLog]:
        """获取用例的变更日志"""
        sql = """
            SELECT * FROM test_case_change_logs 
            WHERE task_id = %s AND case_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (task_id, case_id, limit))
        return [TestCaseChangeLog.from_dict(row) for row in rows]
    
    def get_by_task(
        self,
        task_id: str,
        limit: int = 500,
        offset: int = 0
    ) -> list[TestCaseChangeLog]:
        """获取任务的所有变更日志"""
        sql = """
            SELECT * FROM test_case_change_logs 
            WHERE task_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """
        rows = self.db.fetch_all(sql, (task_id, limit, offset))
        return [TestCaseChangeLog.from_dict(row) for row in rows]
    
    def get_by_change_type(
        self,
        task_id: str,
        change_type: ChangeType,
        limit: int = 100
    ) -> list[TestCaseChangeLog]:
        """按变更类型获取日志"""
        sql = """
            SELECT * FROM test_case_change_logs 
            WHERE task_id = %s AND change_type = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (task_id, change_type.value, limit))
        return [TestCaseChangeLog.from_dict(row) for row in rows]
