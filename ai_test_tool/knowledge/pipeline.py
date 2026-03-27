"""
知识提取管线 V2

多阶段提取架构：
  Stage 1: 聚类预处理 — 按 URL 模式 / 错误类型 / 响应时间聚类
  Stage 2: 规则引擎模式识别 — 认证、错误、性能、安全、依赖（不调用 LLM）
  Stage 3: LLM 深度分析 — 仅对规则引擎低置信度结果调用 LLM
  Stage 4: 后处理 — 去重、合并、置信度校准
"""

import logging
import json
import re
import statistics
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .models import KnowledgeSuggestion

logger = logging.getLogger(__name__)


# =====================================================
# 管线数据结构
# =====================================================

@dataclass
class RequestCluster:
    """请求聚类"""
    pattern: str  # URL 模式（如 /api/user/{id}）
    requests: list[dict[str, Any]] = field(default_factory=list)
    methods: dict[str, int] = field(default_factory=dict)
    status_codes: dict[int, int] = field(default_factory=dict)
    error_count: int = 0
    total_count: int = 0
    response_times: list[float] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        return self.error_count / max(self.total_count, 1)


@dataclass
class PipelineContext:
    """管线上下文，在各阶段之间传递"""
    raw_requests: list[dict[str, Any]] = field(default_factory=list)
    task_id: str = ""
    # Stage 1 输出
    url_clusters: list[RequestCluster] = field(default_factory=list)
    error_clusters: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    # Stage 2 输出
    rule_suggestions: list[KnowledgeSuggestion] = field(default_factory=list)
    # Stage 3 输出
    llm_suggestions: list[KnowledgeSuggestion] = field(default_factory=list)
    # Stage 4 输出（最终结果）
    final_suggestions: list[KnowledgeSuggestion] = field(default_factory=list)


# =====================================================
# 管线阶段抽象
# =====================================================

class PipelineStage(ABC):
    """管线阶段抽象接口"""

    @abstractmethod
    def process(self, ctx: PipelineContext) -> PipelineContext:
        ...


# =====================================================
# Stage 1: 聚类预处理
# =====================================================

class ClusteringStage(PipelineStage):
    """按 URL 模式、错误类型、响应时间进行聚类"""

    _ID_PATTERN = re.compile(r'/\d+(?=/|$)')
    _UUID_PATTERN = re.compile(r'/[0-9a-f]{8}[-]?[0-9a-f]{4}[-]?[0-9a-f]{4}[-]?[0-9a-f]{4}[-]?[0-9a-f]{12}(?=/|$)', re.I)

    def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.raw_requests:
            return ctx

        # 1. 按 URL 模式聚类
        cluster_map: dict[str, RequestCluster] = {}
        for req in ctx.raw_requests:
            url = req.get('url', '')
            path = url.split('?')[0]
            pattern = self._normalize_path(path)
            method = req.get('method', 'GET').upper()
            status = req.get('http_status', 0) or 0
            resp_time = req.get('response_time_ms', 0) or 0
            has_error = req.get('has_error', False) or status >= 400

            if pattern not in cluster_map:
                cluster_map[pattern] = RequestCluster(pattern=pattern)
            cluster = cluster_map[pattern]
            cluster.requests.append(req)
            cluster.total_count += 1
            cluster.methods[method] = cluster.methods.get(method, 0) + 1
            if status:
                cluster.status_codes[status] = cluster.status_codes.get(status, 0) + 1
            if has_error:
                cluster.error_count += 1
            if resp_time > 0:
                cluster.response_times.append(resp_time)

        ctx.url_clusters = sorted(cluster_map.values(), key=lambda c: c.total_count, reverse=True)

        # 2. 按错误状态码聚类
        for req in ctx.raw_requests:
            status = req.get('http_status', 0) or 0
            if status >= 400:
                ctx.error_clusters.setdefault(status, []).append(req)

        logger.info(f"聚类完成: {len(ctx.url_clusters)} 个 URL 模式, {len(ctx.error_clusters)} 种错误码")
        return ctx

    def _normalize_path(self, path: str) -> str:
        """将路径中的动态段（数字ID、UUID）替换为通配符"""
        result = self._UUID_PATTERN.sub('/{id}', path)
        result = self._ID_PATTERN.sub('/{id}', result)
        return result


