# Change: AI Test Tool 代码库大规模重构

<!-- 该文件内容使用AI生成，注意识别准确性 -->

## Why

当前项目存在以下问题：
1. **代码重复**: 多个模块中存在相似的 CRUD 逻辑、数据转换方法
2. **大文件问题**: 多个文件超过 700 行，难以维护
3. **数据库设计冗余**: 20+ 张表设计过于分散，部分表可合并或移除
4. **缺乏抽象**: 重复的模式没有被抽取为基类或工具函数

## What Changes

### 1. 数据库重构
- **合并表**: 将 `test_case_versions` 和 `test_case_change_logs` 合并为单一版本历史表
- **移除表**: 移除 `ai_insights` 表（功能未使用或可通过其他方式实现）
- **优化表**: 精简 `test_cases`、`api_endpoints` 表的字段设计
- **移除冗余表**: 移除 `scheduled_tasks` 表（功能可通过外部调度实现）

### 2. 代码精简
- **合并重复代码**: 在 `models.py` 中抽取 `BaseModel` 基类统一 `to_dict()` / `from_dict()` 方法
- **LLM Provider 重构**: 抽取公共接口，减少 Provider 实现中的重复代码
- **Repository 重构**: 引入泛型 Repository 基类减少 CRUD 重复

### 3. 大文件拆分
- `development.py` (1000行) → 拆分为 `endpoints.py`, `test_cases.py`, `executions.py`
- `models.py` (845行) → 按领域拆分
- `connection.py` (736行) → SQL 定义移至 `schema.sql`

### 4. 架构优化
- 移除未使用的模块和函数
- 统一错误处理和响应格式
- 精简 API 路由层

## Impact

- **Affected specs**: database, api-routes, models, llm-provider
- **Affected code**: 
  - `ai_test_tool/database/` - 全部重构
  - `ai_test_tool/api/routes/` - 大文件拆分
  - `ai_test_tool/llm/` - Provider 重构
- **Breaking changes**: 
  - 数据库 schema 变更需要数据迁移
  - 部分 API 响应格式可能调整

## Success Criteria

1. 代码总行数减少 20%+
2. 数据库表数量从 20+ 减少到 15 以下
3. 最大文件行数控制在 500 行以内
4. 所有现有功能测试通过
5. API 向后兼容
