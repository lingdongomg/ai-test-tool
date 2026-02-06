"""
FastAPI 依赖注入模块

使用 FastAPI 原生 Depends 系统管理服务依赖，提供：
- 服务单例管理
- 数据库连接注入
- 配置注入
"""

from functools import lru_cache
from typing import Generator

from fastapi import Depends

from ..config.settings import AppConfig, get_config
from ..database import get_db_manager, DatabaseManager
from ..database.repository import (
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
    KnowledgeRepository,
    KnowledgeHistoryRepository,
    KnowledgeUsageRepository,
    ExecutionCaseRepository,
    AIInsightRepository,
    ProductionRequestRepository,
    HealthCheckExecutionRepository,
    HealthCheckResultRepository,
    ChatSessionRepository,
    ChatMessageRepository,
)


# =====================================================
# 配置依赖
# =====================================================

def get_app_config() -> AppConfig:
    """获取应用配置"""
    return get_config()


# =====================================================
# 数据库依赖
# =====================================================

def get_database() -> DatabaseManager:
    """获取数据库管理器"""
    return get_db_manager()


# =====================================================
# Repository 依赖（单例）
# =====================================================

@lru_cache()
def get_task_repository() -> TaskRepository:
    """获取任务仓库（单例）"""
    return TaskRepository()


@lru_cache()
def get_request_repository() -> RequestRepository:
    """获取请求仓库（单例）"""
    return RequestRepository()


@lru_cache()
def get_test_case_repository() -> TestCaseRepository:
    """获取测试用例仓库（单例）"""
    return TestCaseRepository()


@lru_cache()
def get_test_case_history_repository() -> TestCaseHistoryRepository:
    """获取测试用例历史仓库（单例）"""
    return TestCaseHistoryRepository()


@lru_cache()
def get_test_result_repository() -> TestResultRepository:
    """获取测试结果仓库（单例）"""
    return TestResultRepository()


@lru_cache()
def get_test_execution_repository() -> TestExecutionRepository:
    """获取测试执行仓库（单例）"""
    return TestExecutionRepository()


@lru_cache()
def get_report_repository() -> ReportRepository:
    """获取报告仓库（单例）"""
    return ReportRepository()


@lru_cache()
def get_api_tag_repository() -> ApiTagRepository:
    """获取API标签仓库（单例）"""
    return ApiTagRepository()


@lru_cache()
def get_api_endpoint_repository() -> ApiEndpointRepository:
    """获取API端点仓库（单例）"""
    return ApiEndpointRepository()


@lru_cache()
def get_test_scenario_repository() -> TestScenarioRepository:
    """获取测试场景仓库（单例）"""
    return TestScenarioRepository()


@lru_cache()
def get_scenario_step_repository() -> ScenarioStepRepository:
    """获取场景步骤仓库（单例）"""
    return ScenarioStepRepository()


@lru_cache()
def get_scenario_execution_repository() -> ScenarioExecutionRepository:
    """获取场景执行仓库（单例）"""
    return ScenarioExecutionRepository()


@lru_cache()
def get_step_result_repository() -> StepResultRepository:
    """获取步骤结果仓库（单例）"""
    return StepResultRepository()


@lru_cache()
def get_knowledge_repository() -> KnowledgeRepository:
    """获取知识库仓库（单例）"""
    return KnowledgeRepository()


@lru_cache()
def get_knowledge_history_repository() -> KnowledgeHistoryRepository:
    """获取知识历史仓库（单例）"""
    return KnowledgeHistoryRepository()


@lru_cache()
def get_knowledge_usage_repository() -> KnowledgeUsageRepository:
    """获取知识使用记录仓库（单例）"""
    return KnowledgeUsageRepository()


@lru_cache()
def get_execution_case_repository() -> ExecutionCaseRepository:
    """获取执行-用例关联仓库（单例）"""
    return ExecutionCaseRepository()


@lru_cache()
def get_ai_insight_repository() -> AIInsightRepository:
    """获取AI洞察仓库（单例）"""
    return AIInsightRepository()


@lru_cache()
def get_production_request_repository() -> ProductionRequestRepository:
    """获取生产请求监控仓库（单例）"""
    return ProductionRequestRepository()


@lru_cache()
def get_health_check_execution_repository() -> HealthCheckExecutionRepository:
    """获取健康检查执行仓库（单例）"""
    return HealthCheckExecutionRepository()