# =====================================================
# Stage 2: 规则引擎模式识别
# =====================================================

class PatternRecognitionStage(PipelineStage):
    """基于规则的模式识别引擎（不调用 LLM）"""

    def __init__(self):
        self.extractors: list['PatternExtractor'] = [
            AuthPatternExtractor(),
            ErrorPatternExtractor(),
            PerformanceExtractor(),
            SecurityPatternExtractor(),
            DependencyExtractor(),
        ]

    def process(self, ctx: PipelineContext) -> PipelineContext:
        for extractor in self.extractors:
            try:
                suggestions = extractor.extract(ctx)
                ctx.rule_suggestions.extend(suggestions)
            except Exception as e:
                logger.warning(f"{extractor.__class__.__name__} 提取失败: {e}")
        logger.info(f"规则引擎提取了 {len(ctx.rule_suggestions)} 条知识")
        return ctx


class PatternExtractor(ABC):
    """模式提取器抽象"""

    @abstractmethod
    def extract(self, ctx: PipelineContext) -> list[KnowledgeSuggestion]:
        ...

    def _make_suggestion(
        self, title: str, content: str, type: str,
        sub_category: str = "", scope: str = "", confidence: float = 0.8,
        tags: list[str] | None = None, evidence: str = "",
        related_urls: list[str] | None = None, task_id: str = ""
    ) -> KnowledgeSuggestion:
        return KnowledgeSuggestion(
            title=title, content=content, type=type,
            sub_category=sub_category, scope=scope,
            confidence=confidence, tags=tags or [],
            source_ref=f"rule_engine:{task_id}",
            reason=f"规则引擎自动提取",
            evidence=evidence,
            related_urls=related_urls or [],
        )


class AuthPatternExtractor(PatternExtractor):
    """从 Header 中识别认证模式"""

    _AUTH_PATTERNS = {
        'bearer_token': ['authorization'],
        'cookie': ['cookie', 'set-cookie'],
        'api_key': ['x-api-key', 'api-key', 'apikey'],
    }

    def extract(self, ctx: PipelineContext) -> list[KnowledgeSuggestion]:
        suggestions = []
        total = len(ctx.raw_requests)
        if total < 3:
            return suggestions

        # 统计认证 header 出现频率
        auth_counts: dict[str, int] = defaultdict(int)
        auth_values: dict[str, set] = defaultdict(set)

        for req in ctx.raw_requests:
            headers = self._parse_headers(req.get('headers', {}))
            for pattern_name, header_keys in self._AUTH_PATTERNS.items():
                for hk in header_keys:
                    if hk in headers:
                        auth_counts[pattern_name] += 1
                        val = str(headers[hk])[:30]
                        # 遮蔽敏感值
                        auth_values[pattern_name].add(val[:8] + "***" if len(val) > 8 else val)
                        break

        for pattern_name, count in auth_counts.items():
            ratio = count / total
            if ratio >= 0.5:
                confidence = min(0.95, 0.7 + ratio * 0.25)
                sample_vals = list(auth_values[pattern_name])[:3]
                suggestions.append(self._make_suggestion(
                    title=f"API 使用 {pattern_name} 认证方式",
                    content=f"分析 {total} 个请求发现，{ratio*100:.0f}% 的请求包含 {pattern_name} 类型的认证信息。"
                           f"测试用例应确保正确设置认证 Header。",
                    type="auth_config",
                    sub_category=pattern_name,
                    confidence=confidence,
                    tags=["认证", pattern_name],
                    evidence=f"样本数: {total}, 命中率: {ratio*100:.1f}%, 示例值: {sample_vals}",
                    task_id=ctx.task_id,
                ))
        return suggestions

    def _parse_headers(self, headers: Any) -> dict[str, str]:
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except (json.JSONDecodeError, ValueError):
                return {}
        if isinstance(headers, dict):
            return {k.lower(): v for k, v in headers.items()}
        return {}


