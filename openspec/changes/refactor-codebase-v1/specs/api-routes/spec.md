# API Routes Specification Changes

<!-- 该文件内容使用AI生成，注意识别准确性 -->

## MODIFIED Requirements

### Requirement: Development Routes Module Structure
系统 SHALL 将开发自测路由模块拆分为子模块以提高可维护性。

#### Scenario: Route registration
- **WHEN** FastAPI 应用启动时
- **THEN** 从 `routes/development/` 包注册所有路由
- **AND** API 端点保持不变

#### Scenario: Module organization
- **WHEN** 访问开发自测功能
- **THEN** 代码组织为: `endpoints.py`（接口管理）、`test_cases.py`（用例管理）、`executions.py`（执行管理）

## REMOVED Requirements

### Requirement: Scheduled Task Routes
**Reason**: 定时任务功能移除
**Migration**: 使用外部调度系统

#### Scenario: Scheduled routes removed
- **WHEN** 请求定时任务相关 API
- **THEN** 返回 404 Not Found

### Requirement: Production Monitoring Routes
**Reason**: 线上监控功能简化或外部化
**Migration**: 集成外部 APM 系统

#### Scenario: Monitoring routes simplified
- **WHEN** 需要线上监控功能
- **THEN** 保留基础健康检查端点
- **AND** 详细监控数据通过外部系统获取

## ADDED Requirements

### Requirement: Unified Error Response
系统 SHALL 使用统一的错误响应格式。

#### Scenario: Error response format
- **WHEN** API 请求发生错误
- **THEN** 返回统一格式: `{"error": {"code": "ERROR_CODE", "message": "描述信息"}}`
- **AND** HTTP 状态码与错误类型匹配
