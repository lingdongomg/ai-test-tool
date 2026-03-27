"""
功能3: 日志异常检测与告警服务
解析日志中的 warning/error 信息，检测异常，生成告警报告
"""

import json
import re
import hashlib
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

from ..database import get_db_manager
from ..llm.chains import LogAnalysisChain, ReportGeneratorChain
from ..llm.provider import get_llm_provider
from ..utils.logger import get_logger


class AnomalySeverity(Enum):
    """异常严重程度"""
    CRITICAL = "critical"    # 严重
    ERROR = "error"          # 错误
    WARNING = "warning"      # 警告
    INFO = "info"            # 信息


class AnomalyType(Enum):
    """异常类型"""
    ERROR_LOG = "error_log"              # 错误日志
    WARNING_LOG = "warning_log"          # 警告日志
    EXCEPTION = "exception"              # 异常堆栈
    TIMEOUT = "timeout"                  # 超时
    HIGH_LATENCY = "high_latency"        # 高延迟
    ERROR_RATE_SPIKE = "error_rate_spike"  # 错误率飙升
    TRAFFIC_ANOMALY = "traffic_anomaly"  # 流量异常
    SECURITY_ALERT = "security_alert"    # 安全告警


@dataclass
class LogAnomaly:
    """日志异常"""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    log_content: str
    timestamp: datetime | None = None
    count: int = 1
    affected_endpoints: list[str] = field(default_factory=list)
    stack_trace: str | None = None
    suggested_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyReport:
    """异常报告"""
    report_id: str
    task_id: str
    title: str
    summary: str
    total_anomalies: int
    critical_count: int
    error_count: int
    warning_count: int
    anomalies: list[LogAnomaly]
    ai_analysis: str | None = None
    recommendations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class LogAnomalyDetectorService:
    """
    日志异常检测服务
    
    功能：
    1. 解析日志中的 warning/error 信息
    2. 检测异常模式（超时、高延迟、错误率等）
    3. 使用 AI 分析异常原因
    4. 生成异常报告
    """
    
    # 常见错误模式
    ERROR_PATTERNS = [
        (r'\b(ERROR|FATAL|CRITICAL)\b', AnomalySeverity.ERROR),
        (r'\b(Exception|Error|Failure)\b.*?:', AnomalySeverity.ERROR),
        (r'(?i)(failed|failure|error|exception)', AnomalySeverity.ERROR),
        (r'(?i)(timeout|timed out)', AnomalySeverity.ERROR),
        (r'(?i)(connection refused|connection reset)', AnomalySeverity.ERROR),
        (r'(?i)(out of memory|oom)', AnomalySeverity.CRITICAL),
        (r'(?i)(deadlock|race condition)', AnomalySeverity.CRITICAL),
    ]
    
    WARNING_PATTERNS = [
        (r'\b(WARN|WARNING)\b', AnomalySeverity.WARNING),
        (r'(?i)(deprecated|deprecation)', AnomalySeverity.WARNING),
        (r'(?i)(slow query|slow request)', AnomalySeverity.WARNING),
        (r'(?i)(retry|retrying)', AnomalySeverity.WARNING),
        (r'(?i)(high memory|high cpu)', AnomalySeverity.WARNING),
    ]
    
    SECURITY_PATTERNS = [
        (r'(?i)(sql injection|xss|csrf)', AnomalySeverity.CRITICAL),
        (r'(?i)(unauthorized|forbidden|access denied)', AnomalySeverity.ERROR),
        (r'(?i)(invalid token|token expired)', AnomalySeverity.WARNING),
        (r'(?i)(brute force|too many attempts)', AnomalySeverity.ERROR),
    ]
    
    # 异常堆栈模式
    STACK_TRACE_PATTERNS = [
        r'Traceback \(most recent call last\):[\s\S]*?(?=\n\n|\Z)',  # Python
        r'at [\w.$]+\([\w.]+:\d+\)[\s\S]*?(?=\n\n|\Z)',  # Java
        r'Error:.*\n\s+at .*\n(?:\s+at .*\n)*',  # JavaScript
    ]
    
    def __init__(self, verbose: bool = False):
        self.logger = get_logger(verbose)
        self.verbose = verbose
        self.db = get_db_manager()
        self._analysis_chain: LogAnalysisChain | None = None
        self._report_chain: ReportGeneratorChain | None = None
    
    @property
    def analysis_chain(self) -> LogAnalysisChain:
        """懒加载分析 Chain"""
        if self._analysis_chain is None:
            provider = get_llm_provider()
            self._analysis_chain = LogAnalysisChain(provider, self.verbose)
        return self._analysis_chain
    
    @property
    def report_chain(self) -> ReportGeneratorChain:
        """懒加载报告 Chain"""
        if self._report_chain is None:
            provider = get_llm_provider()
            self._report_chain = ReportGeneratorChain(provider, self.verbose)
        return self._report_chain
    
    def detect_anomalies_from_task(
        self,
        task_id: str,
        include_ai_analysis: bool = True
    ) -> AnomalyReport:
        """
        从分析任务中检测异常
        
        Args:
            task_id: 分析任务ID
            include_ai_analysis: 是否包含AI分析
            
        Returns:
            异常报告
        """
        self.logger.start_step("检测日志异常")
        
        # 获取任务中的请求记录
        sql = """
            SELECT * FROM parsed_requests 
            WHERE task_id = %s
            ORDER BY timestamp
        """
        requests = self.db.fetch_all(sql, (task_id,))
        
        anomalies: list[LogAnomaly] = []
        
        # 1. 检测错误和警告日志
        error_anomalies = self._detect_error_logs(requests)
        anomalies.extend(error_anomalies)
        
        # 2. 检测异常堆栈
        exception_anomalies = self._detect_exceptions(requests)
        anomalies.extend(exception_anomalies)
        
        # 3. 检测性能异常
        perf_anomalies = self._detect_performance_anomalies(requests)
        anomalies.extend(perf_anomalies)
        
        # 4. 检测安全异常
        security_anomalies = self._detect_security_anomalies(requests)
        anomalies.extend(security_anomalies)
        
        # 5. 检测错误率异常
        rate_anomalies = self._detect_error_rate_anomalies(requests)
        anomalies.extend(rate_anomalies)
        
        # 去重和聚合
        anomalies = self._aggregate_anomalies(anomalies)
        
        # 统计
        critical_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
        error_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.ERROR)
        warning_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.WARNING)
        
        self.logger.info(f"检测到 {len(anomalies)} 个异常: {critical_count} 严重, {error_count} 错误, {warning_count} 警告")
        
        # AI 分析
        ai_analysis = None
        recommendations: list[str] = []
        if include_ai_analysis and anomalies:
            try:
                ai_result = self._ai_analyze_anomalies(anomalies)
                ai_analysis = ai_result.get('analysis', '')
                recommendations = ai_result.get('recommendations', [])
            except Exception as e:
                self.logger.warn(f"AI 分析失败: {e}")
        
        # 生成报告
        report = self._create_report(
            task_id, anomalies, ai_analysis, recommendations
        )
        
        # 保存报告
        self._save_report(report)
        
        self.logger.end_step(f"生成异常报告: {report.report_id}")
        
        return report
    
    def detect_anomalies_from_log_content(
        self,
        log_content: str,
        source_name: str = "manual"
    ) -> list[LogAnomaly]:
        """
        从日志内容直接检测异常
        
        Args:
            log_content: 日志内容
            source_name: 来源名称
            
        Returns:
            异常列表
        """
        anomalies: list[LogAnomaly] = []
        
        # 按行分析
        lines = log_content.split('\n')
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # 检测错误
            for pattern, severity in self.ERROR_PATTERNS:
                if re.search(pattern, line):
                    anomaly = self._create_anomaly_from_line(
                        line, i + 1, AnomalyType.ERROR_LOG, severity
                    )
                    anomalies.append(anomaly)
                    break
            
            # 检测警告
            for pattern, severity in self.WARNING_PATTERNS:
                if re.search(pattern, line):
                    anomaly = self._create_anomaly_from_line(
                        line, i + 1, AnomalyType.WARNING_LOG, severity
                    )
                    anomalies.append(anomaly)
                    break
            
            # 检测安全问题
            for pattern, severity in self.SECURITY_PATTERNS:
                if re.search(pattern, line):
                    anomaly = self._create_anomaly_from_line(
                        line, i + 1, AnomalyType.SECURITY_ALERT, severity
                    )
                    anomalies.append(anomaly)
                    break
        
        # 检测异常堆栈
        for pattern in self.STACK_TRACE_PATTERNS:
            matches = re.finditer(pattern, log_content)
            for match in matches:
                stack_trace = match.group(0)
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(stack_trace[:100].encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.EXCEPTION,
                    severity=AnomalySeverity.ERROR,
                    title="异常堆栈",
                    description="检测到异常堆栈信息",
                    log_content=stack_trace[:500],
                    stack_trace=stack_trace
                )
                anomalies.append(anomaly)
        
        return self._aggregate_anomalies(anomalies)
    
    def detect_anomalies_from_file(
        self,
        file_path: str,
        task_id: str,
        detect_types: list[str] | None = None,
        include_ai_analysis: bool = True
    ) -> AnomalyReport:
        """
        从日志文件检测异常
        
        Args:
            file_path: 日志文件路径
            task_id: 关联任务ID
            detect_types: 要检测的异常类型
            include_ai_analysis: 是否包含AI分析
            
        Returns:
            异常报告
        """
        self.logger.start_step(f"从文件检测异常: {file_path}")
        
        # 流式逐行读取，避免大文件一次性加载到内存
        anomalies: list[LogAnomaly] = []
        line_count = 0
        max_anomalies = 5000  # 防止异常列表过大
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    line_count += 1
                    
                    if len(anomalies) >= max_anomalies:
                        self.logger.info(f"异常数量达到上限 {max_anomalies}，停止检测")
                        break
                    
                    # 检测错误
                    for pattern, severity in self.ERROR_PATTERNS:
                        if re.search(pattern, line):
                            anomaly = self._create_anomaly_from_line(
                                line, line_count, AnomalyType.ERROR_LOG, severity
                            )
                            anomalies.append(anomaly)
                            break
                    
                    # 检测警告
                    for pattern, severity in self.WARNING_PATTERNS:
                        if re.search(pattern, line):
                            anomaly = self._create_anomaly_from_line(
                                line, line_count, AnomalyType.WARNING_LOG, severity
                            )
                            anomalies.append(anomaly)
                            break
                    
                    # 检测安全问题
                    for pattern, severity in self.SECURITY_PATTERNS:
                        if re.search(pattern, line):
                            anomaly = self._create_anomaly_from_line(
                                line, line_count, AnomalyType.SECURITY_ALERT, severity
                            )
                            anomalies.append(anomaly)
                            break
            
            self.logger.info(f"流式读取 {line_count} 行，检测到 {len(anomalies)} 个原始异常")
            anomalies = self._aggregate_anomalies(anomalies)
        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            raise
        
        # 按类型过滤
        if detect_types:
            type_set = set(detect_types)
            anomalies = [a for a in anomalies if a.anomaly_type.value in type_set]
        
        # 统计
        critical_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
        error_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.ERROR)
        warning_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.WARNING)
        
        self.logger.info(f"检测到 {len(anomalies)} 个异常: {critical_count} 严重, {error_count} 错误, {warning_count} 警告")
        
        # AI 分析
        ai_analysis = None
        recommendations: list[str] = []
        if include_ai_analysis and anomalies:
            try:
                ai_result = self._ai_analyze_anomalies(anomalies)
                ai_analysis = ai_result.get('analysis', '')
                recommendations = ai_result.get('recommendations', [])
            except Exception as e:
                self.logger.warn(f"AI 分析失败: {e}")
        
        # 生成报告
        report = self._create_report(
            task_id, anomalies, ai_analysis, recommendations
        )
        
        # 保存报告
        self._save_report(report)
        
        self.logger.end_step(f"生成异常报告: {report.report_id}")
        
        return report
    
    def _detect_error_logs(self, requests: list[dict[str, Any]]) -> list[LogAnomaly]:
        """检测错误日志"""
        anomalies: list[LogAnomaly] = []
        
        for req in requests:
            # 检查 has_error 标记
            if req.get('has_error'):
                error_msg = req.get('error_message', '')
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(f"error:{req['request_id']}".encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.ERROR_LOG,
                    severity=AnomalySeverity.ERROR,
                    title=f"请求错误: {req['method']} {req['url'][:50]}",
                    description=error_msg[:500] if error_msg else "请求处理出错",
                    log_content=req.get('raw_logs', '')[:1000] if req.get('raw_logs') else '',
                    affected_endpoints=[f"{req['method']} {req['url']}"]
                )
                anomalies.append(anomaly)
            
            # 检查 has_warning 标记
            if req.get('has_warning'):
                warning_msg = req.get('warning_message', '')
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(f"warning:{req['request_id']}".encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.WARNING_LOG,
                    severity=AnomalySeverity.WARNING,
                    title=f"请求警告: {req['method']} {req['url'][:50]}",
                    description=warning_msg[:500] if warning_msg else "请求处理有警告",
                    log_content=req.get('raw_logs', '')[:1000] if req.get('raw_logs') else '',
                    affected_endpoints=[f"{req['method']} {req['url']}"]
                )
                anomalies.append(anomaly)
            
            # 检查 HTTP 错误状态码
            status = req.get('http_status', 0)
            if status >= 500:
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(f"5xx:{req['request_id']}".encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.ERROR_LOG,
                    severity=AnomalySeverity.ERROR,
                    title=f"服务器错误 {status}: {req['method']} {req['url'][:50]}",
                    description=f"HTTP {status} 服务器内部错误",
                    log_content=req.get('response_body', '')[:500] if req.get('response_body') else '',
                    affected_endpoints=[f"{req['method']} {req['url']}"],
                    metadata={"status_code": status}
                )
                anomalies.append(anomaly)
            elif status >= 400:
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(f"4xx:{req['request_id']}".encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.WARNING_LOG,
                    severity=AnomalySeverity.WARNING,
                    title=f"客户端错误 {status}: {req['method']} {req['url'][:50]}",
                    description=f"HTTP {status} 客户端请求错误",
                    log_content=req.get('response_body', '')[:500] if req.get('response_body') else '',
                    affected_endpoints=[f"{req['method']} {req['url']}"],
                    metadata={"status_code": status}
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_exceptions(self, requests: list[dict[str, Any]]) -> list[LogAnomaly]:
        """检测异常堆栈"""
        anomalies: list[LogAnomaly] = []
        
        for req in requests:
            raw_logs = req.get('raw_logs', '') or ''
            response_body = req.get('response_body', '') or ''
            
            content = f"{raw_logs}\n{response_body}"
            
            for pattern in self.STACK_TRACE_PATTERNS:
                matches = re.finditer(pattern, content)
                for match in matches:
                    stack_trace = match.group(0)
                    # 提取异常类型
                    exception_type = "Unknown Exception"
                    type_match = re.search(r'(\w+(?:Error|Exception))', stack_trace)
                    if type_match:
                        exception_type = type_match.group(1)
                    
                    anomaly = LogAnomaly(
                        anomaly_id=hashlib.md5(stack_trace[:100].encode()).hexdigest()[:16],
                        anomaly_type=AnomalyType.EXCEPTION,
                        severity=AnomalySeverity.ERROR,
                        title=f"异常: {exception_type}",
                        description=f"在请求 {req['method']} {req['url'][:50]} 中检测到异常",
                        log_content=stack_trace[:500],
                        stack_trace=stack_trace,
                        affected_endpoints=[f"{req['method']} {req['url']}"]
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_performance_anomalies(self, requests: list[dict[str, Any]]) -> list[LogAnomaly]:
        """检测性能异常"""
        anomalies: list[LogAnomaly] = []
        
        # 计算响应时间统计
        response_times = [
            float(req.get('response_time_ms', 0))
            for req in requests
            if req.get('response_time_ms')
        ]
        
        if not response_times:
            return anomalies
        
        avg_time = sum(response_times) / len(response_times)
        
        # 检测高延迟请求（超过平均值3倍或超过5秒）
        threshold = max(avg_time * 3, 5000)
        
        for req in requests:
            response_time = float(req.get('response_time_ms', 0))
            if response_time > threshold:
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(f"slow:{req['request_id']}".encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.HIGH_LATENCY,
                    severity=AnomalySeverity.WARNING if response_time < 10000 else AnomalySeverity.ERROR,
                    title=f"高延迟请求: {response_time:.0f}ms",
                    description=f"请求 {req['method']} {req['url'][:50]} 响应时间 {response_time:.0f}ms，超过阈值 {threshold:.0f}ms",
                    log_content=f"响应时间: {response_time}ms, 平均: {avg_time:.0f}ms",
                    affected_endpoints=[f"{req['method']} {req['url']}"],
                    metadata={
                        "response_time_ms": response_time,
                        "threshold_ms": threshold,
                        "avg_time_ms": avg_time
                    }
                )
                anomalies.append(anomaly)
            
            # 检测超时
            if response_time > 30000:  # 30秒
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(f"timeout:{req['request_id']}".encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.TIMEOUT,
                    severity=AnomalySeverity.ERROR,
                    title=f"请求超时: {response_time:.0f}ms",
                    description=f"请求 {req['method']} {req['url'][:50]} 可能超时",
                    log_content="",
                    affected_endpoints=[f"{req['method']} {req['url']}"],
                    metadata={"response_time_ms": response_time}
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_security_anomalies(self, requests: list[dict[str, Any]]) -> list[LogAnomaly]:
        """检测安全异常"""
        anomalies: list[LogAnomaly] = []
        
        for req in requests:
            url = req.get('url', '')
            body = req.get('body', '') or ''
            raw_logs = req.get('raw_logs', '') or ''
            
            content = f"{url}\n{body}\n{raw_logs}"
            
            for pattern, severity in self.SECURITY_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    match = re.search(pattern, content, re.IGNORECASE)
                    matched_text = match.group(0) if match else ""
                    
                    anomaly = LogAnomaly(
                        anomaly_id=hashlib.md5(f"security:{req['request_id']}:{pattern}".encode()).hexdigest()[:16],
                        anomaly_type=AnomalyType.SECURITY_ALERT,
                        severity=severity,
                        title=f"安全告警: {matched_text[:30]}",
                        description=f"在请求 {req['method']} {req['url'][:50]} 中检测到潜在安全问题",
                        log_content=content[:500],
                        affected_endpoints=[f"{req['method']} {req['url']}"],
                        suggested_actions=[
                            "检查请求来源是否合法",
                            "验证输入参数是否经过安全过滤",
                            "检查相关日志确认是否为攻击行为"
                        ]
                    )
                    anomalies.append(anomaly)
                    break
        
        return anomalies
    
    def _detect_error_rate_anomalies(self, requests: list[dict[str, Any]]) -> list[LogAnomaly]:
        """检测错误率异常"""
        anomalies: list[LogAnomaly] = []
        
        # 按接口分组统计
        endpoint_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "errors": 0})
        
        for req in requests:
            key = f"{req['method']} {req['url'].split('?')[0]}"
            endpoint_stats[key]["total"] += 1
            
            status = req.get('http_status', 0)
            if status >= 400 or req.get('has_error'):
                endpoint_stats[key]["errors"] += 1
        
        # 检测高错误率接口
        for endpoint, stats in endpoint_stats.items():
            if stats["total"] < 5:  # 样本太少，跳过
                continue
            
            error_rate = stats["errors"] / stats["total"]
            
            if error_rate > 0.5:  # 错误率超过50%
                anomaly = LogAnomaly(
                    anomaly_id=hashlib.md5(f"error_rate:{endpoint}".encode()).hexdigest()[:16],
                    anomaly_type=AnomalyType.ERROR_RATE_SPIKE,
                    severity=AnomalySeverity.CRITICAL if error_rate > 0.8 else AnomalySeverity.ERROR,
                    title=f"高错误率: {error_rate:.0%}",
                    description=f"接口 {endpoint} 错误率 {error_rate:.0%} ({stats['errors']}/{stats['total']})",
                    log_content="",
                    affected_endpoints=[endpoint],
                    metadata={
                        "error_rate": error_rate,
                        "total_requests": stats["total"],
                        "error_count": stats["errors"]
                    },
                    suggested_actions=[
                        "检查接口实现是否有bug",
                        "检查依赖服务是否正常",
                        "查看详细错误日志定位问题"
                    ]
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _create_anomaly_from_line(
        self,
        line: str,
        line_number: int,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity
    ) -> LogAnomaly:
        """从日志行创建异常"""
        # 提取时间戳
        timestamp = None
        ts_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', line)
        if ts_match:
            try:
                timestamp = datetime.fromisoformat(ts_match.group(0).replace(' ', 'T'))
            except ValueError:
                pass
        
        return LogAnomaly(
            anomaly_id=hashlib.md5(f"{line_number}:{line[:50]}".encode()).hexdigest()[:16],
            anomaly_type=anomaly_type,
            severity=severity,
            title=self._extract_title(line, anomaly_type),
            description=line[:200],
            log_content=line,
            timestamp=timestamp,
            metadata={"line_number": line_number}
        )
    
    def _extract_title(self, line: str, anomaly_type: AnomalyType) -> str:
        """从日志行提取标题"""
        # 尝试提取错误类型
        error_match = re.search(r'(\w+(?:Error|Exception|Warning|Failed))', line)
        if error_match:
            return error_match.group(1)
        
        # 按类型返回默认标题
        type_titles = {
            AnomalyType.ERROR_LOG: "错误日志",
            AnomalyType.WARNING_LOG: "警告日志",
            AnomalyType.EXCEPTION: "异常",
            AnomalyType.SECURITY_ALERT: "安全告警"
        }
        return type_titles.get(anomaly_type, "异常")
    
    def _aggregate_anomalies(self, anomalies: list[LogAnomaly]) -> list[LogAnomaly]:
        """聚合相似异常"""
        # 按标题分组
        groups: dict[str, list[LogAnomaly]] = defaultdict(list)
        
        for anomaly in anomalies:
            # 使用标题和类型作为分组键
            key = f"{anomaly.anomaly_type.value}:{anomaly.title}"
            groups[key].append(anomaly)
        
        # 聚合
        aggregated: list[LogAnomaly] = []
        for key, group in groups.items():
            if len(group) == 1:
                aggregated.append(group[0])
            else:
                # 合并同类异常
                first = group[0]
                all_endpoints = []
                for a in group:
                    all_endpoints.extend(a.affected_endpoints)
                
                merged = LogAnomaly(
                    anomaly_id=first.anomaly_id,
                    anomaly_type=first.anomaly_type,
                    severity=max(a.severity.value for a in group) and first.severity,  # 取最高严重级别
                    title=f"{first.title} (x{len(group)})",
                    description=first.description,
                    log_content=first.log_content,
                    timestamp=first.timestamp,
                    count=len(group),
                    affected_endpoints=list(set(all_endpoints))[:10],
                    stack_trace=first.stack_trace,
                    suggested_actions=first.suggested_actions,
                    metadata={**first.metadata, "occurrence_count": len(group)}
                )
                aggregated.append(merged)
        
        # 按严重程度排序
        severity_order = {
            AnomalySeverity.CRITICAL: 0,
            AnomalySeverity.ERROR: 1,
            AnomalySeverity.WARNING: 2,
            AnomalySeverity.INFO: 3
        }
        aggregated.sort(key=lambda a: (severity_order.get(a.severity, 9), -a.count))
        
        return aggregated
    
    def _ai_analyze_anomalies(self, anomalies: list[LogAnomaly]) -> dict[str, Any]:
        """使用 AI 分析异常（知识库优先 + LLM 回退）"""
        self.logger.ai_start("AI异常分析", f"{len(anomalies)} 个异常")
        
        # 收集错误信息和端点
        error_messages = [a.description[:200] for a in anomalies[:20]]
        urls = []
        for a in anomalies[:20]:
            urls.extend(a.affected_endpoints[:3])
        urls = list(set(urls))[:10]
        
        # 第一步：通过 Skill 尝试知识库 + 模板诊断
        try:
            from ..skills.analysis_skills import diagnose_with_knowledge
            skill_result = diagnose_with_knowledge(
                error_messages=error_messages,
                urls=urls,
                use_llm_fallback=False,  # 先不回退 LLM
            )
            
            if skill_result.get("source") in ("knowledge", "template"):
                self.logger.info(f"知识库/模板直接诊断成功 (来源: {skill_result['source']})")
                self.logger.ai_end("知识库诊断完成（未调用 LLM）")
                return {
                    "analysis": (
                        f"## 诊断结果（来源: {skill_result['source']}）\n\n"
                        f"**根因**: {skill_result.get('root_cause', '未知')}\n\n"
                        f"**影响**: {skill_result.get('impact', '待评估')}\n\n"
                        f"**建议**: {skill_result.get('suggestion', '无')}"
                    ),
                    "recommendations": [skill_result.get("suggestion", "")] if skill_result.get("suggestion") else [],
                    "source": skill_result["source"],
                }
        except Exception as e:
            self.logger.debug(f"Skill 诊断失败，回退到 LLM: {e}")
        
        # 第二步：LLM 分析（带知识上下文）
        anomaly_summary = []
        for a in anomalies[:20]:
            anomaly_summary.append({
                "type": a.anomaly_type.value,
                "severity": a.severity.value,
                "title": a.title,
                "description": a.description[:200],
                "count": a.count,
                "affected_endpoints": a.affected_endpoints[:5]
            })
        
        # 获取知识上下文
        knowledge_context = ""
        try:
            from ..api.dependencies import get_knowledge_retriever, get_rag_builder
            retriever = get_knowledge_retriever()
            rag_builder = get_rag_builder()
            entries = retriever.retrieve_for_log_analysis(urls=urls, error_messages=error_messages)
            if entries:
                knowledge_context = rag_builder.build_context(
                    query=" ".join(error_messages[:3]),
                    entries=entries,
                )
                self.logger.info(f"注入 {len(entries)} 条知识到诊断上下文")
        except Exception as e:
            self.logger.debug(f"知识上下文构建失败（不影响分析）: {e}")
        
        context = {
            "total_anomalies": len(anomalies),
            "critical_count": sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL),
            "error_count": sum(1 for a in anomalies if a.severity == AnomalySeverity.ERROR),
        }
        if knowledge_context:
            context["knowledge_context"] = knowledge_context
        
        result = self.analysis_chain.diagnose_errors(
            error_logs=json.dumps(anomaly_summary, ensure_ascii=False, indent=2),
            context=context
        )
        
        self.logger.ai_end("LLM 分析完成")
        
        return result
    
    def _create_report(
        self,
        task_id: str,
        anomalies: list[LogAnomaly],
        ai_analysis: str | None,
        recommendations: list[str]
    ) -> AnomalyReport:
        """创建异常报告"""
        report_id = hashlib.md5(
            f"anomaly_report:{task_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        critical_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
        error_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.ERROR)
        warning_count = sum(1 for a in anomalies if a.severity == AnomalySeverity.WARNING)
        
        # 生成摘要
        if critical_count > 0:
            summary = f"发现 {critical_count} 个严重问题需要立即处理"
        elif error_count > 0:
            summary = f"发现 {error_count} 个错误需要关注"
        elif warning_count > 0:
            summary = f"发现 {warning_count} 个警告"
        else:
            summary = "未发现明显异常"
        
        return AnomalyReport(
            report_id=report_id,
            task_id=task_id,
            title=f"日志异常报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            summary=summary,
            total_anomalies=len(anomalies),
            critical_count=critical_count,
            error_count=error_count,
            warning_count=warning_count,
            anomalies=anomalies,
            ai_analysis=ai_analysis,
            recommendations=recommendations
        )
    
    def _save_report(self, report: AnomalyReport) -> None:
        """保存报告到数据库"""
        # 生成 Markdown 内容
        content = self._generate_markdown_report(report)
        
        sql = """
            INSERT INTO analysis_reports 
            (task_id, report_type, title, content, format, statistics, issues, recommendations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        statistics = {
            "total_anomalies": report.total_anomalies,
            "critical_count": report.critical_count,
            "error_count": report.error_count,
            "warning_count": report.warning_count
        }
        
        issues = [
            {
                "id": a.anomaly_id,
                "type": a.anomaly_type.value,
                "severity": a.severity.value,
                "title": a.title,
                "description": a.description[:500],
                "count": a.count
            }
            for a in report.anomalies[:50]
        ]
        
        self.db.execute(sql, (
            report.task_id,
            'analysis',
            report.title,
            content,
            'markdown',
            json.dumps(statistics, ensure_ascii=False),
            json.dumps(issues, ensure_ascii=False),
            json.dumps(report.recommendations, ensure_ascii=False)
        ))
    
    def _generate_markdown_report(self, report: AnomalyReport) -> str:
        """生成 Markdown 格式报告"""
        lines = [
            f"# {report.title}",
            "",
            f"**生成时间**: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 摘要",
            "",
            report.summary,
            "",
            "## 统计",
            "",
            f"- 总异常数: {report.total_anomalies}",
            f"- 严重: {report.critical_count}",
            f"- 错误: {report.error_count}",
            f"- 警告: {report.warning_count}",
            "",
        ]
        
        # 严重问题
        critical_anomalies = [a for a in report.anomalies if a.severity == AnomalySeverity.CRITICAL]
        if critical_anomalies:
            lines.extend([
                "## 🔴 严重问题",
                ""
            ])
            for a in critical_anomalies[:10]:
                lines.extend([
                    f"### {a.title}",
                    "",
                    a.description,
                    "",
                    f"- 类型: {a.anomaly_type.value}",
                    f"- 出现次数: {a.count}",
                    ""
                ])
                if a.suggested_actions:
                    lines.append("**建议操作**:")
                    for action in a.suggested_actions:
                        lines.append(f"- {action}")
                    lines.append("")
        
        # 错误
        error_anomalies = [a for a in report.anomalies if a.severity == AnomalySeverity.ERROR]
        if error_anomalies:
            lines.extend([
                "## 🟠 错误",
                ""
            ])
            for a in error_anomalies[:10]:
                lines.extend([
                    f"### {a.title}",
                    "",
                    a.description[:300],
                    "",
                    f"- 出现次数: {a.count}",
                    ""
                ])
        
        # 警告
        warning_anomalies = [a for a in report.anomalies if a.severity == AnomalySeverity.WARNING]
        if warning_anomalies:
            lines.extend([
                "## 🟡 警告",
                ""
            ])
            for a in warning_anomalies[:10]:
                lines.append(f"- **{a.title}**: {a.description[:100]} (x{a.count})")
            lines.append("")
        
        # AI 分析
        if report.ai_analysis:
            lines.extend([
                "## AI 分析",
                "",
                report.ai_analysis,
                ""
            ])
        
        # 建议
        if report.recommendations:
            lines.extend([
                "## 改进建议",
                ""
            ])
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        return "\n".join(lines)
