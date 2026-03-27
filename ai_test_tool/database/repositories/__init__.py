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
    TestFolderRepository,
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

from .log_source import LogSourceRepository

__all__ = [
    'BaseRepository',
    # Core
    'TaskRepository', 'RequestRepository', 'ReportRepository',
    # Test
    'TestFolderRepository',
    'TestCaseRepository', 'TestCaseHistoryRepository',
    'TestResultRepository', 'TestExecutionRepository', 'ExecutionCaseRepository',
    # API
    'ApiTagRepository', 'ApiEndpointRepository',
    # Knowledge
    'KnowledgeRepository', 'KnowledgeHistoryRepository', 'KnowledgeUsageRepository',
    # Monitoring
    'AIInsightRepository', 'ProductionRequestRepository',
    'HealthCheckExecutionRepository', 'HealthCheckResultRepository',
    # System
    'ChatSessionRepository', 'ChatMessageRepository', 'SystemConfigRepository',
    # Log Source
    'LogSourceRepository',
]
