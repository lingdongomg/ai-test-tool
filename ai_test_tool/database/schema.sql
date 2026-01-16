-- AI Test Tool 数据库表结构
-- 创建数据库
CREATE DATABASE IF NOT EXISTS `ai_test_tool` 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `ai_test_tool`;

-- 分析任务表
CREATE TABLE IF NOT EXISTS `analysis_tasks` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '任务唯一ID',
    `name` VARCHAR(255) NOT NULL COMMENT '任务名称',
    `description` TEXT COMMENT '任务描述',
    `log_file_path` VARCHAR(512) NOT NULL COMMENT '日志文件路径',
    `log_file_size` BIGINT UNSIGNED COMMENT '日志文件大小(字节)',
    `status` ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    `total_lines` INT UNSIGNED DEFAULT 0 COMMENT '日志总行数',
    `processed_lines` INT UNSIGNED DEFAULT 0 COMMENT '已处理行数',
    `total_requests` INT UNSIGNED DEFAULT 0 COMMENT '解析出的请求总数',
    `total_test_cases` INT UNSIGNED DEFAULT 0 COMMENT '生成的测试用例数',
    `error_message` TEXT COMMENT '错误信息',
    `started_at` DATETIME COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析任务表';

-- 解析请求表
CREATE TABLE IF NOT EXISTS `parsed_requests` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '关联任务ID',
    `request_id` VARCHAR(64) NOT NULL COMMENT '请求唯一ID',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP方法',
    `url` VARCHAR(2048) NOT NULL COMMENT '请求URL',
    `category` VARCHAR(100) COMMENT '接口分类',
    `headers` JSON COMMENT '请求头',
    `body` TEXT COMMENT '请求体',
    `query_params` JSON COMMENT '查询参数',
    `http_status` INT COMMENT 'HTTP状态码',
    `response_time_ms` DECIMAL(10,2) COMMENT '响应时间(ms)',
    `response_body` TEXT COMMENT '响应体',
    `has_error` TINYINT(1) DEFAULT 0 COMMENT '是否有错误',
    `error_message` TEXT COMMENT '错误信息',
    `has_warning` TINYINT(1) DEFAULT 0 COMMENT '是否有警告',
    `warning_message` TEXT COMMENT '警告信息',
    `curl_command` TEXT COMMENT 'curl命令',
    `timestamp` VARCHAR(64) COMMENT '请求时间戳',
    `raw_logs` TEXT COMMENT '原始日志',
    `metadata` JSON COMMENT '元数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_method` (`method`),
    INDEX `idx_category` (`category`),
    INDEX `idx_http_status` (`http_status`),
    INDEX `idx_has_error` (`has_error`),
    FOREIGN KEY (`task_id`) REFERENCES `analysis_tasks`(`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='解析请求表';

-- 测试用例表（以接口为维度）
-- 注意：task_id 字段用于存储关联的 endpoint_id（不是 analysis_tasks 的 task_id）
-- case_id 格式为 {endpoint_id}_{hash}
CREATE TABLE IF NOT EXISTS `test_cases` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `case_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '用例唯一ID，格式: {endpoint_id}_{hash}',
    `task_id` VARCHAR(64) NOT NULL COMMENT '关联接口ID（endpoint_id），注意：不是analysis_tasks的外键',
    `name` VARCHAR(255) NOT NULL COMMENT '用例名称',
    `description` TEXT COMMENT '用例描述',
    `category` ENUM('normal', 'boundary', 'exception', 'performance', 'security') DEFAULT 'normal' COMMENT '用例类别',
    `priority` ENUM('high', 'medium', 'low') DEFAULT 'medium' COMMENT '优先级',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP方法',
    `url` VARCHAR(2048) NOT NULL COMMENT '请求URL',
    `headers` JSON COMMENT '请求头',
    `body` JSON COMMENT '请求体',
    `query_params` JSON COMMENT '查询参数',
    `expected_status_code` INT DEFAULT 200 COMMENT '期望状态码',
    `expected_response` JSON COMMENT '期望响应',
    `max_response_time_ms` INT DEFAULT 3000 COMMENT '最大响应时间',
    `tags` JSON COMMENT '标签',
    `group_name` VARCHAR(100) COMMENT '分组名称',
    `dependencies` JSON COMMENT '依赖用例ID',
    `is_enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_category` (`category`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_group_name` (`group_name`),
    INDEX `idx_is_enabled` (`is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试用例表';

-- 测试结果表（单个测试用例的执行结果）
CREATE TABLE IF NOT EXISTS `test_results` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `case_id` VARCHAR(64) NOT NULL COMMENT '关联用例ID',
    `execution_id` VARCHAR(64) NOT NULL COMMENT '执行批次ID',
    `status` ENUM('passed', 'failed', 'error', 'skipped') NOT NULL COMMENT '执行状态',
    `actual_status_code` INT COMMENT '实际状态码',
    `actual_response_time_ms` DECIMAL(10,2) COMMENT '实际响应时间',
    `actual_response_body` TEXT COMMENT '实际响应体',
    `actual_headers` JSON COMMENT '实际响应头',
    `error_message` TEXT COMMENT '错误信息',
    `assertion_results` JSON COMMENT '断言结果',
    `executed_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_case_id` (`case_id`),
    INDEX `idx_execution_id` (`execution_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_executed_at` (`executed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试结果表';

-- 测试执行批次表
CREATE TABLE IF NOT EXISTS `test_executions` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `execution_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '执行唯一ID',
    `name` VARCHAR(255) COMMENT '执行名称',
    `description` TEXT COMMENT '执行描述',
    `trigger_type` ENUM('manual', 'scheduled', 'pipeline', 'api') DEFAULT 'manual' COMMENT '触发类型',
    `status` ENUM('pending', 'running', 'completed', 'cancelled') DEFAULT 'pending' COMMENT '执行状态',
    `base_url` VARCHAR(512) COMMENT '测试目标URL',
    `environment` VARCHAR(50) COMMENT '执行环境',
    `variables` JSON COMMENT '全局变量',
    `headers` JSON COMMENT '全局请求头',
    `total_cases` INT DEFAULT 0 COMMENT '总用例数',
    `passed_cases` INT DEFAULT 0 COMMENT '通过用例数',
    `failed_cases` INT DEFAULT 0 COMMENT '失败用例数',
    `error_cases` INT DEFAULT 0 COMMENT '错误用例数',
    `skipped_cases` INT DEFAULT 0 COMMENT '跳过用例数',
    `duration_ms` BIGINT DEFAULT 0 COMMENT '执行耗时(ms)',
    `error_message` TEXT COMMENT '错误信息',
    `scheduled_task_id` VARCHAR(64) COMMENT '关联定时任务ID',
    `started_at` DATETIME COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`),
    INDEX `idx_trigger_type` (`trigger_type`),
    INDEX `idx_scheduled_task_id` (`scheduled_task_id`),
    INDEX `idx_started_at` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试执行批次表';

-- 执行-用例关联表（记录每次执行包含哪些用例）
CREATE TABLE IF NOT EXISTS `execution_cases` (
    `execution_id` VARCHAR(64) NOT NULL COMMENT '执行ID',
    `case_id` VARCHAR(64) NOT NULL COMMENT '用例ID',
    `order_index` INT DEFAULT 0 COMMENT '执行顺序',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`execution_id`, `case_id`),
    INDEX `idx_case_id` (`case_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='执行用例关联表';

-- 分析报告表
CREATE TABLE IF NOT EXISTS `analysis_reports` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '关联任务ID',
    `report_type` ENUM('analysis', 'test', 'summary') DEFAULT 'analysis' COMMENT '报告类型',
    `title` VARCHAR(255) NOT NULL COMMENT '报告标题',
    `content` LONGTEXT NOT NULL COMMENT '报告内容(Markdown)',
    `format` ENUM('markdown', 'html', 'json') DEFAULT 'markdown' COMMENT '报告格式',
    `statistics` JSON COMMENT '统计数据',
    `issues` JSON COMMENT '问题列表',
    `recommendations` JSON COMMENT '改进建议',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_report_type` (`report_type`),
    FOREIGN KEY (`task_id`) REFERENCES `analysis_tasks`(`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析报告表';

-- 用例标签表
CREATE TABLE IF NOT EXISTS `test_case_tags` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '关联任务ID',
    `case_id` VARCHAR(64) NOT NULL COMMENT '关联用例ID',
    `tag_name` VARCHAR(100) NOT NULL COMMENT '标签名称',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_case_tag` (`task_id`, `case_id`, `tag_name`),
    INDEX `idx_tag_name` (`tag_name`),
    FOREIGN KEY (`task_id`) REFERENCES `analysis_tasks`(`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用例标签表';

-- 用例分组表
CREATE TABLE IF NOT EXISTS `test_case_groups` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '关联任务ID',
    `group_name` VARCHAR(100) NOT NULL COMMENT '分组名称',
    `description` TEXT COMMENT '分组描述',
    `parent_group` VARCHAR(100) COMMENT '父分组',
    `sort_order` INT DEFAULT 0 COMMENT '排序',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_task_group` (`task_id`, `group_name`),
    INDEX `idx_parent_group` (`parent_group`),
    FOREIGN KEY (`task_id`) REFERENCES `analysis_tasks`(`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用例分组表';

-- =====================================================
-- 接口标签管理表（全局标签，不依赖任务）
-- =====================================================
CREATE TABLE IF NOT EXISTS `api_tags` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE COMMENT '标签名称',
    `description` VARCHAR(255) DEFAULT '' COMMENT '标签描述',
    `color` VARCHAR(20) DEFAULT '#1890ff' COMMENT '显示颜色',
    `parent_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '父标签ID（支持层级）',
    `sort_order` INT DEFAULT 0 COMMENT '排序',
    `is_system` TINYINT(1) DEFAULT 0 COMMENT '是否系统标签（不可删除）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_parent_id` (`parent_id`),
    INDEX `idx_sort_order` (`sort_order`),
    FOREIGN KEY (`parent_id`) REFERENCES `api_tags`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='接口标签表';

-- 接口端点表（从接口文档导入）
CREATE TABLE IF NOT EXISTS `api_endpoints` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `endpoint_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '端点唯一ID',
    `name` VARCHAR(255) NOT NULL COMMENT '接口名称',
    `description` TEXT COMMENT '接口描述',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP方法',
    `path` VARCHAR(512) NOT NULL COMMENT '接口路径',
    `summary` VARCHAR(500) COMMENT '接口摘要',
    `parameters` JSON COMMENT '参数定义',
    `request_body` JSON COMMENT '请求体定义',
    `responses` JSON COMMENT '响应定义',
    `security` JSON COMMENT '安全配置',
    `source_type` ENUM('swagger', 'postman', 'manual') DEFAULT 'manual' COMMENT '来源类型',
    `source_file` VARCHAR(255) COMMENT '来源文件名',
    `is_deprecated` TINYINT(1) DEFAULT 0 COMMENT '是否已废弃',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_method` (`method`),
    INDEX `idx_path` (`path`(255)),
    INDEX `idx_source_type` (`source_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='接口端点表';

-- 接口-标签关联表（多对多）
CREATE TABLE IF NOT EXISTS `api_endpoint_tags` (
    `endpoint_id` VARCHAR(64) NOT NULL COMMENT '端点ID',
    `tag_id` BIGINT UNSIGNED NOT NULL COMMENT '标签ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`endpoint_id`, `tag_id`),
    INDEX `idx_tag_id` (`tag_id`),
    FOREIGN KEY (`tag_id`) REFERENCES `api_tags`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='接口标签关联表';

-- =====================================================
-- 测试场景相关表
-- =====================================================

-- 测试场景表
CREATE TABLE IF NOT EXISTS `test_scenarios` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `scenario_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '场景唯一ID',
    `name` VARCHAR(255) NOT NULL COMMENT '场景名称',
    `description` TEXT COMMENT '场景描述',
    `tags` JSON COMMENT '标签',
    `variables` JSON COMMENT '场景变量（初始值）',
    `setup_hooks` JSON COMMENT '前置钩子',
    `teardown_hooks` JSON COMMENT '后置钩子',
    `retry_on_failure` TINYINT(1) DEFAULT 0 COMMENT '失败是否重试',
    `max_retries` INT DEFAULT 3 COMMENT '最大重试次数',
    `is_enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `created_by` VARCHAR(100) COMMENT '创建人',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_is_enabled` (`is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试场景表';

-- 场景步骤表
CREATE TABLE IF NOT EXISTS `scenario_steps` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `scenario_id` VARCHAR(64) NOT NULL COMMENT '关联场景ID',
    `step_id` VARCHAR(64) NOT NULL COMMENT '步骤唯一ID',
    `step_order` INT NOT NULL COMMENT '执行顺序',
    `name` VARCHAR(255) NOT NULL COMMENT '步骤名称',
    `description` TEXT COMMENT '步骤描述',
    `step_type` ENUM('request', 'wait', 'condition', 'loop', 'extract', 'assert') DEFAULT 'request' COMMENT '步骤类型',
    `method` VARCHAR(10) COMMENT 'HTTP方法',
    `url` VARCHAR(2048) COMMENT '请求URL（支持变量替换）',
    `headers` JSON COMMENT '请求头（支持变量替换）',
    `body` JSON COMMENT '请求体（支持变量替换）',
    `query_params` JSON COMMENT '查询参数（支持变量替换）',
    `extractions` JSON COMMENT '响应提取配置（提取变量）',
    `assertions` JSON COMMENT '断言配置',
    `wait_time_ms` INT DEFAULT 0 COMMENT '等待时间(ms)',
    `condition` JSON COMMENT '条件配置（用于条件步骤）',
    `loop_config` JSON COMMENT '循环配置（用于循环步骤）',
    `timeout_ms` INT DEFAULT 30000 COMMENT '超时时间(ms)',
    `continue_on_failure` TINYINT(1) DEFAULT 0 COMMENT '失败是否继续',
    `is_enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_scenario_step` (`scenario_id`, `step_id`),
    INDEX `idx_scenario_id` (`scenario_id`),
    INDEX `idx_step_order` (`step_order`),
    FOREIGN KEY (`scenario_id`) REFERENCES `test_scenarios`(`scenario_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='场景步骤表';

-- 场景执行记录表
CREATE TABLE IF NOT EXISTS `scenario_executions` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `execution_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '执行唯一ID',
    `scenario_id` VARCHAR(64) NOT NULL COMMENT '关联场景ID',
    `trigger_type` ENUM('manual', 'scheduled', 'pipeline', 'api') DEFAULT 'manual' COMMENT '触发类型',
    `status` ENUM('pending', 'running', 'passed', 'failed', 'cancelled') DEFAULT 'pending' COMMENT '执行状态',
    `base_url` VARCHAR(512) COMMENT '测试目标URL',
    `environment` VARCHAR(50) COMMENT '执行环境',
    `variables` JSON COMMENT '执行时变量',
    `total_steps` INT DEFAULT 0 COMMENT '总步骤数',
    `passed_steps` INT DEFAULT 0 COMMENT '通过步骤数',
    `failed_steps` INT DEFAULT 0 COMMENT '失败步骤数',
    `skipped_steps` INT DEFAULT 0 COMMENT '跳过步骤数',
    `duration_ms` BIGINT DEFAULT 0 COMMENT '执行耗时(ms)',
    `error_message` TEXT COMMENT '错误信息',
    `started_at` DATETIME COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_scenario_id` (`scenario_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_trigger_type` (`trigger_type`),
    INDEX `idx_started_at` (`started_at`),
    FOREIGN KEY (`scenario_id`) REFERENCES `test_scenarios`(`scenario_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='场景执行记录表';

-- 步骤执行结果表
CREATE TABLE IF NOT EXISTS `step_results` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `execution_id` VARCHAR(64) NOT NULL COMMENT '关联执行ID',
    `step_id` VARCHAR(64) NOT NULL COMMENT '关联步骤ID',
    `step_order` INT NOT NULL COMMENT '执行顺序',
    `status` ENUM('passed', 'failed', 'error', 'skipped') NOT NULL COMMENT '执行状态',
    `request_url` VARCHAR(2048) COMMENT '实际请求URL',
    `request_headers` JSON COMMENT '实际请求头',
    `request_body` TEXT COMMENT '实际请求体',
    `response_status_code` INT COMMENT '响应状态码',
    `response_headers` JSON COMMENT '响应头',
    `response_body` TEXT COMMENT '响应体',
    `response_time_ms` DECIMAL(10,2) COMMENT '响应时间(ms)',
    `extracted_variables` JSON COMMENT '提取的变量',
    `assertion_results` JSON COMMENT '断言结果',
    `error_message` TEXT COMMENT '错误信息',
    `executed_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    INDEX `idx_execution_id` (`execution_id`),
    INDEX `idx_step_id` (`step_id`),
    INDEX `idx_status` (`status`),
    FOREIGN KEY (`execution_id`) REFERENCES `scenario_executions`(`execution_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='步骤执行结果表';

-- 定时任务表
CREATE TABLE IF NOT EXISTS `scheduled_tasks` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '任务唯一ID',
    `name` VARCHAR(255) NOT NULL COMMENT '任务名称',
    `description` TEXT COMMENT '任务描述',
    `cron_expression` VARCHAR(100) NOT NULL COMMENT 'Cron表达式',
    `case_ids` JSON COMMENT '要执行的测试用例ID列表',
    `endpoint_ids` JSON COMMENT '要执行的接口ID列表',
    `tag_names` JSON COMMENT '按标签筛选',
    `base_url` VARCHAR(512) COMMENT '测试目标URL',
    `environment` VARCHAR(50) COMMENT '执行环境',
    `variables` JSON COMMENT '执行变量',
    `headers` JSON COMMENT '全局请求头',
    `notify_on_failure` TINYINT(1) DEFAULT 1 COMMENT '失败时是否通知',
    `notify_channels` JSON COMMENT '通知渠道',
    `notify_config` JSON COMMENT '通知配置',
    `is_enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `last_run_at` DATETIME COMMENT '上次执行时间',
    `last_run_status` VARCHAR(20) COMMENT '上次执行状态',
    `next_run_at` DATETIME COMMENT '下次执行时间',
    `run_count` INT DEFAULT 0 COMMENT '执行次数',
    `success_count` INT DEFAULT 0 COMMENT '成功次数',
    `failure_count` INT DEFAULT 0 COMMENT '失败次数',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_is_enabled` (`is_enabled`),
    INDEX `idx_next_run_at` (`next_run_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='定时任务表';

-- =====================================================
-- 测试用例版本管理表
-- =====================================================

-- 测试用例版本表（存储每个版本的完整快照）
-- 注意：通过 case_id 前缀匹配关联接口
CREATE TABLE IF NOT EXISTS `test_case_versions` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `version_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '版本唯一ID',
    `case_id` VARCHAR(64) NOT NULL COMMENT '关联用例ID，格式: {endpoint_id}_{hash}',
    `version_number` INT NOT NULL COMMENT '版本号（从1开始递增）',
    `name` VARCHAR(255) NOT NULL COMMENT '用例名称',
    `description` TEXT COMMENT '用例描述',
    `category` ENUM('normal', 'boundary', 'exception', 'performance', 'security') DEFAULT 'normal' COMMENT '用例类别',
    `priority` ENUM('high', 'medium', 'low') DEFAULT 'medium' COMMENT '优先级',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP方法',
    `url` VARCHAR(2048) NOT NULL COMMENT '请求URL',
    `headers` JSON COMMENT '请求头',
    `body` JSON COMMENT '请求体',
    `query_params` JSON COMMENT '查询参数',
    `expected_status_code` INT DEFAULT 200 COMMENT '期望状态码',
    `expected_response` JSON COMMENT '期望响应',
    `max_response_time_ms` INT DEFAULT 3000 COMMENT '最大响应时间',
    `tags` JSON COMMENT '标签',
    `change_type` ENUM('create', 'update', 'delete', 'restore') DEFAULT 'create' COMMENT '变更类型',
    `change_summary` VARCHAR(500) COMMENT '变更摘要',
    `changed_fields` JSON COMMENT '变更的字段列表',
    `changed_by` VARCHAR(100) COMMENT '变更人',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '版本创建时间',
    INDEX `idx_case_id` (`case_id`),
    INDEX `idx_version_number` (`case_id`, `version_number`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试用例版本表';

-- 测试用例变更日志表（轻量级变更记录）
CREATE TABLE IF NOT EXISTS `test_case_change_logs` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `case_id` VARCHAR(64) NOT NULL COMMENT '关联用例ID，格式: {endpoint_id}_{hash}',
    `version_id` VARCHAR(64) NOT NULL COMMENT '关联版本ID',
    `change_type` ENUM('create', 'update', 'delete', 'restore', 'enable', 'disable') NOT NULL COMMENT '变更类型',
    `change_summary` VARCHAR(500) COMMENT '变更摘要',
    `old_value` JSON COMMENT '变更前的值（仅记录变更字段）',
    `new_value` JSON COMMENT '变更后的值（仅记录变更字段）',
    `changed_by` VARCHAR(100) COMMENT '变更人',
    `ip_address` VARCHAR(50) COMMENT 'IP地址',
    `user_agent` VARCHAR(500) COMMENT 'User-Agent',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_case_id` (`case_id`),
    INDEX `idx_version_id` (`version_id`),
    INDEX `idx_change_type` (`change_type`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试用例变更日志表';

-- =====================================================
-- 线上质量监控相关表
-- =====================================================

-- 线上请求监控表
CREATE TABLE IF NOT EXISTS `production_requests` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `request_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '请求唯一ID',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP方法',
    `url` VARCHAR(2048) NOT NULL COMMENT '请求URL',
    `headers` JSON COMMENT '请求头',
    `body` TEXT COMMENT '请求体',
    `query_params` JSON COMMENT '查询参数',
    `expected_status_code` INT DEFAULT 200 COMMENT '期望状态码',
    `expected_response_pattern` VARCHAR(500) COMMENT '期望响应正则模式',
    `source` ENUM('log_parse', 'manual', 'import') DEFAULT 'log_parse' COMMENT '来源',
    `source_task_id` VARCHAR(64) COMMENT '来源任务ID',
    `tags` JSON COMMENT '标签',
    `is_enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `last_check_at` DATETIME COMMENT '上次检查时间',
    `last_check_status` VARCHAR(20) COMMENT '上次检查状态',
    `consecutive_failures` INT DEFAULT 0 COMMENT '连续失败次数',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_method` (`method`),
    INDEX `idx_is_enabled` (`is_enabled`),
    INDEX `idx_source` (`source`),
    INDEX `idx_last_check_status` (`last_check_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='线上请求监控表';

-- 健康检查执行记录表
CREATE TABLE IF NOT EXISTS `health_check_executions` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `execution_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '执行唯一ID',
    `base_url` VARCHAR(512) COMMENT '目标服务器URL',
    `total_requests` INT DEFAULT 0 COMMENT '总请求数',
    `healthy_count` INT DEFAULT 0 COMMENT '健康数',
    `unhealthy_count` INT DEFAULT 0 COMMENT '不健康数',
    `status` ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '执行状态',
    `trigger_type` ENUM('manual', 'scheduled', 'api') DEFAULT 'manual' COMMENT '触发类型',
    `started_at` DATETIME COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`),
    INDEX `idx_trigger_type` (`trigger_type`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='健康检查执行记录表';

-- 健康检查结果表
CREATE TABLE IF NOT EXISTS `health_check_results` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `execution_id` VARCHAR(64) NOT NULL COMMENT '关联执行ID',
    `request_id` VARCHAR(64) NOT NULL COMMENT '关联请求ID',
    `success` TINYINT(1) NOT NULL COMMENT '是否成功',
    `status_code` INT COMMENT '响应状态码',
    `response_time_ms` DECIMAL(10,2) COMMENT '响应时间(ms)',
    `response_body` TEXT COMMENT '响应体',
    `error_message` TEXT COMMENT '错误信息',
    `ai_analysis` JSON COMMENT 'AI分析结果',
    `checked_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
    INDEX `idx_execution_id` (`execution_id`),
    INDEX `idx_request_id` (`request_id`),
    INDEX `idx_success` (`success`),
    INDEX `idx_checked_at` (`checked_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='健康检查结果表';

-- =====================================================
-- AI 洞察表
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_insights` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `insight_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '洞察唯一ID',
    `insight_type` VARCHAR(50) NOT NULL COMMENT '洞察类型',
    `title` VARCHAR(255) NOT NULL COMMENT '标题',
    `description` TEXT COMMENT '描述',
    `severity` ENUM('high', 'medium', 'low') DEFAULT 'medium' COMMENT '严重程度',
    `confidence` DECIMAL(3,2) DEFAULT 0.8 COMMENT '置信度',
    `details` JSON COMMENT '详细信息',
    `recommendations` JSON COMMENT '建议',
    `is_resolved` TINYINT(1) DEFAULT 0 COMMENT '是否已解决',
    `resolved_at` DATETIME COMMENT '解决时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_insight_type` (`insight_type`),
    INDEX `idx_severity` (`severity`),
    INDEX `idx_is_resolved` (`is_resolved`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI洞察表';

-- =====================================================
-- 测试用例生成任务表（异步任务）
-- =====================================================

CREATE TABLE IF NOT EXISTS `test_generation_tasks` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '任务唯一ID',
    `task_type` ENUM('single', 'batch') DEFAULT 'single' COMMENT '任务类型',
    `status` ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    `endpoint_ids` JSON COMMENT '目标接口ID列表',
    `tag_filter` VARCHAR(100) COMMENT '标签筛选',
    `test_types` JSON COMMENT '测试类型',
    `use_ai` TINYINT(1) DEFAULT 1 COMMENT '是否使用AI',
    `skip_existing` TINYINT(1) DEFAULT 1 COMMENT '跳过已有用例的接口',
    `total_endpoints` INT DEFAULT 0 COMMENT '总接口数',
    `processed_endpoints` INT DEFAULT 0 COMMENT '已处理接口数',
    `success_count` INT DEFAULT 0 COMMENT '成功数',
    `failed_count` INT DEFAULT 0 COMMENT '失败数',
    `total_cases_generated` INT DEFAULT 0 COMMENT '生成的用例总数',
    `error_message` TEXT COMMENT '错误信息',
    `errors` JSON COMMENT '详细错误列表',
    `started_at` DATETIME COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试用例生成任务表';
