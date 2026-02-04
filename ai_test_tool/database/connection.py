"""
数据库连接管理
该文件内容使用AI生成，注意识别准确性
使用 SQLite 作为默认数据库，开箱即用
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any
from contextlib import contextmanager
from collections.abc import Generator


class DatabaseConfig:
    """数据库配置"""

    def __init__(
        self,
        db_path: str | None = None,
        timeout: float = 30.0,
        check_same_thread: bool = False,
    ) -> None:
        if db_path is None:
            db_path = os.getenv("SQLITE_DB_PATH", "")
            if not db_path:
                project_root = Path(__file__).parent.parent.parent
                data_dir = project_root / "data"
                data_dir.mkdir(exist_ok=True)
                db_path = str(data_dir / "ai_test_tool.db")
        
        self.db_path = db_path
        self.timeout = timeout
        self.check_same_thread = check_same_thread


class DatabaseManager:
    """
    数据库管理器（SQLite）
    
    特点：
    1. 开箱即用，无需配置外部数据库
    2. 线程安全，使用线程本地连接
    3. 自动创建数据库文件和表结构
    """

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        self.config = config or DatabaseConfig()
        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(
                self.config.db_path,
                timeout=self.config.timeout,
                check_same_thread=self.config.check_same_thread,
            )
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection

    def close(self) -> None:
        """关闭当前线程的连接"""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """获取数据库游标（上下文管理器）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> int:
        """执行SQL语句"""
        sql = sql.replace('%s', '?')
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.rowcount

    def execute_many(self, sql: str, params_list: list[tuple[Any, ...]]) -> int:
        """批量执行SQL语句"""
        sql = sql.replace('%s', '?')
        with self.get_cursor() as cursor:
            cursor.executemany(sql, params_list)
            return cursor.rowcount

    def fetch_one(
        self, sql: str, params: tuple[Any, ...] | None = None
    ) -> dict[str, Any] | None:
        """查询单条记录"""
        sql = sql.replace('%s', '?')
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(
        self, sql: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """查询多条记录"""
        sql = sql.replace('%s', '?')
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows] if rows else []

    def init_database(self) -> None:
        """初始化数据库（创建表）"""
        with self._lock:
            if self._initialized:
                return
            self._create_tables()
            self._initialized = True

    def _create_tables(self) -> None:
        """从 schema.sql 文件创建数据表"""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            schema_sql = schema_path.read_text(encoding='utf-8')
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.executescript(schema_sql)
                conn.commit()
            finally:
                cursor.close()
        else:
            # 回退到内置 SQL
            self._create_tables_inline()

    def _create_tables_inline(self) -> None:
        """内置建表 SQL（作为回退方案）"""
        tables_sql = [
            # 分析任务表
            """
            CREATE TABLE IF NOT EXISTS analysis_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                task_type TEXT DEFAULT 'log_analysis',
                log_file_path TEXT,
                log_file_size INTEGER,
                status TEXT DEFAULT 'pending',
                total_lines INTEGER DEFAULT 0,
                processed_lines INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                total_test_cases INTEGER DEFAULT 0,
                error_message TEXT,
                metadata TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 解析请求表
            """
            CREATE TABLE IF NOT EXISTS parsed_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT,
                headers TEXT,
                body TEXT,
                query_params TEXT,
                http_status INTEGER,
                response_time_ms REAL,
                response_body TEXT,
                has_error INTEGER DEFAULT 0,
                error_message TEXT,
                has_warning INTEGER DEFAULT 0,
                warning_message TEXT,
                curl_command TEXT,
                timestamp TEXT,
                raw_logs TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 接口标签表
            """
            CREATE TABLE IF NOT EXISTS api_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                color TEXT DEFAULT '#1890ff',
                parent_id INTEGER DEFAULT NULL,
                sort_order INTEGER DEFAULT 0,
                is_system INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 接口端点表
            """
            CREATE TABLE IF NOT EXISTS api_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                summary TEXT,
                parameters TEXT,
                request_body TEXT,
                responses TEXT,
                security TEXT,
                source_type TEXT DEFAULT 'manual',
                source_file TEXT,
                is_deprecated INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 接口-标签关联表
            """
            CREATE TABLE IF NOT EXISTS api_endpoint_tags (
                endpoint_id TEXT NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (endpoint_id, tag_id)
            )
            """,
            # 测试用例表
            """
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL UNIQUE,
                endpoint_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'normal',
                priority TEXT DEFAULT 'medium',
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                headers TEXT,
                body TEXT,
                query_params TEXT,
                expected_status_code INTEGER DEFAULT 200,
                expected_response TEXT,
                assertions TEXT,
                max_response_time_ms INTEGER DEFAULT 3000,
                tags TEXT,
                is_enabled INTEGER DEFAULT 1,
                is_ai_generated INTEGER DEFAULT 0,
                source_task_id TEXT,
                version INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 测试用例历史表
            """
            CREATE TABLE IF NOT EXISTS test_case_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                change_summary TEXT,
                snapshot TEXT NOT NULL,
                changed_fields TEXT,
                changed_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 测试执行批次表
            """
            CREATE TABLE IF NOT EXISTS test_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL UNIQUE,
                name TEXT,
                description TEXT,
                execution_type TEXT DEFAULT 'test',
                trigger_type TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'pending',
                base_url TEXT,
                environment TEXT,
                variables TEXT,
                headers TEXT,
                total_cases INTEGER DEFAULT 0,
                passed_cases INTEGER DEFAULT 0,
                failed_cases INTEGER DEFAULT 0,
                error_cases INTEGER DEFAULT 0,
                skipped_cases INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 执行-用例关联表
            """
            CREATE TABLE IF NOT EXISTS execution_cases (
                execution_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                order_index INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (execution_id, case_id)
            )
            """,
            # 测试结果表
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                result_type TEXT DEFAULT 'test',
                status TEXT NOT NULL,
                actual_status_code INTEGER,
                actual_response_time_ms REAL,
                actual_response_body TEXT,
                actual_headers TEXT,
                error_message TEXT,
                assertion_results TEXT,
                ai_analysis TEXT,
                executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 分析报告表
            """
            CREATE TABLE IF NOT EXISTS analysis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                report_type TEXT DEFAULT 'analysis',
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                format TEXT DEFAULT 'markdown',
                statistics TEXT,
                issues TEXT,
                recommendations TEXT,
                severity TEXT DEFAULT 'medium',
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 测试场景表
            """
            CREATE TABLE IF NOT EXISTS test_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                variables TEXT,
                setup_hooks TEXT,
                teardown_hooks TEXT,
                retry_on_failure INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                is_enabled INTEGER DEFAULT 1,
                created_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 场景步骤表
            """
            CREATE TABLE IF NOT EXISTS scenario_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                step_type TEXT DEFAULT 'request',
                method TEXT,
                url TEXT,
                headers TEXT,
                body TEXT,
                query_params TEXT,
                extractions TEXT,
                assertions TEXT,
                wait_time_ms INTEGER DEFAULT 0,
                condition TEXT,
                loop_config TEXT,
                timeout_ms INTEGER DEFAULT 30000,
                continue_on_failure INTEGER DEFAULT 0,
                is_enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (scenario_id, step_id)
            )
            """,
            # 场景执行记录表
            """
            CREATE TABLE IF NOT EXISTS scenario_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL UNIQUE,
                scenario_id TEXT NOT NULL,
                trigger_type TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'pending',
                base_url TEXT,
                environment TEXT,
                variables TEXT,
                total_steps INTEGER DEFAULT 0,
                passed_steps INTEGER DEFAULT 0,
                failed_steps INTEGER DEFAULT 0,
                skipped_steps INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 步骤执行结果表
            """
            CREATE TABLE IF NOT EXISTS step_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                status TEXT NOT NULL,
                request_url TEXT,
                request_headers TEXT,
                request_body TEXT,
                response_status_code INTEGER,
                response_headers TEXT,
                response_body TEXT,
                response_time_ms REAL,
                extracted_variables TEXT,
                assertion_results TEXT,
                error_message TEXT,
                executed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            for sql in tables_sql:
                cursor.execute(sql)
            conn.commit()
        finally:
            cursor.close()


# 全局数据库管理器实例
_db_manager: DatabaseManager | None = None


def get_db_manager(config: DatabaseConfig | None = None) -> DatabaseManager:
    """获取全局数据库管理器"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
        _db_manager.init_database()
    return _db_manager


def set_db_manager(manager: DatabaseManager) -> None:
    """设置全局数据库管理器"""
    global _db_manager
    _db_manager = manager
