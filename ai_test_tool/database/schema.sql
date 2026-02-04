-- AI Test Tool 数据库表结构 (SQLite)
-- 该文件内容使用AI生成，注意识别准确性
-- 重构版本：精简表结构，移除冗余表

-- 开启外键约束
PRAGMA foreign_keys = ON;

-- =====================================================
-- 核心业务表
-- =====================================================

-- 分析任务表
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    task_type TEXT DEFAULT 'log_analysis' CHECK(task_type IN ('log_analysis', 'test_generation', 'report')),
    log_file_path TEXT,
    log_file_size INTEGER,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed')),
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
);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status ON analysis_tasks(status);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_task_type ON analysis_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_created_at ON analysis_tasks(created_at);

-- 解析请求表
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES analysis_tasks(task_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_parsed_requests_task_id ON parsed_requests(task_id);
CREATE INDEX IF NOT EXISTS idx_parsed_requests_method ON parsed_requests(method);
CREATE INDEX IF NOT EXISTS idx_parsed_requests_category ON parsed_requests(category);
CREATE INDEX IF NOT EXISTS idx_parsed_requests_http_status ON parsed_requests(http_status);
CREATE INDEX IF NOT EXISTS idx_parsed_requests_has_error ON parsed_requests(has_error);

-- =====================================================
-- 接口管理表
-- =====================================================

-- 接口标签表
CREATE TABLE IF NOT EXISTS api_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    color TEXT DEFAULT '#1890ff',
    parent_id INTEGER DEFAULT NULL,
    sort_order INTEGER DEFAULT 0,
    is_system INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES api_tags(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_api_tags_parent_id ON api_tags(parent_id);
CREATE INDEX IF NOT EXISTS idx_api_tags_sort_order ON api_tags(sort_order);

-- 接口端点表
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
    source_type TEXT DEFAULT 'manual' CHECK(source_type IN ('swagger', 'postman', 'manual')),
    source_file TEXT,
    is_deprecated INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_method ON api_endpoints(method);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_path ON api_endpoints(path);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_source_type ON api_endpoints(source_type);

-- 接口-标签关联表
CREATE TABLE IF NOT EXISTS api_endpoint_tags (
    endpoint_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (endpoint_id, tag_id),
    FOREIGN KEY (tag_id) REFERENCES api_tags(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_api_endpoint_tags_tag_id ON api_endpoint_tags(tag_id);

-- =====================================================
-- 测试用例表
-- =====================================================

-- 测试用例表（以接口为维度）
CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL UNIQUE,
    endpoint_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'normal' CHECK(category IN ('normal', 'boundary', 'exception', 'performance', 'security')),
    priority TEXT DEFAULT 'medium' CHECK(priority IN ('high', 'medium', 'low')),
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
);
CREATE INDEX IF NOT EXISTS idx_test_cases_endpoint_id ON test_cases(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category);
CREATE INDEX IF NOT EXISTS idx_test_cases_priority ON test_cases(priority);
CREATE INDEX IF NOT EXISTS idx_test_cases_is_enabled ON test_cases(is_enabled);

-- 测试用例历史表（合并版本和变更日志）
CREATE TABLE IF NOT EXISTS test_case_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    change_type TEXT NOT NULL CHECK(change_type IN ('create', 'update', 'delete', 'restore', 'enable', 'disable')),
    change_summary TEXT,
    snapshot TEXT NOT NULL,
    changed_fields TEXT,
    changed_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_case_history_case_id ON test_case_history(case_id);
CREATE INDEX IF NOT EXISTS idx_test_case_history_version ON test_case_history(case_id, version);
CREATE INDEX IF NOT EXISTS idx_test_case_history_created_at ON test_case_history(created_at);

-- =====================================================
-- 测试执行表
-- =====================================================

-- 测试执行批次表
CREATE TABLE IF NOT EXISTS test_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    name TEXT,
    description TEXT,
    execution_type TEXT DEFAULT 'test' CHECK(execution_type IN ('test', 'health_check', 'scenario')),
    trigger_type TEXT DEFAULT 'manual' CHECK(trigger_type IN ('manual', 'scheduled', 'pipeline', 'api')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'cancelled', 'failed')),
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
);
CREATE INDEX IF NOT EXISTS idx_test_executions_status ON test_executions(status);
CREATE INDEX IF NOT EXISTS idx_test_executions_execution_type ON test_executions(execution_type);
CREATE INDEX IF NOT EXISTS idx_test_executions_trigger_type ON test_executions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_test_executions_started_at ON test_executions(started_at);

-- 执行-用例关联表
CREATE TABLE IF NOT EXISTS execution_cases (
    execution_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (execution_id, case_id)
);
CREATE INDEX IF NOT EXISTS idx_execution_cases_case_id ON execution_cases(case_id);

-- 测试结果表（单个测试用例的执行结果）
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    result_type TEXT DEFAULT 'test' CHECK(result_type IN ('test', 'health_check', 'scenario_step')),
    status TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'error', 'skipped')),
    actual_status_code INTEGER,
    actual_response_time_ms REAL,
    actual_response_body TEXT,
    actual_headers TEXT,
    error_message TEXT,
    assertion_results TEXT,
    ai_analysis TEXT,
    executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_results_case_id ON test_results(case_id);
