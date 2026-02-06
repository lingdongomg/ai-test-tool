"""
数据仓库层
该文件内容使用AI生成，注意识别准确性
重构版本：添加泛型基类，减少重复代码
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from .connection import DatabaseManager, get_db_manager
from .models import (
    BaseModel,
    AnalysisTask, TaskStatus, TaskType,
    ParsedRequestRecord,
    TestCaseRecord, TestCaseHistory, ChangeType,
    TestResultRecord,
    TestExecution, ExecutionStatus,
    AnalysisReport, ReportType,
    ApiTag, ApiEndpoint,
    TestScenario, ScenarioStep, ScenarioExecution, StepResult,
    KnowledgeEntry, KnowledgeHistory, KnowledgeUsage,
    KnowledgeType, KnowledgeStatus, KnowledgeSource,
    AIInsight, InsightSeverity,
    ProductionRequest, RequestSource,
    HealthCheckExecution, HealthCheckResult, HealthCheckStatus,
)
from ..utils.sql_security import (
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


class TestCaseRepository(BaseRepository[TestCaseRecord]):
    """测试用例仓库"""
    
    table_name = "test_cases"
    model_class = TestCaseRecord
    
    def create(self, test_case: TestCaseRecord) -> int:
        """创建测试用例"""
        data = test_case.to_dict()
        sql = """
            INSERT INTO test_cases 
            (case_id, endpoint_id, name, description, category, priority, method, url,
             headers, body, query_params, expected_status_code, expected_response,
             assertions, max_response_time_ms, tags, is_enabled, is_ai_generated,
             source_task_id, version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['case_id'], data['endpoint_id'], data['name'], data['description'],
            data['category'], data['priority'], data['method'], data['url'],
            data['headers'], data['body'], data['query_params'],
            data['expected_status_code'], data['expected_response'],
            data['assertions'], data['max_response_time_ms'], data['tags'],
            data['is_enabled'], data['is_ai_generated'], data['source_task_id'],
            data['version']
        )
        return self.db.execute(sql, params)
    
    def create_batch(self, test_cases: list[TestCaseRecord]) -> int:
        """批量创建测试用例"""
        if not test_cases:
            return 0
        
        sql = """
            INSERT INTO test_cases 
            (case_id, endpoint_id, name, description, category, priority, method, url,
             headers, body, query_params, expected_status_code, expected_response,
             assertions, max_response_time_ms, tags, is_enabled, is_ai_generated,
             source_task_id, version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_list = []
        for tc in test_cases:
            data = tc.to_dict()
            params_list.append((
                data['case_id'], data['endpoint_id'], data['name'], data['description'],
                data['category'], data['priority'], data['method'], data['url'],
                data['headers'], data['body'], data['query_params'],
                data['expected_status_code'], data['expected_response'],
                data['assertions'], data['max_response_time_ms'], data['tags'],
                data['is_enabled'], data['is_ai_generated'], data['source_task_id'],
                data['version']
            ))
        
        return self.db.execute_many(sql, params_list)
    
    def get_by_endpoint(self, endpoint_id: str, enabled_only: bool = False) -> list[TestCaseRecord]:
        """获取接口的所有测试用例"""
        if enabled_only:
            sql = "SELECT * FROM test_cases WHERE endpoint_id = %s AND is_enabled = 1 ORDER BY id"
        else:
            sql = "SELECT * FROM test_cases WHERE endpoint_id = %s ORDER BY id"
        rows = self.db.fetch_all(sql, (endpoint_id,))
        return [TestCaseRecord.from_dict(row) for row in rows]
    
    def get_by_id(self, case_id: str) -> TestCaseRecord | None:
        """获取单个测试用例"""
        return self._get_by_field("case_id", case_id)
    
    def update(self, case_id: str, updates: dict[str, Any]) -> int:
        """更新测试用例"""
        if not updates:
            return 0

        updates['updated_at'] = datetime.now().isoformat()
        # 验证字段名
        validated_fields = validate_fields_for_update(updates.keys(), self.table_name)
        set_clauses = [f"{key} = %s" for key in validated_fields]
        params = [updates[key] for key in validated_fields] + [case_id]

        sql = f"UPDATE test_cases SET {', '.join(set_clauses)} WHERE case_id = %s"
        return self.db.execute(sql, tuple(params))
    
    def set_enabled(self, case_id: str, enabled: bool) -> int:
        """设置用例启用状态"""
        return self.update(case_id, {'is_enabled': enabled})
    
    def delete(self, case_id: str) -> int:
        """删除测试用例"""
        return self.delete_by_field("case_id", case_id)
    
    def increment_version(self, case_id: str) -> int:
        """增加版本号"""
        sql = "UPDATE test_cases SET version = version + 1, updated_at = %s WHERE case_id = %s"
        return self.db.execute(sql, (datetime.now().isoformat(), case_id))


class TestCaseHistoryRepository(BaseRepository[TestCaseHistory]):
    """测试用例历史仓库"""
    
    table_name = "test_case_history"
    model_class = TestCaseHistory
    
    def create(self, history: TestCaseHistory) -> int:
        """创建历史记录"""
        data = history.to_dict()
        sql = """
            INSERT INTO test_case_history 
            (case_id, version, change_type, change_summary, snapshot, changed_fields, changed_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['case_id'], data['version'], data['change_type'],
            data['change_summary'], data['snapshot'], data['changed_fields'],
            data['changed_by']
        )
        return self.db.execute(sql, params)
    
    def get_by_case(self, case_id: str, limit: int = 50) -> list[TestCaseHistory]:
        """获取用例的所有历史记录"""
        sql = """
            SELECT * FROM test_case_history 
            WHERE case_id = %s 
            ORDER BY version DESC 
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (case_id, limit))
        return [TestCaseHistory.from_dict(row) for row in rows]
    
    def get_version(self, case_id: str, version: int) -> TestCaseHistory | None:
        """获取指定版本"""
        sql = "SELECT * FROM test_case_history WHERE case_id = %s AND version = %s"
        row = self.db.fetch_one(sql, (case_id, version))
        return TestCaseHistory.from_dict(row) if row else None
    
    def get_latest_version(self, case_id: str) -> int:
        """获取最新版本号"""
        sql = "SELECT MAX(version) as max_version FROM test_case_history WHERE case_id = %s"
        row = self.db.fetch_one(sql, (case_id,))
        return row['max_version'] if row and row['max_version'] else 0


class TestResultRepository(BaseRepository[TestResultRecord]):
    """测试结果仓库"""
    
    table_name = "test_results"
    model_class = TestResultRecord
    
    def create(self, result: TestResultRecord) -> int:
        """创建测试结果"""
        data = result.to_dict()
        sql = """
            INSERT INTO test_results 
            (case_id, execution_id, result_type, status, actual_status_code,
             actual_response_time_ms, actual_response_body, actual_headers,
             error_message, assertion_results, ai_analysis, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['case_id'], data['execution_id'], data['result_type'], data['status'],
            data['actual_status_code'], data['actual_response_time_ms'],
            data['actual_response_body'], data['actual_headers'],
            data['error_message'], data['assertion_results'], data['ai_analysis'],
            data['executed_at']
        )
        return self.db.execute(sql, params)
    
    def create_batch(self, results: list[TestResultRecord]) -> int:
        """批量创建测试结果"""
        if not results:
            return 0
        
        sql = """
            INSERT INTO test_results 
            (case_id, execution_id, result_type, status, actual_status_code,
             actual_response_time_ms, actual_response_body, actual_headers,
             error_message, assertion_results, ai_analysis, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params_list = []
        for r in results:
            data = r.to_dict()
            params_list.append((
                data['case_id'], data['execution_id'], data['result_type'], data['status'],
                data['actual_status_code'], data['actual_response_time_ms'],
                data['actual_response_body'], data['actual_headers'],
                data['error_message'], data['assertion_results'], data['ai_analysis'],
                data['executed_at']
            ))
        
        return self.db.execute_many(sql, params_list)
    
    def get_by_execution(self, execution_id: str) -> list[TestResultRecord]:
        """获取执行批次的所有结果"""
        return self._get_all_by_field("execution_id", execution_id, "id", 10000, 0)
    
    def get_latest_by_case(self, case_id: str) -> TestResultRecord | None:
        """获取用例的最新结果"""
        sql = "SELECT * FROM test_results WHERE case_id = %s ORDER BY executed_at DESC LIMIT 1"
        row = self.db.fetch_one(sql, (case_id,))
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


class TestExecutionRepository(BaseRepository[TestExecution]):
    """测试执行仓库"""
    
    table_name = "test_executions"
    model_class = TestExecution
    
    def create(self, execution: TestExecution) -> int:
        """创建执行记录"""
        data = execution.to_dict()
        sql = """
            INSERT INTO test_executions 
            (execution_id, name, description, execution_type, trigger_type, status,
             base_url, environment, variables, headers, total_cases, passed_cases,
             failed_cases, error_cases, skipped_cases, duration_ms, error_message,
             started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['execution_id'], data['name'], data['description'],
            data['execution_type'], data['trigger_type'], data['status'],
            data['base_url'], data['environment'], data['variables'], data['headers'],
            data['total_cases'], data['passed_cases'], data['failed_cases'],
            data['error_cases'], data['skipped_cases'], data['duration_ms'],
            data['error_message'], data['started_at'], data['completed_at']
        )
        return self.db.execute(sql, params)
    
    def get_by_id(self, execution_id: str) -> TestExecution | None:
        """根据ID获取执行记录"""
        return self._get_by_field("execution_id", execution_id)
    
    def update_status(self, execution_id: str, status: ExecutionStatus, error_message: str = "") -> int:
        """更新执行状态"""
        now = datetime.now().isoformat()
        if status == ExecutionStatus.RUNNING:
            sql = "UPDATE test_executions SET status = %s, started_at = %s WHERE execution_id = %s"
            return self.db.execute(sql, (status.value, now, execution_id))
        elif status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            sql = "UPDATE test_executions SET status = %s, error_message = %s, completed_at = %s WHERE execution_id = %s"
            return self.db.execute(sql, (status.value, error_message, now, execution_id))
        else:
            sql = "UPDATE test_executions SET status = %s WHERE execution_id = %s"
            return self.db.execute(sql, (status.value, execution_id))
    
    def update_counts(self, execution_id: str, **counts: int) -> int:
        """更新执行计数"""
        if not counts:
            return 0
        
        valid_fields = ['total_cases', 'passed_cases', 'failed_cases', 'error_cases', 'skipped_cases', 'duration_ms']
        updates = {k: v for k, v in counts.items() if k in valid_fields}
        
        if not updates:
            return 0
        
        set_clauses = [f"{key} = %s" for key in updates.keys()]
        params = list(updates.values()) + [execution_id]
        
        sql = f"UPDATE test_executions SET {', '.join(set_clauses)} WHERE execution_id = %s"
        return self.db.execute(sql, tuple(params))


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

