# Database Specification Changes

<!-- 该文件内容使用AI生成，注意识别准确性 -->

## REMOVED Requirements

### Requirement: Scheduled Tasks Table
**Reason**: 定时任务功能应由外部调度系统（如 cron、APScheduler）管理，而非存储在业务数据库中
**Migration**: 如有现存定时任务配置，导出为配置文件

#### Scenario: Scheduled tasks removed
- **WHEN** 系统启动时
- **THEN** 不再创建 `scheduled_tasks` 表
- **AND** 定时任务通过外部配置文件管理

### Requirement: AI Insights Table
**Reason**: AI 洞察功能与 `analysis_reports` 表功能重叠，合并以减少冗余
**Migration**: 现有洞察数据迁移至 `analysis_reports` 表的扩展字段

#### Scenario: AI insights merged
- **WHEN** 需要存储 AI 分析洞察时
- **THEN** 使用 `analysis_reports` 表的 `metadata` 字段存储

### Requirement: Production Requests Table
**Reason**: 线上请求监控数据量大，应存储在专用监控系统中
**Migration**: 集成外部 APM 或日志系统

#### Scenario: Production monitoring externalized
- **WHEN** 需要监控线上请求时
- **THEN** 通过外部监控系统收集和存储数据

### Requirement: Test Case Versions and Change Logs Tables
**Reason**: 两张表功能相似，合并为统一的历史记录表
**Migration**: 合并数据至新的 `test_case_history` 表

#### Scenario: Version history unified
- **WHEN** 测试用例被修改时
- **THEN** 在 `test_case_history` 表中记录变更

### Requirement: Health Check Tables
**Reason**: 健康检查功能可简化，无需专门的执行记录表
**Migration**: 健康检查结果合并到 `test_results` 表

#### Scenario: Health check simplified
- **WHEN** 执行健康检查时
- **THEN** 结果存储在 `test_results` 表，通过 `type` 字段区分

### Requirement: Test Generation Tasks Table
**Reason**: 测试生成任务可复用 `analysis_tasks` 表结构
**Migration**: 使用 `analysis_tasks` 表的 `task_type` 字段区分

#### Scenario: Test generation tasks unified
- **WHEN** 创建测试生成任务时
- **THEN** 在 `analysis_tasks` 表中创建记录，`task_type='test_generation'`

## ADDED Requirements

### Requirement: Test Case History Table
系统 SHALL 提供统一的测试用例历史记录表，合并版本和变更日志功能。

#### Scenario: Record test case change
- **WHEN** 测试用例被创建或修改
- **THEN** 系统在 `test_case_history` 表中记录完整的历史快照
- **AND** 包含操作类型（create/update/delete）、操作时间、操作人

#### Scenario: Query test case history
- **WHEN** 查询测试用例的变更历史
- **THEN** 返回按时间倒序排列的历史记录列表

## MODIFIED Requirements

### Requirement: Analysis Tasks Table
系统 SHALL 使用 `analysis_tasks` 表管理所有类型的分析和生成任务。

#### Scenario: Create analysis task
- **WHEN** 创建新的分析任务
- **THEN** 在 `analysis_tasks` 表中创建记录
- **AND** `task_type` 字段标识任务类型（log_analysis/test_generation/report）

#### Scenario: Query tasks by type
- **WHEN** 按类型查询任务
- **THEN** 根据 `task_type` 字段过滤返回结果

### Requirement: Test Results Table
系统 SHALL 使用 `test_results` 表存储所有测试执行结果，包括健康检查。

#### Scenario: Store health check result
- **WHEN** 健康检查执行完成
- **THEN** 结果存储在 `test_results` 表
- **AND** `result_type` 字段值为 `health_check`

#### Scenario: Query results by type
- **WHEN** 按类型查询测试结果
- **THEN** 根据 `result_type` 字段过滤返回结果
