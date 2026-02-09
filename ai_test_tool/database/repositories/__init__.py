"""
Repository 包

导出所有 Repository 类，保持向后兼容
"""

from .base import BaseRepository

from .core import (
    TaskRepository,
    RequestRepository,
    ReportRepository,
)

from .test import (
    TestCaseRepository,
    TestCaseHistoryRepository,
    TestResultRepository,
    TestExecutionRepository,
    ExecutionCaseRepository,
)

from .api import (
    ApiTagRepository,
    ApiEndpointRepository,
)

from .scenario import (
    TestScenarioRepository,
    ScenarioStepRepository,
    ScenarioExecutionRepository,
    StepResultRepository,
)

from .knowledge import (
    KnowledgeRepository,
    KnowledgeHistoryRepository,
    KnowledgeUsageRepository,
)

from .monitoring import (
    AIInsightRepository,
    ProductionRequestRepository,
    HealthCheckExecutionRepository,
    HealthCheckResultRepository,
)

from .system import (
    ChatSessionRepository,
    ChatMessageRepository,
    SystemConfigRepository,
)

__all__ = [
    'BaseRepository',
    # Core
    'TaskRepository', 'RequestRepository', 'ReportRepository',
    # Test
    'TestCaseRepository', 'TestCaseHistoryRepository',
    'TestResultRepository', 'TestExecutionRepository', 'ExecutionCaseRepository',
    # API
    'ApiTagRepository', 'ApiEndpointRepository',
    # Scenario
    'TestScenarioRepository', 'ScenarioStepRepository',
    'ScenarioExecutionRepository', 'StepResultRepository',
    # Knowledge
    'KnowledgeRepository', 'KnowledgeHistoryRepository', 'KnowledgeUsageRepository',
    # Monitoring
    'AIInsightRepository', 'ProductionRequestRepository',
    'HealthCheckExecutionRepository', 'HealthCheckResultRepository',
    # System
    'ChatSessionRepository', 'ChatMessageRepository', 'SystemConfigRepository',
]