class TestScenarioRepository(BaseRepository[TestScenario]):
    """测试场景仓库"""
    
    table_name = "test_scenarios"
    model_class = TestScenario
    
    def create(self, scenario: TestScenario) -> int:
        """创建场景"""
        data = scenario.to_dict()
        sql = """
            INSERT INTO test_scenarios 
            (scenario_id, name, description, tags, variables, setup_hooks,
             teardown_hooks, retry_on_failure, max_retries, is_enabled, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['scenario_id'], data['name'], data['description'], data['tags'],
            data['variables'], data['setup_hooks'], data['teardown_hooks'],
            data['retry_on_failure'], data['max_retries'], data['is_enabled'],
            data['created_by']
        )
        return self.db.execute(sql, params)
    
    def get_by_id(self, scenario_id: str) -> TestScenario | None:
        """根据ID获取场景"""
        return self._get_by_field("scenario_id", scenario_id)
    
    def delete(self, scenario_id: str) -> int:
        """删除场景"""
        return self.delete_by_field("scenario_id", scenario_id)


class ScenarioStepRepository(BaseRepository[ScenarioStep]):
    """场景步骤仓库"""
    
    table_name = "scenario_steps"
    model_class = ScenarioStep
    
    def create(self, step: ScenarioStep) -> int:
        """创建步骤"""
        data = step.to_dict()
        sql = """
            INSERT INTO scenario_steps 
            (scenario_id, step_id, step_order, name, description, step_type,
             method, url, headers, body, query_params, extractions, assertions,
             wait_time_ms, condition, loop_config, timeout_ms, continue_on_failure, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['scenario_id'], data['step_id'], data['step_order'], data['name'],
            data['description'], data['step_type'], data['method'], data['url'],
            data['headers'], data['body'], data['query_params'], data['extractions'],
            data['assertions'], data['wait_time_ms'], data['condition'], data['loop_config'],
            data['timeout_ms'], data['continue_on_failure'], data['is_enabled']
        )
        return self.db.execute(sql, params)
    
    def get_by_scenario(self, scenario_id: str) -> list[ScenarioStep]:
        """获取场景的所有步骤"""
        sql = "SELECT * FROM scenario_steps WHERE scenario_id = %s ORDER BY step_order"
        rows = self.db.fetch_all(sql, (scenario_id,))
        return [ScenarioStep.from_dict(row) for row in rows]


