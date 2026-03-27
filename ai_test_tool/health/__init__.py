# 该文件内容使用AI生成，注意识别准确性
"""
健康度模型模块（精简版）

仅保留 HealthStatus 枚举和基础数据模型，
引擎和检查器功能已移除（由 ProductionMonitorService 直接提供）。
"""

from .models import HealthStatus

__all__ = [
    "HealthStatus",
]
