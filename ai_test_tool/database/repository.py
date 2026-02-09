"""
数据仓库层 - 兼容层

所有 Repository 已拆分至 database/repositories/ 包。
本文件保留 re-export 以保持向后兼容。
"""

# Re-export all repositories from the new package
from .repositories import (  # noqa: F401
    BaseRepository,
    TaskRepository,
    RequestRepository,
    ReportRepository,
    TestCaseRepository,
    TestCaseHistoryRepository,
    TestResultRepository,
    TestExecutionRepository,
    ExecutionCaseRepository,
    ApiTagRepository,
    ApiEndpointRepository,
    TestScenarioRepository,
    ScenarioStepRepository,
    ScenarioExecutionRepository,
    StepResultRepository,
    KnowledgeRepository,
    KnowledgeHistoryRepository,
    KnowledgeUsageRepository,
    AIInsightRepository,
    ProductionRequestRepository,
    HealthCheckExecutionRepository,
    HealthCheckResultRepository,
    ChatSessionRepository,
    ChatMessageRepository,
    SystemConfigRepository,
)
