# 该文件内容使用AI生成，注意识别准确性
"""
分析类 Skill

知识优先 + LLM 回退的智能分析工具。
"""

import logging
import json
from typing import Any
from collections import Counter

from .registry import SkillRegistry, skill

logger = logging.getLogger(__name__)

# 常见错误 → 诊断模板（零 LLM 成本）
ERROR_DIAGNOSIS_TEMPLATES: dict[str, dict[str, str]] = {
    r"out of memory|oom|heap space|memory limit": {
        "root_cause": "内存不足，进程使用的内存超出了系统或容器限制",
        "impact": "服务可能崩溃重启，影响所有正在处理的请求",
        "suggestion": "1. 检查内存泄漏（长期增长的对象）\n2. 增加容器/进程内存限制\n3. 优化大对象的生命周期管理",
    },
    r"timeout|timed out|deadline exceeded": {
        "root_cause": "请求超时，下游服务或数据库响应时间超过预设阈值",
        "impact": "用户请求失败，可能触发重试导致雪崩",
        "suggestion": "1. 检查下游服务健康状态\n2. 优化慢查询\n3. 适当调大超时阈值\n4. 添加熔断机制",
    },
    r"connection refused|connection reset|econnrefused": {
        "root_cause": "连接被拒绝，目标服务未启动或端口未监听",
        "impact": "依赖该服务的所有功能不可用",
        "suggestion": "1. 确认目标服务是否正常运行\n2. 检查网络连通性和防火墙规则\n3. 检查服务发现/DNS 解析",
    },
    r"null\s*pointer|nullpointerexception|nonetype.*attribute|attributeerror.*none": {
        "root_cause": "空指针/空引用异常，代码访问了未初始化或已释放的对象",
        "impact": "请求处理中断，返回 500 错误",
        "suggestion": "1. 检查最近的代码变更\n2. 添加空值检查\n3. 排查数据库返回 null 的场景",
    },
    r"deadlock|lock wait timeout|unable to acquire lock": {
        "root_cause": "死锁或锁等待超时，多个事务/线程互相等待资源",
        "impact": "相关请求阻塞或失败，可能导致连接池耗尽",
        "suggestion": "1. 优化事务范围，减少锁持有时间\n2. 统一锁的获取顺序\n3. 设置合理的锁超时",
    },
    r"unauthorized|401|invalid token|token expired|jwt expired": {
        "root_cause": "认证失败，Token 无效、过期或缺失",
        "impact": "用户无法访问受保护资源",
        "suggestion": "1. 检查 Token 签发和验证逻辑\n2. 确认 Token 过期时间配置\n3. 检查客户端是否正确传递认证信息",
    },
    r"forbidden|403|permission denied|access denied": {
        "root_cause": "权限不足，用户已认证但无权访问该资源",
        "impact": "特定功能不可用",
        "suggestion": "1. 检查用户角色和权限配置\n2. 确认 RBAC/ACL 规则\n3. 检查是否有 IP 白名单限制",
    },
    r"rate limit|too many requests|429|throttle": {
        "root_cause": "请求频率超限，触发了限流策略",
        "impact": "部分请求被拒绝，返回 429 状态码",
        "suggestion": "1. 客户端添加重试退避策略\n2. 优化请求合并/批量化\n3. 必要时调大限流阈值",
    },
    r"disk.*full|no space left|enospc": {
        "root_cause": "磁盘空间不足",
        "impact": "日志写入、数据持久化等操作失败",
        "suggestion": "1. 清理临时文件和过期日志\n2. 扩容磁盘\n3. 配置日志轮转策略",
    },
    r"dns.*resolv|name.*resolution|getaddrinfo": {
        "root_cause": "DNS 解析失败，无法将域名解析为 IP 地址",
        "impact": "依赖该域名的服务调用全部失败",
        "suggestion": "1. 检查 DNS 服务器配置\n2. 确认域名是否正确\n3. 排查网络隔离问题",
    },
}


