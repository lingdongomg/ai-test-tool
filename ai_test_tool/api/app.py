"""
FastAPI 应用创建
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import tags, endpoints, scenarios, executions, imports, analysis, versions, tasks


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
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
    
    # 注册路由
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["分析任务"])
    app.include_router(tags.router, prefix="/api/v1/tags", tags=["标签管理"])
    app.include_router(endpoints.router, prefix="/api/v1/endpoints", tags=["接口管理"])
    app.include_router(scenarios.router, prefix="/api/v1/scenarios", tags=["测试场景"])
    app.include_router(executions.router, prefix="/api/v1/executions", tags=["执行记录"])
    app.include_router(imports.router, prefix="/api/v1/imports", tags=["文档导入"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["智能分析"])
    app.include_router(versions.router, prefix="/api/v1/versions", tags=["版本管理"])
    
    @app.get("/", tags=["健康检查"])
    async def root():
        return {"message": "AI Test Tool API", "version": "1.0.0"}
    
    @app.get("/health", tags=["健康检查"])
    async def health():
        return {"status": "healthy"}
    
    return app