class ScenarioExecutionRepository(BaseRepository[ScenarioExecution]):
    """场景执行仓库"""
    
    table_name = "scenario_executions"
    model_class = ScenarioExecution
    
    def create(self, execution: ScenarioExecution) -> int:
        """创建执行记录"""
        data = execution.to_dict()
        sql = """
            INSERT INTO scenario_executions 
            (execution_id, scenario_id, trigger_type, status, base_url, environment,
             variables, total_steps, passed_steps, failed_steps, skipped_steps,
             duration_ms, error_message, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['execution_id'], data['scenario_id'], data['trigger_type'], data['status'],
            data['base_url'], data['environment'], data['variables'], data['total_steps'],
            data['passed_steps'], data['failed_steps'], data['skipped_steps'],
            data['duration_ms'], data['error_message'], data['started_at'], data['completed_at']
        )
        return self.db.execute(sql, params)
    
    def get_by_id(self, execution_id: str) -> ScenarioExecution | None:
        """根据ID获取执行记录"""
        return self._get_by_field("execution_id", execution_id)
    
    def get_by_scenario(self, scenario_id: str, limit: int = 100) -> list[ScenarioExecution]:
        """获取场景的执行历史"""
        sql = """
            SELECT * FROM scenario_executions 
            WHERE scenario_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (scenario_id, limit))
        return [ScenarioExecution.from_dict(row) for row in rows]