CREATE INDEX IF NOT EXISTS idx_test_results_execution_id ON test_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_test_results_result_type ON test_results(result_type);
CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results(status);
CREATE INDEX IF NOT EXISTS idx_test_results_executed_at ON test_results(executed_at);

-- =====================================================
-- 分析报告表
-- =====================================================

-- 分析报告表
CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    report_type TEXT DEFAULT 'analysis' CHECK(report_type IN ('analysis', 'test', 'summary', 'insight')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    format TEXT DEFAULT 'markdown' CHECK(format IN ('markdown', 'html', 'json')),
    statistics TEXT,
    issues TEXT,
    recommendations TEXT,
    severity TEXT DEFAULT 'medium' CHECK(severity IN ('high', 'medium', 'low')),
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES analysis_tasks(task_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_task_id ON analysis_reports(task_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_report_type ON analysis_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_severity ON analysis_reports(severity);

-- =====================================================
-- 测试场景表
-- =====================================================

-- 测试场景表
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
);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_is_enabled ON test_scenarios(is_enabled);

-- 场景步骤表
CREATE TABLE IF NOT EXISTS scenario_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    step_type TEXT DEFAULT 'request' CHECK(step_type IN ('request', 'wait', 'condition', 'loop', 'extract', 'assert')),
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
    UNIQUE (scenario_id, step_id),
    FOREIGN KEY (scenario_id) REFERENCES test_scenarios(scenario_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_scenario_steps_scenario_id ON scenario_steps(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_steps_step_order ON scenario_steps(step_order);

-- 场景执行记录表
CREATE TABLE IF NOT EXISTS scenario_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    scenario_id TEXT NOT NULL,
    trigger_type TEXT DEFAULT 'manual' CHECK(trigger_type IN ('manual', 'scheduled', 'pipeline', 'api')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'passed', 'failed', 'cancelled')),
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES test_scenarios(scenario_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_scenario_executions_scenario_id ON scenario_executions(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_executions_status ON scenario_executions(status);
CREATE INDEX IF NOT EXISTS idx_scenario_executions_started_at ON scenario_executions(started_at);

-- 步骤执行结果表
CREATE TABLE IF NOT EXISTS step_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'error', 'skipped')),
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
    executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES scenario_executions(execution_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_step_results_execution_id ON step_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_step_results_step_id ON step_results(step_id);
CREATE INDEX IF NOT EXISTS idx_step_results_status ON step_results(status);

-- =====================================================
-- 知识库表
-- 该文件内容使用AI生成，注意识别准确性
-- =====================================================

-- 知识条目表
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('project_config', 'business_rule', 'module_context', 'test_experience')),
    category TEXT DEFAULT '',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT DEFAULT '',
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'pending', 'archived')),
    source TEXT DEFAULT 'manual' CHECK(source IN ('manual', 'log_learning', 'test_learning')),
    source_ref TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT '',
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_type ON knowledge_entries(type);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_status ON knowledge_entries(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_scope ON knowledge_entries(scope);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_priority ON knowledge_entries(priority);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source ON knowledge_entries(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_created_at ON knowledge_entries(created_at);

-- 知识标签关联表
CREATE TABLE IF NOT EXISTS knowledge_tags (
    knowledge_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (knowledge_id, tag),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_entries(knowledge_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_knowledge_tags_tag ON knowledge_tags(tag);

-- 知识版本历史表
CREATE TABLE IF NOT EXISTS knowledge_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    title TEXT NOT NULL,
    changed_by TEXT DEFAULT '',
    changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    change_type TEXT NOT NULL CHECK(change_type IN ('create', 'update', 'archive')),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_entries(knowledge_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_knowledge_history_knowledge_id ON knowledge_history(knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_history_version ON knowledge_history(knowledge_id, version);

-- 知识使用记录表
CREATE TABLE IF NOT EXISTS knowledge_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usage_id TEXT NOT NULL UNIQUE,
    knowledge_id TEXT NOT NULL,
    used_in TEXT NOT NULL,
    context TEXT DEFAULT '',
    helpful INTEGER DEFAULT 0,
    used_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_entries(knowledge_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_knowledge_usage_knowledge_id ON knowledge_usage(knowledge_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_usage_used_in ON knowledge_usage(used_in);
CREATE INDEX IF NOT EXISTS idx_knowledge_usage_used_at ON knowledge_usage(used_at);
