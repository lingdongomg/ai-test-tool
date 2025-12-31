"""
AI Test Tool 核心模块
整合所有功能的主要入口
Python 3.13+ 兼容
"""

import os
import uuid
from typing import Any, Callable
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
from .utils.logger import AILogger, set_logger

# 数据库相关导入（必须依赖）
from .database import (
    get_db_manager,
    DatabaseManager,
    TaskRepository, RequestRepository, TestCaseRepository, 
    TestResultRepository, ReportRepository,
    AnalysisTask, TaskStatus, ParsedRequestRecord,
    TestCaseRecord, TestCaseCategory as DBTestCaseCategory, TestCasePriority as DBTestCasePriority,
    TestResultRecord, TestResultStatus as DBTestResultStatus,
    AnalysisReport, ReportType
)


class TaskCancelledException(Exception):
    """任务被取消异常"""
    pass


class AITestTool:
    """
    AI测试工具主类
    
    提供完整的日志分析和自动化测试功能：
    1. 智能日志解析
    2. 智能分析报告生成
    3. 智能测试用例生成
    4. 智能测试执行
    5. 智能结果验证
    6. MySQL数据持久化
    """
    
    def __init__(
        self,
        config: AppConfig | None = None,
        verbose: bool = False,
        log_dir: str | None = None,
        cancel_check_fn: Callable[[], bool] | None = None
    ) -> None:
        """
        初始化AI测试工具
        
        Args:
            config: 应用配置，如果为None则使用默认配置
            verbose: 是否显示详细的AI处理日志
            log_dir: 日志文件目录，默认为项目根目录下的 logs 目录
            cancel_check_fn: 取消检查函数，返回True表示任务已取消
        """
        self.config = config or get_config()
        set_config(self.config)
        
        self.verbose = verbose
        self._cancel_check_fn = cancel_check_fn
        
        # 初始化日志器
        self.logger = AILogger(verbose=verbose, name="ai_analysis", log_dir=log_dir)
        set_logger(self.logger)
        
        # 初始化各模块
        self._init_modules()
        
        # 初始化数据库（必须）
        self._init_database()
        
        # 存储处理结果
        self.parsed_requests: list[ParsedRequest] = []
        self.analysis_result: dict[str, Any] = {}
        self.test_cases: list[TestCase] = []
        self.test_results: list[TestResult] = []
        self.validation_summary: ValidationSummary | None = None
        
        # 任务相关
        self.task_id: str | None = None
        self.execution_id: str | None = None
    
    def _check_cancelled(self) -> None:
        """检查任务是否已取消，如果取消则抛出异常"""
        if self._cancel_check_fn and self._cancel_check_fn():
            self.logger.warn("任务已被取消")
            raise TaskCancelledException("任务已被用户取消")
    
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
    
    def _init_database(self) -> None:
        """初始化数据库连接"""
        try:
            self.db_manager: DatabaseManager = get_db_manager()
            # 尝试连接数据库
            self.db_manager.connect()
            
            # 初始化仓库
            self.task_repo = TaskRepository(self.db_manager)
            self.request_repo = RequestRepository(self.db_manager)
            self.test_case_repo = TestCaseRepository(self.db_manager)
            self.test_result_repo = TestResultRepository(self.db_manager)
            self.report_repo = ReportRepository(self.db_manager)
            
            self.logger.success("数据库连接成功")
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            raise RuntimeError(f"数据库连接失败，请检查MySQL配置: {e}")
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def _generate_execution_id(self) -> str:
        """生成执行批次ID"""
        return f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
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
        self._check_cancelled()  # 检查是否取消
        
        self.logger.section("AI测试工具 - 日志解析", "🚀")
        
        if not os.path.exists(log_file):
            raise FileNotFoundError(f"日志文件不存在: {log_file}")
        
        file_size = os.path.getsize(log_file)
        file_size_mb = file_size / (1024 * 1024)
        self.logger.info(f"日志文件: {log_file}")
        self.logger.info(f"文件大小: {file_size_mb:.2f} MB")
        
        # 计算总行数
        total_lines = sum(1 for _ in open(log_file, encoding='utf-8', errors='ignore'))
        if max_lines:
            total_lines = min(total_lines, max_lines)
        
        self.logger.info(f"预计处理: {total_lines:,} 行")
        
        # 生成任务ID并创建任务记录
        self.task_id = self._generate_task_id()
        task = AnalysisTask(
            task_id=self.task_id,
            name=f"分析任务 - {Path(log_file).name}",
            log_file_path=log_file,
            log_file_size=file_size,
            status=TaskStatus.RUNNING,
            total_lines=total_lines,
            started_at=datetime.now()
        )
        try:
            self.task_repo.create(task)
        except Exception as e:
            self.logger.warn(f"创建任务记录失败: {e}")
        
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
                self._check_cancelled()  # 每个chunk后检查是否取消
                self.parsed_requests.extend(requests)
                chunk_size = min(self.config.parser.chunk_size, total_lines - processed)
                pbar.update(chunk_size)
                processed += chunk_size
        
        self.logger.success("解析完成")
        self.logger.info(f"   提取请求数: {len(self.parsed_requests)}")
        
        # 更新任务进度
        try:
            self.task_repo.update_progress(
                self.task_id, 
                processed_lines=total_lines,
                total_requests=len(self.parsed_requests)
            )
        except Exception as e:
            self.logger.warn(f"更新任务进度失败: {e}")
        
        return self.parsed_requests
    
    def analyze_requests(self) -> dict[str, Any]:
        """
        分析请求
        
        Returns:
            分析结果
        """
        self._check_cancelled()  # 检查是否取消
        
        if not self.parsed_requests:
            raise ValueError("请先解析日志文件")
        
        self.logger.section("分析请求...", "🔍")
        
        self.logger.start_step("请求分析")
        self.analysis_result = self.analyzer.analyze_requests(self.parsed_requests)
        self.logger.end_step()
        
        self._check_cancelled()  # 检查是否取消
        
        stats = self.analysis_result.get("statistics", {})
        self.logger.info("分析完成:")
        self.logger.info(f"   总请求数: {stats.get('total_requests', 0)}")
        self.logger.info(f"   成功率: {stats.get('success_rate', 'N/A')}")
        self.logger.info(f"   错误数: {stats.get('error_count', 0)}")
        self.logger.info(f"   警告数: {stats.get('warning_count', 0)}")
        
        # 存储解析的请求到数据库
        if self.task_id:
            self._save_parsed_requests_to_db()
        
        return self.analysis_result
    
    def _save_parsed_requests_to_db(self) -> None:
        """保存解析的请求到数据库"""
        if not self.task_id:
            return
        
        try:
            records: list[ParsedRequestRecord] = []
            for i, req in enumerate(self.parsed_requests):
                record = ParsedRequestRecord(
                    task_id=self.task_id,
                    request_id=req.request_id or f"req_{i:06d}",
                    method=req.method,
                    url=req.url,
                    category=req.category or "",
                    headers=req.headers or {},
                    body=req.body,
                    query_params=req.query_params or {},
                    http_status=req.http_status or 0,
                    response_time_ms=req.response_time_ms or 0,
                    response_body=req.response_body,
                    has_error=req.has_error,
                    error_message=req.error_message or "",
                    has_warning=req.has_warning,
                    warning_message=req.warning_message or "",
                    curl_command=req.curl_command or "",
                    timestamp=req.timestamp or "",
                    raw_logs="\n".join(req.raw_logs) if req.raw_logs else ""
                )
                records.append(record)
            
            if records:
                self.request_repo.create_batch(records)
                self.logger.success(f"已保存 {len(records)} 条请求到数据库")
        except Exception as e:
            self.logger.warn(f"保存请求到数据库失败: {e}")
    
    def generate_report(self, output_format: str = "markdown") -> str:
        """
        生成分析报告（存储到数据库）
        
        Args:
            output_format: 输出格式 (markdown/html/json)
            
        Returns:
            报告内容
        """
        self._check_cancelled()  # 检查是否取消
        
        if not self.analysis_result:
            self.analyze_requests()
        
        self.logger.section("生成分析报告...", "📝")
        
        self.logger.start_step("报告生成")
        report = self.report_generator.generate_report(
            requests=self.parsed_requests,
            analysis_result=self.analysis_result,
            output_format=output_format
        )
        self.logger.end_step()
        
        # 存储到数据库
        if self.task_id:
            self._save_report_to_db(
                title="分析报告",
                content=report,
                report_type=ReportType.ANALYSIS,
                statistics=self.analysis_result.get("statistics", {}),
                issues=self.analysis_result.get("issues", {})
            )
        
        self.logger.success("分析报告已生成并存储到数据库")
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
        self._check_cancelled()  # 检查是否取消
        
        if not self.parsed_requests:
            raise ValueError("请先解析日志文件")
        
        self.logger.section("生成测试用例...", "🧪")
        self.logger.info(f"   测试策略: {test_strategy}")
        
        self.logger.start_step("测试用例生成")
        self.test_cases = self.test_generator.generate_from_requests(
            requests=self.parsed_requests,
            test_strategy=test_strategy
        )
        self.logger.end_step(f"生成 {len(self.test_cases)} 个用例")
        
        self._check_cancelled()  # 检查是否取消
        
        self.logger.success(f"生成完成: {len(self.test_cases)} 个测试用例")
        
        # 统计分类
        categories: dict[str, int] = {}
        for tc in self.test_cases:
            cat = tc.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        self.logger.info("   用例分类:")
        for cat, count in sorted(categories.items()):
            self.logger.info(f"     - {cat}: {count}")
        
        # 存储测试用例到数据库
        if self.task_id:
            self._save_test_cases_to_db()
            # 更新任务的测试用例数
            try:
                self.task_repo.update_counts(self.task_id, total_test_cases=len(self.test_cases))
            except Exception as e:
                self.logger.warn(f"更新任务计数失败: {e}")
        
        return self.test_cases
    
    def _save_test_cases_to_db(self) -> None:
        """保存测试用例到数据库"""
        if not self.task_id:
            return
        
        try:
            records: list[TestCaseRecord] = []
            for tc in self.test_cases:
                # 映射 category
                category_map = {
                    "normal": DBTestCaseCategory.NORMAL,
                    "boundary": DBTestCaseCategory.BOUNDARY,
                    "exception": DBTestCaseCategory.EXCEPTION,
                    "performance": DBTestCaseCategory.PERFORMANCE,
                    "security": DBTestCaseCategory.SECURITY,
                }
                db_category = category_map.get(tc.category.value, DBTestCaseCategory.NORMAL)
                
                # 映射 priority
                priority_map = {
                    "high": DBTestCasePriority.HIGH,
                    "medium": DBTestCasePriority.MEDIUM,
                    "low": DBTestCasePriority.LOW,
                }
                db_priority = priority_map.get(tc.priority.value, DBTestCasePriority.MEDIUM)
                
                record = TestCaseRecord(
                    task_id=self.task_id,
                    case_id=tc.id,
                    name=tc.name,
                    description=tc.description or "",
                    category=db_category,
                    priority=db_priority,
                    method=tc.method,
                    url=tc.url,
                    headers=tc.headers or {},
                    body=tc.body,
                    query_params=tc.query_params or {},
                    expected_status_code=tc.expected.status_code,
                    expected_response={},
                    max_response_time_ms=tc.expected.max_response_time_ms,
                    tags=tc.tags or [],
                    group_name="",
                    dependencies=tc.dependencies or [],
                    is_enabled=True
                )
                records.append(record)
            
            if records:
                self.test_case_repo.create_batch(records)
                self.logger.success(f"已保存 {len(records)} 个测试用例到数据库")
        except Exception as e:
            self.logger.warn(f"保存测试用例到数据库失败: {e}")
    
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
        
        self.logger.section("执行测试...", "🚀")
        
        if base_url:
            self.config.test.base_url = base_url
        
        self.logger.info(f"   目标URL: {self.config.test.base_url}")
        self.logger.info(f"   并发数: {concurrent}")
        self.logger.info(f"   用例数: {len(self.test_cases)}")
        
        # 生成执行批次ID
        self.execution_id = self._generate_execution_id()
        
        self.logger.start_step("测试执行")
        
        executor = TestExecutor(
            config=self.config.test,
            progress_callback=self._test_progress_callback
        )
        
        self.logger.info("执行进度:")
        self.test_results = executor.execute_sync(self.test_cases)
        
        self.logger.end_step()
        
        # 统计结果
        passed = sum(1 for r in self.test_results if r.status.value == "passed")
        failed = sum(1 for r in self.test_results if r.status.value == "failed")
        errors = sum(1 for r in self.test_results if r.status.value == "error")
        
        self.logger.success("测试完成:")
        self.logger.info(f"   通过: {passed}")
        self.logger.info(f"   失败: {failed}")
        self.logger.info(f"   错误: {errors}")
        
        # 存储测试结果到数据库
        if self.task_id:
            self._save_test_results_to_db()
        
        return self.test_results
    
    def _save_test_results_to_db(self) -> None:
        """保存测试结果到数据库"""
        if not self.task_id or not self.execution_id:
            return
        
        try:
            records: list[TestResultRecord] = []
            for result in self.test_results:
                # 映射状态
                status_map = {
                    "passed": DBTestResultStatus.PASSED,
                    "failed": DBTestResultStatus.FAILED,
                    "error": DBTestResultStatus.ERROR,
                    "skipped": DBTestResultStatus.SKIPPED,
                }
                db_status = status_map.get(result.status.value, DBTestResultStatus.ERROR)
                
                # 解析 started_at 字符串为 datetime
                executed_at = None
                if result.started_at:
                    try:
                        executed_at = datetime.fromisoformat(result.started_at)
                    except ValueError:
                        executed_at = datetime.now()
                
                record = TestResultRecord(
                    task_id=self.task_id,
                    case_id=result.test_case_id,
                    execution_id=self.execution_id,
                    status=db_status,
                    actual_status_code=result.actual_status_code or 0,
                    actual_response_time_ms=result.actual_response_time_ms or 0,
                    actual_response_body=result.actual_response_body or "",
                    actual_headers=result.actual_headers or {},
                    error_message=result.error_message or "",
                    validation_results=result.validation_results or [],
                    executed_at=executed_at
                )
                records.append(record)
            
            if records:
                self.test_result_repo.create_batch(records)
                self.logger.success(f"已保存 {len(records)} 条测试结果到数据库")
        except Exception as e:
            self.logger.warn(f"保存测试结果到数据库失败: {e}")
    
    def _test_progress_callback(self, current: int, total: int, result: TestResult) -> None:
        """测试进度回调"""
        self.logger.progress_item(current, total, result.status.value, result.test_case_name)
    
    def validate_results(self) -> ValidationSummary:
        """
        验证测试结果
        
        Returns:
            验证摘要
        """
        if not self.test_results:
            raise ValueError("请先执行测试")
        
        self.logger.section("验证测试结果...", "🔍")
        
        self.logger.start_step("结果验证")
        self.validation_summary = self.result_validator.validate_results(
            test_cases=self.test_cases,
            results=self.test_results
        )
        self.logger.end_step()
        
        self.logger.info("验证摘要:")
        self.logger.info(f"   通过率: {self.validation_summary.pass_rate}")
        self.logger.info(f"   平均响应时间: {self.validation_summary.avg_response_time_ms}ms")
        self.logger.info(f"   发现问题: {len(self.validation_summary.issues)}")
        
        if self.validation_summary.recommendations:
            self.logger.info("改进建议:")
            for i, rec in enumerate(self.validation_summary.recommendations, 1):
                self.logger.info(f"   {i}. {rec}")
        
        return self.validation_summary
    
    def export_all(self) -> dict[str, Any]:
        """
        导出所有结果到数据库
        
        Returns:
            导出结果摘要
        """
        self.logger.section("导出报告到数据库...", "💾")
        
        exported: dict[str, Any] = {
            "task_id": self.task_id,
            "reports_saved": []
        }
        
        # 导出验证报告（测试报告）
        if self.validation_summary:
            report_content = self.result_validator.generate_test_report(
                self.test_cases, self.test_results, self.validation_summary
            )
            
            # 存储到数据库
            if self.task_id:
                self._save_report_to_db(
                    title="测试报告",
                    content=report_content,
                    report_type=ReportType.TEST,
                    recommendations=self.validation_summary.recommendations
                )
                exported["reports_saved"].append("test_report")
        
        # 导出分析报告
        if self.analysis_result:
            report_content = self.report_generator.generate_report(
                requests=self.parsed_requests,
                analysis_result=self.analysis_result,
                output_format="markdown"
            )
            
            # 存储到数据库
            if self.task_id:
                self._save_report_to_db(
                    title="分析报告",
                    content=report_content,
                    report_type=ReportType.ANALYSIS,
                    statistics=self.analysis_result.get("statistics", {}),
                    issues=self.analysis_result.get("issues", {})
                )
                exported["reports_saved"].append("analysis_report")
        
        # 更新任务状态
        if self.task_id:
            try:
                self.task_repo.update_status(self.task_id, TaskStatus.COMPLETED)
            except Exception as e:
                self.logger.warn(f"更新任务状态失败: {e}")
        
        if exported["reports_saved"]:
            self.logger.success(f"已保存 {len(exported['reports_saved'])} 份报告到数据库")
            self.logger.info(f"   任务ID: {self.task_id}")
        else:
            self.logger.warn("无可导出的报告")
        
        return exported
    
    def _save_report_to_db(
        self,
        title: str,
        content: str,
        report_type: ReportType,
        statistics: dict[str, Any] | None = None,
        issues: dict[str, Any] | list[dict[str, Any]] | None = None,
        recommendations: list[str] | None = None
    ) -> None:
        """保存报告到数据库"""
        if not self.task_id:
            return
        
        try:
            # 处理 issues 格式
            issues_list: list[dict[str, Any]] = []
            if issues:
                if isinstance(issues, dict):
                    for _, value in issues.items():
                        if isinstance(value, list):
                            issues_list.extend(value)
                else:
                    issues_list = issues
            
            report = AnalysisReport(
                task_id=self.task_id,
                title=title,
                content=content,
                report_type=report_type,
                format="markdown",
                statistics=statistics or {},
                issues=issues_list,
                recommendations=recommendations or []
            )
            self.report_repo.create(report)
            self.logger.debug(f"已保存{title}到数据库")
        except Exception as e:
            self.logger.warn(f"保存{title}到数据库失败: {e}")
    
    def run_full_pipeline(
        self,
        log_file: str,
        max_lines: int | None = None,
        test_strategy: str = "comprehensive",
        run_tests: bool = False,
        base_url: str | None = None
    ) -> dict[str, Any]:
        """
        运行完整流程
        
        Args:
            log_file: 日志文件路径
            max_lines: 最大处理行数
            test_strategy: 测试策略
            run_tests: 是否执行测试
            base_url: 测试目标URL
            
        Returns:
            完整结果
        """
        self.logger.section("AI测试工具 - 完整流程", "🚀")
        self.logger.info(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"   AI模式: 启用")
        self.logger.info(f"   详细日志: {'启用' if self.verbose else '禁用'}")
        self.logger.info(f"   数据库存储: 启用")
        
        self.logger.start_session("完整流程")
        
        try:
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
            
            # 5. 导出结果到数据库
            exported = self.export_all()
            
            self.logger.end_session()
            
            self.logger.separator()
            self.logger.success("完整流程执行完成!")
            if self.task_id:
                self.logger.info(f"   任务ID: {self.task_id}")
            self.logger.separator()
            
            return {
                "task_id": self.task_id,
                "parsed_requests": len(self.parsed_requests),
                "analysis": self.analysis_result.get("statistics", {}),
                "test_cases": len(self.test_cases),
                "test_results": len(self.test_results) if self.test_results else 0,
                "validation": self.validation_summary.to_dict() if self.validation_summary else None,
                "reports_saved": exported.get("reports_saved", [])
            }
        except Exception as e:
            # 更新任务状态为失败
            if self.task_id:
                try:
                    self.task_repo.update_status(self.task_id, TaskStatus.FAILED, str(e))
                except Exception:
                    pass
            raise
    
    def close(self) -> None:
        """关闭资源（数据库连接、日志文件等）"""
        if hasattr(self, 'db_manager'):
            try:
                self.db_manager.close()
            except Exception:
                pass
        
        if hasattr(self, 'logger'):
            try:
                self.logger.close()
            except Exception:
                pass