class StepResultRepository(BaseRepository[StepResult]):
    """步骤结果仓库"""
    
    table_name = "step_results"
    model_class = StepResult
    
    def create(self, result: StepResult) -> int:
        """创建步骤结果"""
        data = result.to_dict()
        sql = """
            INSERT INTO step_results 
            (execution_id, step_id, step_order, status, request_url, request_headers,
             request_body, response_status_code, response_headers, response_body,
             response_time_ms, extracted_variables, assertion_results, error_message, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['execution_id'], data['step_id'], data['step_order'], data['status'],
            data['request_url'], data['request_headers'], data['request_body'],
            data['response_status_code'], data['response_headers'], data['response_body'],
            data['response_time_ms'], data['extracted_variables'], data['assertion_results'],
            data['error_message'], data['executed_at']
        )
        return self.db.execute(sql, params)
    
    def get_by_execution(self, execution_id: str) -> list[StepResult]:
        """获取执行的所有步骤结果"""
        sql = "SELECT * FROM step_results WHERE execution_id = %s ORDER BY step_order"
        rows = self.db.fetch_all(sql, (execution_id,))
        return [StepResult.from_dict(row) for row in rows]


# =====================================================
# 执行-用例关联仓库
# =====================================================

class ExecutionCaseRepository(BaseRepository):
    """
    执行-用例关联仓库

    管理测试执行批次与测试用例的多对多关系。
    """

    table_name = "execution_cases"

    def add_cases(self, execution_id: str, case_ids: list[str]) -> int:
        """
        批量添加用例到执行批次

        Args:
            execution_id: 执行批次ID
            case_ids: 用例ID列表

        Returns:
            成功插入的记录数
        """
        if not case_ids:
            return 0

        sql = """
            INSERT OR IGNORE INTO execution_cases
            (execution_id, case_id, order_index)
            VALUES (%s, %s, %s)
        """
        params_list = [
            (execution_id, case_id, idx)
            for idx, case_id in enumerate(case_ids)
        ]
        return self.db.execute_many(sql, params_list)

    def get_case_ids(self, execution_id: str) -> list[str]:
        """
        获取执行批次的所有用例ID

        Args:
            execution_id: 执行批次ID

        Returns:
            按顺序排列的用例ID列表
        """
        sql = """
            SELECT case_id FROM execution_cases
            WHERE execution_id = %s
            ORDER BY order_index
        """
        rows = self.db.fetch_all(sql, (execution_id,))
        return [row['case_id'] for row in rows]

    def get_cases_with_details(self, execution_id: str) -> list[TestCaseRecord]:
        """
        获取执行批次的所有用例（含详情）

        Args:
            execution_id: 执行批次ID

        Returns:
            按顺序排列的测试用例列表
        """
        sql = """
            SELECT tc.* FROM test_cases tc
            JOIN execution_cases ec ON tc.case_id = ec.case_id
            WHERE ec.execution_id = %s
            ORDER BY ec.order_index
        """
        rows = self.db.fetch_all(sql, (execution_id,))
        return [TestCaseRecord.from_dict(row) for row in rows]

    def remove_case(self, execution_id: str, case_id: str) -> int:
        """移除执行批次中的指定用例"""
        sql = "DELETE FROM execution_cases WHERE execution_id = %s AND case_id = %s"
        return self.db.execute(sql, (execution_id, case_id))

    def remove_all_cases(self, execution_id: str) -> int:
        """移除执行批次中的所有用例"""
        sql = "DELETE FROM execution_cases WHERE execution_id = %s"
        return self.db.execute(sql, (execution_id,))

    def count_cases(self, execution_id: str) -> int:
        """统计执行批次的用例数"""
        return self.count("execution_id = %s", (execution_id,))

    def get_executions_for_case(self, case_id: str, limit: int = 100) -> list[str]:
        """获取包含指定用例的所有执行批次ID"""
        sql = """
            SELECT execution_id FROM execution_cases
            WHERE case_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        rows = self.db.fetch_all(sql, (case_id, limit))
        return [row['execution_id'] for row in rows]


