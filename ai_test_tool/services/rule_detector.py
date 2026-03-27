# 该文件内容使用AI生成，注意识别准确性
"""
实时规则检测引擎

对日志行进行逐行正则匹配（微秒级），不依赖 LLM。
检测 ERROR/WARN/SECURITY 三类模式，返回检测结果。
"""

import re
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """检测结果"""
    severity: str  # critical / error / warning / security
    pattern_name: str  # 匹配的模式名称
    matched_text: str  # 匹配到的文本
    line: str  # 原始日志行
    diagnosis: dict[str, str] | None = None  # 规则模板诊断（如果有）


class RuleDetector:
    """
    实时规则检测引擎

    复用 LogAnomalyDetectorService 的正则模式，
    在日志行进入缓冲区之前进行微秒级检测。
    """

    # ERROR 模式（pattern, severity, name）
    ERROR_PATTERNS: list[tuple[re.Pattern, str, str]] = [
        (re.compile(r'\b(FATAL|CRITICAL)\b', re.IGNORECASE), "critical", "fatal_critical"),
        (re.compile(r'\bERROR\b', re.IGNORECASE), "error", "error_keyword"),
        (re.compile(r'\b(Exception|Traceback)\b'), "error", "exception"),
        (re.compile(r'\b(failed|failure)\b', re.IGNORECASE), "error", "failure"),
        (re.compile(r'\b(timeout|timed\s*out|deadline\s*exceeded)\b', re.IGNORECASE), "error", "timeout"),
        (re.compile(r'\b(connection\s*refused|connection\s*reset|econnrefused)\b', re.IGNORECASE), "error", "connection"),
        (re.compile(r'\b(out\s*of\s*memory|oom|heap\s*space)\b', re.IGNORECASE), "critical", "oom"),
        (re.compile(r'\b(deadlock|race\s*condition)\b', re.IGNORECASE), "error", "deadlock"),
    ]

    # WARN 模式
    WARN_PATTERNS: list[tuple[re.Pattern, str, str]] = [
        (re.compile(r'\bWARN(ING)?\b', re.IGNORECASE), "warning", "warn_keyword"),
        (re.compile(r'\bdeprecated\b', re.IGNORECASE), "warning", "deprecated"),
        (re.compile(r'\b(slow\s*query|slow\s*request)\b', re.IGNORECASE), "warning", "slow"),
        (re.compile(r'\b(retry|retrying)\b', re.IGNORECASE), "warning", "retry"),
        (re.compile(r'\b(high\s*memory|high\s*cpu)\b', re.IGNORECASE), "warning", "high_resource"),
    ]

    # 安全模式
    SECURITY_PATTERNS: list[tuple[re.Pattern, str, str]] = [
        (re.compile(r'\b(sql\s*injection|xss|csrf)\b', re.IGNORECASE), "security", "injection"),
        (re.compile(r'\b(unauthorized|forbidden)\b', re.IGNORECASE), "security", "auth_failure"),
        (re.compile(r'\b(invalid\s*token|expired\s*token)\b', re.IGNORECASE), "security", "token_issue"),
        (re.compile(r'\b(brute\s*force|too\s*many\s*attempts)\b', re.IGNORECASE), "security", "brute_force"),
    ]

    # 常见错误诊断模板
    DIAGNOSIS_TEMPLATES: dict[str, dict[str, str]] = {
        "oom": {
            "root_cause": "内存不足，进程使用的内存超出限制",
            "impact": "服务可能崩溃重启",
            "suggestion": "检查内存泄漏、增加内存限制、优化大对象生命周期",
        },
        "timeout": {
            "root_cause": "请求超时，下游服务或数据库响应过慢",
            "impact": "用户请求失败，可能触发重试雪崩",
            "suggestion": "检查下游服务健康状态、优化慢查询、添加熔断机制",
        },
        "connection": {
            "root_cause": "连接被拒绝，目标服务未启动或端口不可达",
            "impact": "依赖该服务的功能不可用",
            "suggestion": "确认目标服务运行状态、检查网络和防火墙",
        },
        "deadlock": {
            "root_cause": "死锁或锁等待超时",
            "impact": "请求阻塞或失败，可能耗尽连接池",
            "suggestion": "优化事务范围、统一锁获取顺序",
        },
        "auth_failure": {
            "root_cause": "认证/授权失败",
            "impact": "用户无法访问受保护资源",
            "suggestion": "检查 Token 有效性、权限配置、认证服务状态",
        },
        "token_issue": {
            "root_cause": "Token 无效或过期",
            "impact": "需要重新认证",
            "suggestion": "检查 Token 签发逻辑、过期时间配置",
        },
    }

    def check(self, line: str) -> DetectionResult | None:
        """
        检测单行日志

        Returns:
            DetectionResult 如果匹配到模式，否则 None
        """
        if not line or not line.strip():
            return None

        # 按优先级检测：ERROR > SECURITY > WARN
        for pattern, severity, name in self.ERROR_PATTERNS:
            match = pattern.search(line)
            if match:
                return DetectionResult(
                    severity=severity,
                    pattern_name=name,
                    matched_text=match.group(0),
                    line=line[:1000],
                    diagnosis=self.DIAGNOSIS_TEMPLATES.get(name),
                )

        for pattern, severity, name in self.SECURITY_PATTERNS:
            match = pattern.search(line)
            if match:
                return DetectionResult(
                    severity=severity,
                    pattern_name=name,
                    matched_text=match.group(0),
                    line=line[:1000],
                    diagnosis=self.DIAGNOSIS_TEMPLATES.get(name),
                )

        for pattern, severity, name in self.WARN_PATTERNS:
            match = pattern.search(line)
            if match:
                return DetectionResult(
                    severity=severity,
                    pattern_name=name,
                    matched_text=match.group(0),
                    line=line[:1000],
                )

        return None

    def is_error_or_critical(self, result: DetectionResult | None) -> bool:
        """检测结果是否为 ERROR 或 CRITICAL 级别"""
        return result is not None and result.severity in ("error", "critical")

    def is_warning(self, result: DetectionResult | None) -> bool:
        """检测结果是否为 WARNING 级别"""
        return result is not None and result.severity == "warning"
