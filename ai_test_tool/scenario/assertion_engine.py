"""
断言引擎
执行测试断言验证
"""

import re
import json
from typing import Any
from dataclasses import dataclass


@dataclass
class AssertionResult:
    """断言结果"""
    passed: bool
    assertion_type: str
    expected: Any
    actual: Any
    message: str


class AssertionEngine:
    """
    断言引擎
    
    支持的断言类型:
    - equals: 相等
    - not_equals: 不相等
    - contains: 包含
    - not_contains: 不包含
    - starts_with: 以...开头
    - ends_with: 以...结尾
    - matches: 正则匹配
    - greater_than: 大于
    - less_than: 小于
    - greater_than_or_equals: 大于等于
    - less_than_or_equals: 小于等于
    - is_null: 为空
    - is_not_null: 不为空
    - is_empty: 为空（字符串/列表/字典）
    - is_not_empty: 不为空
    - has_key: 包含键
    - has_length: 长度等于
    - type_is: 类型检查
    """
    
    def __init__(self) -> None:
        pass
    
    def assert_all(
        self,
        assertions: list[dict[str, Any]],
        response_body: str,
        response_headers: dict[str, str],
        status_code: int,
        response_time_ms: float
    ) -> list[AssertionResult]:
        """
        执行所有断言
        
        Args:
            assertions: 断言配置列表
            response_body: 响应体
            response_headers: 响应头
            status_code: 状态码
            response_time_ms: 响应时间
        
        Returns:
            断言结果列表
        
        断言配置格式:
        [
            {
                "type": "equals",
                "source": "status|header|body|jsonpath|response_time",
                "expression": "$.code",  # 用于 jsonpath
                "expected": 200
            }
        ]
        """
        results = []
        
        # 解析响应体为 JSON（如果可能）
        try:
            body_json = json.loads(response_body)
        except json.JSONDecodeError:
            body_json = None
        
        for assertion in assertions:
            result = self._execute_assertion(
                assertion=assertion,
                response_body=response_body,
                body_json=body_json,
                response_headers=response_headers,
                status_code=status_code,
                response_time_ms=response_time_ms
            )
            results.append(result)
        
        return results
    
    def _execute_assertion(
        self,
        assertion: dict[str, Any],
        response_body: str,
        body_json: Any,
        response_headers: dict[str, str],
        status_code: int,
        response_time_ms: float
    ) -> AssertionResult:
        """执行单个断言"""
        assertion_type = assertion.get('type', 'equals')
        source = assertion.get('source', 'status')
        expression = assertion.get('expression', '')
        expected = assertion.get('expected')
        
        # 获取实际值
        actual = self._get_actual_value(
            source=source,
            expression=expression,
            response_body=response_body,
            body_json=body_json,
            response_headers=response_headers,
            status_code=status_code,
            response_time_ms=response_time_ms
        )
        
        # 执行断言
        passed, message = self._check_assertion(assertion_type, expected, actual)
        
        return AssertionResult(
            passed=passed,
            assertion_type=assertion_type,
            expected=expected,
            actual=actual,
            message=message
        )
    
    def _get_actual_value(
        self,
        source: str,
        expression: str,
        response_body: str,
        body_json: Any,
        response_headers: dict[str, str],
        status_code: int,
        response_time_ms: float
    ) -> Any:
        """获取实际值"""
        if source == 'status':
            return status_code
        elif source == 'response_time':
            return response_time_ms
        elif source == 'header':
            return response_headers.get(expression)
        elif source == 'body':
            return response_body
        elif source == 'jsonpath':
            if body_json is None:
                return None
            return self._extract_jsonpath(body_json, expression)
        else:
            return None
    
    def _extract_jsonpath(self, data: Any, expression: str) -> Any:
        """简化的 JSONPath 提取"""
        if expression.startswith('$.'):
            expression = expression[2:]
        elif expression.startswith('$'):
            expression = expression[1:]
        
        if not expression:
            return data
        
        current = data
        parts = expression.replace('[', '.').replace(']', '').split('.')
        
        for part in parts:
            if current is None:
                return None
            
            if part.isdigit():
                index = int(part)
                if isinstance(current, list) and 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current
    
    def _check_assertion(
        self,
        assertion_type: str,
        expected: Any,
        actual: Any
    ) -> tuple[bool, str]:
        """检查断言"""
        try:
            if assertion_type == 'equals':
                passed = actual == expected
                msg = f"期望 {expected}，实际 {actual}"
            
            elif assertion_type == 'not_equals':
                passed = actual != expected
                msg = f"期望不等于 {expected}，实际 {actual}"
            
            elif assertion_type == 'contains':
                if isinstance(actual, str):
                    passed = str(expected) in actual
                elif isinstance(actual, (list, dict)):
                    passed = expected in actual
                else:
                    passed = False
                msg = f"期望包含 {expected}，实际 {actual}"
            
            elif assertion_type == 'not_contains':
                if isinstance(actual, str):
                    passed = str(expected) not in actual
                elif isinstance(actual, (list, dict)):
                    passed = expected not in actual
                else:
                    passed = True
                msg = f"期望不包含 {expected}，实际 {actual}"
            
            elif assertion_type == 'starts_with':
                passed = str(actual).startswith(str(expected))
                msg = f"期望以 {expected} 开头，实际 {actual}"
            
            elif assertion_type == 'ends_with':
                passed = str(actual).endswith(str(expected))
                msg = f"期望以 {expected} 结尾，实际 {actual}"
            
            elif assertion_type == 'matches':
                passed = bool(re.match(str(expected), str(actual)))
                msg = f"期望匹配 {expected}，实际 {actual}"
            
            elif assertion_type == 'greater_than':
                passed = float(actual) > float(expected)
                msg = f"期望大于 {expected}，实际 {actual}"
            
            elif assertion_type == 'less_than':
                passed = float(actual) < float(expected)
                msg = f"期望小于 {expected}，实际 {actual}"
            
            elif assertion_type == 'greater_than_or_equals':
                passed = float(actual) >= float(expected)
                msg = f"期望大于等于 {expected}，实际 {actual}"
            
            elif assertion_type == 'less_than_or_equals':
                passed = float(actual) <= float(expected)
                msg = f"期望小于等于 {expected}，实际 {actual}"
            
            elif assertion_type == 'is_null':
                passed = actual is None
                msg = f"期望为空，实际 {actual}"
            
            elif assertion_type == 'is_not_null':
                passed = actual is not None
                msg = f"期望不为空，实际 {actual}"
            
            elif assertion_type == 'is_empty':
                if actual is None:
                    passed = True
                elif isinstance(actual, (str, list, dict)):
                    passed = len(actual) == 0
                else:
                    passed = False
                msg = f"期望为空，实际 {actual}"
            
            elif assertion_type == 'is_not_empty':
                if actual is None:
                    passed = False
                elif isinstance(actual, (str, list, dict)):
                    passed = len(actual) > 0
                else:
                    passed = True
                msg = f"期望不为空，实际 {actual}"
            
            elif assertion_type == 'has_key':
                passed = isinstance(actual, dict) and expected in actual
                msg = f"期望包含键 {expected}，实际 {list(actual.keys()) if isinstance(actual, dict) else actual}"
            
            elif assertion_type == 'has_length':
                if hasattr(actual, '__len__'):
                    passed = len(actual) == int(expected)
                    msg = f"期望长度 {expected}，实际长度 {len(actual)}"
                else:
                    passed = False
                    msg = f"无法获取长度，实际值 {actual}"
            
            elif assertion_type == 'type_is':
                type_map = {
                    'string': str,
                    'int': int,
                    'integer': int,
                    'float': float,
                    'number': (int, float),
                    'bool': bool,
                    'boolean': bool,
                    'list': list,
                    'array': list,
                    'dict': dict,
                    'object': dict,
                    'null': type(None),
                    'none': type(None)
                }
                expected_type = type_map.get(str(expected).lower())
                if expected_type:
                    passed = isinstance(actual, expected_type)
                else:
                    passed = False
                msg = f"期望类型 {expected}，实际类型 {type(actual).__name__}"
            
            else:
                passed = False
                msg = f"未知的断言类型: {assertion_type}"
            
            return passed, msg
        
        except Exception as e:
            return False, f"断言执行错误: {e}"
