"""
该文件内容使用AI生成，注意识别准确性

FastAPI 应用创建
支持结构化 JSON 日志、TraceId 透传、请求计时
"""

import logging
import json
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config.settings import get_config
from ..exceptions import (
    AITestToolError,
    ValidationError,
    NotFoundError,
    FileUploadError,
    DatabaseError,
    LLMError,
    ExternalServiceError,
    get_http_status
)
from .routes import dashboard, development, monitoring, insights, ai_assistant, imports, tasks, knowledge, analysis, log_stream


class JSONLogFormatter(logging.Formatter):
    """结构化 JSON 日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 附加上下文（如 request_id）
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_entry["method"] = record.method
        if hasattr(record, "path"):
            log_entry["path"] = record.path
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    """设置 API 结构化日志"""
    # 创建日志目录
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日志文件名
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"api_{date_str}.log"

    # 配置日志
    logger = logging.getLogger("ai_test_tool.api")
    logger.setLevel(logging.DEBUG)

    # 文件处理器 - JSON 结构化
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONLogFormatter())

    # 控制台处理器 - 人类可读格式
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

    # 加载配置
    config = get_config()
    security_config = config.security

    app = FastAPI(
        title="AI Test Tool API",
        description="智能API测试工具后台服务",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS 配置 - 使用安全配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=security_config.cors_origins_list,
        allow_credentials=security_config.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    # ==================== 异常处理器 ====================

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """处理验证错误 - 400"""
        logger.warning(f"验证错误: {request.method} {request.url.path} - {exc.message}")
        return JSONResponse(
            status_code=400,
            content=exc.to_dict(include_details=True)
        )

    @app.exception_handler(FileUploadError)
    async def file_upload_error_handler(request: Request, exc: FileUploadError):
        """处理文件上传错误 - 400"""
        logger.warning(f"文件上传错误: {request.method} {request.url.path} - {exc.message}")
        return JSONResponse(
            status_code=400,
            content=exc.to_dict(include_details=True)
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        """处理资源不存在错误 - 404"""
        logger.warning(f"资源不存在: {request.method} {request.url.path} - {exc.message}")
        return JSONResponse(
            status_code=404,
            content=exc.to_dict(include_details=True)
        )

    @app.exception_handler(AITestToolError)
    async def custom_error_handler(request: Request, exc: AITestToolError):
        """处理自定义异常"""
        status_code = get_http_status(exc)
        logger.error(f"业务异常 [{exc.code}]: {request.method} {request.url.path} - {exc.message}")
        # 生产环境不暴露详细信息
        include_details = security_config.debug or not security_config.is_production
        return JSONResponse(
            status_code=status_code,
            content=exc.to_dict(include_details=include_details)
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理 - 处理未预期的异常"""
        import traceback
        logger.error(f"未处理异常: {request.method} {request.url.path} - {type(exc).__name__}: {exc}")
        logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")

        # 生产环境不暴露详细错误信息
        if security_config.is_production and not security_config.debug:
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误，请稍后重试"
                }
            )

        # 开发环境返回详细错误信息
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "details": {
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc() if security_config.debug else None
                }
            }
        )

    # 请求日志中间件 - TraceId + 计时
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)",
            extra=log_extra,
        )
        return response

    # ==================== API 路由 ====================
    # 首页仪表盘
    app.include_router(dashboard.router, prefix="/api/v2/dashboard", tags=["仪表盘"])
    # 场景一：开发自测
    app.include_router(development.router, prefix="/api/v2/development", tags=["开发自测"])
    # 场景二：线上监控
    app.include_router(monitoring.router, prefix="/api/v2/monitoring", tags=["线上监控"])
    # 场景三：日志洞察
    app.include_router(insights.router, prefix="/api/v2/insights", tags=["日志洞察"])
    # AI 助手
    app.include_router(ai_assistant.router, prefix="/api/v2/ai", tags=["AI助手"])
    # 接口文档导入
    app.include_router(imports.router, prefix="/api/v2/imports", tags=["文档导入"])
    # 分析任务（日志解析相关）
    app.include_router(tasks.router, prefix="/api/v2/tasks", tags=["分析任务"])
    # 知识库管理
    app.include_router(knowledge.router, prefix="/api/v2/knowledge", tags=["知识库"])
    # 场景四：智能分析（路由分发）
    app.include_router(analysis.router, prefix="/api/v2/analysis", tags=["智能分析"])
    # 实时日志流
    app.include_router(log_stream.router, prefix="/api/v2/log-stream", tags=["实时日志"])

    @app.get("/", tags=["健康检查"])
    async def root():
        return {"message": "AI Test Tool API", "version": "2.0.0"}

    @app.get("/health", tags=["健康检查"])
    async def health():
        """增强健康检查 - 包含数据库连通性和基本指标"""
        from ..database import get_db_manager
        health_detail: dict = {"status": "healthy", "version": "2.0.0"}
        try:
            db = get_db_manager()
            db.fetch_one("SELECT 1")
            health_detail["database"] = "ok"
        except Exception:
            health_detail["database"] = "error"
            health_detail["status"] = "degraded"
        return health_detail

    # H15: 僵尸任务恢复 - 启动时将 RUNNING 状态的任务标记为 FAILED
    def _recover_zombie_tasks():
        """将服务器重启前卡在 RUNNING 状态的任务标记为失败"""
        try:
            from ..database import get_db_manager
            db = get_db_manager()
            count = db.execute(
                "UPDATE analysis_tasks SET status = 'failed', "
                "error_message = '服务器重启，任务被中断' "
                "WHERE status IN ('running', 'pending')"
            )
            if count > 0:
                logger.warning(f"僵尸任务恢复: 将 {count} 个卡死任务标记为 failed")
        except Exception as e:
            logger.error(f"僵尸任务恢复失败: {e}")

    _recover_zombie_tasks()

    logger.info(f"FastAPI 应用创建完成 (环境: {security_config.environment})")
    return app
