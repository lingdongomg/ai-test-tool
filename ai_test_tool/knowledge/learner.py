"""
知识学习引擎

从日志解析和测试执行中提取知识。
V2: 支持多阶段提取管线，通过 KNOWLEDGE_PIPELINE_V2 配置切换。
"""

import logging
import json
import os
import random
from typing import Any
from collections import Counter

from .models import KnowledgeSuggestion
from .store import KnowledgeStore

logger = logging.getLogger(__name__)


def _pipeline_v2_enabled() -> bool:
    """检查是否启用 V2 管线"""
    return os.environ.get('KNOWLEDGE_PIPELINE_V2', 'true').lower() in ('true', '1', 'yes')


# =====================================================
# V2 知识提取 Prompt（针对 8 种类型优化）
# =====================================================

KNOWLEDGE_EXTRACTION_PROMPT_V2 = """你是一个API测试知识提取专家。请分析以下信息，提取可以帮助生成更好测试用例的知识。

## 分析内容
{content}

## 知识类型说明（8 种）
- auth_config: 认证配置（如 Bearer Token、Cookie、API Key、OAuth2 认证方式）
- error_pattern: 错误模式（如特定接口的常见错误、错误码含义、错误触发条件）
- performance_baseline: 性能基线（如响应时间分布、吞吐量、超时阈值）
- business_rule: 业务规则（如参数约束、状态机、速率限制、数据格式要求）
- api_dependency: API 依赖关系（如调用链、前置条件、数据依赖）
- security_rule: 安全规则（如输入校验、敏感数据处理、注入防护）
- env_config: 环境配置（如基础 URL、通用 Header、CORS 配置）
- test_experience: 测试经验（如边界情况、回归测试点、不稳定测试）

## 输出要求
请以 JSON 数组格式输出，每条知识包含：
- title: 知识标题（具体、可操作，如"用户接口需要 Bearer Token 认证"）
- content: 知识内容（详细描述，包含具体的配置值、参数名、规则）
- type: 知识类型（从上述 8 种中选择，优先使用最精确的类型）
- sub_category: 子分类（可选，如 bearer_token / client_error_4xx 等）
- scope: 适用范围（如 /api/user/* 或具体路径）
- tags: 标签数组
- confidence: 置信度（0-1）
- reason: 提取原因

## 注意事项
1. 只提取对测试用例生成直接有帮助的知识
2. 具体的配置值、参数名称要准确，避免泛泛而谈
3. 如果没有发现有价值的知识，返回空数组 []
4. 避免提取"该接口使用 POST 方法"这种显而易见的知识
5. 每条知识应该能直接指导一个或多个测试用例的编写

请输出 JSON 数组："""


# 旧版 prompt（V1 兼容）
KNOWLEDGE_EXTRACTION_PROMPT = """你是一个API测试知识提取专家。请分析以下信息，提取可以帮助生成更好测试用例的知识。

## 分析内容
{content}

## 知识类型说明
- project_config: 项目配置知识（如认证方式、环境变量、通用header参数）
- business_rule: 业务规则知识（如特定模块的参数要求、业务逻辑约束）
- module_context: 模块上下文知识（如模块功能描述、依赖关系）
- test_experience: 测试经验知识（如常见错误、边界情况、最佳实践）

## 输出要求
请提取有价值的知识，以JSON数组格式输出，每条知识包含：
- title: 知识标题（简洁明了）
- content: 知识内容（详细描述，包含具体的配置值或规则）
- type: 知识类型（从上述4种中选择）
- category: 子分类（可选）
- scope: 适用范围（如接口路径 /api/live/*）
- tags: 标签数组（用于分类检索）
- confidence: 置信度（0-1，表示这条知识的可靠程度）
- reason: 提取原因（为什么这是有价值的知识）

## 注意事项
1. 只提取对测试用例生成有帮助的知识
2. 具体的配置值、参数名称要准确
3. 如果没有发现有价值的知识，返回空数组 []
4. 避免提取过于通用或显而易见的知识

请输出JSON数组："""


