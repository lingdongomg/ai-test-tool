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

-- 测试用例表
CREATE TABLE IF NOT EXISTS `test_cases` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '关联任务ID',
    `case_id` VARCHAR(64) NOT NULL COMMENT '用例唯一ID',
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
    UNIQUE KEY `uk_task_case` (`task_id`, `case_id`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_category` (`category`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_group_name` (`group_name`),
    INDEX `idx_is_enabled` (`is_enabled`),
    FOREIGN KEY (`task_id`) REFERENCES `analysis_tasks`(`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试用例表';

-- 测试结果表
CREATE TABLE IF NOT EXISTS `test_results` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `task_id` VARCHAR(64) NOT NULL COMMENT '关联任务ID',
    `case_id` VARCHAR(64) NOT NULL COMMENT '关联用例ID',
    `execution_id` VARCHAR(64) NOT NULL COMMENT '执行批次ID',
    `status` ENUM('passed', 'failed', 'error', 'skipped') NOT NULL COMMENT '执行状态',
    `actual_status_code` INT COMMENT '实际状态码',
    `actual_response_time_ms` DECIMAL(10,2) COMMENT '实际响应时间',
    `actual_response_body` TEXT COMMENT '实际响应体',
    `actual_headers` JSON COMMENT '实际响应头',
    `error_message` TEXT COMMENT '错误信息',
    `validation_results` JSON COMMENT '验证结果',
    `executed_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_case_id` (`case_id`),
    INDEX `idx_execution_id` (`execution_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_executed_at` (`executed_at`),
    FOREIGN KEY (`task_id`) REFERENCES `analysis_tasks`(`task_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试结果表';

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
