"""
API 路由模块

按三大场景组织：
- development: 开发自测
- monitoring: 线上监控
- insights: 日志洞察
- dashboard: 首页仪表盘
- ai_assistant: AI 助手
- imports: 接口文档导入
"""

# 核心路由
from . import dashboard
from . import development
from . import monitoring
from . import insights
from . import ai_assistant
from . import imports
from . import tasks

# 任务取消检查函数
from .tasks import is_task_cancelled

__all__ = [
    "dashboard",
    "development",
    "monitoring",
    "insights",
    "ai_assistant",
    "imports",
    "tasks",
    "is_task_cancelled"
]