class ErrorPatternExtractor(PatternExtractor):
    """从 4xx/5xx 响应中提取错误模式"""

    def extract(self, ctx: PipelineContext) -> list[KnowledgeSuggestion]:
        suggestions = []

        for cluster in ctx.url_clusters:
            if cluster.total_count < 3:
                continue

            # 按错误码分析
            for status, count in cluster.status_codes.items():
                if status < 400:
                    continue
                ratio = count / cluster.total_count
                if ratio < 0.1:
                    continue

                sub_cat = "client_error_4xx" if 400 <= status < 500 else "server_error_5xx"
                confidence = min(0.9, 0.6 + ratio * 0.3)

                # 收集错误消息样本
                error_msgs = []
                for req in cluster.requests:
                    if (req.get('http_status', 0) or 0) == status:
                        msg = req.get('error_message', '') or req.get('response_body', '')
                        if msg:
                            error_msgs.append(str(msg)[:100])
                        if len(error_msgs) >= 3:
                            break

                content = (
                    f"接口模式 `{cluster.pattern}` 的 {status} 错误率为 {ratio*100:.1f}% "
                    f"（{count}/{cluster.total_count} 请求）。"
                )
                if error_msgs:
                    content += f"\n错误消息示例: {'; '.join(error_msgs[:2])}"

                suggestions.append(self._make_suggestion(
                    title=f"{cluster.pattern} 存在 {status} 错误 ({ratio*100:.0f}%)",
                    content=content,
                    type="error_pattern",
                    sub_category=sub_cat,
                    scope=cluster.pattern,
                    confidence=confidence,
                    tags=["错误模式", str(status)],
                    evidence=f"请求数: {cluster.total_count}, 错误数: {count}, 错误率: {ratio*100:.1f}%",
                    related_urls=[cluster.pattern],
                    task_id=ctx.task_id,
                ))
        return suggestions


class PerformanceExtractor(PatternExtractor):
    """计算 P50/P90/P99 响应时间基线"""

    def extract(self, ctx: PipelineContext) -> list[KnowledgeSuggestion]:
        suggestions = []

        for cluster in ctx.url_clusters:
            times = cluster.response_times
            if len(times) < 10:
                continue

            sorted_times = sorted(times)
            n = len(sorted_times)
            p50 = sorted_times[int(n * 0.5)]
            p90 = sorted_times[int(n * 0.9)]
            p99 = sorted_times[min(int(n * 0.99), n - 1)]
            avg = statistics.mean(times)

            # 检测异常慢请求
            slow_threshold = p99 * 2
            slow_count = sum(1 for t in times if t > slow_threshold)

            content = (
                f"接口 `{cluster.pattern}` 性能基线（基于 {n} 个请求）:\n"
                f"- P50: {p50:.0f}ms\n- P90: {p90:.0f}ms\n- P99: {p99:.0f}ms\n- 平均: {avg:.0f}ms"
            )
            if slow_count > 0:
                content += f"\n- 异常慢请求(>{slow_threshold:.0f}ms): {slow_count} 个"

            suggestions.append(self._make_suggestion(
                title=f"{cluster.pattern} 性能基线 (P50={p50:.0f}ms, P99={p99:.0f}ms)",
                content=content,
                type="performance_baseline",
                sub_category="latency_p50",
                scope=cluster.pattern,
                confidence=min(0.95, 0.7 + min(n, 100) / 200),
                tags=["性能", "响应时间"],
                evidence=f"样本数: {n}, P50: {p50:.0f}ms, P90: {p90:.0f}ms, P99: {p99:.0f}ms",
                related_urls=[cluster.pattern],
                task_id=ctx.task_id,
            ))
        return suggestions


class SecurityPatternExtractor(PatternExtractor):
    """检测安全相关模式"""

    _SENSITIVE_PARAMS = ['password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey', 'access_token']
    _INJECTION_PATTERNS = [
        (re.compile(r"['\"]?\s*(OR|AND)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+", re.I), "SQL injection attempt"),
        (re.compile(r"<script", re.I), "XSS attempt"),
    ]

    def extract(self, ctx: PipelineContext) -> list[KnowledgeSuggestion]:
        suggestions = []

        # 1. 检测 URL query string 中的敏感参数
        sensitive_in_url_count = 0
        sensitive_examples: list[str] = []
        for req in ctx.raw_requests:
            url = req.get('url', '')
            if '?' not in url:
                continue
            query_string = url.split('?', 1)[1].lower()
            for param in self._SENSITIVE_PARAMS:
                if param in query_string:
                    sensitive_in_url_count += 1
                    if len(sensitive_examples) < 3:
                        sensitive_examples.append(url.split('?')[0] + f"?{param}=***")
                    break

        if sensitive_in_url_count > 0:
            suggestions.append(self._make_suggestion(
                title="敏感参数出现在 URL query string 中",
                content=(
                    f"发现 {sensitive_in_url_count} 个请求将敏感参数（password/token/secret 等）"
                    f"放在 URL 中传递，存在安全风险。应改用 POST body 或 Header 传递。"
                ),
                type="security_rule",
                sub_category="sensitive_data",
                confidence=0.95,
                tags=["安全", "敏感数据"],
                evidence=f"命中数: {sensitive_in_url_count}, 示例: {sensitive_examples}",
                task_id=ctx.task_id,
            ))

        return suggestions


