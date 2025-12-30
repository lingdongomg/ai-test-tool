"""
智能结果验证器
使用LLM进行智能结果验证
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from .test_case_generator import TestCase
from .test_executor import TestResult, TestStatus
from ..llm.chains import ResultValidatorChain
from ..utils.logger import get_logger


@dataclass
class ValidationSummary:
    """验证摘要"""
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    skipped_cases: int
    pass_rate: str
    avg_response_time_ms: float
    issues: list[dict[str, Any]]
    recommendations: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResultValidator:
    """智能结果验证器"""
    
    def __init__(
        self,
        llm_chain: ResultValidatorChain | None = None,
        verbose: bool = False
    ) -> None:
        self.llm_chain = llm_chain
        self.verbose = verbose
        self.logger = get_logger(verbose)
    
    def validate_results(
        self,
        test_cases: list[TestCase],
        results: list[TestResult]
    ) -> ValidationSummary:
        """验证测试结果"""
        self.logger.start_step("结果验证")
        
        result_map = {r.test_case_id: r for r in results}
        
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        total = len(results)
        
        pass_rate = f"{passed/total*100:.2f}%" if total > 0 else "0%"
        
        response_times = [r.actual_response_time_ms for r in results if r.actual_response_time_ms > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        issues = self._collect_issues(test_cases, results, result_map)
        recommendations = self._generate_recommendations(results, issues)
        
        if self.llm_chain and failed > 0:
            llm_insights = self._llm_analyze_failures(test_cases, results, result_map)
            recommendations.extend(llm_insights.get("recommendations", []))
        
        self.logger.end_step(f"通过率 {pass_rate}")
        
        return ValidationSummary(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            error_cases=errors,
            skipped_cases=skipped,
            pass_rate=pass_rate,
            avg_response_time_ms=round(avg_response_time, 2),
            issues=issues,
            recommendations=recommendations
        )
    
    def _collect_issues(
        self,
        test_cases: list[TestCase],
        results: list[TestResult],
        result_map: dict[str, TestResult]
    ) -> list[dict[str, Any]]:
        """收集问题"""
        issues: list[dict[str, Any]] = []
        
        for tc in test_cases:
            result = result_map.get(tc.id)
            if not result:
                continue
            
            if result.status == TestStatus.FAILED:
                failed_validations = [
                    v for v in result.validation_results
                    if not v.get("passed", True)
                ]
                
                issues.append({
                    "type": "test_failed",
                    "test_case_id": tc.id,
                    "test_case_name": tc.name,
                    "url": tc.url,
                    "method": tc.method,
                    "expected_status": tc.expected.status_code,
                    "actual_status": result.actual_status_code,
                    "failed_validations": failed_validations,
                    "severity": "high" if tc.priority.value == "high" else "medium"
                })
            
            elif result.status == TestStatus.ERROR:
                issues.append({
                    "type": "execution_error",
                    "test_case_id": tc.id,
                    "test_case_name": tc.name,
                    "url": tc.url,
                    "error_message": result.error_message,
                    "severity": "high"
                })
            
            if result.actual_response_time_ms > tc.expected.max_response_time_ms:
                issues.append({
                    "type": "performance",
                    "test_case_id": tc.id,
                    "test_case_name": tc.name,
                    "url": tc.url,
                    "expected_time": tc.expected.max_response_time_ms,
                    "actual_time": result.actual_response_time_ms,
                    "severity": "low"
                })
        
        return issues
    
    def _generate_recommendations(
        self,
        results: list[TestResult],
        issues: list[dict[str, Any]]
    ) -> list[str]:
        """生成建议"""
        recommendations: list[str] = []
        
        issue_types: dict[str, int] = {}
        for issue in issues:
            issue_type = issue.get("type")
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
        
        if issue_types.get("test_failed", 0) > 0:
            count = issue_types["test_failed"]
            recommendations.append(f"有{count}个测试用例失败，建议检查接口实现是否符合预期")
        
        if issue_types.get("execution_error", 0) > 0:
            count = issue_types["execution_error"]
            recommendations.append(f"有{count}个测试执行错误，建议检查测试环境和网络连接")
        
        if issue_types.get("performance", 0) > 0:
            count = issue_types["performance"]
            recommendations.append(f"有{count}个接口响应时间超标，建议进行性能优化")
        
        status_codes: dict[int, int] = {}
        for result in results:
            code = result.actual_status_code
            if code not in status_codes:
                status_codes[code] = 0
            status_codes[code] += 1
        
        if status_codes.get(401, 0) > 0 or status_codes.get(403, 0) > 0:
            recommendations.append("存在认证/授权失败，建议检查Token配置")
        
        if status_codes.get(500, 0) > 0 or status_codes.get(502, 0) > 0:
            recommendations.append("存在服务端错误，建议检查服务端日志")
        
        if status_codes.get(404, 0) > 0:
            recommendations.append("存在404错误，建议检查接口路径是否正确")
        
        if not recommendations:
            recommendations.append("所有测试通过，建议继续保持")
        
        return recommendations
    
    def _llm_analyze_failures(
        self,
        test_cases: list[TestCase],
        results: list[TestResult],
        result_map: dict[str, TestResult]
    ) -> dict[str, Any]:
        """使用LLM分析失败用例"""
        failed_cases: list[dict[str, Any]] = []
        
        for tc in test_cases:
            result = result_map.get(tc.id)
            if result and result.status == TestStatus.FAILED:
                failed_cases.append({
                    "test_case": tc.to_dict(),
                    "actual_response": {
                        "status_code": result.actual_status_code,
                        "response_time_ms": result.actual_response_time_ms,
                        "body": result.actual_response_body[:1000] if result.actual_response_body else None
                    },
                    "expected_response": {
                        "status_code": tc.expected.status_code
                    }
                })
        
        if not failed_cases or len(failed_cases) > 10:
            return {"recommendations": []}
        
        try:
            self.logger.ai_start("失败用例分析", f"{len(failed_cases)}个失败用例")
            
            validations = self.llm_chain.batch_validate(failed_cases)
            
            recommendations: list[str] = []
            for v in validations:
                validation = v.get("validation", {})
                suggestions = validation.get("suggestions", [])
                recommendations.extend(suggestions)
            
            recommendations = list(set(recommendations))
            
            self.logger.ai_end()
            return {"recommendations": recommendations[:5]}
        
        except Exception as e:
            self.logger.error(f"LLM分析失败: {e}")
            return {"recommendations": []}
    
    def generate_test_report(
        self,
        test_cases: list[TestCase],
        results: list[TestResult],
        summary: ValidationSummary
    ) -> str:
        """生成测试报告"""
        lines: list[str] = []
        lines.append("# 测试执行报告\n")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        lines.append("## 1. 执行摘要\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总用例数 | {summary.total_cases} |")
        lines.append(f"| 通过 | {summary.passed_cases} |")
        lines.append(f"| 失败 | {summary.failed_cases} |")
        lines.append(f"| 错误 | {summary.error_cases} |")
        lines.append(f"| 跳过 | {summary.skipped_cases} |")
        lines.append(f"| 通过率 | {summary.pass_rate} |")
        lines.append(f"| 平均响应时间 | {summary.avg_response_time_ms}ms |")
        lines.append("")
        
        lines.append("## 2. 详细结果\n")
        
        result_map = {r.test_case_id: r for r in results}
        
        lines.append("| 用例ID | 名称 | 状态 | 响应时间 | 状态码 |")
        lines.append("|--------|------|------|----------|--------|")
        
        for tc in test_cases:
            result = result_map.get(tc.id)
            if result:
                status_emoji = {
                    TestStatus.PASSED: "✅",
                    TestStatus.FAILED: "❌",
                    TestStatus.ERROR: "⚠️",
                    TestStatus.SKIPPED: "⏭️"
                }.get(result.status, "❓")
                
                lines.append(
                    f"| {tc.id} | {tc.name[:30]} | {status_emoji} {result.status.value} | "
                    f"{result.actual_response_time_ms:.0f}ms | {result.actual_status_code} |"
                )
        lines.append("")
        
        if summary.issues:
            lines.append("## 3. 问题列表\n")
            for i, issue in enumerate(summary.issues[:20], 1):
                lines.append(f"### 3.{i} {issue.get('test_case_name', 'Unknown')}")
                lines.append(f"- **类型**: {issue.get('type')}")
                lines.append(f"- **严重程度**: {issue.get('severity')}")
                lines.append(f"- **URL**: {issue.get('url')}")
                if issue.get('error_message'):
                    lines.append(f"- **错误**: {issue.get('error_message')}")
                lines.append("")
        
        lines.append("## 4. 改进建议\n")
        for i, rec in enumerate(summary.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        return "\n".join(lines)
