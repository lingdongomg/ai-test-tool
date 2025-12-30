"""
日志格式自动检测模块
支持多种日志格式的智能识别
"""

import json
import re
from enum import Enum
from typing import Any


class LogFormat(Enum):
    """支持的日志格式"""
    JSON = "json"
    JSONL = "jsonl"
    NGINX = "nginx"
    APACHE = "apache"
    GIN = "gin"
    SPRING = "spring"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class LogFormatDetector:
    """日志格式检测器"""
    
    PATTERNS: dict[LogFormat, list[str]] = {
        LogFormat.JSON: [
            r'^\s*\{.*\}\s*$',
        ],
        LogFormat.JSONL: [
            r'^\s*\{"__CONTENT__"',
            r'^\s*\{"timestamp"',
            r'^\s*\{"level"',
            r'^\s*\{"message"',
        ],
        LogFormat.NGINX: [
            r'^\d+\.\d+\.\d+\.\d+\s+-\s+-\s+\[',
            r'^\d+\.\d+\.\d+\.\d+\s+\d+\.\d+\.\d+\.\d+',
        ],
        LogFormat.APACHE: [
            r'^\d+\.\d+\.\d+\.\d+\s+-\s+\w+\s+\[',
        ],
        LogFormat.GIN: [
            r'\[GIN\]',
            r'\[GIN-debug\]',
        ],
        LogFormat.SPRING: [
            r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+\s+(INFO|DEBUG|WARN|ERROR)',
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+',
        ],
    }
    
    API_REQUEST_PATTERNS: list[str] = [
        r'API请求信息',
        r'request.*method.*url',
        r'(GET|POST|PUT|DELETE|PATCH)\s+["\']?/\w+',
        r'HTTP/\d\.\d',
    ]
    
    def __init__(self) -> None:
        self._compiled_patterns: dict[LogFormat, list[re.Pattern[str]]] = {}
        self._api_patterns: list[re.Pattern[str]] = []
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """预编译正则表达式"""
        for fmt, patterns in self.PATTERNS.items():
            self._compiled_patterns[fmt] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._api_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.API_REQUEST_PATTERNS
        ]
    
    def detect_format(self, sample_lines: list[str]) -> LogFormat:
        """检测日志格式"""
        if not sample_lines:
            return LogFormat.UNKNOWN
        
        format_scores: dict[LogFormat, int] = {fmt: 0 for fmt in LogFormat}
        
        for line in sample_lines[:100]:
            line = line.strip()
            if not line:
                continue
            
            if self._is_json(line):
                format_scores[LogFormat.JSON] += 1
                if self._is_jsonl_format(line):
                    format_scores[LogFormat.JSONL] += 2
            
            for fmt, patterns in self._compiled_patterns.items():
                for pattern in patterns:
                    if pattern.search(line):
                        format_scores[fmt] += 1
        
        best_format = max(format_scores, key=format_scores.get)
        if format_scores[best_format] == 0:
            return LogFormat.UNKNOWN
        
        return best_format
    
    def _is_json(self, line: str) -> bool:
        """检查是否是有效JSON"""
        try:
            json.loads(line)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
    
    def _is_jsonl_format(self, line: str) -> bool:
        """检查是否是JSONL格式"""
        try:
            data = json.loads(line)
            jsonl_fields = [
                '__CONTENT__', '__TIMESTAMP__', '__FILENAME__',
                'timestamp', 'level', 'message', 'log'
            ]
            return any(field in data for field in jsonl_fields)
        except (json.JSONDecodeError, ValueError, TypeError):
            return False
    
    def has_api_requests(self, sample_lines: list[str]) -> bool:
        """检查日志中是否包含API请求信息"""
        for line in sample_lines[:200]:
            for pattern in self._api_patterns:
                if pattern.search(line):
                    return True
        return False
    
    def get_format_info(self, sample_lines: list[str]) -> dict[str, Any]:
        """获取日志格式详细信息"""
        detected_format = self.detect_format(sample_lines)
        has_api = self.has_api_requests(sample_lines)
        
        structure_info = self._analyze_structure(sample_lines, detected_format)
        
        return {
            "format": detected_format.value,
            "format_name": detected_format.name,
            "has_api_requests": has_api,
            "structure": structure_info,
            "sample_count": len(sample_lines),
            "recommendations": self._get_recommendations(detected_format, has_api)
        }
    
    def _analyze_structure(
        self,
        sample_lines: list[str],
        fmt: LogFormat
    ) -> dict[str, Any]:
        """分析日志结构"""
        if fmt in [LogFormat.JSON, LogFormat.JSONL]:
            return self._analyze_json_structure(sample_lines)
        else:
            return self._analyze_text_structure(sample_lines)
    
    def _analyze_json_structure(self, sample_lines: list[str]) -> dict[str, Any]:
        """分析JSON日志结构"""
        fields: set[str] = set()
        nested_fields: set[str] = set()
        
        for line in sample_lines[:50]:
            try:
                data = json.loads(line.strip())
                if isinstance(data, dict):
                    for key, value in data.items():
                        fields.add(key)
                        if isinstance(value, dict):
                            nested_fields.add(key)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        
        return {
            "type": "json",
            "top_level_fields": list(fields),
            "nested_fields": list(nested_fields)
        }
    
    def _analyze_text_structure(self, sample_lines: list[str]) -> dict[str, Any]:
        """分析文本日志结构"""
        delimiters = {
            "tab": "\t",
            "pipe": "|",
            "comma": ",",
            "space": " "
        }
        
        delimiter_counts: dict[str, int] = {d: 0 for d in delimiters}
        
        for line in sample_lines[:50]:
            for name, char in delimiters.items():
                delimiter_counts[name] += line.count(char)
        
        likely_delimiter = max(delimiter_counts, key=delimiter_counts.get)
        
        return {
            "type": "text",
            "likely_delimiter": likely_delimiter,
            "delimiter_char": delimiters[likely_delimiter]
        }
    
    def _get_recommendations(
        self,
        fmt: LogFormat,
        has_api: bool
    ) -> list[str]:
        """获取处理建议"""
        recommendations: list[str] = []
        
        if fmt == LogFormat.UNKNOWN:
            recommendations.append("日志格式未能自动识别，建议手动指定格式或提供格式说明")
        
        if not has_api:
            recommendations.append("未检测到明显的API请求信息，可能需要调整解析规则")
        
        if fmt == LogFormat.JSONL:
            recommendations.append("检测到JSONL格式，将使用JSON解析器逐行处理")
        
        if fmt == LogFormat.GIN:
            recommendations.append("检测到Gin框架日志，将使用专用解析规则")
        
        return recommendations