class DependencyExtractor(PatternExtractor):
    """分析请求时序，提取 API 调用链依赖"""

    def extract(self, ctx: PipelineContext) -> list[KnowledgeSuggestion]:
        suggestions = []
        if len(ctx.raw_requests) < 5:
            return suggestions

        # 简单的时序分析：检查是否有登录/token 请求总是出现在其他请求之前
        login_patterns = ['login', 'auth', 'token', 'signin', 'session']
        login_cluster = None
        for cluster in ctx.url_clusters:
            pattern_lower = cluster.pattern.lower()
            if any(lp in pattern_lower for lp in login_patterns):
                login_cluster = cluster
                break

        if login_cluster and login_cluster.total_count >= 1:
            other_count = sum(c.total_count for c in ctx.url_clusters if c != login_cluster)
            if other_count > login_cluster.total_count * 2:
                suggestions.append(self._make_suggestion(
                    title=f"API 依赖: 其他接口依赖 {login_cluster.pattern} 获取认证",
                    content=(
                        f"日志显示 `{login_cluster.pattern}` 是认证入口接口 "
                        f"（{login_cluster.total_count} 次调用），其余接口共 {other_count} 次调用。"
                        f"测试场景应先调用此接口获取认证 token。"
                    ),
                    type="api_dependency",
                    sub_category="prerequisite",
                    scope=login_cluster.pattern,
                    confidence=0.75,
                    tags=["依赖", "认证流程"],
                    evidence=f"认证接口调用: {login_cluster.total_count}, 其余接口: {other_count}",
                    related_urls=[login_cluster.pattern],
                    task_id=ctx.task_id,
                ))

        return suggestions


# =====================================================
# Stage 3: LLM 深度分析（选择性调用）
# =====================================================

