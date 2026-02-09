"""
数据模型包
该文件内容使用AI生成，注意识别准确性
导出所有模型类以保持向后兼容
"""

# 基类和枚举
from .base import (
    BaseModel,
    TaskStatus, TaskType,
    TestCaseCategory, TestCasePriority, TestResultStatus,
    ReportType, TriggerType, ExecutionStatus, ExecutionType, ResultType,
    EndpointSourceType, ScenarioStepType, ScenarioStatus, ChangeType,
    KnowledgeType, KnowledgeStatus, KnowledgeSource,
)

# 任务相关模型
from .task import AnalysisTask, ParsedRequestRecord, AnalysisReport

# 测试相关模型
from .test import TestCaseRecord, TestCaseHistory, TestExecution, TestResultRecord

# API 相关模型
from .api import ApiTag, ApiEndpoint

# 场景相关模型
from .scenario import TestScenario, ScenarioStep, ScenarioExecution, StepResult

# 知识库相关模型
from .knowledge import KnowledgeEntry, KnowledgeHistory, KnowledgeUsage

# 监控相关模型
from .monitoring import (
    AIInsight, InsightSeverity,
    ProductionRequest, RequestSource,
    HealthCheckExecution, HealthCheckResult, HealthCheckStatus,
)


# =====================================================
# 兼容性别名（保持向后兼容）
# =====================================================

class ScheduledTask:
    """已废弃：定时任务模型（功能已移除）"""
    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("ScheduledTask 已废弃，请使用外部调度系统")


class TestCaseVersion:
    """已废弃：测试用例版本模型（已合并到 TestCaseHistory）"""
    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("TestCaseVersion 已废弃，请使用 TestCaseHistory")


class TestCaseChangeLog:
    """已废弃：测试用例变更日志模型（已合并到 TestCaseHistory）"""
    def __init__(self, *args, **kwargs):
        raise DeprecationWarning("TestCaseChangeLog 已废弃，请使用 TestCaseHistory")


__all__ = [
    # 基类和枚举
    'BaseModel',
    'TaskStatus', 'TaskType',
    'TestCaseCategory', 'TestCasePriority', 'TestResultStatus',
    'ReportType', 'TriggerType', 'ExecutionStatus', 'ExecutionType', 'ResultType',
    'EndpointSourceType', 'ScenarioStepType', 'ScenarioStatus', 'ChangeType',
    'KnowledgeType', 'KnowledgeStatus', 'KnowledgeSource',
    # 模型
    'AnalysisTask', 'ParsedRequestRecord', 'AnalysisReport',
    'TestCaseRecord', 'TestCaseHistory', 'TestExecution', 'TestResultRecord',
    'ApiTag', 'ApiEndpoint',
    'TestScenario', 'ScenarioStep', 'ScenarioExecution', 'StepResult',
    'KnowledgeEntry', 'KnowledgeHistory', 'KnowledgeUsage',
    # 监控相关
    'AIInsight', 'InsightSeverity',
    'ProductionRequest', 'RequestSource',
    'HealthCheckExecution', 'HealthCheckResult', 'HealthCheckStatus',
    # 兼容性别名
    'ScheduledTask', 'TestCaseVersion', 'TestCaseChangeLog',
]
