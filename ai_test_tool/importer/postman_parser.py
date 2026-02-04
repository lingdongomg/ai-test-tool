"""
Postman Collection 解析器
支持 Postman Collection v2.0 和 v2.1 格式
"""

import json
import hashlib
from typing import Any
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from ..database.models import ApiEndpoint, EndpointSourceType


class PostmanParser:
    """Postman Collection 解析器"""
    
    def __init__(self) -> None:
        self.endpoints: list[ApiEndpoint] = []
        self.tags: set[str] = set()
        self.source_file: str = ""
    
    def parse_file(self, file_path: str) -> list[ApiEndpoint]:
        """解析 Postman Collection JSON 文件"""
        path = Path(file_path)
        self.source_file = path.name
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self.parse(data)
    
    def parse(self, data: dict[str, Any]) -> list[ApiEndpoint]:
        """解析 Postman Collection 数据"""
        self.endpoints = []
        self.tags = set()
        
        # 检查是否是 Postman Collection 格式
        info = data.get('info', {})
        if not info:
            raise ValueError("无效的 Postman Collection 格式")
        
        schema = info.get('schema', '')
        if 'postman' not in schema.lower() and '_postman_id' not in info:
            raise ValueError("无法识别的 Postman Collection 格式")
        
        # 解析 items
        items = data.get('item', [])
        self._parse_items(items, parent_folder="")
        
        return self.endpoints
    
    def _parse_items(
        self,
        items: list[dict[str, Any]],
        parent_folder: str = ""
    ) -> None:
        """递归解析 items"""
        for item in items:
            # 检查是否是文件夹
            if 'item' in item:
                # 这是一个文件夹
                folder_name = item.get('name', 'Unknown')
                self.tags.add(folder_name)
                
                # 构建完整的文件夹路径
                full_folder = f"{parent_folder}/{folder_name}" if parent_folder else folder_name
                
                # 递归解析子项
                self._parse_items(item['item'], full_folder)
            else:
                # 这是一个请求
                endpoint = self._create_endpoint_from_item(item, parent_folder)
                if endpoint:
                    self.endpoints.append(endpoint)
    
    def _create_endpoint_from_item(
        self,
        item: dict[str, Any],
        folder: str = ""
    ) -> ApiEndpoint | None:
        """从 Postman item 创建端点"""
        request = item.get('request')
        if not request:
            return None
        
        # 解析方法
        method = request.get('method', 'GET').upper()
        
        # 解析 URL
        url_data = request.get('url', {})
        if isinstance(url_data, str):
            path = url_data
            query_params: list[dict[str, Any]] = []
        else:
            path = self._build_path_from_url(url_data)
            query_params = self._parse_query_params(url_data)
        
        # 生成唯一ID
        endpoint_id = self._generate_endpoint_id(method, path)
        
        # 解析请求头
        headers = self._parse_headers(request.get('header', []))
        
        # 解析请求体
        request_body = self._parse_body(request.get('body', {}))
        
        # 解析参数
        parameters = self._build_parameters(url_data, query_params)
        
        # 使用文件夹作为标签
        tags = [folder] if folder else []
        
        # 解析描述
        description = ""
        if isinstance(request.get('description'), str):
            description = request['description']
        elif isinstance(request.get('description'), dict):
            description = request['description'].get('content', '')
        
        return ApiEndpoint(
            endpoint_id=endpoint_id,
            name=item.get('name', f"{method} {path}"),
            description=description,
            method=method,
            path=path,
            summary=item.get('name', ''),
            parameters=parameters,
            request_body=request_body,
            responses={},  # Postman 不包含响应定义
            security=[],
            source_type=EndpointSourceType.POSTMAN,
            source_file=self.source_file,
            is_deprecated=False,
            tags=tags
        )
    
    def _build_path_from_url(self, url_data: dict[str, Any]) -> str:
        """从 URL 数据构建路径"""
        if isinstance(url_data, str):
            parsed = urlparse(url_data)
            return parsed.path or url_data
        
        # 处理 Postman URL 对象
        raw = url_data.get('raw', '')
        if raw:
            # 尝试提取路径部分
            try:
                parsed = urlparse(raw)
                return parsed.path or raw
            except Exception:
                pass
        
        # 从 path 数组构建
        path_parts = url_data.get('path', [])
        if path_parts:
            return '/' + '/'.join(path_parts)
        
        return raw or '/'
    
    def _parse_query_params(self, url_data: dict[str, Any]) -> list[dict[str, Any]]:
        """解析查询参数"""
        if isinstance(url_data, str):
            parsed = urlparse(url_data)
            params = parse_qs(parsed.query)
            return [
                {'name': k, 'value': v[0] if len(v) == 1 else v}
                for k, v in params.items()
            ]
        
        query = url_data.get('query', [])
        return [
            {
                'name': q.get('key', ''),
                'value': q.get('value', ''),
                'description': q.get('description', ''),
                'disabled': q.get('disabled', False)
            }
            for q in query
        ]
    
    def _parse_headers(self, headers: list[dict[str, Any]]) -> dict[str, str]:
        """解析请求头"""
        result = {}
        for header in headers:
            if not header.get('disabled', False):
                key = header.get('key', '')
                value = header.get('value', '')
                if key:
                    result[key] = value
        return result
    
    def _parse_body(self, body: dict[str, Any]) -> dict[str, Any]:
        """解析请求体"""
        if not body:
            return {}
        
        mode = body.get('mode', '')
        result: dict[str, Any] = {'mode': mode}
        
        if mode == 'raw':
            result['content'] = body.get('raw', '')
            options = body.get('options', {})
            if 'raw' in options:
                result['language'] = options['raw'].get('language', 'text')
        elif mode == 'formdata':
            result['formdata'] = body.get('formdata', [])
        elif mode == 'urlencoded':
            result['urlencoded'] = body.get('urlencoded', [])
        elif mode == 'file':
            result['file'] = body.get('file', {})
        
        return result
    
    def _build_parameters(
        self,
        url_data: dict[str, Any],
        query_params: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """构建参数列表"""
        parameters = []
        
        # 路径参数
        if isinstance(url_data, dict):
            for var in url_data.get('variable', []):
                parameters.append({
                    'name': var.get('key', ''),
                    'in': 'path',
                    'required': True,
                    'type': 'string',
                    'description': var.get('description', ''),
                    'value': var.get('value', '')
                })
        
        # 查询参数
        for param in query_params:
            parameters.append({
                'name': param.get('name', ''),
                'in': 'query',
                'required': False,
                'type': 'string',
                'description': param.get('description', ''),
                'value': param.get('value', '')
            })
        
        return parameters
    
    def _generate_endpoint_id(self, method: str, path: str) -> str:
        """生成端点唯一ID"""
        content = f"{method}:{path}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_tags(self) -> list[str]:
        """获取所有解析到的标签（文件夹名称）"""
        return sorted(list(self.tags))
