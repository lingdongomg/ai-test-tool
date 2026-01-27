# Models Specification Changes

<!-- 该文件内容使用AI生成，注意识别准确性 -->

## ADDED Requirements

### Requirement: Base Model Class
系统 SHALL 提供统一的 BaseModel 基类，所有数据模型继承该基类以获得通用功能。

#### Scenario: Model serialization
- **WHEN** 调用任意模型的 `to_dict()` 方法
- **THEN** 返回包含所有字段的字典
- **AND** datetime 类型自动转换为 ISO 格式字符串

#### Scenario: Model deserialization
- **WHEN** 调用任意模型的 `from_dict()` 类方法
- **THEN** 从字典创建模型实例
- **AND** 忽略字典中不存在于模型的字段

### Requirement: Model Module Structure
系统 SHALL 将数据模型按领域拆分为独立模块文件。

#### Scenario: Import models
- **WHEN** 导入 models 包
- **THEN** 可以访问所有领域的模型类
- **AND** 模块结构为: base.py, task.py, test.py, api.py, scenario.py

## REMOVED Requirements

### Requirement: Redundant Model Classes
**Reason**: 移除与已删除数据库表对应的模型类
**Migration**: 更新所有引用这些模型的代码

#### Scenario: Models removed
- **WHEN** 编译代码时
- **THEN** 以下模型类不再存在: ScheduledTask, AIInsight, ProductionRequest, HealthCheckExecution, HealthCheckResult, TestCaseVersion, TestCaseChangeLog, TestGenerationTask
