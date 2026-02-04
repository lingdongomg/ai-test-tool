"""
响应提取器
从 HTTP 响应中提取数据并存储为变量
"""

import re
import json
from typing import Any


class ResponseExtractor:
    """
    响应提取器
    
    支持的提取方式:
    - jsonpath: JSONPath 表达式
    - regex: 正则表达式
    - header: 响应头
    - body: 整个响应体
    """
    
    def __init__(self) -> None:
        pass
    
    def extract(
        self,
        extraction_config: dict[str, Any],
        response_body: str,
        response_headers: dict[str, str],
        status_code: int
    ) -> dict[str, Any]:
        """
        执行提取
        
        Args:
            extraction_config: 提取配置
            response_body: 响应体
            response_headers: 响应头
            status_code: 状态码
        
        Returns:
            提取的变量字典
        
        提取配置格式:
        {
            "variable_name": {
                "source": "jsonpath|regex|header|body|status",
                "expression": "$.data.id",
                "default": null
            }
        }
        """
        extracted = {}
        
        for var_name, config in extraction_config.items():
            source = config.get('source', 'jsonpath')
            expression = config.get('expression', '')
            default = config.get('default')
            
            try:
                if source == 'jsonpath':
                    value = self._extract_jsonpath(response_body, expression)
                elif source == 'regex':
                    value = self._extract_regex(response_body, expression)
                elif source == 'header':
                    value = response_headers.get(expression, default)
                elif source == 'body':
                    value = response_body
                elif source == 'status':
                    value = status_code
                else:
                    value = default
                
                extracted[var_name] = value if value is not None else default
            except Exception:
                extracted[var_name] = default
        
        return extracted
    
    def extract_list(
        self,
        extractions: list[dict[str, Any]],
        response_body: str,
        response_headers: dict[str, str],
        status_code: int
    ) -> dict[str, Any]:
        """
        执行提取列表
        
        Args:
            extractions: 提取配置列表
            response_body: 响应体
            response_headers: 响应头
            status_code: 状态码
        
        Returns:
            提取的变量字典
        
        提取配置列表格式:
        [
            {
                "name": "user_id",
                "source": "jsonpath",
                "expression": "$.data.id",
                "default": null
            }
        ]
        """
        extracted = {}
        
        for config in extractions:
            var_name = config.get('name', '')
            if not var_name:
                continue
            
            source = config.get('source', 'jsonpath')
            expression = config.get('expression', '')
            default = config.get('default')
            
            try:
                if source == 'jsonpath':
                    value = self._extract_jsonpath(response_body, expression)
                elif source == 'regex':
                    value = self._extract_regex(response_body, expression)
                elif source == 'header':
                    value = response_headers.get(expression, default)
                elif source == 'body':
                    value = response_body
                elif source == 'status':
                    value = status_code
                else:
                    value = default
                
                extracted[var_name] = value if value is not None else default
            except Exception:
                extracted[var_name] = default
        
        return extracted
    
    def _extract_jsonpath(self, body: str, expression: str) -> Any:
        """
        使用简化的 JSONPath 提取
        
        支持的语法:
        - $.key: 根级别键
        - $.nested.key: 嵌套键
        - $.array[0]: 数组索引
        - $.array[*].key: 数组所有元素的键
        """
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None
        
        # 移除开头的 $
        if expression.startswith('$.'):
            expression = expression[2:]
        elif expression.startswith('$'):
            expression = expression[1:]
        
        if not expression:
            return data
        
        return self._navigate_path(data, expression)
    
    def _navigate_path(self, data: Any, path: str) -> Any:
        """导航 JSON 路径"""
        current = data
        parts = self._split_path(path)
        
        for part in parts:
            if current is None:
                return None
            
            # 处理数组通配符
            if part == '*':
                if isinstance(current, list):
                    continue  # 保持当前为列表
                return None
            
            # 处理数组索引
            if isinstance(part, int) or (isinstance(part, str) and part.isdigit()):
                index = int(part)
                if isinstance(current, list):
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    return None
            # 处理字典键
            elif isinstance(current, dict):
                current = current.get(part)
            # 处理列表中的所有元素
            elif isinstance(current, list):
                results = []
                for item in current:
                    if isinstance(item, dict) and part in item:
                        results.append(item[part])
                current = results if results else None
            else:
                return None
        
        return current
    
    def _split_path(self, path: str) -> list[str]:
        """分割路径"""
        parts = []
        current = ""
        i = 0
        
        while i < len(path):
            char = path[i]
            
            if char == '.':
                if current:
                    parts.append(current)
                    current = ""
            elif char == '[':
                if current:
                    parts.append(current)
                    current = ""
                j = path.find(']', i)
                if j > i:
                    parts.append(path[i+1:j])
                    i = j
            else:
                current += char
            
            i += 1
        
        if current:
            parts.append(current)
        
        return parts
    
    def _extract_regex(self, body: str, pattern: str) -> Any:
        """使用正则表达式提取"""
        try:
            match = re.search(pattern, body)
            if match:
                # 如果有分组，返回第一个分组
                if match.groups():
                    return match.group(1)
                return match.group(0)
            return None
        except re.error:
            return None
