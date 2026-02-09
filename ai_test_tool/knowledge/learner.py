"""
知识学习引擎
该文件内容使用AI生成，注意识别准确性

从日志解析和测试执行中提取知识
"""

import logging
import json
from typing import Any

from .models import KnowledgeSuggestion
from .store import KnowledgeStore

logger = logging.getLogger(__name__)


# 知识提取提示词模板
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
    
    def set_llm_chain(self, chain: Any) -> None:
        """设置LLM链"""
        self._llm_chain = chain
    
    def extract_from_log_analysis(
        self,
        parsed_requests: list[dict[str, Any]],
        task_id: str = ""
    ) -> list[KnowledgeSuggestion]:
        """
        从日志解析结果中提取知识
        
        Args:
            parsed_requests: 解析的请求列表
            task_id: 关联的任务ID
        
        Returns:
            知识建议列表
        """
        if not parsed_requests:
            return []
        
        # 准备分析内容
        content_parts = ["## 日志解析结果分析\n"]
        
        # 统计信息
        urls = [req.get('url', '') for req in parsed_requests]
        unique_urls = list(set(urls))
        
        content_parts.append(f"解析了 {len(parsed_requests)} 个请求，涉及 {len(unique_urls)} 个不同的接口。\n")
        
        # 分析header模式
        header_patterns = self._analyze_headers(parsed_requests)
        if header_patterns:
            content_parts.append("### Header模式分析")
            for pattern in header_patterns:
                content_parts.append(f"- {pattern}")
            content_parts.append("")
        
        # 分析URL模式
        url_patterns = self._analyze_url_patterns(unique_urls)
        if url_patterns:
            content_parts.append("### URL模式分析")
            for pattern in url_patterns:
                content_parts.append(f"- {pattern}")
            content_parts.append("")
        
        # 分析错误模式
        error_patterns = self._analyze_errors(parsed_requests)
        if error_patterns:
            content_parts.append("### 错误模式分析")
            for pattern in error_patterns:
                content_parts.append(f"- {pattern}")
            content_parts.append("")
        
        # 样例请求
        content_parts.append("### 样例请求")
        for req in parsed_requests[:5]:
            content_parts.append(self._format_request_sample(req))
        
        content = "\n".join(content_parts)
        
        # 调用LLM提取知识
        suggestions = self._extract_with_llm(content, f"log_analysis:{task_id}")
        
        return suggestions
    
    def extract_from_test_results(
        self,
        test_results: list[dict[str, Any]],
        execution_id: str = ""
    ) -> list[KnowledgeSuggestion]:
        """
        从测试执行结果中提取知识（特别是失败案例）
        
        Args:
            test_results: 测试结果列表
            execution_id: 关联的执行ID
        
        Returns:
            知识建议列表
        """
        if not test_results:
            return []
        
        # 筛选失败的测试
        failed_tests = [r for r in test_results if r.get('status') in ('failed', 'error')]
        
        if not failed_tests:
            return []
        
        # 准备分析内容
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
        
        # 调用LLM提取知识
        suggestions = self._extract_with_llm(content, f"test_execution:{execution_id}")
        
        return suggestions
    
    def extract_from_api_doc(
        self,
        api_doc: dict[str, Any],
        source_file: str = ""
    ) -> list[KnowledgeSuggestion]:
        """
        从API文档中提取知识
        
        Args:
            api_doc: API文档（OpenAPI/Swagger格式）
            source_file: 来源文件
        
        Returns:
            知识建议列表
        """
        if not api_doc:
            return []
        
        content_parts = ["## API文档分析\n"]
        
        # 提取基本信息
        info = api_doc.get('info', {})
        if info:
            content_parts.append(f"API名称: {info.get('title', 'Unknown')}")
            content_parts.append(f"版本: {info.get('version', 'Unknown')}")
            if info.get('description'):
                content_parts.append(f"描述: {info.get('description')}")
            content_parts.append("")
        
        # 提取安全配置
        security_defs = api_doc.get('securityDefinitions', api_doc.get('components', {}).get('securitySchemes', {}))
        if security_defs:
            content_parts.append("### 安全配置")
            for name, config in security_defs.items():
                content_parts.append(f"- {name}: {config.get('type', '')} - {config.get('description', '')}")
            content_parts.append("")
        
        # 提取通用参数
        paths = api_doc.get('paths', {})
        common_params = self._extract_common_params(paths)
        if common_params:
            content_parts.append("### 通用参数模式")
            for param in common_params:
                content_parts.append(f"- {param}")
            content_parts.append("")
        
        content = "\n".join(content_parts)
        
        # 调用LLM提取知识
        suggestions = self._extract_with_llm(content, f"api_doc:{source_file}")
        
        return suggestions
    
    def _analyze_headers(self, requests: list[dict[str, Any]]) -> list[str]:
        """分析header模式"""
        patterns = []
        
        # 统计常见header
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
                header_values[key_lower].add(str(value)[:50])  # 截断长值
        
        # 找出高频header
        total = len(requests)
        for header, count in sorted(header_counts.items(), key=lambda x: -x[1]):
            if count >= total * 0.5:  # 出现在50%以上请求中
                values = header_values.get(header, set())
                if len(values) <= 3:
                    patterns.append(f"Header '{header}' 出现在 {count}/{total} 请求中，值: {', '.join(values)}")
                else:
                    patterns.append(f"Header '{header}' 出现在 {count}/{total} 请求中")
        
        return patterns[:10]
    
    def _analyze_url_patterns(self, urls: list[str]) -> list[str]:
        """分析URL模式"""
        patterns = []
        
        # 提取路径前缀
        prefixes: dict[str, int] = {}
        for url in urls:
            path = url.split('?')[0]
            parts = path.strip('/').split('/')
            if len(parts) >= 2:
                prefix = '/' + '/'.join(parts[:2])
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        # 找出高频前缀
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
        
        # 按状态码分组
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
    
    def _format_request_sample(self, req: dict[str, Any]) -> str:
        """格式化请求样例"""
        lines = []
        lines.append(f"- {req.get('method', 'GET')} {req.get('url', '')}")
        
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
        
        # 找出高频参数
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
        """
        使用LLM提取知识
        """
        if not self._llm_chain:
            logger.warning("LLM chain not configured, skipping knowledge extraction")
            return []
        
        try:
            prompt = KNOWLEDGE_EXTRACTION_PROMPT.format(content=content)
            response = self._llm_chain.invoke(prompt)
            
            # 解析JSON响应
            response_text = response if isinstance(response, str) else str(response)
            
            # 尝试提取JSON
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                items = json.loads(json_str)
            else:
                logger.warning("No JSON array found in LLM response")
                return []
            
            # 转换为KnowledgeSuggestion
            suggestions = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                suggestion = KnowledgeSuggestion(
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    type=item.get('type', 'project_config'),
                    category=item.get('category', ''),
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
    
    def learn_and_save(
        self,
        content: str,
        source_ref: str,
        auto_approve: bool = False,
        created_by: str = ""
    ) -> list[str]:
        """
        学习并保存知识
        
        Args:
            content: 要分析的内容
            source_ref: 来源引用
            auto_approve: 是否自动审核通过
            created_by: 创建者
        
        Returns:
            创建的知识ID列表
        """
        suggestions = self._extract_with_llm(content, source_ref)
        
        created_ids = []
        for suggestion in suggestions:
            # 只保存置信度较高的
            if suggestion.confidence < 0.5:
                continue
            
            item = self.store.create_from_suggestion(suggestion, created_by)
            created_ids.append(item.knowledge_id)
            
            # 自动审核
            if auto_approve and suggestion.confidence >= 0.8:
                self.store.approve([item.knowledge_id])
        
        return created_ids
