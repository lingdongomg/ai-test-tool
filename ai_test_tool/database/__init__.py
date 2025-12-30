"""
数据库模块
提供MySQL数据库连接和数据持久化功能
"""

from .connection import DatabaseManager, get_db_manager
from .models import (
    AnalysisTask,
    ParsedRequestRecord,
    TestCaseRecord,
    TestResultRecord,
    AnalysisReport
)
from .repository import (
    TaskRepository,
    RequestRepository,
    TestCaseRepository,
    TestResultRepository,
    ReportRepository
)

__all__ = [
    "DatabaseManager",
    "get_db_manager",
    "AnalysisTask",
    "ParsedRequestRecord",
    "TestCaseRecord",
    "TestResultRecord",
    "AnalysisReport",
    "TaskRepository",
    "RequestRepository",
    "TestCaseRepository",
    "TestResultRepository",
    "ReportRepository"
]