@lru_cache()
def get_health_check_result_repository() -> HealthCheckResultRepository:
    """获取健康检查结果仓库（单例）"""
    return HealthCheckResultRepository()


@lru_cache()
def get_chat_session_repository() -> ChatSessionRepository:
    """获取对话会话仓库（单例）"""
    return ChatSessionRepository()


@lru_cache()
def get_chat_message_repository() -> ChatMessageRepository:
    """获取对话消息仓库（单例）"""
    return ChatMessageRepository()


# =====================================================
# 服务依赖（延迟导入避免循环依赖）
# =====================================================

@lru_cache()
def get_ai_assistant_service():
    """获取 AI 助手服务（单例）"""
    from ..services.ai_assistant import AIAssistantService
    config = get_config()
    return AIAssistantService(verbose=config.llm.debug)


@lru_cache()
def get_production_monitor_service():
    """获取生产监控服务（单例）"""
    from ..services.production_monitor import ProductionMonitorService
    return ProductionMonitorService()


@lru_cache()
def get_intelligent_analysis_service():
    """获取智能分析服务（单例）"""
    from ..services.intelligent_analysis import IntelligentAnalysisService
    return IntelligentAnalysisService()


@lru_cache()
def get_endpoint_test_generator():
    """获取接口测试生成器（单例）"""
    from ..services.endpoint_test_generator import EndpointTestGenerator
    return EndpointTestGenerator()


@lru_cache()
def get_log_anomaly_detector():
    """获取日志异常检测器（单例）"""
    from ..services.log_anomaly_detector import LogAnomalyDetector
    return LogAnomalyDetector()


@lru_cache()
def get_knowledge_store():
    """获取知识库存储（单例）"""
    from ..knowledge import KnowledgeStore
    return KnowledgeStore()


@lru_cache()
def get_knowledge_retriever():
    """获取知识检索器（单例）"""
    from ..knowledge import KnowledgeRetriever
    return KnowledgeRetriever(get_knowledge_store())


@lru_cache()
def get_rag_context_builder():
    """获取 RAG 上下文构建器（单例）"""
    from ..knowledge import RAGContextBuilder
    return RAGContextBuilder()


@lru_cache()
def get_knowledge_learner():
    """获取知识学习器（单例）"""
    from ..knowledge import KnowledgeLearner
    from ..llm.chains import KnowledgeExtractionChain
    learner = KnowledgeLearner(get_knowledge_store())
    chain = KnowledgeExtractionChain()
    learner.set_llm_chain(chain)
    return learner


@lru_cache()
def get_log_anomaly_detector_service():
    """获取日志异常检测服务（单例）"""
    from ..services.log_anomaly_detector import LogAnomalyDetectorService
    return LogAnomalyDetectorService(verbose=True)


# =====================================================
# 清除缓存（用于测试）
# =====================================================

def clear_dependency_cache():
    """清除所有依赖缓存（用于测试）"""
    get_task_repository.cache_clear()
    get_request_repository.cache_clear()
    get_test_case_repository.cache_clear()
    get_test_case_history_repository.cache_clear()
    get_test_result_repository.cache_clear()
    get_test_execution_repository.cache_clear()
    get_report_repository.cache_clear()
    get_api_tag_repository.cache_clear()
    get_api_endpoint_repository.cache_clear()
    get_test_scenario_repository.cache_clear()
    get_scenario_step_repository.cache_clear()
    get_scenario_execution_repository.cache_clear()
    get_step_result_repository.cache_clear()
    get_knowledge_repository.cache_clear()
    get_knowledge_history_repository.cache_clear()
    get_knowledge_usage_repository.cache_clear()
    get_execution_case_repository.cache_clear()
    get_ai_insight_repository.cache_clear()
    get_production_request_repository.cache_clear()
    get_health_check_execution_repository.cache_clear()
    get_health_check_result_repository.cache_clear()
    get_ai_assistant_service.cache_clear()
    get_production_monitor_service.cache_clear()
    get_intelligent_analysis_service.cache_clear()
    get_endpoint_test_generator.cache_clear()
    get_log_anomaly_detector.cache_clear()
    get_knowledge_store.cache_clear()
    get_knowledge_retriever.cache_clear()
    get_rag_context_builder.cache_clear()
    get_knowledge_learner.cache_clear()
    get_log_anomaly_detector_service.cache_clear()