class LLMAnalysisStage(PipelineStage):

    def extract(self, ctx: PipelineContext) -> list[KnowledgeSuggestion]:
        suggestions: list[KnowledgeSuggestion] = []

        for cluster in ctx.url_clusters:
            if cluster.total_count < 3:
                continue

            # 收集该聚类下所有请求的参数
            all_params: dict[str, list[str]] = defaultdict(list)
            body_fields: dict[str, list] = defaultdict(list)
            body_count = 0

            for req in cluster.requests:
                # query_params
                qp = req.get('query_params', {})
                if isinstance(qp, str):
                    try:
                        qp = json.loads(qp)
                    except (json.JSONDecodeError, ValueError):
                        qp = {}
                if isinstance(qp, dict):
                    for k, v in qp.items():
                        all_params[k].append(str(v))

                # body 字段分析
                body = req.get('body')
                if body:
                    body_dict = self._parse_body(body)
                    if body_dict:
                        body_count += 1
                        for k, v in body_dict.items():
                            body_fields[k].append(v)

            # 分析 query 参数模式
            if all_params:
                self._extract_param_knowledge(
                    all_params, cluster, ctx.task_id, suggestions
                )

            # 分析 body 字段 schema
            if body_count >= 3 and body_fields:
                self._extract_body_schema(
                    body_fields, body_count, cluster, ctx.task_id, suggestions
                )

        return suggestions

    def _extract_param_knowledge(
        self, all_params: dict[str, list[str]],
        cluster, task_id: str,
        suggestions: list[KnowledgeSuggestion]
    ) -> None:
        total = cluster.total_count
        param_info_parts: list[str] = []
        required_params: list[str] = []
        pagination_found: list[str] = []
        filter_found: list[str] = []
        sort_found: list[str] = []
        enum_params: dict[str, list[str]] = {}

        for param_name, values in all_params.items():
            ratio = len(values) / total
            lower_name = param_name.lower()

            # 必传参数识别
            if ratio >= 0.9:
                required_params.append(param_name)

            # 分页/过滤/排序模式
            if lower_name in self._PAGINATION_PARAMS:
                pagination_found.append(param_name)
            elif lower_name in self._FILTER_PARAMS:
                filter_found.append(param_name)
            elif lower_name in self._SORT_PARAMS:
                sort_found.append(param_name)

            # 枚举值检测
            unique_vals = list(set(values))
            if 2 <= len(unique_vals) <= 10 and len(values) >= 3:
                enum_params[param_name] = unique_vals

            param_info_parts.append(
                f"- `{param_name}`: 出现 {len(values)}/{total} 次 ({ratio*100:.0f}%)"
                f", 不同值 {len(set(values))} 个"
            )

        if not param_info_parts:
            return

        # 汇总知识
        content_parts = [f"接口 `{cluster.pattern}` 的查询参数分析（{total} 个请求样本）:\n"]
        content_parts.extend(param_info_parts)

        if required_params:
            content_parts.append(f"\n**疑似必传参数**: {', '.join(required_params)}")
        if pagination_found:
            content_parts.append(f"**分页参数**: {', '.join(pagination_found)}")
        if filter_found:
            content_parts.append(f"**过滤参数**: {', '.join(filter_found)}")
        if sort_found:
            content_parts.append(f"**排序参数**: {', '.join(sort_found)}")
        if enum_params:
            for p, vals in list(enum_params.items())[:5]:
                content_parts.append(f"**`{p}` 枚举值**: {vals}")

        suggestions.append(self._make_suggestion(
            title=f"接口 {cluster.pattern} 查询参数模式",
            content='\n'.join(content_parts),
            type="business_rule",
            sub_category="param_constraint",
            scope=cluster.pattern,
            confidence=min(0.9, 0.5 + len(all_params) * 0.05),
            tags=["参数分析", "查询条件"],
            evidence=f"样本数: {total}, 参数种类: {len(all_params)}",
            related_urls=[cluster.pattern],
            task_id=task_id,
        ))

    def _extract_body_schema(
        self, body_fields: dict[str, list],
        body_count: int, cluster, task_id: str,
        suggestions: list[KnowledgeSuggestion]
    ) -> None:
        schema_parts: list[str] = []
        for field_name, values in list(body_fields.items())[:20]:
            non_none = [v for v in values if v is not None]
            types = set(type(v).__name__ for v in non_none) if non_none else {'null'}
            ratio = len(non_none) / body_count
            required = "必填" if ratio >= 0.9 else "可选"

            unique_vals = list(set(str(v) for v in non_none))
            val_hint = ""
            if 2 <= len(unique_vals) <= 8:
                val_hint = f", 枚举值: {unique_vals[:5]}"
            elif len(unique_vals) == 1:
                val_hint = f", 固定值: {unique_vals[0]}"

            schema_parts.append(
                f"- `{field_name}` ({'/'.join(types)}, {required}, 出现{ratio*100:.0f}%{val_hint})"
            )

        if not schema_parts:
            return

        content = (
            f"接口 `{cluster.pattern}` 请求体字段结构（{body_count} 个请求样本）:\n"
            + '\n'.join(schema_parts)
        )

        suggestions.append(self._make_suggestion(
            title=f"接口 {cluster.pattern} 请求体 Schema",
            content=content,
            type="business_rule",
            sub_category="data_format",
            scope=cluster.pattern,
            confidence=min(0.85, 0.5 + body_count * 0.02),
            tags=["请求体", "Schema", "字段结构"],
            evidence=f"样本数: {body_count}, 字段数: {len(body_fields)}",
            related_urls=[cluster.pattern],
            task_id=task_id,
        ))

    def _parse_body(self, body) -> dict | None:
        if isinstance(body, dict):
            return body
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
                return parsed if isinstance(parsed, dict) else None
            except (json.JSONDecodeError, ValueError):
                return None
        return None

    def set_llm_chain(self, chain: Any) -> None:
        self._llm_chain = chain

    def process(self, ctx: PipelineContext) -> PipelineContext:
        if not self._llm_chain:
            logger.info("LLM chain 未配置，跳过 LLM 分析阶段")
            return ctx

        # 选择需要 LLM 分析的聚类：
        # 1. 规则引擎未覆盖的聚类（大聚类但无任何 rule 产出）
        # 2. 包含复杂业务模式的聚类
        covered_patterns = {s.scope for s in ctx.rule_suggestions if s.scope}
        uncovered_clusters = [
            c for c in ctx.url_clusters
            if c.pattern not in covered_patterns and c.total_count >= 5
        ]

        # 最多分析 top 5 个未覆盖的大聚类
        for cluster in uncovered_clusters[:5]:
            samples = self._select_representative_samples(cluster)
            if not samples:
                continue

            content = self._build_analysis_prompt(cluster, samples)
            suggestions = self._call_llm(content, ctx.task_id)
            ctx.llm_suggestions.extend(suggestions)

        logger.info(f"LLM 分析了 {min(len(uncovered_clusters), 5)} 个聚类，提取 {len(ctx.llm_suggestions)} 条知识")
        return ctx

    def _select_representative_samples(self, cluster: RequestCluster, max_samples: int = 5) -> list[dict]:
        """从聚类中选取代表性样本"""
        reqs = cluster.requests
        if len(reqs) <= max_samples:
            return reqs

        samples = []
        # 优先取错误请求
        errors = [r for r in reqs if r.get('has_error') or (r.get('http_status', 200) or 200) >= 400]
        if errors:
            samples.append(errors[0])

        # 取成功请求
        success = [r for r in reqs if (r.get('http_status', 200) or 200) < 400 and r not in samples]
        if success:
            samples.append(success[0])

        # 补齐
        remaining = [r for r in reqs if r not in samples]
        for r in remaining[:max_samples - len(samples)]:
            samples.append(r)

        return samples

    def _build_analysis_prompt(self, cluster: RequestCluster, samples: list[dict]) -> str:
        """为 LLM 构建分析 prompt（包含内容级字段）"""
        lines = [
            f"## 接口模式分析: {cluster.pattern}",
            f"- 总请求数: {cluster.total_count}",
            f"- 方法分布: {dict(cluster.methods)}",
            f"- 状态码: {dict(cluster.status_codes)}",
            f"- 错误率: {cluster.error_rate*100:.1f}%",
            "",
            "### 代表性样本请求",
        ]
        for i, req in enumerate(samples, 1):
            lines.append(f"\n**样本 {i}**: {req.get('method','GET')} {req.get('url','')}")
            lines.append(f"  状态码: {req.get('http_status', 'N/A')}")
            headers = req.get('headers', {})
            if isinstance(headers, str):
                try:
                    headers = json.loads(headers)
                except Exception:
                    headers = {}
            if headers:
                filtered = {k: v for k, v in headers.items()
                           if any(x in k.lower() for x in ['content-type', 'authorization', 'x-'])}
                if filtered:
                    lines.append(f"  关键 Headers: {json.dumps(filtered, ensure_ascii=False)[:200]}")
            if req.get('error_message'):
                lines.append(f"  错误: {req['error_message'][:200]}")

            # 补充查询参数
            qp = req.get('query_params', {})
            if isinstance(qp, str):
                try:
                    qp = json.loads(qp)
                except Exception:
                    qp = {}
            if qp:
                lines.append(f"  查询参数: {json.dumps(qp, ensure_ascii=False)[:300]}")

            # 补充请求体（截断）
            body = req.get('body')
            if body:
                body_str = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)
                lines.append(f"  请求体: {body_str[:500]}")

            # 补充响应体（截断）
            resp = req.get('response_body')
            if resp:
                resp_str = json.dumps(resp, ensure_ascii=False) if isinstance(resp, dict) else str(resp)
                lines.append(f"  响应体: {resp_str[:500]}")

        return "\n".join(lines)

    def _call_llm(self, content: str, task_id: str) -> list[KnowledgeSuggestion]:
        """调用 LLM 提取知识"""
        from .learner import KNOWLEDGE_EXTRACTION_PROMPT_V2
        try:
            prompt = KNOWLEDGE_EXTRACTION_PROMPT_V2.format(content=content)
            if hasattr(self._llm_chain, 'extract_knowledge'):
                items = self._llm_chain.extract_knowledge(content)
            else:
                response = self._llm_chain.invoke(prompt)
                response_text = response if isinstance(response, str) else str(response)
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    items = json.loads(response_text[json_start:json_end])
                else:
                    return []

            suggestions = []
            for item in items or []:
                if not isinstance(item, dict):
                    continue
                s = KnowledgeSuggestion(
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    type=item.get('type', 'business_rule'),
                    sub_category=item.get('sub_category', ''),
                    scope=item.get('scope', ''),
                    tags=item.get('tags', []),
                    confidence=float(item.get('confidence', 0.5)),
                    source_ref=f"llm_analysis:{task_id}",
                    reason=item.get('reason', ''),
                    evidence=f"LLM 深度分析",
                )
                if s.title and s.content:
                    suggestions.append(s)
            return suggestions
        except Exception as e:
            logger.error(f"LLM 分析失败: {e}")
            return []


