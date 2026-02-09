"""
场景相关 Repository：场景、步骤、执行、结果
"""

from datetime import datetime
from typing import Any

from .base import BaseRepository
from ..models import TestScenario, ScenarioStep, ScenarioExecution, StepResult


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

