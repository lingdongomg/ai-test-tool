"""
知识库领域模型
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class KnowledgeTypeEnum(str, Enum):
    """知识类型枚举（V2 扩展为 8 种 + 旧类型兼容）"""
    # V2 主要类型
    AUTH_CONFIG = "auth_config"                    # 认证配置知识
    ERROR_PATTERN = "error_pattern"                # 错误模式知识
    PERFORMANCE_BASELINE = "performance_baseline"  # 性能基线知识
    BUSINESS_RULE = "business_rule"                # 业务规则知识
    API_DEPENDENCY = "api_dependency"              # API 依赖关系知识
    SECURITY_RULE = "security_rule"                # 安全规则知识
    ENV_CONFIG = "env_config"                      # 环境配置知识
    TEST_EXPERIENCE = "test_experience"            # 测试经验知识
    # 旧类型（向后兼容）
    PROJECT_CONFIG = "project_config"
    MODULE_CONTEXT = "module_context"


# V2 知识类型的二级子分类定义
KNOWLEDGE_SUB_CATEGORIES: dict[str, list[str]] = {
    "auth_config": ["bearer_token", "cookie", "api_key", "oauth2", "basic_auth"],
    "error_pattern": ["client_error_4xx", "server_error_5xx", "timeout", "connection", "rate_limit"],
    "performance_baseline": ["latency_p50", "latency_p90", "latency_p99", "throughput", "error_rate"],
    "business_rule": ["param_constraint", "state_machine", "rate_limit", "data_format"],
    "api_dependency": ["call_chain", "prerequisite", "data_dependency"],
    "security_rule": ["input_validation", "auth_requirement", "sensitive_data", "injection"],
    "env_config": ["base_url", "common_header", "cors", "proxy"],
    "test_experience": ["edge_case", "regression", "flaky_test", "boundary"],
}

# 旧类型 → 新类型映射关键词规则
_OLD_TYPE_MIGRATION_KEYWORDS: dict[str, list[tuple[list[str], str]]] = {
    "project_config": [
        (["auth", "token", "bearer", "认证", "授权", "cookie", "api_key"], "auth_config"),
        (["url", "host", "base_url", "环境", "cors", "proxy", "域名"], "env_config"),
    ],
    "module_context": [
        (["依赖", "调用链", "前置", "prerequisite", "dependency"], "api_dependency"),
    ],
}


def migrate_knowledge_type(old_type: str, content: str = "") -> str:
    """将旧知识类型映射到新类型（基于内容关键词）"""
    if old_type not in _OLD_TYPE_MIGRATION_KEYWORDS:
        return old_type
    content_lower = content.lower()
    for keywords, new_type in _OLD_TYPE_MIGRATION_KEYWORDS[old_type]:
        if any(kw in content_lower for kw in keywords):
            return new_type
    # 默认映射
    return {"project_config": "env_config", "module_context": "api_dependency"}.get(old_type, old_type)


@dataclass
class KnowledgeItem:
    """知识条目DTO"""
    knowledge_id: str
    title: str
    content: str
    type: str = KnowledgeTypeEnum.ENV_CONFIG.value
    category: str = ""
    sub_category: str = ""  # V2: 二级子分类
    scope: str = ""
    priority: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: str = ""  # V2: 支撑证据

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
    sub_category: str = ""  # V2: 二级子分类
    scope: str = ""
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0  # 置信度 0-1
    source_ref: str = ""  # 来源引用
    reason: str = ""  # 提取原因
    related_urls: list[str] = field(default_factory=list)  # V2: 关联 URL 列表
    evidence: str = ""  # V2: 支撑证据
