-- AI Test Tool 数据库表结构 (SQLite)
-- 首次运行时自动创建

-- 开启外键约束
PRAGMA foreign_keys = ON;

-- 分析任务表
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    log_file_path TEXT NOT NULL,
    log_file_size INTEGER,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    total_lines INTEGER DEFAULT 0,
    processed_lines INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    total_test_cases INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status ON analysis_tasks(status);
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

-- 测试用例表（以接口为维度）
-- 注意：task_id 字段用于存储关联的 endpoint_id（不是 analysis_tasks 的 task_id）
-- case_id 格式为 {endpoint_id}_{hash}
CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL UNIQUE,
    task_id TEXT NOT NULL,
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
    max_response_time_ms INTEGER DEFAULT 3000,
    tags TEXT,
    group_name TEXT,
    dependencies TEXT,
    is_enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_cases_task_id ON test_cases(task_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category);
CREATE INDEX IF NOT EXISTS idx_test_cases_priority ON test_cases(priority);
CREATE INDEX IF NOT EXISTS idx_test_cases_group_name ON test_cases(group_name);
CREATE INDEX IF NOT EXISTS idx_test_cases_is_enabled ON test_cases(is_enabled);

-- 测试结果表（单个测试用例的执行结果）
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'error', 'skipped')),
    actual_status_code INTEGER,
    actual_response_time_ms REAL,
    actual_response_body TEXT,
    actual_headers TEXT,
    error_message TEXT,
    assertion_results TEXT,
    executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_results_case_id ON test_results(case_id);
CREATE INDEX IF NOT EXISTS idx_test_results_execution_id ON test_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results(status);
CREATE INDEX IF NOT EXISTS idx_test_results_executed_at ON test_results(executed_at);

-- 测试执行批次表
CREATE TABLE IF NOT EXISTS test_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    name TEXT,
    description TEXT,
    trigger_type TEXT DEFAULT 'manual' CHECK(trigger_type IN ('manual', 'scheduled', 'pipeline', 'api')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'cancelled')),
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
    scheduled_task_id TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_executions_status ON test_executions(status);
