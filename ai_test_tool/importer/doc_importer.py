"""
接口文档导入器
统一处理 Swagger 和 Postman 格式的导入
支持增量更新：更新已有接口、新增缺失接口
"""

import json
from typing import Any, Literal
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from .swagger_parser import SwaggerParser
from .postman_parser import PostmanParser
from ..database.models import ApiEndpoint, ApiTag


class UpdateStrategy(Enum):
    """更新策略"""
    MERGE = "merge"          # 合并更新：更新已有，新增缺失
    REPLACE = "replace"      # 完全替换：删除旧数据，导入新数据
    SKIP = "skip"            # 跳过已有：仅新增缺失


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    message: str
    endpoints: list[ApiEndpoint] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # 增量更新统计
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    deleted_count: int = 0
    
    @property
    def endpoint_count(self) -> int:
        return len(self.endpoints)
    
    @property
    def tag_count(self) -> int:
        return len(self.tags)


@dataclass
class EndpointDiff:
    """接口差异"""
    endpoint_id: str
    method: str
    path: str
    name: str
    status: Literal["new", "updated", "unchanged", "deleted"]
    changes: list[str] = field(default_factory=list)  # 变更字段列表


class DocImporter:
    """接口文档导入器"""
    
    def __init__(self) -> None:
        self.swagger_parser = SwaggerParser()
        self.postman_parser = PostmanParser()
    
    def import_file(
        self,
        file_path: str,
        doc_type: Literal["swagger", "postman", "auto"] = "auto"
    ) -> ImportResult:
        """
        导入接口文档文件
        
        Args:
            file_path: 文件路径
            doc_type: 文档类型，支持 swagger/postman/auto
        
        Returns:
            ImportResult: 导入结果
        """
        path = Path(file_path)
        
        if not path.exists():
            return ImportResult(
                success=False,
                message=f"文件不存在: {file_path}",
                errors=[f"文件不存在: {file_path}"]
            )
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return ImportResult(
                success=False,
                message=f"JSON 解析失败: {e}",
                errors=[f"JSON 解析失败: {e}"]
            )
        except Exception as e:
            return ImportResult(
                success=False,
                message=f"文件读取失败: {e}",
                errors=[f"文件读取失败: {e}"]
            )
        
        return self.import_json(data, doc_type, path.name)
    
    def import_json(
        self,
        data: dict[str, Any],
        doc_type: Literal["swagger", "postman", "auto"] = "auto",
        source_file: str = "import.json"
    ) -> ImportResult:
        """
        导入 JSON 数据
        
        Args:
            data: JSON 数据
            doc_type: 文档类型
            source_file: 来源文件名
        
        Returns:
            ImportResult: 导入结果
        """
        # 自动检测文档类型
        if doc_type == "auto":
            doc_type = self._detect_doc_type(data)
            if doc_type == "auto":
                return ImportResult(
                    success=False,
                    message="无法自动识别文档类型，请手动指定 swagger 或 postman",
                    errors=["无法自动识别文档类型"]
                )
        
        try:
            if doc_type == "swagger":
                self.swagger_parser.source_file = source_file
                endpoints = self.swagger_parser.parse(data)
                tags = self.swagger_parser.get_tags()
            else:
                self.postman_parser.source_file = source_file
                endpoints = self.postman_parser.parse(data)
                tags = self.postman_parser.get_tags()
            
            return ImportResult(
                success=True,
                message=f"成功解析 {len(endpoints)} 个接口，{len(tags)} 个标签",
                endpoints=endpoints,
                tags=tags
            )
        except Exception as e:
            return ImportResult(
                success=False,
                message=f"解析失败: {e}",
                errors=[str(e)]
            )
    
    def compare_endpoints(
        self,
        new_endpoints: list[ApiEndpoint],
        existing_endpoints: list[ApiEndpoint]
    ) -> list[EndpointDiff]:
        """
        比较新旧接口列表，生成差异报告
        
        Args:
            new_endpoints: 新导入的接口列表
            existing_endpoints: 已存在的接口列表
            
        Returns:
            差异列表
        """
        diffs: list[EndpointDiff] = []
        
        # 构建已存在接口的索引（按 method + path）
        existing_map: dict[str, ApiEndpoint] = {}
        for ep in existing_endpoints:
            key = f"{ep.method.upper()}:{ep.path}"
            existing_map[key] = ep
        
        new_keys: set[str] = set()
        
        # 检查新接口
        for new_ep in new_endpoints:
            key = f"{new_ep.method.upper()}:{new_ep.path}"
            new_keys.add(key)
            
            if key in existing_map:
                # 已存在，检查是否有变更
                old_ep = existing_map[key]
                changes = self._compare_endpoint_fields(old_ep, new_ep)
                
                if changes:
                    diffs.append(EndpointDiff(
                        endpoint_id=old_ep.endpoint_id,
                        method=new_ep.method,
                        path=new_ep.path,
                        name=new_ep.name,
                        status="updated",
                        changes=changes
                    ))
                else:
                    diffs.append(EndpointDiff(
                        endpoint_id=old_ep.endpoint_id,
                        method=new_ep.method,
                        path=new_ep.path,
                        name=new_ep.name,
                        status="unchanged"
                    ))
            else:
                # 新接口
                diffs.append(EndpointDiff(
                    endpoint_id=new_ep.endpoint_id,
                    method=new_ep.method,
                    path=new_ep.path,
                    name=new_ep.name,
                    status="new"
                ))
        
        # 检查已删除的接口
        for key, old_ep in existing_map.items():
            if key not in new_keys:
                diffs.append(EndpointDiff(
                    endpoint_id=old_ep.endpoint_id,
                    method=old_ep.method,
                    path=old_ep.path,
                    name=old_ep.name,
                    status="deleted"
                ))
        
        return diffs
    
    def _compare_endpoint_fields(
        self,
        old_ep: ApiEndpoint,
        new_ep: ApiEndpoint
    ) -> list[str]:
        """比较两个接口的字段差异"""
        changes: list[str] = []
        
        # 比较基本字段
        if old_ep.name != new_ep.name:
            changes.append("name")
        if old_ep.description != new_ep.description:
            changes.append("description")
        if old_ep.summary != new_ep.summary:
            changes.append("summary")
        
        # 比较参数（转为JSON字符串比较）
        old_params = json.dumps(old_ep.parameters, sort_keys=True) if old_ep.parameters else ""
        new_params = json.dumps(new_ep.parameters, sort_keys=True) if new_ep.parameters else ""
        if old_params != new_params:
            changes.append("parameters")
        
        # 比较请求体
        old_body = json.dumps(old_ep.request_body, sort_keys=True) if old_ep.request_body else ""
        new_body = json.dumps(new_ep.request_body, sort_keys=True) if new_ep.request_body else ""
        if old_body != new_body:
            changes.append("request_body")
        
        # 比较响应
        old_resp = json.dumps(old_ep.responses, sort_keys=True) if old_ep.responses else ""
        new_resp = json.dumps(new_ep.responses, sort_keys=True) if new_ep.responses else ""
        if old_resp != new_resp:
            changes.append("responses")
        
        # 比较标签
        if set(old_ep.tags or []) != set(new_ep.tags or []):
            changes.append("tags")
        
        return changes
    
    def apply_import(
        self,
        new_endpoints: list[ApiEndpoint],
        existing_endpoints: list[ApiEndpoint],
        strategy: UpdateStrategy = UpdateStrategy.MERGE
    ) -> tuple[list[ApiEndpoint], list[ApiEndpoint], list[str]]:
        """
        应用导入策略，返回需要创建、更新、删除的接口
        
        Args:
            new_endpoints: 新导入的接口
            existing_endpoints: 已存在的接口
            strategy: 更新策略
            
        Returns:
            (to_create, to_update, to_delete_ids)
        """
        to_create: list[ApiEndpoint] = []
        to_update: list[ApiEndpoint] = []
        to_delete_ids: list[str] = []
        
        # 构建已存在接口的索引
        existing_map: dict[str, ApiEndpoint] = {}
        for ep in existing_endpoints:
            key = f"{ep.method.upper()}:{ep.path}"
            existing_map[key] = ep
        
        new_keys: set[str] = set()
        
        for new_ep in new_endpoints:
            key = f"{new_ep.method.upper()}:{new_ep.path}"
            new_keys.add(key)
            
            if key in existing_map:
                old_ep = existing_map[key]
                
                if strategy == UpdateStrategy.SKIP:
                    # 跳过已有
                    continue
                elif strategy in (UpdateStrategy.MERGE, UpdateStrategy.REPLACE):
                    # 检查是否有变更
                    changes = self._compare_endpoint_fields(old_ep, new_ep)
                    if changes:
                        # 保留原有的 endpoint_id
                        new_ep.endpoint_id = old_ep.endpoint_id
                        new_ep.id = old_ep.id
                        to_update.append(new_ep)
            else:
                # 新接口
                to_create.append(new_ep)
        
        # 完全替换模式下，删除不在新文档中的接口
        if strategy == UpdateStrategy.REPLACE:
            for key, old_ep in existing_map.items():
                if key not in new_keys:
                    to_delete_ids.append(old_ep.endpoint_id)
        
        return to_create, to_update, to_delete_ids
    
    def _detect_doc_type(self, data: dict[str, Any]) -> Literal["swagger", "postman", "auto"]:
        """自动检测文档类型"""
        # Swagger/OpenAPI 特征
        if 'swagger' in data or 'openapi' in data:
            return "swagger"
        
        # Postman Collection 特征
        info = data.get('info', {})
        if info:
            schema = info.get('schema', '')
            if 'postman' in schema.lower():
                return "postman"
            if '_postman_id' in info:
                return "postman"
        
        # 检查是否有 item 数组（Postman 特征）
        if 'item' in data and isinstance(data['item'], list):
            return "postman"
        
        # 检查是否有 paths 对象（Swagger 特征）
        if 'paths' in data and isinstance(data['paths'], dict):
            return "swagger"
        
        return "auto"
    
    def create_tags_from_result(self, result: ImportResult) -> list[ApiTag]:
        """从导入结果创建标签对象"""
        return [
            ApiTag(
                name=tag,
                description=f"从接口文档导入的标签: {tag}",
                color=self._generate_tag_color(tag)
            )
            for tag in result.tags
        ]
    
    def _generate_tag_color(self, tag_name: str) -> str:
        """根据标签名生成颜色"""
        colors = [
            "#1890ff",  # 蓝色
            "#52c41a",  # 绿色
            "#faad14",  # 黄色
            "#f5222d",  # 红色
            "#722ed1",  # 紫色
            "#13c2c2",  # 青色
            "#eb2f96",  # 粉色
            "#fa8c16",  # 橙色
        ]
        # 根据标签名的 hash 选择颜色
        index = hash(tag_name) % len(colors)
        return colors[index]
