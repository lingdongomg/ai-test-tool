"""
FastAPI 应用创建
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import tags, endpoints, scenarios, executions, imports, analysis, versions, tasks, test_cases


def setup_logging() -> logging.Logger:
    """设置 API 日志"""
    # 创建日志目录
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志文件名
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"api_{date_str}.log"
    
    # 配置日志
    logger = logging.getLogger("ai_test_tool.api")
    logger.setLevel(logging.DEBUG)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # 添加处理器
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    # 设置日志
    logger = setup_logging()
    logger.info("正在创建 FastAPI 应用...")
    
    app = FastAPI(
        title="AI Test Tool API",
        description="智能API测试工具后台服务",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"请求异常: {request.method} {request.url.path} - {type(exc).__name__}: {exc}")
        import traceback
        logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(exc)}"}
        )
    
    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.debug(f"请求: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.debug(f"响应: {request.method} {request.url.path} - {response.status_code}")
        return response
    
    # 注册路由
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["分析任务"])
    app.include_router(tags.router, prefix="/api/v1/tags", tags=["标签管理"])
    app.include_router(endpoints.router, prefix="/api/v1/endpoints", tags=["接口管理"])
    app.include_router(scenarios.router, prefix="/api/v1/scenarios", tags=["测试场景"])
    app.include_router(executions.router, prefix="/api/v1/executions", tags=["执行记录"])
    app.include_router(imports.router, prefix="/api/v1/imports", tags=["文档导入"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["智能分析"])
    app.include_router(versions.router, prefix="/api/v1/versions", tags=["版本管理"])
    app.include_router(test_cases.router, tags=["测试用例管理"])
    
    @app.get("/", tags=["健康检查"])
    async def root():
        return {"message": "AI Test Tool API", "version": "1.0.0"}
    
    @app.get("/health", tags=["健康检查"])
    async def health():
        return {"status": "healthy"}
    
    logger.info("FastAPI 应用创建完成")
    return app
