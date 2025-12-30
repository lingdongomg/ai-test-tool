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
    ANALYSIS_REPORT_PROMPT,
    TEST_CASE_GENERATION_PROMPT,
    RESULT_VALIDATION_PROMPT,
    LOG_DIAGNOSIS_PROMPT
)
from ..utils.logger import get_logger


class BaseChain:
    """Chain基类"""
    
    def __init__(self, provider: LLMProvider | None = None, verbose: bool = False) -> None:
        self.provider = provider or get_llm_provider()
        self.verbose = verbose
        self.logger = get_logger(verbose)
    
    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """解析JSON响应"""
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试找到JSON对象
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
        
        # 返回原始响应
        self.logger.warn("JSON解析失败，返回原始响应")
        return {"raw_response": response, "parse_error": True}
    
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
    
    def analyze_logs(self, log_content: str) -> dict[str, Any]:
        """
        智能分析日志内容
        
        Args:
            log_content: 日志内容（可以是多行）
            
        Returns:
            分析结果，包含requests、errors、warnings、analysis
        """
        prompt = LOG_ANALYSIS_PROMPT.format(log_content=log_content)
        response = self._call_llm(prompt, "日志分析")
        result = self._parse_json_response(response)
        
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
    
    def categorize_requests(self, requests: list[dict[str, Any]]) -> dict[str, Any]:
        """对请求进行智能分类"""
        requests_json = json.dumps(requests[:50], ensure_ascii=False, indent=2)
        prompt = LOG_CATEGORIZATION_PROMPT.format(requests_json=requests_json)
        response = self._call_llm(prompt, "请求分类")
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
        test_strategy: str = "comprehensive"
    ) -> dict[str, Any]:
        """生成测试用例"""
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
