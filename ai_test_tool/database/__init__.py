"""
数据库模块
该文件内容使用AI生成，注意识别准确性
"""

from .connection import (
    DatabaseConfig,
    DatabaseManager,
    get_db_manager,
    set_db_manager,
)

from .models import (
    # 基类
    BaseModel,
    # 枚举
    TaskStatus,
    TaskType,
    TestCaseCategory,
    TestCasePriority,
    TestResultStatus,
    ReportType,
    TriggerType,
    ExecutionStatus,
    ExecutionType,
    ResultType,
    EndpointSourceType,
    StepType,
    ScenarioStatus,
    ChangeType,
    # 模型
    AnalysisTask,
    ParsedRequestRecord,
    ApiTag,
    ApiEndpoint,
    TestCaseRecord,
    TestCaseHistory,
    TestExecution,
    TestResultRecord,
    AnalysisReport,
    TestScenario,
    ScenarioStep,
    ScenarioExecution,
    StepResult,
)

from .repository import (
    # 基类
    BaseRepository,
    # 仓库
    TaskRepository,
    RequestRepository,
    TestCaseRepository,
    TestCaseHistoryRepository,
    TestResultRepository,
    TestExecutionRepository,
    ReportRepository,
    ApiTagRepository,
    ApiEndpointRepository,
    TestScenarioRepository,
    ScenarioStepRepository,
    ScenarioExecutionRepository,
    StepResultRepository,
)


__all__ = [
    # 连接
    'DatabaseConfig',
    'DatabaseManager',
    'get_db_manager',
    'set_db_manager',
    # 枚举
    'TaskStatus',
    'TaskType',
    'TestCaseCategory',
    'TestCasePriority',
    'TestResultStatus',
    'ReportType',
    'TriggerType',
    'ExecutionStatus',
    'ExecutionType',
    'ResultType',
    'EndpointSourceType',
    'StepType',
    'ScenarioStatus',
    'ChangeType',
    # 模型
    'BaseModel',
    'AnalysisTask',
    'ParsedRequestRecord',
    'ApiTag',
    'ApiEndpoint',
    'TestCaseRecord',
    'TestCaseHistory',
    'TestExecution',
    'TestResultRecord',
    'AnalysisReport',
    'TestScenario',
    'ScenarioStep',
    'ScenarioExecution',
    'StepResult',
    # 仓库
    'BaseRepository',
    'TaskRepository',
    'RequestRepository',
    'TestCaseRepository',
    'TestCaseHistoryRepository',
    'TestResultRepository',
    'TestExecutionRepository',
    'ReportRepository',
    'ApiTagRepository',
    'ApiEndpointRepository',
    'TestScenarioRepository',
    'ScenarioStepRepository',
    'ScenarioExecutionRepository',
    'StepResultRepository',
]
