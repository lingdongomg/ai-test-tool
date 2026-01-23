"""
数据库模块
提供 SQLite 数据库连接和数据持久化功能（开箱即用）
"""

from .connection import DatabaseManager, get_db_manager
from .models import (
    AnalysisTask,
    TaskStatus,
    ParsedRequestRecord,
    TestCaseRecord,
    TestCaseCategory,
    TestCasePriority,
    TestResultRecord,
    TestResultStatus,
    AnalysisReport,
    ReportType,
    # 新增模型
    ApiTag,
    ApiEndpoint,
    EndpointSourceType,
    TestScenario,
    ScenarioStep,
    StepType,
    ScenarioExecution,
    ScenarioStatus,
    TriggerType,
    StepResult,
    ScheduledTask
)
from .repository import (
    TaskRepository,
    RequestRepository,
    TestCaseRepository,
    TestResultRepository,
    ReportRepository
)

__all__ = [
    # 连接管理
    "DatabaseManager",
    "get_db_manager",
    # 基础模型
    "AnalysisTask",
    "TaskStatus",
    "ParsedRequestRecord",
    "TestCaseRecord",
    "TestCaseCategory",
    "TestCasePriority",
    "TestResultRecord",
    "TestResultStatus",
    "AnalysisReport",
    "ReportType",
    # 标签和端点模型
    "ApiTag",
    "ApiEndpoint",
    "EndpointSourceType",
    # 场景模型
    "TestScenario",
    "ScenarioStep",
    "StepType",
    "ScenarioExecution",
    "ScenarioStatus",
    "TriggerType",
    "StepResult",
    "ScheduledTask",
    # 仓库
    "TaskRepository",
    "RequestRepository",
    "TestCaseRepository",
    "TestResultRepository",
    "ReportRepository"
]
