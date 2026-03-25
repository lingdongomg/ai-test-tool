"""
知识库 V2 数据库迁移脚本
扩展知识类型、新增字段（sub_category, evidence）
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATION_SQL = """
-- 1. 新增 sub_category 字段
ALTER TABLE knowledge_entries ADD COLUMN sub_category TEXT DEFAULT '';

-- 2. 新增 evidence 字段
ALTER TABLE knowledge_entries ADD COLUMN evidence TEXT DEFAULT '';
"""

# 旧 CHECK 约束在 SQLite 中无法直接修改，
# 但 SQLite 的 CHECK 约束只在 INSERT/UPDATE 时校验，
# 而 ALTER TABLE ADD COLUMN 不受影响。
# 对于 type 和 source 列的扩展值，SQLite 3.35+ 支持 ALTER TABLE DROP/ADD CHECK，
# 但更简单的方式是重建表。这里我们通过关闭 CHECK 的严格模式来处理：
# 实际上 SQLite 的 CHECK 约束写在 CREATE TABLE 里，ALTER TABLE 无法修改它。
# 不过好在 SQLite 对已有数据的 CHECK 只在写入时校验。
# 我们需要确保新类型值能写入——最佳做法是重建表。

REBUILD_TABLE_SQL = """
-- 备份数据
CREATE TABLE IF NOT EXISTS knowledge_entries_backup AS SELECT * FROM knowledge_entries;

-- 删除旧表
DROP TABLE IF EXISTS knowledge_entries;

-- 创建新表（扩展 CHECK 约束）
CREATE TABLE knowledge_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('project_config', 'business_rule', 'module_context', 'test_experience', 'auth_config', 'error_pattern', 'performance_baseline', 'api_dependency', 'security_rule', 'env_config')),
    category TEXT DEFAULT '',
    sub_category TEXT DEFAULT '',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT DEFAULT '',
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'pending', 'archived')),
    source TEXT DEFAULT 'manual' CHECK(source IN ('manual', 'log_learning', 'test_learning', 'realtime_log', 'rule_engine', 'api_doc_sync')),
    source_ref TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT '',
    version INTEGER DEFAULT 1
);

-- 恢复数据（新字段取默认值）
INSERT INTO knowledge_entries (
    id, knowledge_id, type, category, title, content, scope, priority,
    status, source, source_ref, metadata, created_at, updated_at, created_by, version
)
SELECT
    id, knowledge_id, type, category, title, content, scope, priority,
    status, source, source_ref, metadata, created_at, updated_at, created_by, version
FROM knowledge_entries_backup;

-- 重建索引
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_type ON knowledge_entries(type);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_status ON knowledge_entries(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_scope ON knowledge_entries(scope);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_priority ON knowledge_entries(priority);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source ON knowledge_entries(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_created_at ON knowledge_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_type_status ON knowledge_entries(type, status);

-- 重建外键引用的标签表（如果存在）
-- knowledge_tags 通过 ON DELETE CASCADE 关联，需要确保外键完整性
-- SQLite 的 FOREIGN KEY 在这种重建场景下需要重新启用

-- 清理备份
DROP TABLE IF EXISTS knowledge_entries_backup;
"""

# 知识关系表（用于记录去重合并关系）
KNOWLEDGE_RELATIONS_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK(relation_type IN ('merged_from', 'replaced_by', 'conflicts_with', 'depends_on')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id, relation_type)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_relations_source ON knowledge_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_relations_target ON knowledge_relations(target_id);
"""


def run_migration(db_path: str) -> bool:
    """
    执行知识库 V2 迁移

    Args:
        db_path: SQLite 数据库文件路径

    Returns:
        是否成功
    """
    if not Path(db_path).exists():
        logger.info(f"数据库文件不存在: {db_path}，跳过迁移（将使用新 schema 创建）")
        return True

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # 检查是否已迁移（sub_category 字段是否存在）
        cursor.execute("PRAGMA table_info(knowledge_entries)")
        columns = {row[1] for row in cursor.fetchall()}

        if "sub_category" in columns:
            logger.info("知识库 V2 迁移已完成，跳过")
            # 仍然确保关系表存在
            conn.executescript(KNOWLEDGE_RELATIONS_SQL)
            conn.commit()
            return True

        logger.info("开始知识库 V2 数据库迁移...")

        # 关闭外键约束以便重建表
        cursor.execute("PRAGMA foreign_keys = OFF")

        # 重建表
        conn.executescript(REBUILD_TABLE_SQL)

        # 创建关系表
        conn.executescript(KNOWLEDGE_RELATIONS_SQL)

        # 重新启用外键约束
        cursor.execute("PRAGMA foreign_keys = ON")

        conn.commit()
        logger.info("知识库 V2 数据库迁移完成")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"知识库 V2 迁移失败: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/ai_test_tool.db"
    success = run_migration(db_path)
    sys.exit(0 if success else 1)
