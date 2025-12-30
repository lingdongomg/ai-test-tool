"""
智能报告生成器
基于LLM生成专业的分析报告
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..parser.log_parser import ParsedRequest
from ..llm.chains import ReportGeneratorChain
from ..utils.logger import get_logger


class ReportGenerator:
    """智能报告生成器"""
    
    def __init__(
        self,
        llm_chain: ReportGeneratorChain | None = None,
        verbose: bool = False
    ) -> None:
        self.llm_chain = llm_chain
        self.verbose = verbose
        self.logger = get_logger(verbose)
    
    def generate_report(
        self,
        requests: list[ParsedRequest],
        analysis_result: dict[str, Any],
        output_format: str = "markdown"
    ) -> str:
        """生成分析报告"""
        self.logger.start_step("报告生成")
        
        if self.llm_chain:
            report = self._generate_llm_report(requests, analysis_result, output_format)
        else:
            report = self._generate_rule_based_report(requests, analysis_result, output_format)
        
        self.logger.end_step()
        return report
    
    def _generate_llm_report(
        self,
        requests: list[ParsedRequest],
        analysis_result: dict[str, Any],
        output_format: str
    ) -> str:
        """使用LLM生成报告"""
        summary_data = analysis_result.get("statistics", {})
        
        error_logs = [
            {"url": r.url, "method": r.method, "error": r.error_message}
            for r in requests if r.has_error
        ][:20]
        
        warning_logs = [
            {"url": r.url, "method": r.method, "warning": r.warning_message}
            for r in requests if r.has_warning
        ][:20]
        
        performance_data = analysis_result.get("performance", {})
        
        try:
            report = self.llm_chain.generate_report(
                summary_data=summary_data,
                error_logs=error_logs,
                warning_logs=warning_logs,
                performance_data=performance_data
            )
            
            if output_format == "html":
                return self._markdown_to_html(report)
            elif output_format == "json":
                return json.dumps({
                    "report": report,
                    "generated_at": datetime.now().isoformat(),
                    "summary": summary_data
                }, ensure_ascii=False, indent=2)
            
            return report
            
        except Exception as e:
            self.logger.error(f"LLM报告生成失败: {e}")
            self.logger.info("使用规则生成报告")
            return self._generate_rule_based_report(requests, analysis_result, output_format)
    
    def _generate_rule_based_report(
        self,
        requests: list[ParsedRequest],
        analysis_result: dict[str, Any],
        output_format: str
    ) -> str:
        """基于规则生成报告"""
        stats = analysis_result.get("statistics", {})
        issues = analysis_result.get("issues", {})
        performance = analysis_result.get("performance", {})
        
        report_lines: list[str] = []
        
        # 标题
        report_lines.append("# API日志分析报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 执行摘要
        report_lines.append("## 1. 执行摘要\n")
        report_lines.append(f"本次分析共处理 **{stats.get('total_requests', 0)}** 个API请求。")
        report_lines.append(f"成功率: **{stats.get('success_rate', 'N/A')}**")
        report_lines.append(f"发现 **{stats.get('error_count', 0)}** 个错误和 **{stats.get('warning_count', 0)}** 个警告。\n")
        
        # 请求统计
        report_lines.append("## 2. 请求统计\n")
        report_lines.append("### 2.1 总体统计\n")
        report_lines.append("| 指标 | 数值 |")
        report_lines.append("|------|------|")
        report_lines.append(f"| 总请求数 | {stats.get('total_requests', 0)} |")
        report_lines.append(f"| 成功请求 | {stats.get('success_count', 0)} |")
        report_lines.append(f"| 客户端错误(4xx) | {stats.get('client_error_count', 0)} |")
        report_lines.append(f"| 服务端错误(5xx) | {stats.get('server_error_count', 0)} |")
        report_lines.append(f"| 错误日志数 | {stats.get('error_count', 0)} |")
        report_lines.append(f"| 警告日志数 | {stats.get('warning_count', 0)} |")
        report_lines.append("")
        
        # 方法分布
        report_lines.append("### 2.2 请求方法分布\n")
        method_dist = stats.get('method_distribution', {})
        if method_dist:
            report_lines.append("| 方法 | 数量 |")
            report_lines.append("|------|------|")
            for method, count in sorted(method_dist.items()):
                report_lines.append(f"| {method} | {count} |")
            report_lines.append("")
        
        # 分类分布
        report_lines.append("### 2.3 接口分类分布\n")
        category_dist = stats.get('category_distribution', {})
        if category_dist:
            report_lines.append("| 分类 | 数量 |")
            report_lines.append("|------|------|")
            for category, count in sorted(category_dist.items(), key=lambda x: -x[1]):
                report_lines.append(f"| {category} | {count} |")
            report_lines.append("")
        
        # 问题分析
        report_lines.append("## 3. 问题分析\n")
        
        # 错误
        errors = issues.get('errors', [])
        report_lines.append(f"### 3.1 错误日志 ({len(errors)}个)\n")
        if errors:
            report_lines.append("| URL | 方法 | 错误信息 |")
            report_lines.append("|-----|------|----------|")
            for err in errors[:10]:
                msg = err.get('message', '')[:50] + '...' if len(err.get('message', '')) > 50 else err.get('message', '')
                report_lines.append(f"| {err.get('url', '')} | {err.get('method', '')} | {msg} |")
            if len(errors) > 10:
                report_lines.append(f"\n*...还有 {len(errors) - 10} 个错误*\n")
        else:
            report_lines.append("未发现错误日志。\n")
        
        # 警告
        warnings = issues.get('warnings', [])
        report_lines.append(f"### 3.2 警告日志 ({len(warnings)}个)\n")
        if warnings:
            report_lines.append("| URL | 方法 | 警告信息 |")
            report_lines.append("|-----|------|----------|")
            for warn in warnings[:10]:
                msg = warn.get('message', '')[:50] + '...' if len(warn.get('message', '')) > 50 else warn.get('message', '')
                report_lines.append(f"| {warn.get('url', '')} | {warn.get('method', '')} | {msg} |")
            if len(warnings) > 10:
                report_lines.append(f"\n*...还有 {len(warnings) - 10} 个警告*\n")
        else:
            report_lines.append("未发现警告日志。\n")
        
        # 失败请求
        failed = issues.get('failed_requests', [])
        report_lines.append(f"### 3.3 失败请求 ({len(failed)}个)\n")
        if failed:
            report_lines.append("| URL | 方法 | 状态码 |")
            report_lines.append("|-----|------|--------|")
            for req in failed[:10]:
                report_lines.append(f"| {req.get('url', '')} | {req.get('method', '')} | {req.get('http_status', '')} |")
        else:
            report_lines.append("未发现失败请求。\n")
        
        # 性能分析
        report_lines.append("## 4. 性能分析\n")
        if performance.get('no_data'):
            report_lines.append("无性能数据。\n")
        else:
            report_lines.append("| 指标 | 数值 |")
            report_lines.append("|------|------|")
            report_lines.append(f"| 平均响应时间 | {performance.get('avg_response_time_ms', 'N/A')} ms |")
            report_lines.append(f"| 最小响应时间 | {performance.get('min_response_time_ms', 'N/A')} ms |")
            report_lines.append(f"| 最大响应时间 | {performance.get('max_response_time_ms', 'N/A')} ms |")
            report_lines.append(f"| P50响应时间 | {performance.get('p50_response_time_ms', 'N/A')} ms |")
            report_lines.append(f"| P90响应时间 | {performance.get('p90_response_time_ms', 'N/A')} ms |")
            if performance.get('p99_response_time_ms'):
                report_lines.append(f"| P99响应时间 | {performance.get('p99_response_time_ms')} ms |")
            report_lines.append(f"| 慢请求数(>1s) | {performance.get('slow_request_count', 0)} |")
            report_lines.append(f"| 超慢请求数(>3s) | {performance.get('very_slow_request_count', 0)} |")
            report_lines.append("")
            
            # 慢请求列表
            slow_requests = issues.get('slow_requests', [])
            if slow_requests:
                report_lines.append("### 4.1 慢请求列表\n")
                report_lines.append("| URL | 方法 | 响应时间(ms) |")
                report_lines.append("|-----|------|--------------|")
                for req in sorted(slow_requests, key=lambda x: -x.get('response_time_ms', 0))[:10]:
                    report_lines.append(f"| {req.get('url', '')} | {req.get('method', '')} | {req.get('response_time_ms', '')} |")
                report_lines.append("")
        
        # 改进建议
        report_lines.append("## 5. 改进建议\n")
        suggestions = self._generate_suggestions(stats, issues, performance)
        for i, suggestion in enumerate(suggestions, 1):
            report_lines.append(f"{i}. {suggestion}")
        report_lines.append("")
        
        report = "\n".join(report_lines)
        
        if output_format == "html":
            return self._markdown_to_html(report)
        elif output_format == "json":
            return json.dumps({
                "report": report,
                "generated_at": datetime.now().isoformat(),
                "summary": stats
            }, ensure_ascii=False, indent=2)
        
        return report
    
    def _generate_suggestions(
        self,
        stats: dict[str, Any],
        issues: dict[str, Any],
        performance: dict[str, Any]
    ) -> list[str]:
        """生成改进建议"""
        suggestions: list[str] = []
        
        # 基于错误率
        total = stats.get('total_requests', 0)
        success = stats.get('success_count', 0)
        if total > 0:
            success_rate = success / total
            if success_rate < 0.95:
                suggestions.append(f"成功率({success_rate*100:.1f}%)低于95%，建议排查失败原因")
        
        # 基于错误数
        error_count = stats.get('error_count', 0)
        if error_count > 0:
            suggestions.append(f"发现{error_count}个错误日志，建议优先处理")
        
        # 基于性能
        if not performance.get('no_data'):
            avg_time = performance.get('avg_response_time_ms', 0)
            if avg_time > 500:
                suggestions.append(f"平均响应时间({avg_time}ms)较高，建议进行性能优化")
            
            slow_count = performance.get('slow_request_count', 0)
            if slow_count > 0:
                suggestions.append(f"发现{slow_count}个慢请求(>1s)，建议分析慢查询原因")
        
        # 基于失败请求
        failed = issues.get('failed_requests', [])
        if failed:
            status_codes = {r.get('http_status') for r in failed}
            if 500 in status_codes or any(s >= 500 for s in status_codes if s):
                suggestions.append("存在5xx服务端错误，建议检查服务端日志")
            if 401 in status_codes or 403 in status_codes:
                suggestions.append("存在认证/授权错误，建议检查Token和权限配置")
        
        if not suggestions:
            suggestions.append("整体表现良好，建议持续监控")
        
        return suggestions
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """将Markdown转换为HTML"""
        try:
            import markdown
            html = markdown.markdown(
                markdown_content,
                extensions=['tables', 'fenced_code']
            )
            return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>API日志分析报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1200px; margin: 0 auto; padding: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        h3 {{ color: #888; }}
        code {{ background-color: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
        except ImportError:
            return f"<pre>{markdown_content}</pre>"
    
    def save_report(
        self,
        report: str,
        output_path: str,
        output_format: str = "markdown"
    ) -> str:
        """保存报告到文件"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        ext_map = {
            "markdown": ".md",
            "html": ".html",
            "json": ".json"
        }
        
        if not path.suffix:
            path = path.with_suffix(ext_map.get(output_format, ".md"))
        
        path.write_text(report, encoding='utf-8')
        
        return str(path)
