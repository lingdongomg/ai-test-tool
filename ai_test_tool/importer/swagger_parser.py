"""
Swagger/OpenAPI 文档解析器
支持 OpenAPI 2.0 (Swagger) 和 OpenAPI 3.0+ 格式
"""

import json
import hashlib
from typing import Any
from pathlib import Path

from ..database.models import ApiEndpoint, EndpointSourceType


class SwaggerParser:
    """Swagger/OpenAPI 解析器"""
    
    def __init__(self) -> None:
        self.endpoints: list[ApiEndpoint] = []
        self.tags: set[str] = set()
        self.source_file: str = ""
    
    def parse_file(self, file_path: str) -> list[ApiEndpoint]:
        """解析 Swagger/OpenAPI JSON 文件"""
        path = Path(file_path)
        self.source_file = path.name
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self.parse(data)
    
    def parse(self, data: dict[str, Any]) -> list[ApiEndpoint]:
        """解析 Swagger/OpenAPI 数据"""
        self.endpoints = []
        self.tags = set()
        
        # 检测版本
        if 'swagger' in data:
            # OpenAPI 2.0 (Swagger)
            self._parse_swagger_2(data)
        elif 'openapi' in data:
            # OpenAPI 3.0+
            self._parse_openapi_3(data)
        else:
            raise ValueError("无法识别的文档格式，需要 Swagger 2.0 或 OpenAPI 3.0+ 格式")
        
        return self.endpoints
    
    def _parse_swagger_2(self, data: dict[str, Any]) -> None:
        """解析 Swagger 2.0 格式"""
        base_path = data.get('basePath', '')
        paths = data.get('paths', {})
        
        # 解析全局标签
        for tag in data.get('tags', []):
            self.tags.add(tag.get('name', ''))
        
        for path, methods in paths.items():
            full_path = f"{base_path}{path}" if base_path else path
            
            for method, spec in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint = self._create_endpoint_from_swagger_2(
                        method=method.upper(),
                        path=full_path,
                        spec=spec
                    )
                    self.endpoints.append(endpoint)
    
    def _parse_openapi_3(self, data: dict[str, Any]) -> None:
        """解析 OpenAPI 3.0+ 格式"""
        paths = data.get('paths', {})
        
        # 解析全局标签
        for tag in data.get('tags', []):
            self.tags.add(tag.get('name', ''))
        
        for path, methods in paths.items():
            for method, spec in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint = self._create_endpoint_from_openapi_3(
                        method=method.upper(),
                        path=path,
                        spec=spec
                    )
                    self.endpoints.append(endpoint)
    
    def _create_endpoint_from_swagger_2(
        self,
        method: str,
        path: str,
        spec: dict[str, Any]
    ) -> ApiEndpoint:
        """从 Swagger 2.0 规范创建端点"""
        # 生成唯一ID
        endpoint_id = self._generate_endpoint_id(method, path)
        
        # 提取标签
        tags = spec.get('tags', [])
        for tag in tags:
            self.tags.add(tag)
        
        # 解析参数
        parameters = []
        for param in spec.get('parameters', []):
            parameters.append({
                'name': param.get('name', ''),
                'in': param.get('in', ''),
                'required': param.get('required', False),
                'type': param.get('type', ''),
                'description': param.get('description', ''),
                'schema': param.get('schema', {})
            })
        
        # 解析请求体 (Swagger 2.0 中 body 参数)
        request_body = {}
        for param in spec.get('parameters', []):
            if param.get('in') == 'body':
                request_body = {
                    'required': param.get('required', False),
                    'schema': param.get('schema', {}),
                    'description': param.get('description', '')
                }
                break
        
        # 解析响应
        responses = {}
        for status_code, response in spec.get('responses', {}).items():
            responses[status_code] = {
                'description': response.get('description', ''),
                'schema': response.get('schema', {})
            }
        
        return ApiEndpoint(
            endpoint_id=endpoint_id,
            name=spec.get('summary', '') or spec.get('operationId', f"{method} {path}"),
            description=spec.get('description', ''),
            method=method,
            path=path,
            summary=spec.get('summary', ''),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=spec.get('security', []),
            source_type=EndpointSourceType.SWAGGER,
            source_file=self.source_file,
            is_deprecated=spec.get('deprecated', False),
            tags=tags
        )
    
    def _create_endpoint_from_openapi_3(
        self,
        method: str,
        path: str,
        spec: dict[str, Any]
    ) -> ApiEndpoint:
        """从 OpenAPI 3.0 规范创建端点"""
        endpoint_id = self._generate_endpoint_id(method, path)
        
        # 提取标签
        tags = spec.get('tags', [])
        for tag in tags:
            self.tags.add(tag)
        
        # 解析参数
        parameters = []
        for param in spec.get('parameters', []):
            parameters.append({
                'name': param.get('name', ''),
                'in': param.get('in', ''),
                'required': param.get('required', False),
                'description': param.get('description', ''),
                'schema': param.get('schema', {})
            })
        
        # 解析请求体 (OpenAPI 3.0)
        request_body = {}
        if 'requestBody' in spec:
            rb = spec['requestBody']
            request_body = {
                'required': rb.get('required', False),
                'description': rb.get('description', ''),
                'content': rb.get('content', {})
            }
        
        # 解析响应
        responses = {}
        for status_code, response in spec.get('responses', {}).items():
            responses[status_code] = {
                'description': response.get('description', ''),
                'content': response.get('content', {})
            }
        
        return ApiEndpoint(
            endpoint_id=endpoint_id,
            name=spec.get('summary', '') or spec.get('operationId', f"{method} {path}"),
            description=spec.get('description', ''),
            method=method,
            path=path,
            summary=spec.get('summary', ''),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=spec.get('security', []),
            source_type=EndpointSourceType.SWAGGER,
            source_file=self.source_file,
            is_deprecated=spec.get('deprecated', False),
            tags=tags
        )
    
    def _generate_endpoint_id(self, method: str, path: str) -> str:
        """生成端点唯一ID"""
        content = f"{method}:{path}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_tags(self) -> list[str]:
        """获取所有解析到的标签"""
        return sorted(list(self.tags))
