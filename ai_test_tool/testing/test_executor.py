"""
测试执行器
执行测试用例并收集结果
Python 3.13+ 兼容
"""

import json
import asyncio
import time
from typing import Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

import httpx

from .test_case_generator import TestCase
from ..config import get_config, TestConfig


class TestStatus(Enum):
    """测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """测试结果"""
    test_case_id: str
    test_case_name: str
    status: TestStatus
    actual_status_code: int = 0
    actual_response_time_ms: float = 0
    actual_response_body: str | None = None
    actual_headers: dict[str, str] = field(default_factory=dict)
    error_message: str = ""
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value
        return result


class TestExecutor:
    """测试执行器"""
    
    def __init__(
        self,
        config: TestConfig | None = None,
        progress_callback: Callable[[int, int, TestResult], None] | None = None
    ) -> None:
        self.config = config or get_config().test
        self.progress_callback = progress_callback
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True
            )
        return self._client
    
    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def execute_test_case(self, test_case: TestCase) -> TestResult:
        """执行单个测试用例"""
        result = TestResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            status=TestStatus.RUNNING,
            started_at=datetime.now().isoformat()
        )
        
        try:
            client = await self._get_client()
            
            # 构建请求URL
            url = self._build_url(test_case)
            
            # 合并headers
            headers = {**self.config.headers, **test_case.headers}
            
            # 准备请求体
            content = None
            if test_case.body:
                content = json.dumps(test_case.body, ensure_ascii=False)
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            
            # 执行请求
            start_time = time.time()
            
            response = await client.request(
                method=test_case.method,
                url=url,
                headers=headers,
                content=content
            )
            
            end_time = time.time()
            
            # 记录结果
            result.actual_status_code = response.status_code
            result.actual_response_time_ms = (end_time - start_time) * 1000
            result.actual_headers = dict(response.headers)
            
            try:
                result.actual_response_body = response.text[:5000]  # 限制大小
            except Exception:
                result.actual_response_body = "<binary content>"
            
            # 验证结果
            validation_results = self._validate_response(test_case, response, result.actual_response_time_ms)
            result.validation_results = validation_results
            
            # 判断是否通过
            all_passed = all(v.get("passed", False) for v in validation_results)
            result.status = TestStatus.PASSED if all_passed else TestStatus.FAILED
            
        except httpx.TimeoutException:
            result.status = TestStatus.ERROR
            result.error_message = f"请求超时 (>{self.config.timeout}s)"
        except httpx.ConnectError as e:
            result.status = TestStatus.ERROR
            result.error_message = f"连接失败: {e!s}"
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = f"执行错误: {e!s}"
        
        result.finished_at = datetime.now().isoformat()
        return result
    
    def _build_url(self, test_case: TestCase) -> str:
        """构建完整URL"""
        url = test_case.url
        
        # 如果不是完整URL，添加base_url
        if not url.startswith(('http://', 'https://')):
            url = f"{self.config.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        # 添加查询参数
        if test_case.query_params:
            params = "&".join(f"{k}={v}" for k, v in test_case.query_params.items())
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{params}"
        
        return url
    
    def _validate_response(
        self,
        test_case: TestCase,
        response: httpx.Response,
        response_time_ms: float
    ) -> list[dict[str, Any]]:
        """验证响应"""
        validations: list[dict[str, Any]] = []
        expected = test_case.expected
        
        # 1. 验证状态码
        status_passed = response.status_code == expected.status_code
        validations.append({
            "check": "status_code",
            "expected": expected.status_code,
            "actual": response.status_code,
            "passed": status_passed,
            "message": "状态码匹配" if status_passed else f"期望{expected.status_code}，实际{response.status_code}"
        })
        
        # 2. 验证响应时间
        time_passed = response_time_ms <= expected.max_response_time_ms
        validations.append({
            "check": "response_time",
            "expected": f"<={expected.max_response_time_ms}ms",
            "actual": f"{response_time_ms:.2f}ms",
            "passed": time_passed,
            "message": "响应时间正常" if time_passed else "响应时间过长"
        })
        
        # 3. 验证响应内容包含
        response_text = response.text
        for keyword in expected.response_contains:
            contains = keyword in response_text
            validations.append({
                "check": "response_contains",
                "expected": keyword,
                "actual": "found" if contains else "not found",
                "passed": contains,
                "message": f"响应包含'{keyword}'" if contains else f"响应不包含'{keyword}'"
            })
        
        # 4. 验证响应内容不包含
        for keyword in expected.response_not_contains:
            not_contains = keyword not in response_text
            validations.append({
                "check": "response_not_contains",
                "expected": f"not contain '{keyword}'",
                "actual": "not found" if not_contains else "found",
                "passed": not_contains,
                "message": f"响应不包含'{keyword}'" if not_contains else f"响应意外包含'{keyword}'"
            })
        
        # 5. 执行自定义验证规则
        for rule in expected.validation_rules:
            rule_result = self._execute_validation_rule(rule, response)
            validations.append(rule_result)
        
        return validations
    
    def _execute_validation_rule(
        self,
        rule: Any,
        response: httpx.Response
    ) -> dict[str, Any]:
        """执行自定义验证规则"""
        try:
            # 尝试解析JSON响应
            try:
                response_data = response.json()
            except Exception:
                response_data = response.text
            
            # 获取字段值
            actual_value = self._get_field_value(response_data, rule.field)
            
            # 执行规则验证
            passed = False
            if rule.rule == "equals":
                passed = actual_value == rule.expected_value
            elif rule.rule == "contains":
                passed = rule.expected_value in str(actual_value)
            elif rule.rule == "exists":
                passed = actual_value is not None
            elif rule.rule == "type":
                passed = type(actual_value).__name__ == rule.expected_value
            elif rule.rule == "range":
                min_val, max_val = rule.expected_value
                passed = min_val <= actual_value <= max_val
            
            return {
                "check": f"rule:{rule.rule}",
                "field": rule.field,
                "expected": rule.expected_value,
                "actual": actual_value,
                "passed": passed,
                "message": rule.description or f"{rule.field} {rule.rule} 验证"
            }
        except Exception as e:
            return {
                "check": f"rule:{rule.rule}",
                "field": rule.field,
                "passed": False,
                "message": f"验证规则执行失败: {e!s}"
            }
    
    def _get_field_value(self, data: Any, field_path: str) -> Any:
        """获取嵌套字段值"""
        if not field_path:
            return data
        
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if index < len(current) else None
            else:
                return None
        
        return current
    
    async def execute_test_suite(
        self,
        test_cases: list[TestCase],
        concurrent: int | None = None
    ) -> list[TestResult]:
        """执行测试套件"""
        concurrent = concurrent or self.config.concurrent_requests
        total = len(test_cases)
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(concurrent)
        
        async def run_with_semaphore(tc: TestCase, index: int) -> TestResult:
            async with semaphore:
                result = await self.execute_test_case(tc)
                if self.progress_callback:
                    self.progress_callback(index + 1, total, result)
                return result
        
        # 并发执行
        tasks = [
            run_with_semaphore(tc, i)
            for i, tc in enumerate(test_cases)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results: list[TestResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(TestResult(
                    test_case_id=test_cases[i].id,
                    test_case_name=test_cases[i].name,
                    status=TestStatus.ERROR,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        await self.close()
        return final_results
    
    def execute_sync(self, test_cases: list[TestCase]) -> list[TestResult]:
        """同步执行测试套件"""
        return asyncio.run(self.execute_test_suite(test_cases))


def run_tests(
    test_cases: list[TestCase],
    base_url: str | None = None,
    concurrent: int = 5,
    progress_callback: Callable[[int, int, TestResult], None] | None = None
) -> list[TestResult]:
    """
    便捷函数：运行测试
    
    Args:
        test_cases: 测试用例列表
        base_url: 基础URL
        concurrent: 并发数
        progress_callback: 进度回调
        
    Returns:
        测试结果列表
    """
    config = TestConfig(
        base_url=base_url or get_config().test.base_url,
        concurrent_requests=concurrent
    )
    
    executor = TestExecutor(config=config, progress_callback=progress_callback)
    return executor.execute_sync(test_cases)
