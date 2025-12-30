"""
变量解析器
支持在请求中使用变量占位符，实现参数传递
"""

import re
import json
from typing import Any


class VariableResolver:
    """
    变量解析器
    
    支持的变量格式:
    - ${variable_name}: 简单变量替换
    - ${variable.nested.key}: 嵌套变量访问
    - ${variable[0]}: 数组索引访问
    - ${variable[0].key}: 组合访问
    """
    
    VARIABLE_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, variables: dict[str, Any] | None = None) -> None:
        """
        初始化变量解析器
        
        Args:
            variables: 初始变量字典
        """
        self.variables: dict[str, Any] = variables or {}
    
    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)
    
    def update_variables(self, variables: dict[str, Any]) -> None:
        """批量更新变量"""
        self.variables.update(variables)
    
    def clear_variables(self) -> None:
        """清空变量"""
        self.variables.clear()
    
    def resolve_string(self, text: str) -> str:
        """
        解析字符串中的变量
        
        Args:
            text: 包含变量占位符的字符串
        
        Returns:
            解析后的字符串
        """
        def replace_var(match: re.Match[str]) -> str:
            var_path = match.group(1)
            value = self._resolve_path(var_path)
            if value is None:
                return match.group(0)  # 保留原始占位符
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        
        return self.VARIABLE_PATTERN.sub(replace_var, text)
    
    def resolve_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        解析字典中的所有变量
        
        Args:
            data: 包含变量占位符的字典
        
        Returns:
            解析后的字典
        """
        result = {}
        for key, value in data.items():
            resolved_key = self.resolve_string(key) if isinstance(key, str) else key
            result[resolved_key] = self._resolve_value(value)
        return result
    
    def resolve_list(self, data: list[Any]) -> list[Any]:
        """
        解析列表中的所有变量
        
        Args:
            data: 包含变量占位符的列表
        
        Returns:
            解析后的列表
        """
        return [self._resolve_value(item) for item in data]
    
    def _resolve_value(self, value: Any) -> Any:
        """递归解析值"""
        if isinstance(value, str):
            # 检查是否整个字符串就是一个变量
            match = self.VARIABLE_PATTERN.fullmatch(value)
            if match:
                # 整个字符串是变量，保留原始类型
                resolved = self._resolve_path(match.group(1))
                return resolved if resolved is not None else value
            # 字符串中包含变量，进行替换
            return self.resolve_string(value)
        elif isinstance(value, dict):
            return self.resolve_dict(value)
        elif isinstance(value, list):
            return self.resolve_list(value)
        else:
            return value
    
    def _resolve_path(self, path: str) -> Any:
        """
        解析变量路径
        
        支持:
        - simple_var
        - nested.key
        - array[0]
        - nested.array[0].key
        """
        parts = self._parse_path(path)
        current = self.variables
        
        for part in parts:
            if current is None:
                return None
            
            if isinstance(part, int):
                # 数组索引
                if isinstance(current, list) and 0 <= part < len(current):
                    current = current[part]
                else:
                    return None
            else:
                # 字典键
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
        
        return current
    
    def _parse_path(self, path: str) -> list[str | int]:
        """
        解析路径字符串
        
        Examples:
            "name" -> ["name"]
            "user.name" -> ["user", "name"]
            "items[0]" -> ["items", 0]
            "users[0].name" -> ["users", 0, "name"]
        """
        parts: list[str | int] = []
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
                # 找到匹配的 ]
                j = path.find(']', i)
                if j > i:
                    index_str = path[i+1:j]
                    try:
                        parts.append(int(index_str))
                    except ValueError:
                        parts.append(index_str)  # 非数字索引
                    i = j
            else:
                current += char
            
            i += 1
        
        if current:
            parts.append(current)
        
        return parts
    
    def has_variables(self, text: str) -> bool:
        """检查字符串是否包含变量"""
        return bool(self.VARIABLE_PATTERN.search(text))
    
    def extract_variables(self, text: str) -> list[str]:
        """提取字符串中的所有变量名"""
        return self.VARIABLE_PATTERN.findall(text)
