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
    API_DOC_COMPARISON_PROMPT
)
from ..utils.logger import get_logger


class BaseChain:
    """Chain基类"""
    
    def __init__(self, provider: LLMProvider | None = None, verbose: bool = False) -> None:
        self.provider = provider or get_llm_provider()
        self.verbose = verbose
        self.logger = get_logger(verbose)
    
    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """
        解析JSON响应
        
        尝试多种方式解析AI返回的JSON，并记录详细的DEBUG日志
        """
        self.logger.debug(f"开始解析JSON响应，响应长度: {len(response)} 字符")
        
        # 预处理：去除可能的BOM和首尾空白
        response = response.strip().lstrip('\ufeff')
        
        # 预处理：移除深度思考模型的 <think>...</think> 标签
        # 支持 DeepSeek、QwQ 等模型的思考过程输出
        think_match = re.search(r'<think>[\s\S]*?</think>\s*', response)
        if think_match:
            think_content = think_match.group(0)
            self.logger.debug(f"检测到思考标签，长度: {len(think_content)} 字符，已移除")
            response = response[len(think_content):].strip()
        
        # 方法1: 尝试直接解析
        try:
            result = json.loads(response)
            self.logger.debug("JSON解析成功（直接解析）")
            return result
        except json.JSONDecodeError as e:
            self.logger.debug(f"直接解析失败: {e}")
        
        # 方法2: 尝试提取```json```代码块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                result = json.loads(json_str)
                self.logger.debug("JSON解析成功（从代码块提取）")
                return result
            except json.JSONDecodeError as e:
                self.logger.debug(f"代码块JSON解析失败: {e}")
        
        # 方法3: 尝试找到最外层的JSON对象 {}
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            try:
                result = json.loads(json_str)
                self.logger.debug("JSON解析成功（提取花括号内容）")
                return result
            except json.JSONDecodeError as e:
                self.logger.debug(f"花括号内容解析失败: {e}")
                
                # 方法4: 尝试修复常见的JSON格式问题
                fixed_json = self._try_fix_json(json_str)
                if fixed_json:
                    try:
                        result = json.loads(fixed_json)
                        self.logger.debug("JSON解析成功（修复后）")
                        return result
                    except json.JSONDecodeError as e:
                        self.logger.debug(f"修复后解析仍失败: {e}")
        
        # 方法5: 尝试找到JSON数组 []
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            try:
                result = json.loads(json_str)
                self.logger.debug("JSON解析成功（提取数组）")
                return {"data": result}  # 包装为对象
            except json.JSONDecodeError as e:
                self.logger.debug(f"数组解析失败: {e}")
        
        # 方法6: 尝试修复被截断的JSON（AI输出因max_tokens被截断）
        start = response.find('{')
        if start >= 0:
            truncated_json = response[start:]
            result = self._try_fix_truncated_json(truncated_json)
            if result:
                self.logger.debug("JSON解析成功（截断修复）")
                return result
        
        # 所有方法都失败，记录警告和完整响应（用于调试）
        self.logger.warn(f"JSON解析失败，返回原始响应")
        # 记录完整响应到DEBUG日志，便于排查问题
        self.logger.debug(f"原始响应完整内容:\n{response}")
        
        return {"raw_response": response, "parse_error": True}
    
    def _try_fix_json(self, json_str: str) -> str | None:
        """
        尝试修复常见的JSON格式问题
        
        Args:
            json_str: 可能有问题的JSON字符串
            
        Returns:
            修复后的JSON字符串，如果无法修复则返回None
        """
        try:
            # 修复1: 移除尾部逗号（常见于AI生成的JSON）
            # 例如: {"a": 1,} -> {"a": 1}
            fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
            
            # 修复2: 处理单引号（某些AI可能用单引号）
            # 注意：这个修复可能不完美，但对简单情况有效
            if "'" in fixed and '"' not in fixed:
                fixed = fixed.replace("'", '"')
            
            # 修复3: 处理未转义的换行符
            fixed = fixed.replace('\n', '\\n').replace('\r', '\\r')
            # 但保留JSON结构中的换行
            fixed = re.sub(r'\\n\s*([{\[\]}:,"])', lambda m: '\n' + m.group(1), fixed)
            
            # 修复4: 处理注释（某些AI可能添加注释）
            fixed = re.sub(r'//.*$', '', fixed, flags=re.MULTILINE)
            fixed = re.sub(r'/\*.*?\*/', '', fixed, flags=re.DOTALL)
            
            return fixed if fixed != json_str else None
        except Exception:
            return None
    
    def _try_fix_truncated_json(self, json_str: str) -> dict[str, Any] | None:
        """
        尝试修复被截断的JSON（AI输出因max_tokens限制被截断）
        
        Args:
            json_str: 被截断的JSON字符串
            
        Returns:
            修复后的字典，如果无法修复则返回None
        """
        try:
            # 统计未闭合的括号
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')
            
            if open_braces <= 0 and open_brackets <= 0:
                return None  # 括号已平衡，不是截断问题
            
            self.logger.debug(f"检测到截断JSON: 未闭合 {{ = {open_braces}, [ = {open_brackets}")
            
            # 尝试找到最后一个完整的对象/数组元素
            # 策略：从后往前找到最后一个逗号或冒号后的位置，截断到那里
            
            # 移除末尾不完整的内容（找到最后一个完整的值）
            # 常见模式：截断在字符串中间、数字中间、或对象/数组中间
            
            fixed = json_str.rstrip()
            
            # 如果以逗号结尾，移除逗号
            fixed = re.sub(r',\s*$', '', fixed)
            
            # 如果在字符串中间被截断（有未闭合的引号）
            quote_count = fixed.count('"') - fixed.count('\\"')
            if quote_count % 2 == 1:
                # 找到最后一个未转义的引号位置
                last_quote = fixed.rfind('"')
                if last_quote > 0:
                    # 检查这个引号是否是键的开始
                    before_quote = fixed[:last_quote].rstrip()
                    if before_quote.endswith(':') or before_quote.endswith(',') or before_quote.endswith('[') or before_quote.endswith('{'):
                        # 这是一个值的开始，截断到冒号/逗号之前
                        if before_quote.endswith(':'):
                            fixed = before_quote[:-1].rstrip()
                            # 还需要移除键
                            key_match = re.search(r',?\s*"[^"]*"\s*$', fixed)
                            if key_match:
                                fixed = fixed[:key_match.start()]
                        else:
                            fixed = before_quote[:-1] if before_quote[-1] in ',{[' else before_quote
                    else:
                        # 在值中间被截断，添加闭合引号
                        fixed = fixed + '"'
            
            # 移除末尾不完整的键值对
            # 模式: "key": 没有值
            fixed = re.sub(r',?\s*"[^"]*"\s*:\s*$', '', fixed)
            
            # 移除末尾的逗号
            fixed = re.sub(r',\s*$', '', fixed)
            
            # 补全缺失的闭合括号
            open_braces = fixed.count('{') - fixed.count('}')
            open_brackets = fixed.count('[') - fixed.count(']')
            
            # 按照嵌套顺序补全（简化处理：先补]再补}）
            fixed += ']' * open_brackets
            fixed += '}' * open_braces
            
            # 尝试解析修复后的JSON
            result = json.loads(fixed)
            self.logger.debug(f"截断JSON修复成功")
            return result
            
        except Exception as e:
            self.logger.debug(f"截断JSON修复失败: {e}")
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
    """日志分析Chain - 核心智能分析"""
    
    # 重试提示词 - 当AI没有输出JSON时使用
    RETRY_PROMPT = """你之前的回复没有按要求输出JSON格式。请重新分析并**只输出JSON**，不要输出任何解释文字。

原始日志内容：
```
{log_content}
```

请直接输出符合以下格式的JSON（如果没有HTTP请求，requests数组为空）：
```json
{{
  "requests": [],
  "errors": [],
  "warnings": [],
  "analysis": {{"total_requests": 0, "success_count": 0, "error_count": 0, "warning_count": 0, "observations": []}}
}}
```

只输出JSON："""
    
    def analyze_logs(self, log_content: str, max_retries: int = 2) -> dict[str, Any]:
        """
        智能分析日志内容，支持失败重试
        
        Args:
            log_content: 日志内容（可以是多行）
            max_retries: 最大重试次数（默认2次）
            
        Returns:
            分析结果，包含requests、errors、warnings、analysis
        """
        prompt = LOG_ANALYSIS_PROMPT.format(log_content=log_content)
        result: dict[str, Any] = {"parse_error": True}  # 初始化
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                # 重试时使用更简洁的提示词
                self.logger.debug(f"JSON解析失败，进行第 {attempt} 次重试")
                prompt = self.RETRY_PROMPT.format(log_content=log_content)
            
            response = self._call_llm(prompt, "日志分析")
            result = self._parse_json_response(response)
            
            # 检查是否解析成功（不是原始响应）
            if not result.get("parse_error"):
                break
            
            # 如果还有重试机会，继续
            if attempt < max_retries:
                self.logger.debug(f"将进行重试...")
        
        # 确保返回结构完整
        if "requests" not in result:
            result["requests"] = []
        if "errors" not in result:
            result["errors"] = []
        if "warnings" not in result:
            result["warnings"] = []
        if "analysis" not in result:
            result["analysis"] = {}
        
        # 记录解析结果
        req_count = len(result["requests"])
        err_count = len(result["errors"])
        if req_count > 0 or err_count > 0:
            self.logger.debug(f"   解析结果: {req_count}个请求, {err_count}个错误")
            
        return result
    
    def categorize_requests(
        self,
        requests: list[dict[str, Any]],
        api_doc_context: str = ""
    ) -> dict[str, Any]:
        """
        对请求进行智能分类
        
        Args:
            requests: 请求列表
            api_doc_context: 接口文档上下文（RAG）
        """
        requests_json = json.dumps(requests[:50], ensure_ascii=False, indent=2)
        
        if api_doc_context:
            # 使用带RAG的提示词
            prompt = LOG_CATEGORIZATION_WITH_RAG_PROMPT.format(
                api_doc_context=api_doc_context,
                requests_json=requests_json
            )
        else:
            prompt = LOG_CATEGORIZATION_PROMPT.format(requests_json=requests_json)
        
        response = self._call_llm(prompt, "请求分类")
        return self._parse_json_response(response)
    
    def compare_with_api_doc(
        self,
        api_doc_summary: str,
        coverage_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        对比分析接口文档与实际日志
        
        Args:
            api_doc_summary: 接口文档摘要
            coverage_data: 覆盖分析数据
        """
        prompt = API_DOC_COMPARISON_PROMPT.format(
            api_doc_summary=api_doc_summary,
            coverage_data=json.dumps(coverage_data, ensure_ascii=False, indent=2)
        )
        response = self._call_llm(prompt, "文档对比分析")
        return self._parse_json_response(response)
    
    def diagnose_errors(self, error_logs: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """诊断错误日志"""
        prompt = LOG_DIAGNOSIS_PROMPT.format(
            error_logs=error_logs,
            context=json.dumps(context or {}, ensure_ascii=False)
        )
        response = self._call_llm(prompt, "错误诊断")
        return self._parse_json_response(response)


class ReportGeneratorChain(BaseChain):
    """报告生成Chain"""
    
    def generate_report(
        self,
        summary_data: dict[str, Any],
        error_logs: list[dict[str, Any]],
        warning_logs: list[dict[str, Any]],
        performance_data: dict[str, Any]
    ) -> str:
        """生成分析报告"""
        prompt = ANALYSIS_REPORT_PROMPT.format(
            summary_data=json.dumps(summary_data, ensure_ascii=False, indent=2),
            error_logs=json.dumps(error_logs[:20], ensure_ascii=False, indent=2),
            warning_logs=json.dumps(warning_logs[:20], ensure_ascii=False, indent=2),
            performance_data=json.dumps(performance_data, ensure_ascii=False, indent=2)
        )
        return self._call_llm(prompt, "报告生成")


class TestCaseGeneratorChain(BaseChain):
    """测试用例生成Chain"""
    
    def generate_test_cases(
        self,
        api_info: dict[str, Any],
        sample_requests: list[dict[str, Any]],
        test_strategy: str = "comprehensive",
        api_doc_context: str = ""
    ) -> dict[str, Any]:
        """
        生成测试用例
        
        Args:
            api_info: API信息
            sample_requests: 示例请求
            test_strategy: 测试策略
            api_doc_context: 接口文档上下文（RAG）
        """
        if api_doc_context:
            prompt = TEST_CASE_GENERATION_WITH_RAG_PROMPT.format(
                api_doc_context=api_doc_context,
                api_info=json.dumps(api_info, ensure_ascii=False, indent=2),
                sample_requests=json.dumps(sample_requests[:10], ensure_ascii=False, indent=2),
                test_strategy=test_strategy
            )
        else:
            prompt = TEST_CASE_GENERATION_PROMPT.format(
                api_info=json.dumps(api_info, ensure_ascii=False, indent=2),
                sample_requests=json.dumps(sample_requests[:10], ensure_ascii=False, indent=2),
                test_strategy=test_strategy
            )
        
        response = self._call_llm(prompt, "测试用例生成")
        result = self._parse_json_response(response)
        
        # 记录生成结果
        tc_count = len(result.get("test_cases", []))
        if tc_count > 0:
            self.logger.debug(f"   生成了 {tc_count} 个测试用例")
        
        return result


class ResultValidatorChain(BaseChain):
    """结果验证Chain"""
    
    def validate_response(
        self,
        test_case: dict[str, Any],
        actual_response: dict[str, Any],
        expected_response: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """验证测试结果"""
        prompt = RESULT_VALIDATION_PROMPT.format(
            test_case=json.dumps(test_case, ensure_ascii=False, indent=2),
            actual_response=json.dumps(actual_response, ensure_ascii=False, indent=2),
            expected_response=json.dumps(expected_response or {}, ensure_ascii=False, indent=2)
        )
        response = self._call_llm(prompt, "结果验证")
        return self._parse_json_response(response)


class CurlGeneratorChain(BaseChain):
    """Curl命令生成Chain"""
    
    def generate_curl(
        self,
        request_info: dict[str, Any],
        base_url: str = "http://localhost:8080"
    ) -> str:
        """
        生成curl命令
        
        Args:
            request_info: 请求信息
            base_url: 基础URL
            
        Returns:
            curl命令字符串
        """
        method = request_info.get("method", "GET").upper()
        url = request_info.get("url", "")
        headers = request_info.get("headers", {})
        body = request_info.get("body")
        
        # 构建完整URL
        if not url.startswith("http"):
            full_url = f"{base_url.rstrip('/')}{url}"
        else:
            full_url = url
        
        # 构建curl命令
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
            escaped_body = body.replace("'", "'\\''")
            parts.append(f"-d '{escaped_body}'")
        
        return " ".join(parts)
