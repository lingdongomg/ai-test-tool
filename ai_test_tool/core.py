"""
AI Test Tool 核心模块
整合所有功能的主要入口
Python 3.13+ 兼容
"""

import os
from typing import Any
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

from .config import AppConfig, get_config, set_config
from .parser.log_parser import LogParser, ParsedRequest
from .analyzer.request_analyzer import RequestAnalyzer
from .analyzer.report_generator import ReportGenerator
from .testing.test_case_generator import TestCaseGenerator, TestCase
from .testing.test_executor import TestExecutor, TestResult
from .testing.result_validator import ResultValidator, ValidationSummary
from .llm.chains import LogAnalysisChain, ReportGeneratorChain, TestCaseGeneratorChain, ResultValidatorChain
from .utils.logger import AILogger, get_logger, set_logger


class AITestTool:
    """
    AI测试工具主类
    
    提供完整的日志分析和自动化测试功能：
    1. 智能日志解析
    2. 智能分析报告生成
    3. 智能测试用例生成
    4. 智能测试执行
    5. 智能结果验证
    """
    
    def __init__(
        self,
        config: AppConfig | None = None,
        verbose: bool = False
    ) -> None:
        """
        初始化AI测试工具
        
        Args:
            config: 应用配置，如果为None则使用默认配置
            verbose: 是否显示详细的AI处理日志
        """
        self.config = config or get_config()
        set_config(self.config)
        
        self.verbose = verbose
        
        # 初始化日志器
        self.logger = AILogger(verbose=verbose, name="AITestTool")
        set_logger(self.logger)
        
        # 初始化各模块
        self._init_modules()
        
        # 存储处理结果
        self.parsed_requests: list[ParsedRequest] = []
        self.analysis_result: dict[str, Any] = {}
        self.test_cases: list[TestCase] = []
        self.test_results: list[TestResult] = []
        self.validation_summary: ValidationSummary | None = None
    
    def _init_modules(self) -> None:
        """初始化各功能模块"""
        # LLM Chains（带日志监控）
        self.log_chain = LogAnalysisChain(verbose=self.verbose)
        self.report_chain = ReportGeneratorChain(verbose=self.verbose)
        self.test_gen_chain = TestCaseGeneratorChain(verbose=self.verbose)
        self.validator_chain = ResultValidatorChain(verbose=self.verbose)
        
        # 功能模块
        self.parser = LogParser(llm_chain=self.log_chain, verbose=self.verbose)
        self.analyzer = RequestAnalyzer(llm_chain=self.log_chain, verbose=self.verbose)
        self.report_generator = ReportGenerator(llm_chain=self.report_chain, verbose=self.verbose)
        self.test_generator = TestCaseGenerator(llm_chain=self.test_gen_chain, verbose=self.verbose)
        self.result_validator = ResultValidator(llm_chain=self.validator_chain, verbose=self.verbose)
    
    def parse_log_file(
        self,
        log_file: str,
        max_lines: int | None = None
    ) -> list[ParsedRequest]:
        """
        解析日志文件
        
        Args:
            log_file: 日志文件路径
            max_lines: 最大处理行数
            
        Returns:
            解析后的请求列表
        """
        print(f"\n{'='*60}")
        print("🚀 AI测试工具 - 日志解析")
        print(f"{'='*60}")
        
        if not os.path.exists(log_file):
            raise FileNotFoundError(f"日志文件不存在: {log_file}")
        
        file_size = os.path.getsize(log_file) / (1024 * 1024)
        print(f"📂 日志文件: {log_file}")
        print(f"📊 文件大小: {file_size:.2f} MB")
        
        # 计算总行数
        total_lines = sum(1 for _ in open(log_file, encoding='utf-8', errors='ignore'))
        if max_lines:
            total_lines = min(total_lines, max_lines)
        
        print(f"📊 预计处理: {total_lines:,} 行")
        
        self.logger.start_session(f"解析 {log_file}")
        
        # 解析日志
        self.parsed_requests = []
        
        with tqdm(total=total_lines, desc="解析进度", unit="行") as pbar:
            processed = 0
            for requests in self.parser.parse_file(
                log_file,
                chunk_size=self.config.parser.chunk_size,
                max_lines=max_lines
            ):
                self.parsed_requests.extend(requests)
                chunk_size = min(self.config.parser.chunk_size, total_lines - processed)
                pbar.update(chunk_size)
                processed += chunk_size
        
        print(f"\n✅ 解析完成")
        print(f"   提取请求数: {len(self.parsed_requests)}")
        
        return self.parsed_requests
    
    def analyze_requests(self) -> dict[str, Any]:
        """
        分析请求
        
        Returns:
            分析结果
        """
        if not self.parsed_requests:
            raise ValueError("请先解析日志文件")
        
        print(f"\n{'='*60}")
        print("🔍 分析请求...")
        print(f"{'='*60}")
        
        self.logger.start_step("请求分析")
        self.analysis_result = self.analyzer.analyze_requests(self.parsed_requests)
        self.logger.end_step()
        
        stats = self.analysis_result.get("statistics", {})
        print(f"\n📊 分析完成:")
        print(f"   总请求数: {stats.get('total_requests', 0)}")
        print(f"   成功率: {stats.get('success_rate', 'N/A')}")
        print(f"   错误数: {stats.get('error_count', 0)}")
        print(f"   警告数: {stats.get('warning_count', 0)}")
        
        return self.analysis_result
    
    def generate_report(
        self,
        output_format: str = "markdown",
        output_path: str | None = None
    ) -> str:
        """
        生成分析报告
        
        Args:
            output_format: 输出格式 (markdown/html/json)
            output_path: 输出路径
            
        Returns:
            报告内容或文件路径
        """
        if not self.analysis_result:
            self.analyze_requests()
        
        print(f"\n{'='*60}")
        print("📝 生成分析报告...")
        print(f"{'='*60}")
        
        self.logger.start_step("报告生成")
        report = self.report_generator.generate_report(
            requests=self.parsed_requests,
            analysis_result=self.analysis_result,
            output_format=output_format
        )
        self.logger.end_step()
        
        if output_path:
            saved_path = self.report_generator.save_report(
                report, output_path, output_format
            )
            print(f"✅ 报告已保存: {saved_path}")
            return saved_path
        
        return report
    
    def generate_test_cases(
        self,
        test_strategy: str = "comprehensive"
    ) -> list[TestCase]:
        """
        生成测试用例
        
        Args:
            test_strategy: 测试策略 (comprehensive/quick/security)
            
        Returns:
            测试用例列表
        """
        if not self.parsed_requests:
            raise ValueError("请先解析日志文件")
        
        print(f"\n{'='*60}")
        print("🧪 生成测试用例...")
        print(f"{'='*60}")
        print(f"   测试策略: {test_strategy}")
        
        self.logger.start_step("测试用例生成")
        self.test_cases = self.test_generator.generate_from_requests(
            requests=self.parsed_requests,
            test_strategy=test_strategy
        )
        self.logger.end_step(f"生成 {len(self.test_cases)} 个用例")
        
        print(f"\n✅ 生成完成: {len(self.test_cases)} 个测试用例")
        
        # 统计分类
        categories: dict[str, int] = {}
        for tc in self.test_cases:
            cat = tc.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        print("   用例分类:")
        for cat, count in sorted(categories.items()):
            print(f"     - {cat}: {count}")
        
        return self.test_cases
    
    def run_tests(
        self,
        base_url: str | None = None,
        concurrent: int = 5
    ) -> list[TestResult]:
        """
        执行测试
        
        Args:
            base_url: 测试目标URL
            concurrent: 并发数
            
        Returns:
            测试结果列表
        """
        if not self.test_cases:
            raise ValueError("请先生成测试用例")
        
        print(f"\n{'='*60}")
        print("🚀 执行测试...")
        print(f"{'='*60}")
        
        if base_url:
            self.config.test.base_url = base_url
        
        print(f"   目标URL: {self.config.test.base_url}")
        print(f"   并发数: {concurrent}")
        print(f"   用例数: {len(self.test_cases)}")
        
        self.logger.start_step("测试执行")
        
        executor = TestExecutor(
            config=self.config.test,
            progress_callback=self._test_progress_callback
        )
        
        print("\n执行进度:")
        self.test_results = executor.execute_sync(self.test_cases)
        
        self.logger.end_step()
        
        # 统计结果
        passed = sum(1 for r in self.test_results if r.status.value == "passed")
        failed = sum(1 for r in self.test_results if r.status.value == "failed")
        errors = sum(1 for r in self.test_results if r.status.value == "error")
        
        print(f"\n✅ 测试完成:")
        print(f"   通过: {passed}")
        print(f"   失败: {failed}")
        print(f"   错误: {errors}")
        
        return self.test_results
    
    def _test_progress_callback(self, current: int, total: int, result: TestResult) -> None:
        """测试进度回调"""
        status_emoji = {
            "passed": "✅",
            "failed": "❌",
            "error": "⚠️"
        }.get(result.status.value, "❓")
        
        print(f"   [{current}/{total}] {status_emoji} {result.test_case_name[:40]}")
    
    def validate_results(self) -> ValidationSummary:
        """
        验证测试结果
        
        Returns:
            验证摘要
        """
        if not self.test_results:
            raise ValueError("请先执行测试")
        
        print(f"\n{'='*60}")
        print("🔍 验证测试结果...")
        print(f"{'='*60}")
        
        self.logger.start_step("结果验证")
        self.validation_summary = self.result_validator.validate_results(
            test_cases=self.test_cases,
            results=self.test_results
        )
        self.logger.end_step()
        
        print(f"\n📊 验证摘要:")
        print(f"   通过率: {self.validation_summary.pass_rate}")
        print(f"   平均响应时间: {self.validation_summary.avg_response_time_ms}ms")
        print(f"   发现问题: {len(self.validation_summary.issues)}")
        
        if self.validation_summary.recommendations:
            print("\n💡 改进建议:")
            for i, rec in enumerate(self.validation_summary.recommendations, 1):
                print(f"   {i}. {rec}")
        
        return self.validation_summary
    
    def export_all(self, output_dir: str | None = None) -> dict[str, str]:
        """
        导出所有结果（报告文件）
        
        注意：请求数据、测试用例、测试结果已存储到MySQL数据库，
        此方法仅导出报告文件。
        
        Args:
            output_dir: 输出目录
            
        Returns:
            导出的文件路径字典
        """
        output_path = Path(output_dir or self.config.output.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*60}")
        print("💾 导出报告...")
        print(f"{'='*60}")
        
        exported: dict[str, str] = {}
        
        # 导出验证报告
        if self.validation_summary:
            report = self.result_validator.generate_test_report(
                self.test_cases, self.test_results, self.validation_summary
            )
            report_path = str(output_path / "test_report.md")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            exported["test_report"] = report_path
            print(f"   ✅ 测试报告: {report_path}")
        
        # 导出分析报告
        if self.analysis_result:
            report_path = str(output_path / "analysis_report.md")
            self.generate_report(output_format="markdown", output_path=report_path)
            exported["analysis_report"] = report_path
        
        print(f"\n   📝 数据已存储到MySQL数据库")
        
        return exported
    
    def run_full_pipeline(
        self,
        log_file: str,
        max_lines: int | None = None,
        test_strategy: str = "comprehensive",
        run_tests: bool = False,
        base_url: str | None = None,
        output_dir: str | None = None
    ) -> dict[str, Any]:
        """
        运行完整流程
        
        Args:
            log_file: 日志文件路径
            max_lines: 最大处理行数
            test_strategy: 测试策略
            run_tests: 是否执行测试
            base_url: 测试目标URL
            output_dir: 输出目录
            
        Returns:
            完整结果
        """
        print(f"\n{'='*60}")
        print("🚀 AI测试工具 - 完整流程")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   AI模式: 启用")
        print(f"   详细日志: {'启用' if self.verbose else '禁用'}")
        print(f"{'='*60}")
        
        self.logger.start_session("完整流程")
        
        # 1. 解析日志
        self.parse_log_file(log_file, max_lines)
        
        # 2. 分析请求
        self.analyze_requests()
        
        # 3. 生成测试用例
        self.generate_test_cases(test_strategy)
        
        # 4. 执行测试（可选）
        if run_tests:
            self.run_tests(base_url)
            self.validate_results()
        
        # 5. 导出结果
        exported = self.export_all(output_dir)
        
        self.logger.end_session()
        
        print(f"\n{'='*60}")
        print("✅ 完整流程执行完成!")
        print(f"{'='*60}\n")
        
        return {
            "parsed_requests": len(self.parsed_requests),
            "analysis": self.analysis_result.get("statistics", {}),
            "test_cases": len(self.test_cases),
            "test_results": len(self.test_results) if self.test_results else 0,
            "validation": self.validation_summary.to_dict() if self.validation_summary else None,
            "exported_files": exported
        }
