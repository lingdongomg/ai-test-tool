"""
AI处理日志模块
提供AI处理过程的可视化监控
支持控制台输出和文件日志
Python 3.13+ 兼容
"""

import os
import sys
import time
from typing import Any, TextIO
from datetime import datetime
from enum import Enum
from pathlib import Path


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    AI = "AI"
    WARN = "WARN"
    ERROR = "ERROR"


class AILogger:
    """
    AI处理日志器
    
    提供AI处理过程的实时监控和日志输出
    支持同时输出到控制台和文件
    """
    
    def __init__(
        self,
        verbose: bool = False,
        name: str = "AITestTool",
        log_dir: str | None = None,
        enable_file_log: bool = True
    ) -> None:
        """
        初始化日志器
        
        Args:
            verbose: 是否显示详细日志
            name: 日志器名称（项目名）
            log_dir: 日志目录，默认为项目根目录下的 logs 目录
            enable_file_log: 是否启用文件日志
        """
        self.verbose = verbose
        self.name = name
        self.enable_file_log = enable_file_log
        self._start_time: float | None = None
        self._step_start: float | None = None
        self._current_step: str = ""
        self._log_file: TextIO | None = None
        self._log_file_path: str | None = None
        
        # 统计信息
        self.stats: dict[str, Any] = {
            "ai_calls": 0,
            "ai_tokens_in": 0,
            "ai_tokens_out": 0,
            "ai_time_ms": 0,
            "errors": 0,
            "warnings": 0
        }
        
        # 初始化文件日志
        if enable_file_log:
            self._init_file_log(log_dir)
    
    def _init_file_log(self, log_dir: str | None = None) -> None:
        """初始化文件日志"""
        if log_dir is None:
            # 默认在项目根目录下创建 logs 目录
            log_dir = os.path.join(os.getcwd(), "logs")
        
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 生成日志文件名: 项目名_日期.log
        date_str = datetime.now().strftime("%Y%m%d")
        log_filename = f"{self.name}_{date_str}.log"
        self._log_file_path = str(log_path / log_filename)
        
        try:
            self._log_file = open(self._log_file_path, 'a', encoding='utf-8')
        except Exception as e:
            print(f"警告: 无法创建日志文件 {self._log_file_path}: {e}")
            self._log_file = None
    
    def _format_time(self) -> str:
        """格式化当前时间"""
        return datetime.now().strftime("%H:%M:%S")
    
    def _format_datetime(self) -> str:
        """格式化完整日期时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_elapsed(self) -> str:
        """获取已用时间"""
        if self._start_time:
            elapsed = time.time() - self._start_time
            return f"{elapsed:.1f}s"
        return "0.0s"
    
    def _write_to_file(self, level: LogLevel, message: str) -> None:
        """写入日志到文件"""
        if self._log_file is None:
            return
        
        try:
            timestamp = self._format_datetime()
            elapsed = self._get_elapsed()
            log_line = f"[{timestamp}] [{elapsed}] [{level.value}] {message}\n"
            self._log_file.write(log_line)
            self._log_file.flush()
        except Exception:
            pass  # 文件写入失败时静默处理
    
    def _print(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        """打印日志"""
        icons = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.AI: "🤖",
            LogLevel.WARN: "⚠️",
            LogLevel.ERROR: "❌"
        }
        
        colors = {
            LogLevel.DEBUG: "\033[90m",  # 灰色
            LogLevel.INFO: "\033[0m",     # 默认
            LogLevel.AI: "\033[36m",      # 青色
            LogLevel.WARN: "\033[33m",    # 黄色
            LogLevel.ERROR: "\033[31m"    # 红色
        }
        
        reset = "\033[0m"
        icon = icons.get(level, "")
        color = colors.get(level, "")
        
        timestamp = self._format_time()
        elapsed = self._get_elapsed()
        
        # 只有verbose模式才显示DEBUG级别
        if level == LogLevel.DEBUG and not self.verbose:
            # 但仍然写入文件
            self._write_to_file(level, message)
            return
        
        # 输出到控制台
        print(f"{color}[{timestamp}] [{elapsed}] {icon} {message}{reset}", **kwargs)
        sys.stdout.flush()
        
        # 输出到文件
        self._write_to_file(level, message)
    
    def start_session(self, description: str = "") -> None:
        """开始一个会话"""
        self._start_time = time.time()
        self._print(LogLevel.INFO, f"开始处理: {description}")
    
    def end_session(self) -> None:
        """结束会话"""
        elapsed = time.time() - self._start_time if self._start_time else 0
        self._print(LogLevel.INFO, f"处理完成，总耗时: {elapsed:.2f}s")
        self._print_stats()
    
    def _print_stats(self) -> None:
        """打印统计信息"""
        if self.stats["ai_calls"] > 0:
            self._print(LogLevel.INFO, "AI处理统计:")
            self._print(LogLevel.INFO, f"   调用次数: {self.stats['ai_calls']}")
            self._print(LogLevel.INFO, f"   总耗时: {self.stats['ai_time_ms']:.0f}ms")
            self._print(LogLevel.INFO, f"   平均耗时: {self.stats['ai_time_ms'] / self.stats['ai_calls']:.0f}ms/次")
            if self.stats["errors"] > 0:
                self._print(LogLevel.WARN, f"   错误数: {self.stats['errors']}")
    
    def start_step(self, step_name: str) -> None:
        """开始一个步骤"""
        self._step_start = time.time()
        self._current_step = step_name
        self._print(LogLevel.INFO, f"[{step_name}] 开始...")
    
    def end_step(self, result: str = "完成") -> None:
        """结束当前步骤"""
        if self._step_start:
            elapsed = (time.time() - self._step_start) * 1000
            self._print(LogLevel.INFO, f"[{self._current_step}] {result} ({elapsed:.0f}ms)")
        self._step_start = None
    
    def info(self, message: str) -> None:
        """输出信息日志"""
        self._print(LogLevel.INFO, message)
    
    def debug(self, message: str) -> None:
        """输出调试日志"""
        self._print(LogLevel.DEBUG, message)
    
    def warn(self, message: str) -> None:
        """输出警告日志"""
        self.stats["warnings"] += 1
        self._print(LogLevel.WARN, message)
    
    def error(self, message: str) -> None:
        """输出错误日志"""
        self.stats["errors"] += 1
        self._print(LogLevel.ERROR, message)
    
    def ai_start(self, operation: str, input_preview: str = "") -> None:
        """
        AI操作开始
        
        Args:
            operation: 操作名称
            input_preview: 输入预览（截断显示）
        """
        self._step_start = time.time()
        self._current_step = operation
        self._print(LogLevel.AI, f"[AI] {operation} - 处理中...")
        
        if self.verbose and input_preview:
            preview = input_preview[:200] + "..." if len(input_preview) > 200 else input_preview
            self._print(LogLevel.DEBUG, f"   输入: {preview}")
    
    def ai_progress(self, message: str) -> None:
        """AI处理进度"""
        if self.verbose:
            self._print(LogLevel.AI, f"   → {message}")
    
    def ai_end(self, result_preview: str = "", tokens_in: int = 0, tokens_out: int = 0) -> None:
        """
        AI操作结束
        
        Args:
            result_preview: 结果预览
            tokens_in: 输入token数
            tokens_out: 输出token数
        """
        elapsed = (time.time() - self._step_start) * 1000 if self._step_start else 0
        
        self.stats["ai_calls"] += 1
        self.stats["ai_time_ms"] += elapsed
        self.stats["ai_tokens_in"] += tokens_in
        self.stats["ai_tokens_out"] += tokens_out
        
        self._print(LogLevel.AI, f"[AI] {self._current_step} - 完成 ({elapsed:.0f}ms)")
        
        if self.verbose and result_preview:
            preview = result_preview[:300] + "..." if len(result_preview) > 300 else result_preview
            self._print(LogLevel.DEBUG, f"   输出: {preview}")
        
        self._step_start = None
    
    def ai_error(self, error: str) -> None:
        """AI操作错误"""
        self.stats["errors"] += 1
        self._print(LogLevel.ERROR, f"[AI] {self._current_step} - 失败: {error}")
    
    def batch_progress(self, current: int, total: int, message: str = "") -> None:
        """批次处理进度"""
        percent = (current / total * 100) if total > 0 else 0
        bar_len = 30
        filled = int(bar_len * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        
        msg = f" - {message}" if message else ""
        progress_str = f"[{bar}] {current}/{total} ({percent:.1f}%){msg}"
        print(f"\r   {progress_str}  ", end="", flush=True)
        
        # 写入文件（只在完成时写入，避免大量重复日志）
        if current >= total:
            print()  # 换行
            self._write_to_file(LogLevel.INFO, f"批处理完成: {progress_str}")
    
    def separator(self, char: str = "=", length: int = 60) -> None:
        """输出分隔线"""
        line = char * length
        self._print(LogLevel.INFO, line)
    
    def section(self, title: str, icon: str = "🚀") -> None:
        """输出章节标题"""
        self.separator()
        self._print(LogLevel.INFO, f"{icon} {title}")
        self.separator()
    
    def success(self, message: str) -> None:
        """输出成功信息"""
        self._print(LogLevel.INFO, f"✅ {message}")
    
    def progress_item(self, current: int, total: int, status: str, name: str) -> None:
        """输出进度项"""
        status_emoji = {
            "passed": "✅",
            "failed": "❌",
            "error": "⚠️"
        }.get(status, "❓")
        self._print(LogLevel.INFO, f"   [{current}/{total}] {status_emoji} {name[:40]}")
    
    def close(self) -> None:
        """关闭日志器，释放资源"""
        if self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None
    
    def __del__(self) -> None:
        """析构时关闭文件"""
        self.close()


# 全局日志器实例
_logger: AILogger | None = None


def get_logger(verbose: bool = False) -> AILogger:
    """获取全局日志器"""
    global _logger
    if _logger is None:
        _logger = AILogger(verbose=verbose)
    elif verbose and not _logger.verbose:
        _logger.verbose = verbose
    return _logger


def set_logger(logger: AILogger) -> None:
    """设置全局日志器"""
    global _logger
    _logger = logger
