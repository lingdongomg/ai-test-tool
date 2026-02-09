"""
分析策略包

导入所有策略模块以触发 @strategy 装饰器注册
"""

from . import (  # noqa: F401
    error,
    performance,
    security,
    api,
    root_cause,
    cot,
    react,
    causal,
    alert,
    health,
)