@skill(
    name="diagnose_with_knowledge",
    description="带知识库上下文的错误诊断。先查知识库已知模式，再匹配诊断模板，最后回退 LLM。",
    category="analysis",
    parameters={
        "error_messages": "错误信息列表",
        "urls": "相关接口URL列表(可选)",
        "use_llm_fallback": "是否允许 LLM 回退(默认True)",
    },
    returns="诊断结果：root_cause, impact, suggestion, source(knowledge/template/llm)",
)
def diagnose_with_knowledge(
    error_messages: list[str],
    urls: list[str] | None = None,
    use_llm_fallback: bool = True,
) -> dict[str, Any]:
    """三层诊断：知识库 → 模板 → LLM"""
    import re

    if not error_messages:
        return {"error": "无错误信息", "source": "none"}

    combined_error = " ".join(error_messages)

    # 第一层：查知识库
    try:
        from .knowledge_skills import lookup_error_pattern
        kb_result = lookup_error_pattern(
            error_message=combined_error[:200],
            endpoint=urls[0] if urls else "",
        )
        if kb_result.get("high_confidence_match") and kb_result.get("entries"):
            entry = kb_result["entries"][0]
            return {
                "root_cause": entry.get("title", ""),
                "detail": entry.get("content", ""),
                "source": "knowledge",
                "confidence": entry.get("confidence", 0.8),
            }
    except Exception as e:
        logger.debug(f"知识库查询失败: {e}")

    # 第二层：匹配诊断模板
    for pattern, diagnosis in ERROR_DIAGNOSIS_TEMPLATES.items():
        if re.search(pattern, combined_error, re.IGNORECASE):
            return {
                "root_cause": diagnosis["root_cause"],
                "impact": diagnosis["impact"],
                "suggestion": diagnosis["suggestion"],
                "matched_pattern": pattern,
                "source": "template",
                "confidence": 0.7,
            }

    # 第三层：LLM 回退
    if use_llm_fallback:
        try:
            from ..api.dependencies import get_knowledge_retriever, get_rag_builder
            retriever = get_knowledge_retriever()
            rag_builder = get_rag_builder()

            # 检索相关知识作为上下文
            entries = retriever.retrieve_for_log_analysis(
                urls=urls or [],
                error_messages=error_messages,
            )
            knowledge_context = rag_builder.build_context(
                query=combined_error[:200],
                entries=entries,
            ) if entries else ""

            return {
                "root_cause": "需要 LLM 深度分析（未匹配已知模式）",
                "error_summary": combined_error[:500],
                "knowledge_context": knowledge_context[:1000] if knowledge_context else "",
                "source": "needs_llm",
                "confidence": 0.0,
            }
        except Exception as e:
            logger.warning(f"RAG 上下文构建失败: {e}")

    return {
        "root_cause": "未知错误模式",
        "error_summary": combined_error[:500],
        "source": "unknown",
        "confidence": 0.0,
    }


@skill(
    name="generate_report_from_template",
    description="使用 Markdown 模板生成分析报告（不调用 LLM）",
    category="analysis",
    parameters={
        "title": "报告标题",
        "anomalies": "异常列表",
        "diagnosis": "诊断结果(可选)",
        "stats": "统计数据(可选)",
    },
    returns="Markdown 格式的报告内容",
)
def generate_report_from_template(
    title: str,
    anomalies: list[dict[str, Any]] | None = None,
    diagnosis: dict[str, Any] | None = None,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """模板报告生成"""
    anomalies = anomalies or []
    sections = [f"# {title}\n"]

    # 摘要
    severity_counter: Counter = Counter()
    type_counter: Counter = Counter()
    for a in anomalies:
        severity_counter[a.get("severity", "unknown")] += 1
        type_counter[a.get("type", "unknown")] += 1

    sections.append("## 摘要\n")
    sections.append(f"- 异常总数: **{len(anomalies)}**")
    if severity_counter:
        for sev, cnt in severity_counter.most_common():
            sections.append(f"- {sev}: {cnt}")
    sections.append("")

    # 异常类型分布
    if type_counter:
        sections.append("## 异常类型分布\n")
        for t, cnt in type_counter.most_common(10):
            sections.append(f"| {t} | {cnt} |")
        sections.append("")

    # 诊断结果
    if diagnosis:
        sections.append("## 根因分析\n")
        sections.append(f"**根因**: {diagnosis.get('root_cause', '未知')}\n")
        if diagnosis.get("impact"):
            sections.append(f"**影响范围**: {diagnosis['impact']}\n")
        if diagnosis.get("suggestion"):
            sections.append(f"**建议**:\n{diagnosis['suggestion']}\n")
        sections.append(f"*分析来源: {diagnosis.get('source', 'unknown')}*\n")

    # 统计数据
    if stats:
        sections.append("## 统计数据\n")
        sections.append(f"```json\n{json.dumps(stats, ensure_ascii=False, indent=2)}\n```\n")

    # 异常详情
    if anomalies:
        sections.append("## 异常详情（前 20 条）\n")
        for i, a in enumerate(anomalies[:20], 1):
            sections.append(
                f"{i}. [{a.get('severity', '?')}] **{a.get('title', '未知')}**"
                f"  \n   {a.get('description', '')[:200]}"
            )
        sections.append("")

    content = "\n".join(sections)
    return {"content": content, "format": "markdown", "word_count": len(content)}


def register_analysis_skills(registry: SkillRegistry) -> None:
    """确保分析类 Skill 被导入注册"""
    logger.info("分析类 Skill 已注册: diagnose_with_knowledge, generate_report_from_template")
