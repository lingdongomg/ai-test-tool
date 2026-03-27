# 该文件内容使用AI生成，注意识别准确性
"""
LangChain Chains
封装各种LLM处理链，带有日志监控
Python 3.13+ 兼容
"""

import json
import re
from typing import Any

from .provider import LLMProvider, get_llm_provider
from .prompts import (
    LOG_ANALYSIS_PROMPT,
    LOG_CATEGORIZATION_PROMPT,
    LOG_CATEGORIZATION_WITH_RAG_PROMPT,
    ANALYSIS_REPORT_PROMPT,
    TEST_CASE_GENERATION_PROMPT,
    TEST_CASE_GENERATION_WITH_RAG_PROMPT,
    RESULT_VALIDATION_PROMPT,
    LOG_DIAGNOSIS_PROMPT,
    API_DOC_COMPARISON_PROMPT,
    KNOWLEDGE_EXTRACTION_PROMPT,
    TEST_CASE_GENERATION_WITH_KNOWLEDGE_PROMPT,
)
from ..utils.logger import get_logger


class BaseChain:
    """Chain基类 - 提供JSON解析和LLM调用基础设施"""

    def __init__(
        self, provider: LLMProvider | None = None, verbose: bool = False
    ) -> None:
        self.provider = provider or get_llm_provider()
        self.verbose = verbose
        self.logger = get_logger(verbose)

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """解析JSON响应，支持多种格式"""
        response = response.strip().lstrip("\ufeff")

        # 移除深度思考模型的 <think>...</think> 标签
        response = re.sub(r"<think>[\s\S]*?</think>\s*", "", response).strip()

        # 尝试多种解析方式
        for parser in [
            self._parse_direct,
            self._parse_code_block,
            self._parse_braces,
            self._parse_array,
        ]:
            result = parser(response)
            if result is not None:
                return result

        # 尝试修复截断的JSON
        result = self._try_fix_truncated_json(response)
        if result:
            return result

        self.logger.warn("JSON解析失败，返回原始响应")
        return {"raw_response": response, "parse_error": True}

    def _parse_direct(self, s: str) -> dict[str, Any] | None:
        """直接解析JSON"""
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None

    def _parse_code_block(self, s: str) -> dict[str, Any] | None:
        """从```json```代码块提取"""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        return None

    def _parse_braces(self, s: str) -> dict[str, Any] | None:
        """提取花括号内容"""
        start, end = s.find("{"), s.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = s[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复常见问题
                fixed = self._fix_common_issues(json_str)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        return None

    def _parse_array(self, s: str) -> dict[str, Any] | None:
        """提取数组内容"""
        start, end = s.find("["), s.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return {"data": json.loads(s[start:end])}
            except json.JSONDecodeError:
                pass
        return None

    def _fix_common_issues(self, s: str) -> str:
        """修复常见JSON格式问题"""
        s = re.sub(r",\s*([}\]])", r"\1", s)  # 移除尾部逗号
        s = re.sub(r"//.*$", "", s, flags=re.MULTILINE)  # 移除注释
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
        return s

    def _try_fix_truncated_json(self, s: str) -> dict[str, Any] | None:
        """修复被截断的JSON"""
        start = s.find("{")
        if start < 0:
            return None

        try:
            truncated = s[start:].rstrip()
            truncated = re.sub(r",\s*$", "", truncated)

            # 补全缺失的闭合括号
            open_braces = truncated.count("{") - truncated.count("}")
            open_brackets = truncated.count("[") - truncated.count("]")

            if open_braces <= 0 and open_brackets <= 0:
                return None

            # 移除不完整的键值对
            truncated = re.sub(r',?\s*"[^"]*"\s*:\s*$', "", truncated)
            truncated = re.sub(r",\s*$", "", truncated)

            # 补全括号
            truncated += "]" * max(0, truncated.count("[") - truncated.count("]"))
            truncated += "}" * max(0, truncated.count("{") - truncated.count("}"))

            return json.loads(truncated)
        except Exception:
            return None

    def _call_llm(self, prompt: str, operation: str) -> str:
        """调用LLM并记录日志"""
        self.logger.ai_start(operation, prompt)
        try:
            response = self.provider.generate(prompt)
            self.logger.ai_end(response)
            return response
        except Exception as e:
            self.logger.ai_error(str(e))
            raise


class LogAnalysisChain(BaseChain):
    """日志分析Chain"""

    RETRY_PROMPT = """你之前的回复没有按要求输出JSON格式。请重新分析并**只输出JSON**。
原始日志：
```
{log_content}
```
直接输出JSON（如果没有HTTP请求，requests数组为空）："""

    def analyze_logs(self, log_content: str, max_retries: int = 2) -> dict[str, Any]:
        """智能分析日志内容"""
        prompt = LOG_ANALYSIS_PROMPT.format(log_content=log_content)

        result = {}

        for attempt in range(max_retries + 1):
            if attempt > 0:
                prompt = self.RETRY_PROMPT.format(log_content=log_content)

            response = self._call_llm(prompt, "日志分析")
            result = self._parse_json_response(response)

            if not result.get("parse_error"):
                break

        # 确保返回结构完整
        result.setdefault("requests", [])
        result.setdefault("errors", [])
        result.setdefault("warnings", [])
        result.setdefault("analysis", {})
        return result

    def categorize_requests(
        self, requests: list[dict[str, Any]], api_doc_context: str = ""
    ) -> dict[str, Any]:
        """对请求进行智能分类（规则优先 + LLM 回退）"""
        # 第一步：用规则引擎分类（零 LLM 成本）
        from ..skills.data_skills import classify_request
        categorized = []
        uncategorized = []
        category_summary: dict[str, int] = {}

        for req in requests[:50]:
            url = req.get("url", "")
            result = classify_request(url)
            cat = result.get("category", "其他")
            confidence = result.get("confidence", 0)

            if confidence >= 0.7:
                categorized.append({"url": url, "category": cat, "source": "rule"})
                category_summary[cat] = category_summary.get(cat, 0) + 1
            else:
                uncategorized.append(req)

        # 第二步：只对未分类的请求调用 LLM
        if uncategorized and len(uncategorized) <= len(requests) * 0.5:
            # 未分类数量较少时才调 LLM，节省 token
            try:
                requests_json = json.dumps(uncategorized, ensure_ascii=False, indent=2)
                if api_doc_context:
                    prompt = LOG_CATEGORIZATION_WITH_RAG_PROMPT.format(
                        api_doc_context=api_doc_context, requests_json=requests_json
                    )
                else:
                    prompt = LOG_CATEGORIZATION_PROMPT.format(requests_json=requests_json)

                llm_result = self._parse_json_response(self._call_llm(prompt, "请求分类"))
                for item in llm_result.get("categorized_requests", []):
                    item["source"] = "llm"
                    categorized.append(item)
                    cat = item.get("category", "其他")
                    category_summary[cat] = category_summary.get(cat, 0) + 1
            except Exception as e:
                logger.warning(f"LLM 分类回退失败: {e}")
                for req in uncategorized:
                    categorized.append({"url": req.get("url", ""), "category": "其他", "source": "fallback"})
                    category_summary["其他"] = category_summary.get("其他", 0) + 1
        elif uncategorized:
            # 全量调 LLM
            requests_json = json.dumps(requests[:50], ensure_ascii=False, indent=2)
            if api_doc_context:
                prompt = LOG_CATEGORIZATION_WITH_RAG_PROMPT.format(
                    api_doc_context=api_doc_context, requests_json=requests_json
                )
            else:
                prompt = LOG_CATEGORIZATION_PROMPT.format(requests_json=requests_json)
            return self._parse_json_response(self._call_llm(prompt, "请求分类"))

        return {"categorized_requests": categorized, "category_summary": category_summary}

    def compare_with_api_doc(
        self, api_doc_summary: str, coverage_data: dict[str, Any]
    ) -> dict[str, Any]:
        """对比分析接口文档与实际日志"""
        prompt = API_DOC_COMPARISON_PROMPT.format(
            api_doc_summary=api_doc_summary,
            coverage_data=json.dumps(coverage_data, ensure_ascii=False, indent=2),
        )
        return self._parse_json_response(self._call_llm(prompt, "文档对比分析"))

    def diagnose_errors(
        self, error_logs: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """诊断错误日志（支持知识上下文增强）"""
        ctx = context or {}
        knowledge_context = ctx.pop("knowledge_context", "")

        if knowledge_context:
            from .prompts import LOG_DIAGNOSIS_WITH_RAG_PROMPT
            prompt = LOG_DIAGNOSIS_WITH_RAG_PROMPT.format(
                knowledge_context=knowledge_context,
                error_logs=error_logs,
                context=json.dumps(ctx, ensure_ascii=False),
            )
        else:
            prompt = LOG_DIAGNOSIS_PROMPT.format(
                error_logs=error_logs, context=json.dumps(ctx, ensure_ascii=False)
            )
        return self._parse_json_response(self._call_llm(prompt, "错误诊断"))


class ReportGeneratorChain(BaseChain):
    """报告生成Chain"""

    def generate_report(
        self,
        summary_data: dict[str, Any],
        error_logs: list[dict[str, Any]],
        warning_logs: list[dict[str, Any]],
        performance_data: dict[str, Any],
        use_template: bool = True,
    ) -> str:
        """生成分析报告（模板优先 + LLM 回退）"""
        # 模板优先：简单场景直接用 Markdown 模板
        if use_template and len(error_logs) + len(warning_logs) <= 30:
            try:
                from ..skills.analysis_skills import generate_report_from_template
                anomalies = []
                for e in error_logs:
                    anomalies.append({
                        "type": e.get("type", "error"),
                        "severity": "error",
                        "title": e.get("message", e.get("title", "错误")),
                        "description": str(e.get("message", ""))[:200],
                    })
                for w in warning_logs:
                    anomalies.append({
                        "type": w.get("type", "warning"),
                        "severity": "warning",
                        "title": w.get("message", w.get("title", "警告")),
                        "description": str(w.get("message", ""))[:200],
                    })

                result = generate_report_from_template(
                    title="日志分析报告",
                    anomalies=anomalies,
                    stats=summary_data,
                )
                content = result.get("content", "")
                if content:
                    logger.info("使用模板生成报告（跳过 LLM）")
                    return content
            except Exception as e:
                logger.debug(f"模板报告生成失败，回退到 LLM: {e}")

        # LLM 回退
        prompt = ANALYSIS_REPORT_PROMPT.format(
            summary_data=json.dumps(summary_data, ensure_ascii=False, indent=2),
            error_logs=json.dumps(error_logs[:20], ensure_ascii=False, indent=2),
            warning_logs=json.dumps(warning_logs[:20], ensure_ascii=False, indent=2),
            performance_data=json.dumps(performance_data, ensure_ascii=False, indent=2),
        )
        return self._call_llm(prompt, "报告生成")


class TestCaseGeneratorChain(BaseChain):
    """测试用例生成Chain"""

    def generate_test_cases(
        self,
        api_info: dict[str, Any],
        sample_requests: list[dict[str, Any]],
        test_strategy: str = "comprehensive",
        api_doc_context: str = "",
    ) -> dict[str, Any]:
        """生成测试用例"""
        if api_doc_context:
            prompt = TEST_CASE_GENERATION_WITH_RAG_PROMPT.format(
                api_doc_context=api_doc_context,
                api_info=json.dumps(api_info, ensure_ascii=False, indent=2),
                sample_requests=json.dumps(
                    sample_requests[:10], ensure_ascii=False, indent=2
                ),
                test_strategy=test_strategy,
            )
        else:
            prompt = TEST_CASE_GENERATION_PROMPT.format(
                api_info=json.dumps(api_info, ensure_ascii=False, indent=2),
                sample_requests=json.dumps(
                    sample_requests[:10], ensure_ascii=False, indent=2
                ),
                test_strategy=test_strategy,
            )

        return self._parse_json_response(self._call_llm(prompt, "测试用例生成"))


class ResultValidatorChain(BaseChain):
    """结果验证Chain"""

    def validate_response(
        self,
        test_case: dict[str, Any],
        actual_response: dict[str, Any],
        expected_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """验证测试结果"""
        prompt = RESULT_VALIDATION_PROMPT.format(
            test_case=json.dumps(test_case, ensure_ascii=False, indent=2),
            actual_response=json.dumps(actual_response, ensure_ascii=False, indent=2),
            expected_response=json.dumps(
                expected_response or {}, ensure_ascii=False, indent=2
            ),
        )
        return self._parse_json_response(self._call_llm(prompt, "结果验证"))


class CurlGeneratorChain(BaseChain):
    """Curl命令生成Chain（纯代码实现，不依赖LLM）"""

    def generate_curl(
        self, request_info: dict[str, Any], base_url: str = "http://localhost:8080"
    ) -> str:
        """生成curl命令"""
        method = request_info.get("method", "GET").upper()
        url = request_info.get("url", "")
        headers = request_info.get("headers", {})
        body = request_info.get("body")

        full_url = f"{base_url.rstrip('/')}{url}" if not url.startswith("http") else url
        parts = ["curl", "-s"]

        if method != "GET":
            parts.append(f"-X {method}")

        parts.append(f'"{full_url}"')

        for key, value in headers.items():
            parts.append(f'-H "{key}: {value}"')

        if body:
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False)
            if "Content-Type" not in headers:
                parts.append('-H "Content-Type: application/json"')
            parts.append(
                f"-d '{body.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'"
            )

        return " ".join(parts)


# 该文件内容使用AI生成，注意识别准确性
class KnowledgeExtractionChain(BaseChain):
    """知识提取Chain - 从日志和测试结果中提取知识"""

    def extract_knowledge(self, content: str) -> list[dict[str, Any]]:
        """
        从内容中提取知识
        
        Args:
            content: 要分析的内容（日志、测试结果等）
        
        Returns:
            提取的知识列表
        """
        prompt = KNOWLEDGE_EXTRACTION_PROMPT.format(content=content)
        response = self._call_llm(prompt, "知识提取")
        
        # 解析响应
        result = self._parse_json_response(response)
        
        # 如果是数组，直接返回
        if isinstance(result, list):
            return result
        
        # 如果是包装在data中的数组
        if isinstance(result.get('data'), list):
            return result['data']
        
        # 解析失败返回空
        if result.get('parse_error'):
            return []
        
        return []


class KnowledgeEnhancedTestGeneratorChain(BaseChain):
    """知识增强的测试用例生成Chain"""

    def generate_test_cases(
        self,
        api_info: dict[str, Any],
        sample_requests: list[dict[str, Any]],
        knowledge_context: str,
        test_strategy: str = "comprehensive",
    ) -> dict[str, Any]:
        """
        生成知识增强的测试用例
        
        Args:
            api_info: API信息
            sample_requests: 样例请求
            knowledge_context: 知识库上下文
            test_strategy: 测试策略
        
        Returns:
            生成的测试用例
        """
        prompt = TEST_CASE_GENERATION_WITH_KNOWLEDGE_PROMPT.format(
            knowledge_context=knowledge_context,
            api_info=json.dumps(api_info, ensure_ascii=False, indent=2),
            sample_requests=json.dumps(
                sample_requests[:10], ensure_ascii=False, indent=2
            ),
            test_strategy=test_strategy,
        )

        return self._parse_json_response(self._call_llm(prompt, "知识增强测试用例生成"))
