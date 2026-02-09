"""
测试相关 Repository：用例、历史、结果、执行、执行关联
"""

from datetime import datetime
from typing import Any

from .base import BaseRepository
from ..models import (
    TestCaseRecord, TestCaseHistory, ChangeType,
    TestResultRecord,
    TestExecution, ExecutionStatus,
)
from ...utils.sql_security import validate_fields_for_update


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