# =====================================================
# Stage 4: 后处理（去重、合并、置信度校准）
# =====================================================

class PostProcessingStage(PipelineStage):
    """去重、合并、置信度校准"""

    def process(self, ctx: PipelineContext) -> PipelineContext:
        all_suggestions = ctx.rule_suggestions + ctx.llm_suggestions

        if not all_suggestions:
            ctx.final_suggestions = []
            return ctx

        # 1. 过滤低置信度
        filtered = [s for s in all_suggestions if s.confidence >= 0.3]

        # 2. 精确去重：相同 type + scope + 相似 title
        deduplicated = self._deduplicate(filtered)

        # 3. 按置信度排序
        deduplicated.sort(key=lambda s: s.confidence, reverse=True)

        ctx.final_suggestions = deduplicated
        logger.info(f"后处理: {len(all_suggestions)} → {len(deduplicated)} 条知识（过滤+去重）")
        return ctx

    def _deduplicate(self, suggestions: list[KnowledgeSuggestion]) -> list[KnowledgeSuggestion]:
        """简单的精确去重：同 type+scope 下 title 相似则合并"""
        seen: dict[str, KnowledgeSuggestion] = {}
        for s in suggestions:
            key = f"{s.type}|{s.scope}|{self._normalize_title(s.title)}"
            if key in seen:
                existing = seen[key]
                # 保留置信度更高的，合并 evidence
                if s.confidence > existing.confidence:
                    s.evidence = f"{s.evidence}; {existing.evidence}" if existing.evidence else s.evidence
                    seen[key] = s
                else:
                    existing.evidence = f"{existing.evidence}; {s.evidence}" if s.evidence else existing.evidence
            else:
                seen[key] = s
        return list(seen.values())

    def _normalize_title(self, title: str) -> str:
        """规范化标题用于去重比较"""
        # 去除数字、百分比等变化部分
        result = re.sub(r'\d+(\.\d+)?%?', 'N', title)
        result = re.sub(r'\s+', ' ', result).strip().lower()
        return result