class KnowledgeLearner:
    """
    知识学习引擎

    从各种来源提取知识：
    - 日志解析结果
    - 测试执行结果
    - API文档
    """

    def __init__(
        self,
        store: KnowledgeStore,
        llm_chain: Any = None
    ):
        self.store = store
        self._llm_chain = llm_chain
        self._pipeline = None

    def set_llm_chain(self, chain: Any) -> None:
        """设置LLM链"""
        self._llm_chain = chain
        if self._pipeline:
            self._pipeline.set_llm_chain(chain)

    def _get_pipeline(self):
        """懒加载 V2 管线"""
        if self._pipeline is None:
            from .pipeline import ExtractionPipeline
            self._pipeline = ExtractionPipeline(llm_chain=self._llm_chain)
        return self._pipeline

    def extract_from_log_analysis(
        self,
        parsed_requests: list[dict[str, Any]],
        task_id: str = ""
    ) -> list[KnowledgeSuggestion]:
        """
        从日志解析结果中提取知识

        V2: 使用多阶段管线提取。可通过 KNOWLEDGE_PIPELINE_V2=false 回退到旧逻辑。
        """
        if not parsed_requests:
            return []

        if _pipeline_v2_enabled():
            logger.info(f"使用 V2 管线提取知识（{len(parsed_requests)} 个请求）")
            pipeline = self._get_pipeline()
            return pipeline.run(parsed_requests, task_id)

        # V1 旧逻辑
        return self._extract_from_log_analysis_v1(parsed_requests, task_id)

    def _extract_from_log_analysis_v1(
        self,
        parsed_requests: list[dict[str, Any]],
        task_id: str = ""
    ) -> list[KnowledgeSuggestion]:
        """V1 旧逻辑：一次性摘要 → LLM 提取"""
        content_parts = ["## 日志解析结果分析\n"]

        urls = [req.get('url', '') for req in parsed_requests]
        unique_urls = list(set(urls))
        content_parts.append(f"解析了 {len(parsed_requests)} 个请求，涉及 {len(unique_urls)} 个不同的接口。\n")

        method_counter = Counter(req.get('method', 'GET') for req in parsed_requests)
        content_parts.append("### HTTP方法分布")
        for method, count in method_counter.most_common():
            content_parts.append(f"- {method}: {count} 次")
        content_parts.append("")

        status_counter = Counter(req.get('http_status', 0) for req in parsed_requests if req.get('http_status'))
        if status_counter:
            content_parts.append("### 响应状态码分布")
            for status, count in status_counter.most_common(10):
                content_parts.append(f"- {status}: {count} 次")
            content_parts.append("")

        header_patterns = self._analyze_headers(parsed_requests)
        if header_patterns:
            content_parts.append("### Header模式分析")
            for pattern in header_patterns:
                content_parts.append(f"- {pattern}")
            content_parts.append("")

        url_patterns = self._analyze_url_patterns(unique_urls)
        if url_patterns:
            content_parts.append("### URL模式分析")
            for pattern in url_patterns:
                content_parts.append(f"- {pattern}")
            content_parts.append("")

        error_patterns = self._analyze_errors(parsed_requests)
        if error_patterns:
            content_parts.append("### 错误模式分析")
            for pattern in error_patterns:
                content_parts.append(f"- {pattern}")
            content_parts.append("")

        sample_requests = self._diverse_sample(parsed_requests, max_samples=20)
        content_parts.append(f"### 样例请求（从 {len(parsed_requests)} 个请求中采样 {len(sample_requests)} 个）")
        for req in sample_requests:
            content_parts.append(self._format_request_sample(req))

        content = "\n".join(content_parts)
        return self._extract_with_llm(content, f"log_analysis:{task_id}")

    def extract_from_test_results(
        self,
        test_results: list[dict[str, Any]],
        execution_id: str = ""
    ) -> list[KnowledgeSuggestion]:
        """从测试执行结果中提取知识（特别是失败案例）"""
        if not test_results:
            return []

        failed_tests = [r for r in test_results if r.get('status') in ('failed', 'error')]
        if not failed_tests:
            return []

        content_parts = ["## 测试失败分析\n"]
        content_parts.append(f"共 {len(failed_tests)} 个测试失败。\n")

        for i, test in enumerate(failed_tests[:10], 1):
            content_parts.append(f"### 失败案例 {i}")
            content_parts.append(f"- 接口: {test.get('method', '')} {test.get('url', '')}")
            content_parts.append(f"- 期望状态码: {test.get('expected_status_code', '')}")
            content_parts.append(f"- 实际状态码: {test.get('actual_status_code', '')}")
            if test.get('error_message'):
                content_parts.append(f"- 错误信息: {test.get('error_message')}")
            if test.get('ai_analysis'):
                content_parts.append(f"- AI分析: {test.get('ai_analysis')}")
            content_parts.append("")

        content = "\n".join(content_parts)
        return self._extract_with_llm(content, f"test_execution:{execution_id}")

    def extract_from_api_doc(
        self,
        api_doc: dict[str, Any],
        source_file: str = ""
    ) -> list[KnowledgeSuggestion]:
        """从API文档中提取知识"""
        if not api_doc:
            return []

        content_parts = ["## API文档分析\n"]

        info = api_doc.get('info', {})
        if info:
            content_parts.append(f"API名称: {info.get('title', 'Unknown')}")
            content_parts.append(f"版本: {info.get('version', 'Unknown')}")
            if info.get('description'):
                content_parts.append(f"描述: {info.get('description')}")
            content_parts.append("")

        security_defs = api_doc.get('securityDefinitions', api_doc.get('components', {}).get('securitySchemes', {}))
        if security_defs:
            content_parts.append("### 安全配置")
            for name, config in security_defs.items():
                content_parts.append(f"- {name}: {config.get('type', '')} - {config.get('description', '')}")
            content_parts.append("")

        paths = api_doc.get('paths', {})
        common_params = self._extract_common_params(paths)
        if common_params:
            content_parts.append("### 通用参数模式")
            for param in common_params:
                content_parts.append(f"- {param}")
            content_parts.append("")

        content = "\n".join(content_parts)
        return self._extract_with_llm(content, f"api_doc:{source_file}")

    # =====================================================
    # 辅助方法
    # =====================================================

    def _analyze_headers(self, requests: list[dict[str, Any]]) -> list[str]:
        """分析header模式"""
        patterns = []
        header_counts: dict[str, int] = {}
        header_values: dict[str, set] = {}

        for req in requests:
            headers = req.get('headers', {})
            if isinstance(headers, str):
                try:
                    headers = json.loads(headers)
                except (json.JSONDecodeError, ValueError):
                    continue

            for key, value in headers.items():
                key_lower = key.lower()
                header_counts[key_lower] = header_counts.get(key_lower, 0) + 1
                if key_lower not in header_values:
                    header_values[key_lower] = set()
                header_values[key_lower].add(str(value)[:50])

        total = len(requests)
        for header, count in sorted(header_counts.items(), key=lambda x: -x[1]):
            if count >= total * 0.5:
                values = header_values.get(header, set())
                if len(values) <= 3:
                    patterns.append(f"Header '{header}' 出现在 {count}/{total} 请求中，值: {', '.join(values)}")
                else:
                    patterns.append(f"Header '{header}' 出现在 {count}/{total} 请求中")

        return patterns[:10]

    def _analyze_url_patterns(self, urls: list[str]) -> list[str]:
        """分析URL模式"""
        patterns = []
        prefixes: dict[str, int] = {}
        for url in urls:
            path = url.split('?')[0]
            parts = path.strip('/').split('/')
            if len(parts) >= 2:
                prefix = '/' + '/'.join(parts[:2])
                prefixes[prefix] = prefixes.get(prefix, 0) + 1

        for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1])[:5]:
            if count >= 2:
                patterns.append(f"路径前缀 '{prefix}' 出现 {count} 次")
        return patterns

    def _analyze_errors(self, requests: list[dict[str, Any]]) -> list[str]:
        """分析错误模式"""
        patterns = []
        error_requests = [r for r in requests if r.get('has_error') or r.get('http_status', 200) >= 400]
        if not error_requests:
            return []

        status_groups: dict[int, list] = {}
        for req in error_requests:
            status = req.get('http_status', 0)
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(req)

        for status, reqs in sorted(status_groups.items()):
            sample_urls = [r.get('url', '')[:50] for r in reqs[:3]]
            patterns.append(f"状态码 {status} 出现 {len(reqs)} 次，示例: {', '.join(sample_urls)}")
        return patterns[:5]

    def _diverse_sample(self, requests: list[dict[str, Any]], max_samples: int = 20) -> list[dict[str, Any]]:
        """从请求列表中多样化采样"""
        if len(requests) <= max_samples:
            return requests

        samples: list[dict[str, Any]] = []
        used_indices: set[int] = set()

        error_quota = max_samples // 2
        error_indices = [i for i, r in enumerate(requests)
                         if r.get('has_error') or (r.get('http_status') or 200) >= 400]
        if error_indices:
            picked = random.sample(error_indices, min(len(error_indices), error_quota))
            for idx in picked:
                samples.append(requests[idx])
                used_indices.add(idx)

        remaining = max_samples - len(samples)
        url_groups: dict[str, list[int]] = {}
        for i, req in enumerate(requests):
            if i in used_indices:
                continue
            url = req.get('url', '')
            path = url.split('?')[0]
            parts = path.strip('/').split('/')
            prefix = '/'.join(parts[:2]) if len(parts) >= 2 else path
            url_groups.setdefault(prefix, []).append(i)

        if url_groups:
            per_group = max(1, remaining // len(url_groups))
            for indices in url_groups.values():
                picked = random.sample(indices, min(len(indices), per_group))
                for idx in picked:
                    if len(samples) >= max_samples:
                        break
                    samples.append(requests[idx])
                    used_indices.add(idx)

        if len(samples) < max_samples:
            pool = [i for i in range(len(requests)) if i not in used_indices]
            extra = random.sample(pool, min(len(pool), max_samples - len(samples)))
            for idx in extra:
                samples.append(requests[idx])

        return samples

    def _format_request_sample(self, req: dict[str, Any]) -> str:
        """格式化请求样例"""
        lines = [f"- {req.get('method', 'GET')} {req.get('url', '')}"]

        headers = req.get('headers', {})
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except (json.JSONDecodeError, ValueError):
                headers = {}

        if headers:
            important_headers = ['authorization', 'content-type', 'x-', 'game-id', 'token']
            filtered = {k: v for k, v in headers.items()
                       if any(ih in k.lower() for ih in important_headers)}
            if filtered:
                lines.append(f"  Headers: {json.dumps(filtered, ensure_ascii=False)}")

        if req.get('http_status'):
            lines.append(f"  Status: {req.get('http_status')}")
        return "\n".join(lines)

    def _extract_common_params(self, paths: dict[str, Any]) -> list[str]:
        """从API paths中提取通用参数"""
        params: list[str] = []
        param_counts: dict[str, int] = {}

        for path, methods in paths.items():
            for method, spec in methods.items():
                if not isinstance(spec, dict):
                    continue
                for param in spec.get('parameters', []):
                    if isinstance(param, dict):
                        name = param.get('name', '')
                        location = param.get('in', '')
                        if name and location:
                            key = f"{location}:{name}"
                            param_counts[key] = param_counts.get(key, 0) + 1

        for key, count in sorted(param_counts.items(), key=lambda x: -x[1])[:10]:
            if count >= 3:
                location, name = key.split(':', 1)
                params.append(f"参数 '{name}' (in {location}) 出现 {count} 次")
        return params

    def _extract_with_llm(
        self,
        content: str,
        source_ref: str
    ) -> list[KnowledgeSuggestion]:
        """使用LLM提取知识"""
        if not self._llm_chain:
            logger.warning("LLM chain not configured, skipping knowledge extraction")
            return []

        try:
            if hasattr(self._llm_chain, 'extract_knowledge'):
                items = self._llm_chain.extract_knowledge(content)
            else:
                # V2 使用新 prompt
                prompt_template = KNOWLEDGE_EXTRACTION_PROMPT_V2 if _pipeline_v2_enabled() else KNOWLEDGE_EXTRACTION_PROMPT
                prompt = prompt_template.format(content=content)
                response = self._llm_chain.invoke(prompt)
                response_text = response if isinstance(response, str) else str(response)
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    items = json.loads(response_text[json_start:json_end])
                else:
                    logger.warning("No JSON array found in LLM response")
                    return []

            if not items:
                logger.info(f"LLM returned empty result for {source_ref}")
                return []

            suggestions = []
            for item in items:
                if not isinstance(item, dict):
                    continue

                suggestion = KnowledgeSuggestion(
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    type=item.get('type', 'business_rule'),
                    category=item.get('category', ''),
                    sub_category=item.get('sub_category', ''),
                    scope=item.get('scope', ''),
                    tags=item.get('tags', []),
                    confidence=float(item.get('confidence', 0.5)),
                    source_ref=source_ref,
                    reason=item.get('reason', '')
                )

                if suggestion.title and suggestion.content:
                    suggestions.append(suggestion)

            logger.info(f"Extracted {len(suggestions)} knowledge suggestions from {source_ref}")
            return suggestions

        except Exception as e:
            logger.error(f"Failed to extract knowledge with LLM: {e}")
            return []

    def learn_from_task(
        self,
        task_id: str,
        auto_approve: bool = False,
    ) -> tuple[list[str], list[dict]]:
        """从已完成的日志分析任务中学习知识"""
        from ..database.repository import RequestRepository, TaskRepository
        from ..database.models.base import TaskStatus

        task_repo = TaskRepository()
        request_repo = RequestRepository()

        task = task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        if task.status != TaskStatus.COMPLETED:
            raise ValueError(f"任务状态不是 completed（当前: {task.status.value}）")

        rows = request_repo.db.fetch_all(
            "SELECT * FROM parsed_requests WHERE task_id = %s",
            (task_id,)
        )
        if not rows:
            raise ValueError(f"任务 {task_id} 无解析请求数据")

        parsed_requests = [dict(r) for r in rows]
        suggestions = self.extract_from_log_analysis(parsed_requests, task_id)
        if not suggestions:
            return [], []

        created_ids = []
        items_detail = []
        filtered_count = 0
        for suggestion in suggestions:
            if suggestion.confidence < 0.3:
                filtered_count += 1
                continue

            item = self.store.create_from_suggestion(suggestion, "log_task_learning")
            created_ids.append(item.knowledge_id)

            status = "pending"
            if auto_approve and suggestion.confidence >= 0.8:
                self.store.approve([item.knowledge_id])
                status = "active"

            items_detail.append({
                "knowledge_id": item.knowledge_id,
                "title": suggestion.title,
                "type": suggestion.type,
                "confidence": round(suggestion.confidence, 2),
                "status": status,
            })

        if filtered_count > 0:
            logger.info(f"任务 {task_id}: {filtered_count} 条建议因置信度低于 0.3 被过滤")
        if suggestions and not created_ids:
            logger.warning(f"任务 {task_id}: LLM返回了 {len(suggestions)} 条建议，但全部因置信度过低被过滤")
        logger.info(f"从任务 {task_id} 学习完成，创建 {len(created_ids)} 条知识")
        return created_ids, items_detail

    def learn_and_save(
        self,
        content: str,
        source_ref: str,
        auto_approve: bool = False,
        created_by: str = ""
    ) -> list[str]:
        """学习并保存知识"""
        suggestions = self._extract_with_llm(content, source_ref)

        created_ids = []
        filtered_count = 0
        for suggestion in suggestions:
            if suggestion.confidence < 0.3:
                filtered_count += 1
                continue

            item = self.store.create_from_suggestion(suggestion, created_by)
            created_ids.append(item.knowledge_id)

            if auto_approve and suggestion.confidence >= 0.8:
                self.store.approve([item.knowledge_id])

        if filtered_count > 0:
            logger.info(f"learn_and_save({source_ref}): {filtered_count} 条建议因置信度低于 0.3 被过滤")
        if suggestions and not created_ids:
            logger.warning(f"learn_and_save({source_ref}): LLM返回了 {len(suggestions)} 条建议，但全部因置信度过低被过滤")

        return created_ids
