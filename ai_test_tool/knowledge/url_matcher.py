# 该文件内容使用AI生成，注意识别准确性
"""
URL 模式匹配器

从 analyzer/api_knowledge_base.py 提取的 URL 匹配逻辑，
统一到 knowledge 模块，供 KnowledgeRetriever 使用。

三级匹配策略：
1. 精确路径匹配（分数 100）
2. 规范化路径匹配 — 数字 ID 替换为通配符（分数 80）
3. 路径段模糊匹配（分数最高 60）
"""

import re
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .models import KnowledgeItem

logger = logging.getLogger(__name__)


@dataclass
class UrlMatchResult:
    """URL 匹配结果"""
    item: KnowledgeItem
    score: float
    match_type: str  # "exact" | "normalized" | "segment"


class UrlPatternMatcher:
    """
    URL 模式匹配器

    从 knowledge_base 知识条目中提取 scope 字段（通常为 API 路径），
    构建索引，支持 URL 模式匹配检索。
    """

    def __init__(self):
        # 按精确路径索引: path_lower -> [KnowledgeItem]
        self._path_index: dict[str, list[KnowledgeItem]] = defaultdict(list)
        # 按规范化路径索引: normalized_path -> [KnowledgeItem]
        self._normalized_path_index: dict[str, list[KnowledgeItem]] = defaultdict(list)
        # 按路径段索引: segment -> [KnowledgeItem]
        self._segment_index: dict[str, list[KnowledgeItem]] = defaultdict(list)

    def build_index(self, items: list[KnowledgeItem]) -> int:
        """
        从知识条目构建 URL 索引

        使用知识条目的 scope 字段作为 API 路径进行索引。

        Args:
            items: 知识条目列表

        Returns:
            索引的条目数
        """
        self._path_index.clear()
        self._normalized_path_index.clear()
        self._segment_index.clear()

        count = 0
        for item in items:
            scope = (item.scope or "").strip()
            if not scope or not scope.startswith("/"):
                continue

            path_lower = scope.lower()

            # 精确路径索引
            self._path_index[path_lower].append(item)

            # 规范化路径索引：路径参数 {xxx} 和 :xxx 替换为 *
            normalized = re.sub(r'\{[^}]+\}', '*', path_lower)
            normalized = re.sub(r':[^/]+', '*', normalized)
            self._normalized_path_index[normalized].append(item)

            # 路径段索引
            segments = [
                s for s in scope.strip('/').split('/')
                if s and not s.startswith('{') and not s.startswith(':')
            ]
            for segment in segments:
                self._segment_index[segment.lower()].append(item)

            count += 1

        logger.debug(f"UrlPatternMatcher: indexed {count} items")
        return count

    def match(self, url: str, max_results: int = 10) -> list[UrlMatchResult]:
        """
        根据 URL 匹配知识条目

        Args:
            url: 请求 URL（可包含查询参数）
            max_results: 最大返回数

        Returns:
            按匹配分数降序排列的结果列表
        """
        # 提取路径部分
        path = url.split('?')[0]
        path_lower = path.lower()

        matches: dict[str, UrlMatchResult] = {}  # knowledge_id -> result

        # 1. 精确路径匹配（分数 100）
        if path_lower in self._path_index:
            for item in self._path_index[path_lower]:
                if item.knowledge_id not in matches:
                    matches[item.knowledge_id] = UrlMatchResult(
                        item=item, score=100.0, match_type="exact"
                    )

        # 2. 规范化路径匹配（分数 80）
        normalized = re.sub(r'/\d+', '/*', path_lower)
        if normalized in self._normalized_path_index:
            for item in self._normalized_path_index[normalized]:
                if item.knowledge_id not in matches:
                    matches[item.knowledge_id] = UrlMatchResult(
                        item=item, score=80.0, match_type="normalized"
                    )

        # 3. 路径段模糊匹配（分数最高 60）
        path_segments = [
            s.lower() for s in path.strip('/').split('/')
            if s and not s.isdigit()
        ]
        if path_segments:
            segment_counts: dict[str, int] = defaultdict(int)
            segment_items: dict[str, KnowledgeItem] = {}
            for segment in path_segments:
                if segment in self._segment_index:
                    for item in self._segment_index[segment]:
                        kid = item.knowledge_id
                        segment_counts[kid] += 1
                        segment_items[kid] = item

            for kid, match_count in segment_counts.items():
                if kid not in matches:
                    item = segment_items[kid]
                    scope_segments = [
                        s for s in (item.scope or "").strip('/').split('/')
                        if s and not s.startswith('{')
                    ]
                    total = max(len(path_segments), len(scope_segments), 1)
                    score = (match_count / total) * 60
                    if score > 5:  # 过滤太低的匹配
                        matches[kid] = UrlMatchResult(
                            item=item, score=score, match_type="segment"
                        )

        # 排序并截取
        sorted_results = sorted(matches.values(), key=lambda x: x.score, reverse=True)
        return sorted_results[:max_results]
