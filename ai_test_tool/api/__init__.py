"""
FastAPI 后台服务模块
提供 REST API 接口
"""

from .app import create_app
from .routes import dashboard, development, monitoring, insights, ai_assistant, imports

__all__ = [
    "create_app",
    "dashboard",
    "development",
    "monitoring",
    "insights",
    "ai_assistant",
    "imports"
]
