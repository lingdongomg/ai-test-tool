# 该文件内容使用AI生成，注意识别准确性
"""
知识检索类 Skill

零 LLM 成本，通过 KnowledgeRetriever 按类型检索知识库。
"""

import logging
from typing import Any

from .registry import SkillRegistry, skill

logger = logging.getLogger(__name__)


def _get_retriever():
    """延迟获取 KnowledgeRetriever 单例"""
    from ..api.dependencies import get_knowledge_retriever
    return get_knowledge_retriever()


def _format_entries(entries: list) -> list[dict[str, Any]]:
    """将知识条目格式化为简洁的字典列表"""
    results = []
    for e in entries[:10]:
        results.append({
            "title": getattr(e, 'title', str(e)),
            "content": getattr(e, 'content', '')[:300],
            "type": getattr(e, 'type', ''),
            "scope": getattr(e, 'scope', ''),
            "confidence": getattr(e, 'confidence', 0),
        })
    return results


@skill(
    name="lookup_error_pattern",
    description="从知识库查找已知的错误模式和解决方案。如果找到高置信度匹配，可直接使用而无需 LLM 分析。",
    category="knowledge",
    parameters={
        "error_message": "错误信息（如 'Connection refused'、'OOM'）",
        "status_code": "HTTP 状态码(可选)",
        "endpoint": "相关接口路径(可选)",
    },
    returns="已知错误模式列表，含诊断建议",
)
def lookup_error_pattern(
    error_message: str = "",
    status_code: int = 0,
    endpoint: str = "",
) -> dict[str, Any]:
    """查找已知错误模式"""
    try:
        retriever = _get_retriever()

        query_parts = []
        if error_message:
            query_parts.append(error_message)
        if status_code:
            query_parts.append(f"HTTP {status_code}")
        if endpoint:
            query_parts.append(endpoint)

        query = " ".join(query_parts) or "error"

        entries = retriever.retrieve(
            query=query,
            knowledge_types=["error_pattern"],
            scope=endpoint or None,
            limit=5,
        )

        results = _format_entries(entries)
        has_high_confidence = any(r.get('confidence', 0) >= 0.8 for r in results)

        return {
            "found": len(results) > 0,
            "high_confidence_match": has_high_confidence,
            "entries": results,
            "message": "找到高置信度匹配，可直接使用" if has_high_confidence else
                       f"找到 {len(results)} 条相关知识" if results else "知识库中无匹配记录",
        }
    except Exception as e:
        logger.warning(f"lookup_error_pattern 失败: {e}")
        return {"found": False, "high_confidence_match": False, "entries": [], "error": str(e)}


@skill(
    name="lookup_service_dependency",
    description="查找 API 接口的服务依赖关系（调用链、前置条件）",
    category="knowledge",
    parameters={"endpoint": "接口路径"},
    returns="服务依赖信息",
)
def lookup_service_dependency(endpoint: str) -> dict[str, Any]:
    """查找服务依赖"""
    try:
        retriever = _get_retriever()
        entries = retriever.retrieve(
            query=endpoint,
            knowledge_types=["api_dependency"],
            scope=endpoint,
            limit=5,
        )
        return {"found": len(entries) > 0, "entries": _format_entries(entries)}
    except Exception as e:
        return {"found": False, "entries": [], "error": str(e)}


@skill(
    name="lookup_performance_baseline",
    description="查找接口的性能基线（响应时间分位数、吞吐量）",
    category="knowledge",
    parameters={"endpoint": "接口路径"},
    returns="性能基线数据",
)
def lookup_performance_baseline(endpoint: str) -> dict[str, Any]:
    """查找性能基线"""
    try:
        retriever = _get_retriever()
        entries = retriever.retrieve(
            query=endpoint,
            knowledge_types=["performance_baseline"],
            scope=endpoint,
            limit=3,
        )
        return {"found": len(entries) > 0, "entries": _format_entries(entries)}
    except Exception as e:
        return {"found": False, "entries": [], "error": str(e)}


@skill(
    name="lookup_auth_config",
    description="查找接口的认证配置（Bearer Token、Cookie、API Key 等）",
    category="knowledge",
    parameters={"endpoint": "接口路径(可选，为空查全局配置)"},
    returns="认证配置信息",
)
def lookup_auth_config(endpoint: str = "") -> dict[str, Any]:
    """查找认证配置"""
    try:
        retriever = _get_retriever()
        entries = retriever.retrieve(
            query=endpoint or "认证配置",
            knowledge_types=["auth_config"],
            scope=endpoint or None,
            limit=5,
        )
        return {"found": len(entries) > 0, "entries": _format_entries(entries)}
    except Exception as e:
        return {"found": False, "entries": [], "error": str(e)}


@skill(
    name="lookup_business_rule",
    description="查找业务规则（参数约束、状态机、数据格式等）",
    category="knowledge",
    parameters={"query": "查询关键词", "scope": "适用范围(可选)"},
    returns="业务规则列表",
)
def lookup_business_rule(query: str, scope: str = "") -> dict[str, Any]:
    """查找业务规则"""
    try:
        retriever = _get_retriever()
        entries = retriever.retrieve(
            query=query,
            knowledge_types=["business_rule"],
            scope=scope or None,
            limit=5,
        )
        return {"found": len(entries) > 0, "entries": _format_entries(entries)}
    except Exception as e:
        return {"found": False, "entries": [], "error": str(e)}


def register_knowledge_skills(registry: SkillRegistry) -> None:
    """确保知识检索类 Skill 被导入注册"""
    logger.info("知识检索类 Skill 已注册: lookup_error_pattern, lookup_service_dependency, "
                "lookup_performance_baseline, lookup_auth_config, lookup_business_rule")