# =====================================================
# 管线总控
# =====================================================

class ExtractionPipeline:
    """
    知识提取管线

    用法:
        pipeline = ExtractionPipeline(llm_chain=my_chain)
        suggestions = pipeline.run(parsed_requests, task_id="xxx")
    """

    def __init__(self, llm_chain: Any = None):
        self._llm_stage = LLMAnalysisStage(llm_chain)
        self.stages: list[PipelineStage] = [
            ClusteringStage(),
            PatternRecognitionStage(),
            self._llm_stage,
            PostProcessingStage(),
        ]

    def set_llm_chain(self, chain: Any) -> None:
        self._llm_stage.set_llm_chain(chain)

    def run(
        self,
        parsed_requests: list[dict[str, Any]],
        task_id: str = ""
    ) -> list[KnowledgeSuggestion]:
        """
        执行完整管线

        Args:
            parsed_requests: 解析后的请求字典列表
            task_id: 关联的任务 ID

        Returns:
            提取的知识建议列表
        """
        ctx = PipelineContext(raw_requests=parsed_requests, task_id=task_id)

        for stage in self.stages:
            try:
                ctx = stage.process(ctx)
            except Exception as e:
                logger.error(f"管线阶段 {stage.__class__.__name__} 失败: {e}")

        return ctx.final_suggestions
