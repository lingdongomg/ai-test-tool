"""
Swagger/OpenAPI 文档解析器
支持 OpenAPI 2.0 (Swagger) 和 OpenAPI 3.0+ 格式
"""

import json
import hashlib
import logging
from typing import Any
from pathlib import Path

from ..database.models import ApiEndpoint, EndpointSourceType

logger = logging.getLogger(__name__)

MAX_REF_DEPTH = 10


class SwaggerParser:
    """Swagger/OpenAPI 解析器"""

    def __init__(self) -> None:
        self.endpoints: list[ApiEndpoint] = []
        self.tags: set[str] = set()
        self.source_file: str = ""
        self._root_doc: dict[str, Any] = {}

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
        self._root_doc = data

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

    # ----------------------------------------------------------------
    # $ref 解析
    # ----------------------------------------------------------------

    def _resolve_ref(self, ref_path: str, depth: int = 0) -> dict[str, Any]:
        """
        解析 $ref 引用，返回引用指向的对象

        支持:
        - Swagger 2.0: #/definitions/ModelName
        - OpenAPI 3.0: #/components/schemas/ModelName
        - 通用 JSON Pointer: #/any/path/segments

        Args:
            ref_path: $ref 字符串，如 "#/definitions/User"
            depth: 当前递归深度

        Returns:
            解析后的对象；如果无法解析则返回空字典
        """
        if depth > MAX_REF_DEPTH:
            logger.warning(f"$ref 解析超过最大深度 {MAX_REF_DEPTH}: {ref_path}")
            return {"type": "object", "description": "circular reference"}

        if not ref_path or not ref_path.startswith("#/"):
            logger.warning(f"不支持的 $ref 格式（仅支持文档内部引用）: {ref_path}")
            return {}

        # 按 JSON Pointer 规范解析路径
        parts = ref_path[2:].split("/")
        current: Any = self._root_doc
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                logger.warning(f"$ref 引用目标不存在: {ref_path}")
                return {}

        if not isinstance(current, dict):
            return {}

        # 递归解析结果中可能包含的嵌套 $ref
        return self._resolve_schema(dict(current), depth + 1)

    def _resolve_schema(self, schema: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        """
        递归解析 schema 中所有 $ref 引用

        处理:
        - 顶层 $ref
        - properties 中每个字段的 $ref
        - items 中的 $ref (数组类型)
        - allOf / oneOf / anyOf 中的 $ref
        - additionalProperties 中的 $ref

        Args:
            schema: JSON Schema 对象
            depth: 当前递归深度

        Returns:
            所有 $ref 被展开后的 schema
        """
        if depth > MAX_REF_DEPTH:
            return {"type": "object", "description": "circular reference"}

        if not isinstance(schema, dict):
            return schema

        # 顶层 $ref — 用引用目标替换整个 schema
        if "$ref" in schema:
            resolved = self._resolve_ref(schema["$ref"], depth)
            # 保留 $ref 旁边的额外属性（如 description、nullable 等）
            extra = {k: v for k, v in schema.items() if k != "$ref"}
            if extra:
                resolved = {**resolved, **extra}
            return resolved

        result = dict(schema)

        # properties
        if "properties" in result and isinstance(result["properties"], dict):
            resolved_props = {}
            for name, prop in result["properties"].items():
                resolved_props[name] = self._resolve_schema(prop, depth + 1) if isinstance(prop, dict) else prop
            result["properties"] = resolved_props

        # items (数组)
        if "items" in result and isinstance(result["items"], dict):
            result["items"] = self._resolve_schema(result["items"], depth + 1)

        # allOf / oneOf / anyOf
        for keyword in ("allOf", "oneOf", "anyOf"):
            if keyword in result and isinstance(result[keyword], list):
                result[keyword] = [
                    self._resolve_schema(item, depth + 1) if isinstance(item, dict) else item
                    for item in result[keyword]
                ]
                # 对 allOf 做合并展平
                if keyword == "allOf":
                    result = self._merge_allof(result)

        # additionalProperties
        if "additionalProperties" in result and isinstance(result["additionalProperties"], dict):
            result["additionalProperties"] = self._resolve_schema(result["additionalProperties"], depth + 1)

        return result

    def _merge_allof(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        合并 allOf 中的多个 schema 为一个统一的 schema

        将所有子 schema 的 properties、required 合并到顶层
        """
        all_of = schema.pop("allOf", [])
        if not all_of:
            return schema

        merged_properties: dict[str, Any] = {}
        merged_required: list[str] = []

        # 先取顶层已有的 properties
        merged_properties.update(schema.get("properties", {}))
        merged_required.extend(schema.get("required", []))

        for sub_schema in all_of:
            if not isinstance(sub_schema, dict):
                continue
            merged_properties.update(sub_schema.get("properties", {}))
            merged_required.extend(sub_schema.get("required", []))
            # 继承 type
            if "type" in sub_schema and "type" not in schema:
                schema["type"] = sub_schema["type"]

        if merged_properties:
            schema["properties"] = merged_properties
        if merged_required:
            schema["required"] = list(dict.fromkeys(merged_required))  # 去重保序

        if "type" not in schema and merged_properties:
            schema["type"] = "object"

        return schema

    # ----------------------------------------------------------------
    # Swagger 2.0
    # ----------------------------------------------------------------

    def _parse_swagger_2(self, data: dict[str, Any]) -> None:
        """解析 Swagger 2.0 格式"""
        base_path = data.get('basePath', '').rstrip('/')  # 移除尾部斜杠
        paths = data.get('paths', {})

        # 解析全局标签
        for tag in data.get('tags', []):
            self.tags.add(tag.get('name', ''))

        for path, methods in paths.items():
            # 规范化路径：确保 path 以 / 开头，避免双斜杠
            normalized_path = path if path.startswith('/') else f"/{path}"
            # 如果 basePath 只是 "/" 则忽略，避免 //path 的情况
            if base_path and base_path != '/':
                full_path = f"{base_path}{normalized_path}"
            else:
                full_path = normalized_path

            for method, spec in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint = self._create_endpoint_from_swagger_2(
                        method=method.upper(),
                        path=full_path,
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

        # 解析参数（解析 $ref）
        parameters = []
        for param in spec.get('parameters', []):
            resolved_schema = self._resolve_schema(param.get('schema', {}))
            parameters.append({
                'name': param.get('name', ''),
                'in': param.get('in', ''),
                'required': param.get('required', False),
                'type': param.get('type', resolved_schema.get('type', '')),
                'description': param.get('description', ''),
                'schema': resolved_schema
            })

        # 解析请求体 (Swagger 2.0 中 body 参数)
        request_body = {}
        for param in spec.get('parameters', []):
            if param.get('in') == 'body':
                resolved_schema = self._resolve_schema(param.get('schema', {}))
                request_body = {
                    'required': param.get('required', False),
                    'schema': resolved_schema,
                    'description': param.get('description', '')
                }
                break

        # 解析响应（解析 $ref）
        responses = {}
        for status_code, response in spec.get('responses', {}).items():
            resolved_schema = self._resolve_schema(response.get('schema', {}))
            responses[status_code] = {
                'description': response.get('description', ''),
                'schema': resolved_schema
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

    # ----------------------------------------------------------------
    # OpenAPI 3.0+
    # ----------------------------------------------------------------

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

        # 解析参数（解析 $ref）
        parameters = []
        for param in spec.get('parameters', []):
            # 参数本身可能是 $ref
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])
            resolved_schema = self._resolve_schema(param.get('schema', {}))
            parameters.append({
                'name': param.get('name', ''),
                'in': param.get('in', ''),
                'required': param.get('required', False),
                'description': param.get('description', ''),
                'schema': resolved_schema
            })

        # 解析请求体 (OpenAPI 3.0)，解析 $ref
        request_body = {}
        if 'requestBody' in spec:
            rb = spec['requestBody']
            # requestBody 本身可能是 $ref
            if "$ref" in rb:
                rb = self._resolve_ref(rb["$ref"])
            content = rb.get('content', {})
            resolved_content = self._resolve_content(content)
            request_body = {
                'required': rb.get('required', False),
                'description': rb.get('description', ''),
                'content': resolved_content
            }

        # 解析响应（解析 $ref）
        responses = {}
        for status_code, response in spec.get('responses', {}).items():
            # response 本身可能是 $ref
            if "$ref" in response:
                response = self._resolve_ref(response["$ref"])
            content = response.get('content', {})
            resolved_content = self._resolve_content(content)
            responses[status_code] = {
                'description': response.get('description', ''),
                'content': resolved_content
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

    def _resolve_content(self, content: dict[str, Any]) -> dict[str, Any]:
        """解析 content 中各 media type 的 schema $ref"""
        resolved = {}
        for media_type, media_obj in content.items():
            if not isinstance(media_obj, dict):
                resolved[media_type] = media_obj
                continue
            resolved_media = dict(media_obj)
            if 'schema' in resolved_media:
                resolved_media['schema'] = self._resolve_schema(resolved_media['schema'])
            resolved[media_type] = resolved_media
        return resolved

    # ----------------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------------

    def _generate_endpoint_id(self, method: str, path: str) -> str:
        """生成端点唯一ID"""
        content = f"{method}:{path}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get_tags(self) -> list[str]:
        """获取所有解析到的标签"""
        return sorted(list(self.tags))
