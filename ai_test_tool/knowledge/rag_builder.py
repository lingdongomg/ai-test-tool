"""
RAG上下文构建器
该文件内容使用AI生成，注意识别准确性

将检索到的知识转化为LLM可用的上下文格式
"""

import logging
from typing import Any

from .models import KnowledgeItem, KnowledgeSearchResult, RAGContext

logger = logging.getLogger(__name__)


# 知识类型的中文描述
TYPE_DESCRIPTIONS = {
    "project_config": "项目配置",
    "business_rule": "业务规则",
    "module_context": "模块知识",
    "test_experience": "测试经验"
}


class RAGContextBuilder:
    """
    RAG上下文构建器
    
    将检索到的知识转化为结构化的上下文文本，供LLM使用
    """
    
    def __init__(
        self,
        max_tokens: int = 2000,
        include_metadata: bool = True
    ):
        """
        Args:
            max_tokens: 最大token数量限制（估算）
            include_metadata: 是否包含元数据（类型、范围等）
        """
        self.max_tokens = max_tokens
        self.include_metadata = include_metadata
        
        # 大约每4个字符1个token（中英文混合估算）
        self.chars_per_token = 4
    
    def build(self, results: list[KnowledgeSearchResult]) -> RAGContext:
        """
        从检索结果构建RAG上下文
        
        Args:
            results: 知识检索结果列表（已按相关度排序）
        
        Returns:
            RAGContext对象
        """
        if not results:
            return RAGContext(
                context_text="",
                knowledge_items=[],
                token_count=0
            )
        
        # 提取知识条目
        items = [r.item for r in results]
        
        # 构建上下文文本
        context_text = self._format_context(items)
        
        # 估算token数量
        token_count = len(context_text) // self.chars_per_token
        
        # 如果超出限制，截断
        if token_count > self.max_tokens:
            context_text, items = self._truncate(items)
            token_count = len(context_text) // self.chars_per_token
        
        return RAGContext(
            context_text=context_text,
            knowledge_items=items,
            token_count=token_count
        )
    
    def build_from_items(self, items: list[KnowledgeItem]) -> RAGContext:
        """从知识条目直接构建上下文"""
        if not items:
            return RAGContext(
                context_text="",
                knowledge_items=[],
                token_count=0
            )
        
        context_text = self._format_context(items)
        token_count = len(context_text) // self.chars_per_token
        
        if token_count > self.max_tokens:
            context_text, items = self._truncate(items)
            token_count = len(context_text) // self.chars_per_token
        
        return RAGContext(
            context_text=context_text,
            knowledge_items=items,
            token_count=token_count
        )
    
    def _format_context(self, items: list[KnowledgeItem]) -> str:
        """
        格式化上下文文本
        """
        if not items:
            return ""
        
        sections = []
        sections.append("=== 相关知识库内容 ===\n")
        
        # 按类型分组
        grouped = self._group_by_type(items)
        
        for type_key, type_items in grouped.items():
            type_name = TYPE_DESCRIPTIONS.get(type_key, type_key)
            sections.append(f"\n【{type_name}】")
            
            for i, item in enumerate(type_items, 1):
                sections.append(self._format_item(item, i))
        
        sections.append("\n=== 知识库内容结束 ===")
        
        return "\n".join(sections)
    
    def _format_item(self, item: KnowledgeItem, index: int) -> str:
        """格式化单个知识条目"""
        lines = []
        
        lines.append(f"\n{index}. {item.title}")
        lines.append(f"   {item.content}")
        
        if self.include_metadata:
            metadata_parts = []
            if item.scope:
                metadata_parts.append(f"适用范围: {item.scope}")
            if item.tags:
                metadata_parts.append(f"标签: {', '.join(item.tags)}")
            
            if metadata_parts:
                lines.append(f"   [{'; '.join(metadata_parts)}]")
        
        return "\n".join(lines)
    
    def _group_by_type(self, items: list[KnowledgeItem]) -> dict[str, list[KnowledgeItem]]:
        """按类型分组"""
        grouped: dict[str, list[KnowledgeItem]] = {}
        
        # 定义类型顺序
        type_order = ["project_config", "business_rule", "module_context", "test_experience"]
        
        for item in items:
            if item.type not in grouped:
                grouped[item.type] = []
            grouped[item.type].append(item)
        
        # 按顺序排列
        ordered = {}
        for t in type_order:
            if t in grouped:
                ordered[t] = grouped[t]
        
        # 添加其他类型
        for t, items_list in grouped.items():
            if t not in ordered:
                ordered[t] = items_list
        
        return ordered
    
    def _truncate(self, items: list[KnowledgeItem]) -> tuple[str, list[KnowledgeItem]]:
        """
        截断以满足token限制
        
        策略：从后往前移除低优先级的知识
        """
        max_chars = self.max_tokens * self.chars_per_token
        
        # 逐个添加直到达到限制
        included_items = []
        current_text = "=== 相关知识库内容 ===\n"
        
        for item in items:
            item_text = self._format_item(item, len(included_items) + 1)
            
            if len(current_text) + len(item_text) + 50 <= max_chars:
                current_text += item_text + "\n"
                included_items.append(item)
            else:
                break
        
        current_text += "\n=== 知识库内容结束 ==="
        
        return current_text, included_items
    
    def format_for_prompt(
        self,
        context: RAGContext,
        prefix: str = "",
        suffix: str = ""
    ) -> str:
        """
        格式化为可直接插入prompt的文本
        
        Args:
            context: RAG上下文
            prefix: 前缀文本
            suffix: 后缀文本
        
        Returns:
            格式化后的文本
        """
        if context.is_empty:
            return ""
        
        parts = []
        if prefix:
            parts.append(prefix)
        parts.append(context.context_text)
        if suffix:
            parts.append(suffix)
        
        return "\n".join(parts)
    
    def build_test_generation_context(
        self,
        results: list[KnowledgeSearchResult],
        api_info: dict[str, Any] | None = None
    ) -> str:
        """
        构建测试生成专用的上下文
        
        Args:
            results: 检索结果
            api_info: API信息（method, path等）
        
        Returns:
            格式化的上下文文本
        """
        rag_context = self.build(results)
        
        if rag_context.is_empty:
            return ""
        
        # 添加使用说明
        prompt_parts = [
            "在生成测试用例时，请参考以下项目知识库中的相关信息：",
            "",
            rag_context.context_text,
            "",
            "请确保生成的测试用例符合上述知识中描述的规则和配置要求。"
        ]
        
        return "\n".join(prompt_parts)
