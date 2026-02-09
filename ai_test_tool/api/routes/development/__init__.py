"""
开发自测模块 API
该文件内容使用AI生成，注意识别准确性
将路由拆分为多个子模块以提高可维护性
"""

from fastapi import APIRouter

from .endpoints import router as endpoints_router
from .test_cases import router as test_cases_router
from .executions import router as executions_router
from .schemas import (
    GenerateTestsRequest,
    ExecuteTestsRequest,
    TestExecutionResult,
    UpdateTestCaseRequest,
)

# 创建主路由，合并所有子路由
router = APIRouter()

# 包含各子模块的路由
router.include_router(endpoints_router)
router.include_router(test_cases_router)
router.include_router(executions_router)


__all__ = [
    'router',
    'GenerateTestsRequest',
    'ExecuteTestsRequest',
    'TestExecutionResult',
    'UpdateTestCaseRequest',
]
