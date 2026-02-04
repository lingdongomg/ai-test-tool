"""
接口文档RAG知识库
将接口文档构建为知识库，供AI分析时检索使用
Python 3.13+ 兼容
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict

from ..database.models import ApiEndpoint, ApiTag


@dataclass
class EndpointKnowledge:
    """接口知识条目"""
    endpoint_id: str
    method: str
    path: str
    name: str
    summary: str
    description: str
    tags: list[str]
    parameters: list[dict[str, Any]]
    request_body: dict[str, Any]
    responses: dict[str, Any]
    
    # 用于匹配的规范化路径（去除路径参数）
    normalized_path: str = ""
    # 路径段用于模糊匹配
    path_segments: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        # 规范化路径，将路径参数替换为通配符
        import re
        self.normalized_path = re.sub(r'\{[^}]+\}', '*', self.path)
        self.normalized_path = re.sub(r':[^/]+', '*', self.normalized_path)
        # 提取路径段
        self.path_segments = [s for s in self.path.strip('/').split('/') if s and not s.startswith('{')]
    
    def to_context_string(self) -> str:
        """转换为上下文字符串，供AI使用"""
        lines = [
            f"接口: {self.method} {self.path}",
            f"名称: {self.name}",
        ]
        if self.summary:
            lines.append(f"摘要: {self.summary}")
        if self.description:
            lines.append(f"描述: {self.description}")
        if self.tags:
            lines.append(f"标签: {', '.join(self.tags)}")
        if self.parameters:
            params_str = ", ".join([
                f"{p.get('name')}({p.get('in', 'query')})"
                for p in self.parameters[:5]
            ])
            if len(self.parameters) > 5:
                params_str += f" ... 等{len(self.parameters)}个参数"
            lines.append(f"参数: {params_str}")
        if self.request_body:
            lines.append("请求体: 有")
        return "\n".join(lines)


class ApiKnowledgeBase:
    """接口文档知识库"""
    
    def __init__(self):
        # 所有接口知识
        self._endpoints: dict[str, EndpointKnowledge] = {}
        # 按路径索引
        self._path_index: dict[str, list[str]] = defaultdict(list)
        # 按规范化路径索引
        self._normalized_path_index: dict[str, list[str]] = defaultdict(list)
        # 按标签索引
        self._tag_index: dict[str, list[str]] = defaultdict(list)
        # 按方法索引
        self._method_index: dict[str, list[str]] = defaultdict(list)
        # 路径段索引（用于模糊匹配）
        self._segment_index: dict[str, list[str]] = defaultdict(list)
        # 所有标签
        self._tags: dict[str, ApiTag] = {}
    
    def load_from_endpoints(self, endpoints: list[ApiEndpoint], tags: list[ApiTag] | None = None) -> int:
        """
        从接口端点列表加载知识库
        
        Args:
            endpoints: 接口端点列表
            tags: 标签列表（可选）
            
        Returns:
            加载的接口数量
        """
        # 加载标签
        if tags:
            for tag in tags:
                self._tags[tag.name] = tag
        
        count = 0
        for ep in endpoints:
            knowledge = EndpointKnowledge(
                endpoint_id=ep.endpoint_id,
                method=ep.method.upper(),
                path=ep.path,
                name=ep.name,
                summary=ep.summary or "",
                description=ep.description or "",
                tags=ep.tags if ep.tags else [],
                parameters=ep.parameters if ep.parameters else [],
                request_body=ep.request_body if ep.request_body else {},
                responses=ep.responses if ep.responses else {}
            )
            
            self._add_to_index(knowledge)
            count += 1
        
        return count
    
    def _add_to_index(self, knowledge: EndpointKnowledge) -> None:
        """添加到索引"""
        eid = knowledge.endpoint_id
        self._endpoints[eid] = knowledge
        
        # 路径索引
        self._path_index[knowledge.path.lower()].append(eid)
        
        # 规范化路径索引
        self._normalized_path_index[knowledge.normalized_path.lower()].append(eid)
        
        # 标签索引
        for tag in knowledge.tags:
            self._tag_index[tag.lower()].append(eid)
        
        # 方法索引
        self._method_index[knowledge.method].append(eid)
        
        # 路径段索引
        for segment in knowledge.path_segments:
            self._segment_index[segment.lower()].append(eid)
    
    def search_by_url(self, url: str, method: str = "") -> list[EndpointKnowledge]:
        """
        根据URL搜索匹配的接口
        
        Args:
            url: 请求URL
            method: HTTP方法（可选）
            
        Returns:
            匹配的接口列表（按相关度排序）
        """
        import re
        
        # 提取路径部分
        path = url.split('?')[0]
        path_lower = path.lower()
        method_upper = method.upper() if method else ""
        
        matches: dict[str, float] = {}  # endpoint_id -> score
        
        # 1. 精确路径匹配（最高优先级）
        if path_lower in self._path_index:
            for eid in self._path_index[path_lower]:
                if not method_upper or self._endpoints[eid].method == method_upper:
                    matches[eid] = 100.0
        
        # 2. 规范化路径匹配
        normalized = re.sub(r'/\d+', '/*', path_lower)  # 数字ID替换为通配符
        if normalized in self._normalized_path_index:
            for eid in self._normalized_path_index[normalized]:
                if eid not in matches:
                    if not method_upper or self._endpoints[eid].method == method_upper:
                        matches[eid] = 80.0
        
        # 3. 路径段匹配（模糊匹配）
        path_segments = [s.lower() for s in path.strip('/').split('/') if s and not s.isdigit()]
        if path_segments:
            segment_matches: dict[str, int] = defaultdict(int)
            for segment in path_segments:
                if segment in self._segment_index:
                    for eid in self._segment_index[segment]:
                        segment_matches[eid] += 1
            
            for eid, match_count in segment_matches.items():
                if eid not in matches:
                    # 计算匹配度
                    total_segments = len(self._endpoints[eid].path_segments)
                    if total_segments > 0:
                        score = (match_count / max(len(path_segments), total_segments)) * 60
                        if not method_upper or self._endpoints[eid].method == method_upper:
                            matches[eid] = score
        
        # 排序并返回
        sorted_eids = sorted(matches.keys(), key=lambda x: matches[x], reverse=True)
        return [self._endpoints[eid] for eid in sorted_eids[:10]]
    
    def search_by_tag(self, tag: str) -> list[EndpointKnowledge]:
        """根据标签搜索接口"""
        tag_lower = tag.lower()
        eids = self._tag_index.get(tag_lower, [])
        return [self._endpoints[eid] for eid in eids]
    
    def get_all_tags(self) -> list[str]:
        """获取所有标签"""
        return list(self._tag_index.keys())
    
    def get_tag_statistics(self) -> dict[str, int]:
        """获取标签统计"""
        return {tag: len(eids) for tag, eids in self._tag_index.items()}
    
    def get_all_endpoints(self) -> list[EndpointKnowledge]:
        """获取所有接口"""
        return list(self._endpoints.values())
    
    def get_endpoints_summary(self, max_count: int = 100) -> str:
        """
        获取接口摘要，用于AI上下文
        
        Args:
            max_count: 最大接口数
            
        Returns:
            摘要字符串
        """
        lines = ["## 接口文档概览\n"]
        
        # 按标签分组
        tag_groups: dict[str, list[EndpointKnowledge]] = defaultdict(list)
        untagged: list[EndpointKnowledge] = []
        
        for ep in list(self._endpoints.values())[:max_count]:
            if ep.tags:
                for tag in ep.tags:
                    tag_groups[tag].append(ep)
            else:
                untagged.append(ep)
        
        # 输出分组信息
        for tag, eps in sorted(tag_groups.items()):
            lines.append(f"\n### {tag} ({len(eps)}个接口)")
            for ep in eps[:10]:
                lines.append(f"- {ep.method} {ep.path}: {ep.name}")
            if len(eps) > 10:
                lines.append(f"  ... 等{len(eps)}个接口")
        
        if untagged:
            lines.append(f"\n### 未分类 ({len(untagged)}个接口)")
            for ep in untagged[:10]:
                lines.append(f"- {ep.method} {ep.path}: {ep.name}")
        
        return "\n".join(lines)
    
    def build_rag_context(
        self,
        urls: list[str],
        methods: list[str] | None = None,
        max_results: int = 20
    ) -> str:
        """
        为一组URL构建RAG上下文
        
        Args:
            urls: URL列表
            methods: 对应的HTTP方法列表（可选）
            max_results: 最大结果数
            
        Returns:
            RAG上下文字符串
        """
        if not methods:
            methods = [""] * len(urls)
        
        # 搜索匹配的接口
        matched: dict[str, tuple[EndpointKnowledge, str]] = {}  # endpoint_id -> (knowledge, matched_url)
        unmatched_urls: list[str] = []
        
        for url, method in zip(urls, methods):
            results = self.search_by_url(url, method)
            if results:
                for r in results[:2]:  # 每个URL最多取2个匹配
                    if r.endpoint_id not in matched:
                        matched[r.endpoint_id] = (r, url)
            else:
                unmatched_urls.append(url)
        
        # 构建上下文
        lines = ["## 接口文档参考\n"]
        lines.append("以下是与待分析请求相关的接口文档信息：\n")
        
        count = 0
        for eid, (knowledge, matched_url) in matched.items():
            if count >= max_results:
                break
            lines.append(f"### 接口 {count + 1}")
            lines.append(knowledge.to_context_string())
            lines.append("")
            count += 1
        
        if unmatched_urls:
            lines.append("\n## 未匹配的请求URL")
            lines.append("以下URL在接口文档中未找到匹配，可能是：")
            lines.append("1. 第三方接口")
            lines.append("2. 接口文档未收录")
            lines.append("3. 新增接口\n")
            for url in unmatched_urls[:20]:
                lines.append(f"- {url}")
        
        return "\n".join(lines)
    
    def analyze_coverage(self, urls: list[str], methods: list[str] | None = None) -> dict[str, Any]:
        """
        分析日志URL与接口文档的覆盖情况
        
        Args:
            urls: 日志中的URL列表
            methods: 对应的HTTP方法列表（可选）
            
        Returns:
            覆盖分析结果
        """
        if not methods:
            methods = [""] * len(urls)
        
        # 统计
        matched_urls: list[dict[str, Any]] = []
        unmatched_urls: list[str] = []
        matched_endpoints: set[str] = set()
        
        for url, method in zip(urls, methods):
            results = self.search_by_url(url, method)
            if results:
                best_match = results[0]
                matched_endpoints.add(best_match.endpoint_id)
                matched_urls.append({
                    "url": url,
                    "method": method,
                    "matched_endpoint": {
                        "path": best_match.path,
                        "name": best_match.name,
                        "tags": best_match.tags
                    }
                })
            else:
                unmatched_urls.append(url)
        
        # 计算未被调用的接口
        all_endpoint_ids = set(self._endpoints.keys())
        uncalled_endpoints = all_endpoint_ids - matched_endpoints
        uncalled_list = [
            {
                "path": self._endpoints[eid].path,
                "method": self._endpoints[eid].method,
                "name": self._endpoints[eid].name,
                "tags": self._endpoints[eid].tags
            }
            for eid in uncalled_endpoints
        ]
        
        return {
            "total_log_urls": len(urls),
            "matched_count": len(matched_urls),
            "unmatched_count": len(unmatched_urls),
            "match_rate": f"{len(matched_urls) / len(urls) * 100:.1f}%" if urls else "0%",
            "total_doc_endpoints": len(self._endpoints),
            "called_endpoints": len(matched_endpoints),
            "uncalled_endpoints": len(uncalled_endpoints),
            "doc_coverage": f"{len(matched_endpoints) / len(self._endpoints) * 100:.1f}%" if self._endpoints else "0%",
            "unmatched_urls": unmatched_urls[:50],  # 可能是第三方接口或文档遗漏
            "uncalled_endpoints_list": uncalled_list[:50],  # 文档中有但日志中没调用的接口
            "matched_details": matched_urls[:100]
        }
    
    def suggest_tags_for_url(self, url: str, method: str = "") -> list[str]:
        """
        根据URL建议标签
        
        Args:
            url: 请求URL
            method: HTTP方法
            
        Returns:
            建议的标签列表
        """
        results = self.search_by_url(url, method)
        tags: dict[str, int] = defaultdict(int)
        
        for r in results:
            for tag in r.tags:
                tags[tag] += 1
        
        # 按出现次数排序
        sorted_tags = sorted(tags.keys(), key=lambda x: tags[x], reverse=True)
        return sorted_tags[:5]
    
    @property
    def size(self) -> int:
        """知识库大小"""
        return len(self._endpoints)
    
    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return len(self._endpoints) == 0