CREATE INDEX IF NOT EXISTS idx_test_executions_trigger_type ON test_executions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_test_executions_scheduled_task_id ON test_executions(scheduled_task_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_started_at ON test_executions(started_at);

-- 执行-用例关联表（记录每次执行包含哪些用例）
CREATE TABLE IF NOT EXISTS execution_cases (
    execution_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (execution_id, case_id)
);
CREATE INDEX IF NOT EXISTS idx_execution_cases_case_id ON execution_cases(case_id);

-- 分析报告表
CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    report_type TEXT DEFAULT 'analysis' CHECK(report_type IN ('analysis', 'test', 'summary')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    format TEXT DEFAULT 'markdown' CHECK(format IN ('markdown', 'html', 'json')),
    statistics TEXT,
    issues TEXT,
    recommendations TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES analysis_tasks(task_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_task_id ON analysis_reports(task_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_report_type ON analysis_reports(report_type);

-- 用例标签表
CREATE TABLE IF NOT EXISTS test_case_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (task_id, case_id, tag_name),
    FOREIGN KEY (task_id) REFERENCES analysis_tasks(task_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_test_case_tags_tag_name ON test_case_tags(tag_name);

-- 用例分组表
CREATE TABLE IF NOT EXISTS test_case_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    group_name TEXT NOT NULL,
    description TEXT,
    parent_group TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (task_id, group_name),
    FOREIGN KEY (task_id) REFERENCES analysis_tasks(task_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_test_case_groups_parent_group ON test_case_groups(parent_group);

-- =====================================================
-- 接口标签管理表（全局标签，不依赖任务）
-- =====================================================
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

-- 接口端点表（从接口文档导入）
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

-- 接口-标签关联表（多对多）
CREATE TABLE IF NOT EXISTS api_endpoint_tags (
    endpoint_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (endpoint_id, tag_id),
    FOREIGN KEY (tag_id) REFERENCES api_tags(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_api_endpoint_tags_tag_id ON api_endpoint_tags(tag_id);

-- =====================================================
-- 测试场景相关表
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
CREATE INDEX IF NOT EXISTS idx_scenario_executions_trigger_type ON scenario_executions(trigger_type);
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

-- 定时任务表
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    cron_expression TEXT NOT NULL,
    case_ids TEXT,
    endpoint_ids TEXT,
    tag_names TEXT,
    base_url TEXT,
    environment TEXT,
    variables TEXT,
    headers TEXT,
    notify_on_failure INTEGER DEFAULT 1,
    notify_channels TEXT,
    notify_config TEXT,
    is_enabled INTEGER DEFAULT 1,
    last_run_at TEXT,
    last_run_status TEXT,
    next_run_at TEXT,
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_is_enabled ON scheduled_tasks(is_enabled);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run_at ON scheduled_tasks(next_run_at);

-- =====================================================
-- 测试用例版本管理表
-- =====================================================

-- 测试用例版本表（存储每个版本的完整快照）
-- 注意：通过 case_id 前缀匹配关联接口
CREATE TABLE IF NOT EXISTS test_case_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id TEXT NOT NULL UNIQUE,
    case_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
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
    max_response_time_ms INTEGER DEFAULT 3000,
    tags TEXT,
    change_type TEXT DEFAULT 'create' CHECK(change_type IN ('create', 'update', 'delete', 'restore')),
    change_summary TEXT,
    changed_fields TEXT,
    changed_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_case_versions_case_id ON test_case_versions(case_id);
CREATE INDEX IF NOT EXISTS idx_test_case_versions_version_number ON test_case_versions(case_id, version_number);
CREATE INDEX IF NOT EXISTS idx_test_case_versions_created_at ON test_case_versions(created_at);

-- 测试用例变更日志表（轻量级变更记录）
CREATE TABLE IF NOT EXISTS test_case_change_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK(change_type IN ('create', 'update', 'delete', 'restore', 'enable', 'disable')),
    change_summary TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_case_change_logs_case_id ON test_case_change_logs(case_id);
CREATE INDEX IF NOT EXISTS idx_test_case_change_logs_version_id ON test_case_change_logs(version_id);
CREATE INDEX IF NOT EXISTS idx_test_case_change_logs_change_type ON test_case_change_logs(change_type);
CREATE INDEX IF NOT EXISTS idx_test_case_change_logs_created_at ON test_case_change_logs(created_at);

-- =====================================================
-- 线上质量监控相关表
-- =====================================================

-- 线上请求监控表
CREATE TABLE IF NOT EXISTS production_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    headers TEXT,
    body TEXT,
    query_params TEXT,
    expected_status_code INTEGER DEFAULT 200,
    expected_response_pattern TEXT,
    source TEXT DEFAULT 'log_parse' CHECK(source IN ('log_parse', 'manual', 'import')),
    source_task_id TEXT,
    tags TEXT,
    is_enabled INTEGER DEFAULT 1,
    last_check_at TEXT,
    last_check_status TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_production_requests_method ON production_requests(method);
CREATE INDEX IF NOT EXISTS idx_production_requests_is_enabled ON production_requests(is_enabled);
CREATE INDEX IF NOT EXISTS idx_production_requests_source ON production_requests(source);
CREATE INDEX IF NOT EXISTS idx_production_requests_last_check_status ON production_requests(last_check_status);

-- 健康检查执行记录表
CREATE TABLE IF NOT EXISTS health_check_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    base_url TEXT,
    total_requests INTEGER DEFAULT 0,
    healthy_count INTEGER DEFAULT 0,
    unhealthy_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    trigger_type TEXT DEFAULT 'manual' CHECK(trigger_type IN ('manual', 'scheduled', 'api')),
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_health_check_executions_status ON health_check_executions(status);
CREATE INDEX IF NOT EXISTS idx_health_check_executions_trigger_type ON health_check_executions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_health_check_executions_created_at ON health_check_executions(created_at);

-- 健康检查结果表
CREATE TABLE IF NOT EXISTS health_check_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    success INTEGER NOT NULL,
    status_code INTEGER,
    response_time_ms REAL,
    response_body TEXT,
    error_message TEXT,
    ai_analysis TEXT,
    checked_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_health_check_results_execution_id ON health_check_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_health_check_results_request_id ON health_check_results(request_id);
CREATE INDEX IF NOT EXISTS idx_health_check_results_success ON health_check_results(success);
CREATE INDEX IF NOT EXISTS idx_health_check_results_checked_at ON health_check_results(checked_at);

-- =====================================================
-- AI 洞察表
-- =====================================================

CREATE TABLE IF NOT EXISTS ai_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_id TEXT NOT NULL UNIQUE,
    insight_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'medium' CHECK(severity IN ('high', 'medium', 'low')),
    confidence REAL DEFAULT 0.8,
    details TEXT,
    recommendations TEXT,
    is_resolved INTEGER DEFAULT 0,
    resolved_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_insights_insight_type ON ai_insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_ai_insights_severity ON ai_insights(severity);
CREATE INDEX IF NOT EXISTS idx_ai_insights_is_resolved ON ai_insights(is_resolved);
CREATE INDEX IF NOT EXISTS idx_ai_insights_created_at ON ai_insights(created_at);

-- =====================================================
-- 测试用例生成任务表（异步任务）
-- =====================================================

CREATE TABLE IF NOT EXISTS test_generation_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    task_type TEXT DEFAULT 'single' CHECK(task_type IN ('single', 'batch')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    endpoint_ids TEXT,
    tag_filter TEXT,
    test_types TEXT,
    use_ai INTEGER DEFAULT 1,
    skip_existing INTEGER DEFAULT 1,
    total_endpoints INTEGER DEFAULT 0,
    processed_endpoints INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    total_cases_generated INTEGER DEFAULT 0,
    error_message TEXT,
    errors TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_test_generation_tasks_status ON test_generation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_test_generation_tasks_created_at ON test_generation_tasks(created_at);
