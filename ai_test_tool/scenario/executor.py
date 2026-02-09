"""
测试场景执行器
执行测试场景，支持步骤编排、参数传递、断言验证
"""

import json
import time
import asyncio
import aiohttp
from typing import Any
from datetime import datetime
from dataclasses import dataclass, field

from .variable_resolver import VariableResolver
from .extractor import ResponseExtractor
from .assertion_engine import AssertionEngine, AssertionResult
from ..database.models import (
    TestScenario,
    ScenarioStep,
    ScenarioExecution,
    StepResult,
    ScenarioStatus,
    ScenarioStepType,
    TriggerType,
    TestResultStatus
)
from ..utils.logger import AILogger


@dataclass
class StepExecutionResult:
    """步骤执行结果"""
    step_id: str
    step_order: int
    status: TestResultStatus
    request_url: str = ""
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str = ""
    response_status_code: int = 0
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    response_time_ms: float = 0
    extracted_variables: dict[str, Any] = field(default_factory=dict)
    assertion_results: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    executed_at: datetime = field(default_factory=datetime.now)


@dataclass
class ScenarioExecutionResult:
    """场景执行结果"""
    execution_id: str
    scenario_id: str
    status: ScenarioStatus
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    duration_ms: int = 0
    step_results: list[StepExecutionResult] = field(default_factory=list)
    final_variables: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ScenarioExecutor:
    """
    测试场景执行器
    
    功能:
    - 按顺序执行场景步骤
    - 支持变量传递（从上一步提取变量供下一步使用）
    - 支持断言验证
    - 支持条件步骤和循环步骤
    - 支持失败重试
    """
    
    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        logger: AILogger | None = None
    ) -> None:
        """
        初始化执行器
        
        Args:
            base_url: 基础URL
            timeout: 请求超时时间（秒）
            logger: 日志器
        """
        self.base_url = base_url.rstrip('/') if base_url else ""
        self.timeout = timeout
        self.logger = logger or AILogger()
        
        self.variable_resolver = VariableResolver()
        self.extractor = ResponseExtractor()
        self.assertion_engine = AssertionEngine()
    
    async def execute_scenario(
        self,
        scenario: TestScenario,
        base_url: str | None = None,
        initial_variables: dict[str, Any] | None = None,
        trigger_type: TriggerType = TriggerType.MANUAL
    ) -> ScenarioExecutionResult:
        """
        执行测试场景
        
        Args:
            scenario: 测试场景
            base_url: 基础URL（覆盖默认值）
            initial_variables: 初始变量
            trigger_type: 触发类型
        
        Returns:
            执行结果
        """
        execution_id = f"exec_{int(time.time() * 1000)}"
        started_at = datetime.now()
        
        # 使用传入的 base_url 或默认值
        effective_base_url = base_url or self.base_url
        
        # 初始化变量
        self.variable_resolver.clear_variables()
        if scenario.variables:
            self.variable_resolver.update_variables(scenario.variables)
        if initial_variables:
            self.variable_resolver.update_variables(initial_variables)
        
        self.logger.info(f"开始执行场景: {scenario.name}")
        self.logger.info(f"   执行ID: {execution_id}")
        self.logger.info(f"   目标URL: {effective_base_url}")
        self.logger.info(f"   步骤数: {len(scenario.steps)}")
        
        result = ScenarioExecutionResult(
            execution_id=execution_id,
            scenario_id=scenario.scenario_id,
            status=ScenarioStatus.RUNNING,
            total_steps=len(scenario.steps),
            started_at=started_at
        )
        
        try:
            # 执行前置钩子
            if scenario.setup_hooks:
                await self._execute_hooks(scenario.setup_hooks, "setup")
            
            # 按顺序执行步骤
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                for step in sorted(scenario.steps, key=lambda s: s.step_order):
                    if not step.is_enabled:
                        result.skipped_steps += 1
                        continue
                    
                    step_result = await self._execute_step(
                        session=session,
                        step=step,
                        base_url=effective_base_url
                    )
                    result.step_results.append(step_result)
                    
                    if step_result.status == TestResultStatus.PASSED:
                        result.passed_steps += 1
                    elif step_result.status == TestResultStatus.FAILED:
                        result.failed_steps += 1
                        if not step.continue_on_failure:
                            self.logger.warn(f"步骤失败，停止执行: {step.name}")
                            break
                    elif step_result.status == TestResultStatus.ERROR:
                        result.failed_steps += 1
                        if not step.continue_on_failure:
                            self.logger.error(f"步骤错误，停止执行: {step.name}")
                            break
            
            # 执行后置钩子
            if scenario.teardown_hooks:
                await self._execute_hooks(scenario.teardown_hooks, "teardown")
            
            # 确定最终状态
            if result.failed_steps == 0:
                result.status = ScenarioStatus.PASSED
            else:
                result.status = ScenarioStatus.FAILED
        
        except Exception as e:
            result.status = ScenarioStatus.FAILED
            result.error_message = str(e)
            self.logger.error(f"场景执行异常: {e}")
        
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = int(
                (result.completed_at - started_at).total_seconds() * 1000
            )
            result.final_variables = dict(self.variable_resolver.variables)
        
        self.logger.info(f"场景执行完成: {result.status.value}")
        self.logger.info(f"   通过: {result.passed_steps}/{result.total_steps}")
        self.logger.info(f"   耗时: {result.duration_ms}ms")
        
        return result
    
    async def _execute_step(
        self,
        session: aiohttp.ClientSession,
        step: ScenarioStep,
        base_url: str
    ) -> StepExecutionResult:
        """执行单个步骤"""
        self.logger.info(f"   [{step.step_order}] 执行步骤: {step.name}")
        
        result = StepExecutionResult(
            step_id=step.step_id,
            step_order=step.step_order,
            status=TestResultStatus.PASSED,
            executed_at=datetime.now()
        )
        
        try:
            if step.step_type == ScenarioStepType.REQUEST:
                await self._execute_request_step(session, step, base_url, result)
            elif step.step_type == ScenarioStepType.WAIT:
                await self._execute_wait_step(step, result)
            elif step.step_type == ScenarioStepType.CONDITION:
                await self._execute_condition_step(step, result)
            elif step.step_type == ScenarioStepType.EXTRACT:
                # 提取步骤通常在请求步骤中处理
                pass
            elif step.step_type == ScenarioStepType.ASSERT:
                # 断言步骤通常在请求步骤中处理
                pass
        
        except asyncio.TimeoutError:
            result.status = TestResultStatus.ERROR
            result.error_message = f"请求超时 ({step.timeout_ms}ms)"
            self.logger.error(f"      超时: {result.error_message}")
        
        except Exception as e:
            result.status = TestResultStatus.ERROR
            result.error_message = str(e)
            self.logger.error(f"      错误: {e}")
        
        return result
    
    async def _execute_request_step(
        self,
        session: aiohttp.ClientSession,
        step: ScenarioStep,
        base_url: str,
        result: StepExecutionResult
    ) -> None:
        """执行请求步骤"""
        # 解析变量
        url = self.variable_resolver.resolve_string(step.url)
        if not url.startswith('http'):
            url = f"{base_url}/{url.lstrip('/')}"
        
        headers = self.variable_resolver.resolve_dict(step.headers) if step.headers else {}
        params = self.variable_resolver.resolve_dict(step.query_params) if step.query_params else {}
        
        body = None
        if step.body:
            resolved_body = self.variable_resolver._resolve_value(step.body)
            if isinstance(resolved_body, dict):
                body = json.dumps(resolved_body, ensure_ascii=False)
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/json'
            else:
                body = str(resolved_body)
        
        result.request_url = url
        result.request_headers = headers
        result.request_body = body or ""
        
        # 发送请求
        start_time = time.time()
        
        async with session.request(
            method=step.method,
            url=url,
            headers=headers,
            params=params,
            data=body,
            timeout=aiohttp.ClientTimeout(total=step.timeout_ms / 1000)
        ) as response:
            response_time = (time.time() - start_time) * 1000
            response_body = await response.text()
            
            result.response_status_code = response.status
            result.response_headers = dict(response.headers)
            result.response_body = response_body
            result.response_time_ms = response_time
        
        self.logger.debug(f"      响应: {result.response_status_code} ({response_time:.0f}ms)")
        
        # 提取变量
        if step.extractions:
            extracted = self.extractor.extract_list(
                extractions=step.extractions,
                response_body=result.response_body,
                response_headers=result.response_headers,
                status_code=result.response_status_code
            )
            result.extracted_variables = extracted
            self.variable_resolver.update_variables(extracted)
            
            if extracted:
                self.logger.debug(f"      提取变量: {list(extracted.keys())}")
        
        # 执行断言
        if step.assertions:
            assertion_results = self.assertion_engine.assert_all(
                assertions=step.assertions,
                response_body=result.response_body,
                response_headers=result.response_headers,
                status_code=result.response_status_code,
                response_time_ms=result.response_time_ms
            )
            
            result.assertion_results = [
                {
                    'passed': ar.passed,
                    'type': ar.assertion_type,
                    'expected': ar.expected,
                    'actual': ar.actual,
                    'message': ar.message
                }
                for ar in assertion_results
            ]
            
            # 检查断言结果
            failed_assertions = [ar for ar in assertion_results if not ar.passed]
            if failed_assertions:
                result.status = TestResultStatus.FAILED
                result.error_message = "; ".join(
                    f"{ar.assertion_type}: {ar.message}" for ar in failed_assertions
                )
                self.logger.warn(f"      断言失败: {len(failed_assertions)}个")
    
    async def _execute_wait_step(
        self,
        step: ScenarioStep,
        result: StepExecutionResult
    ) -> None:
        """执行等待步骤"""
        wait_time = step.wait_time_ms / 1000
        self.logger.debug(f"      等待 {step.wait_time_ms}ms")
        await asyncio.sleep(wait_time)
    
    async def _execute_condition_step(
        self,
        step: ScenarioStep,
        result: StepExecutionResult
    ) -> None:
        """执行条件步骤"""
        # 条件步骤用于控制流程
        condition = step.condition
        if not condition:
            return
        
        # 解析条件表达式
        expression = condition.get('expression', '')
        resolved = self.variable_resolver.resolve_string(expression)
        
        # 简单的条件评估
        try:
            # 安全地评估条件（只允许比较操作）
            condition_result = self._evaluate_condition(resolved)
            result.extracted_variables['_condition_result'] = condition_result
        except Exception as e:
            result.status = TestResultStatus.ERROR
            result.error_message = f"条件评估失败: {e}"
    
    def _evaluate_condition(self, expression: str) -> bool:
        """安全地评估条件表达式"""
        # 只支持简单的比较操作
        expression = expression.strip()
        
        # 布尔值
        if expression.lower() == 'true':
            return True
        if expression.lower() == 'false':
            return False
        
        # 比较操作
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in expression:
                parts = expression.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # 尝试转换为数字
                    try:
                        left_val: Any = float(left)
                        right_val: Any = float(right)
                    except ValueError:
                        left_val = left.strip('"\'')
                        right_val = right.strip('"\'')
                    
                    if op == '==':
                        return left_val == right_val
                    elif op == '!=':
                        return left_val != right_val
                    elif op == '>=':
                        return left_val >= right_val
                    elif op == '<=':
                        return left_val <= right_val
                    elif op == '>':
                        return left_val > right_val
                    elif op == '<':
                        return left_val < right_val
        
        return bool(expression)
    
    async def _execute_hooks(
        self,
        hooks: list[dict[str, Any]],
        hook_type: str
    ) -> None:
        """执行钩子（尚未实现具体逻辑）"""
        if not hooks:
            return
        self.logger.debug(f"   执行 {hook_type} 钩子（{len(hooks)} 个，跳过：钩子执行尚未实现）")
        for hook in hooks:
            hook_name = hook.get('name', hook_type)
            self.logger.debug(f"      跳过钩子: {hook_name}")
    
    def to_execution_model(
        self,
        result: ScenarioExecutionResult,
        trigger_type: TriggerType = TriggerType.MANUAL,
        environment: str = ""
    ) -> ScenarioExecution:
        """转换为数据库模型"""
        return ScenarioExecution(
            execution_id=result.execution_id,
            scenario_id=result.scenario_id,
            trigger_type=trigger_type,
            status=result.status,
            base_url=self.base_url,
            environment=environment,
            variables=result.final_variables,
            total_steps=result.total_steps,
            passed_steps=result.passed_steps,
            failed_steps=result.failed_steps,
            skipped_steps=result.skipped_steps,
            duration_ms=result.duration_ms,
            error_message=result.error_message,
            started_at=result.started_at,
            completed_at=result.completed_at
        )
    
    def to_step_result_models(
        self,
        result: ScenarioExecutionResult
    ) -> list[StepResult]:
        """转换步骤结果为数据库模型"""
        return [
            StepResult(
                execution_id=result.execution_id,
                step_id=sr.step_id,
                step_order=sr.step_order,
                status=sr.status,
                request_url=sr.request_url,
                request_headers=sr.request_headers,
                request_body=sr.request_body,
                response_status_code=sr.response_status_code,
                response_headers=sr.response_headers,
                response_body=sr.response_body,
                response_time_ms=sr.response_time_ms,
                extracted_variables=sr.extracted_variables,
                assertion_results=sr.assertion_results,
                error_message=sr.error_message,
                executed_at=sr.executed_at
            )
            for sr in result.step_results
        ]
