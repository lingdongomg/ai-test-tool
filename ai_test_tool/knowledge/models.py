"""
知识库领域模型
该文件内容使用AI生成，注意识别准确性
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class KnowledgeTypeEnum(str, Enum):
    """知识类型枚举"""
    PROJECT_CONFIG = "project_config"      # 项目配置知识
    BUSINESS_RULE = "business_rule"        # 业务规则知识
    MODULE_CONTEXT = "module_context"      # 模块上下文知识
    TEST_EXPERIENCE = "test_experience"    # 测试经验知识


@dataclass
class KnowledgeItem:
    """知识条目DTO"""
    knowledge_id: str
    title: str
    content: str
    type: str = KnowledgeTypeEnum.PROJECT_CONFIG.value
    category: str = ""
    scope: str = ""
    priority: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_text(self) -> str:
        """转换为文本（用于embedding）"""
        parts = [self.title, self.content]
        if self.category:
            parts.append(f"分类: {self.category}")
        if self.scope:
            parts.append(f"适用范围: {self.scope}")
        if self.tags:
            parts.append(f"标签: {', '.join(self.tags)}")
        return "\n".join(parts)


@dataclass
class KnowledgeSearchResult:
    """知识检索结果"""
    item: KnowledgeItem
    score: float  # 相似度分数 0-1
    source: str = "semantic"  # 匹配来源: semantic, keyword, scope
    
    def __lt__(self, other: "KnowledgeSearchResult") -> bool:
        return self.score < other.score


@dataclass
class KnowledgeContext:
    """知识检索上下文"""
    query: str  # 查询文本
    types: list[str] = field(default_factory=list)  # 限制知识类型
    tags: list[str] = field(default_factory=list)  # 限制标签
    scope: str = ""  # 限制范围（如接口路径）
    top_k: int = 5  # 返回数量
    min_score: float = 0.3  # 最低相似度阈值


@dataclass
class RAGContext:
    """RAG上下文"""
    context_text: str  # 格式化的上下文文本
    knowledge_items: list[KnowledgeItem]  # 原始知识条目
    token_count: int = 0  # 估算的token数量
    
    @property
    def is_empty(self) -> bool:
        return len(self.knowledge_items) == 0


@dataclass
class KnowledgeSuggestion:
    """知识建议（从学习中提取）"""
    title: str
    content: str
    type: str
    category: str = ""
    scope: str = ""
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 置信度 0-1
    source_ref: str = ""  # 来源引用
    reason: str = ""  # 提取原因