# =====================================================
# 兼容性别名（保持向后兼容）
# =====================================================

# 为旧代码提供兼容性
TestCaseVersionRepository = TestCaseHistoryRepository
TestCaseChangeLogRepository = TestCaseHistoryRepository


# =====================================================
# 知识库仓库
# 该文件内容使用AI生成，注意识别准确性
# =====================================================

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
            data['insight_id'], data['insight_type'], data['title'],
            data['description'], data['severity'], data['confidence'],
            data['details'], data['recommendations'],
            data['is_resolved'], data['resolved_at']
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
        offset: int = 0
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
        return {row['severity']: row['count'] for row in rows}

    def search(
        self,
        keyword: str | None = None,
        severity: InsightSeverity | None = None,
        insight_type: str | None = None,
        is_resolved: bool | None = None,
        limit: int = 100,
        offset: int = 0
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
        page_size: int = 20
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
        total = count_result['count'] if count_result else 0

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
        stats = self.db.fetch_one("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) as unresolved,
                SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low
            FROM ai_insights
        """)

        # 按类型统计
        type_stats = self.db.fetch_all("""
            SELECT
                insight_type,
                COUNT(*) as count
            FROM ai_insights
            GROUP BY insight_type
            ORDER BY count DESC
        """)

        return {
            'total': stats['total'] if stats else 0,
            'unresolved': stats['unresolved'] if stats else 0,
            'by_severity': {
                'high': stats['high'] if stats else 0,
                'medium': stats['medium'] if stats else 0,
                'low': stats['low'] if stats else 0
            },
            'by_type': [
                {'type': t['insight_type'], 'count': t['count']}
                for t in type_stats
            ]
        }

    def get_by_types(
        self,
        types: list[str],
        is_resolved: bool | None = None,
        page: int = 1,
        page_size: int = 20
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
        total = count_result['count'] if count_result else 0

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
    allowed_sort_fields = frozenset({"id", "created_at", "updated_at", "method", "last_check_at"})

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
            data['request_id'], data['method'], data['url'],
            data['headers'], data['body'], data['query_params'],
            data['expected_status_code'], data['expected_response_pattern'],
            data['source'], data['source_task_id'], data['tags'],
            data['is_enabled'], data['last_check_at'],
            data['last_check_status'], data['consecutive_failures']
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

        updates['updated_at'] = datetime.now().isoformat()
        validated_fields = validate_fields_for_update(updates.keys(), self.table_name)
        set_clauses = [f"{key} = %s" for key in validated_fields]
        params = [updates[key] for key in validated_fields] + [request_id]

        sql = f"UPDATE production_requests SET {', '.join(set_clauses)} WHERE request_id = %s"
        return self.db.execute(sql, tuple(params))

    def update_check_status(
        self,
        request_id: str,
        status: str,
        increment_failures: bool = False
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
        return self.update(request_id, {'is_enabled': 1 if enabled else 0})

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
        return {row['status'] or 'unknown': row['count'] for row in rows}

    def search_paginated(
        self,
        tag: str | None = None,
        is_enabled: bool | None = None,
        last_status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[ProductionRequest], int]:
        """
        分页搜索监控请求

        Returns:
            元组: (请求列表, 总数)
        """
        from ..utils.sql_security import build_safe_like

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
        total = count_result['count'] if count_result else 0

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
        stats = self.db.fetch_one("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled,
                SUM(CASE WHEN last_check_status = 'healthy' THEN 1 ELSE 0 END) as healthy,
                SUM(CASE WHEN last_check_status = 'unhealthy' THEN 1 ELSE 0 END) as unhealthy,
                SUM(CASE WHEN consecutive_failures >= 3 THEN 1 ELSE 0 END) as critical
            FROM production_requests
        """)

        total = stats['total'] if stats else 0
        healthy = stats['healthy'] if stats else 0

        return {
            'total': total,
            'enabled': stats['enabled'] if stats else 0,
            'healthy': healthy,
            'unhealthy': stats['unhealthy'] if stats else 0,
            'critical': stats['critical'] if stats else 0,
            'health_rate': round(healthy / total * 100, 2) if total > 0 else 0
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
            data['execution_id'], data['base_url'], data['total_requests'],
            data['healthy_count'], data['unhealthy_count'], data['status'],
            data['trigger_type'], data['started_at'], data['completed_at']
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
        unhealthy_count: int | None = None
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
        page_size: int = 20
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
        count_sql = f"SELECT COUNT(*) as count FROM health_check_executions {where_clause}"
        count_result = self.db.fetch_one(count_sql, tuple(params) if params else None)
        total = count_result['count'] if count_result else 0

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
        return [HealthCheckExecution.from_dict(row) for row in rows]


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
            data['execution_id'], data['request_id'], data['success'],
            data['status_code'], data['response_time_ms'], data['response_body'],
            data['error_message'], data['ai_analysis'], data['checked_at']
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
            params_list.append((
                data['execution_id'], data['request_id'], data['success'],
                data['status_code'], data['response_time_ms'], data['response_body'],
                data['error_message'], data['ai_analysis'], data['checked_at']
            ))
        return self.db.execute_many(sql, params_list)

    def get_by_execution(self, execution_id: str) -> list[HealthCheckResult]:
        """获取执行批次的所有结果"""
        sql = "SELECT * FROM health_check_results WHERE execution_id = %s ORDER BY id"
        rows = self.db.fetch_all(sql, (execution_id,))
        return [HealthCheckResult.from_dict(row) for row in rows]

    def get_by_request(self, request_id: str, limit: int = 100) -> list[HealthCheckResult]:
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
        return row if row else {'total': 0, 'success_count': 0, 'avg_response_time': 0}

    def delete_by_execution(self, execution_id: str) -> int:
        """删除执行批次的所有结果"""
        return self.delete_by_field("execution_id", execution_id)

    def get_by_execution_with_request_details(self, execution_id: str) -> list[dict[str, Any]]:
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
        stats = self.db.fetch_one("""
            SELECT
                COUNT(*) as total_checks,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(response_time_ms) as avg_response_time
            FROM health_check_results
            WHERE DATE(checked_at) = DATE('now')
        """)

        return {
            'total_checks': stats['total_checks'] if stats else 0,
            'success_count': stats['success_count'] if stats else 0,
            'avg_response_time': round(stats['avg_response_time'] or 0, 2) if stats else 0
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
        rows = self.db.fetch_all(sql, (f'-{days} days',))
        return [
            {
                'date': str(t['date']),
                'total': t['total'],
                'success': t['success'],
                'success_rate': round(t['success'] / t['total'] * 100, 2) if t['total'] > 0 else 0,
                'avg_time': round(t['avg_time'] or 0, 2)
            }
            for t in rows
        ]


# =====================================================
# 对话会话仓库
# 该文件内容使用AI生成，注意识别准确性
# =====================================================

class ChatSessionRepository:
    """对话会话仓库"""

    table_name = "chat_sessions"

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db or get_db_manager()

    def create(self, session_id: str, title: str = "", context: dict | None = None) -> str:
        """创建会话"""
        import json
        sql = """
            INSERT INTO chat_sessions (session_id, title, context)
            VALUES (%s, %s, %s)
        """
        context_str = json.dumps(context or {}, ensure_ascii=False)
        self.db.execute(sql, (session_id, title, context_str))
        return session_id

    def get_by_id(self, session_id: str) -> dict | None:
        """根据ID获取会话"""
        sql = "SELECT * FROM chat_sessions WHERE session_id = %s"
        return self.db.fetch_one(sql, (session_id,))

    def update_title(self, session_id: str, title: str) -> int:
        """更新会话标题"""
        sql = """
            UPDATE chat_sessions
            SET title = %s, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = %s
        """
        return self.db.execute(sql, (title, session_id))

    def increment_message_count(self, session_id: str) -> int:
        """增加消息计数"""
        sql = """
            UPDATE chat_sessions
            SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = %s
        """
        return self.db.execute(sql, (session_id,))

    def list_recent(self, limit: int = 20) -> list[dict]:
        """获取最近的会话列表"""
        sql = """
            SELECT * FROM chat_sessions
            ORDER BY updated_at DESC
            LIMIT %s
        """
        return self.db.fetch_all(sql, (limit,))

    def delete(self, session_id: str) -> int:
        """删除会话"""
        sql = "DELETE FROM chat_sessions WHERE session_id = %s"
        return self.db.execute(sql, (session_id,))


class ChatMessageRepository:
    """对话消息仓库"""

    table_name = "chat_messages"

    def __init__(self, db: DatabaseManager | None = None) -> None:
        self.db = db or get_db_manager()

    def create(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> str:
        """创建消息"""
        import json
        sql = """
            INSERT INTO chat_messages (message_id, session_id, role, content, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """
        metadata_str = json.dumps(metadata or {}, ensure_ascii=False)
        self.db.execute(sql, (message_id, session_id, role, content, metadata_str))
        return message_id

    def get_by_session(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict]:
        """获取会话的所有消息"""
        sql = """
            SELECT * FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s OFFSET %s
        """
        return self.db.fetch_all(sql, (session_id, limit, offset))

    def get_recent_by_session(self, session_id: str, limit: int = 10) -> list[dict]:
        """获取会话最近的N条消息（用于构建上下文）"""
        sql = """
            SELECT * FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        messages = self.db.fetch_all(sql, (session_id, limit))
        # 反转顺序使其按时间正序排列
        return list(reversed(messages))

    def count_by_session(self, session_id: str) -> int:
        """统计会话消息数量"""
        sql = "SELECT COUNT(*) as count FROM chat_messages WHERE session_id = %s"
        result = self.db.fetch_one(sql, (session_id,))
        return result['count'] if result else 0

    def delete_by_session(self, session_id: str) -> int:
        """删除会话的所有消息"""
        sql = "DELETE FROM chat_messages WHERE session_id = %s"
        return self.db.execute(sql, (session_id,))
