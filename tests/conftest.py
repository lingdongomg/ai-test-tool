# 该文件内容使用AI生成，注意识别准确性
"""
测试配置文件
"""

import pytest
import sys
import os

# 将项目根目录添加到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def test_db():
    """测试数据库fixture（内存数据库）"""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def mock_config():
    """模拟配置"""
    from unittest.mock import Mock
    config = Mock()
    config.security.cors_origins_list = ["*"]
    config.security.cors_allow_credentials = True
    config.security.debug = True
    config.security.is_production = False
    config.security.environment = "test"
    config.llm.debug = False
    config.task.max_workers = 2
    return config
