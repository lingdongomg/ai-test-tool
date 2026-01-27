# 重构任务清单

<!-- 该文件内容使用AI生成，注意识别准确性 -->

## 1. 数据库重构
- [ ] 1.1 分析现有数据库表使用情况，确定需要移除的表
- [ ] 1.2 设计新的精简数据库 Schema
- [ ] 1.3 更新 `schema.sql` 文件
- [ ] 1.4 更新 `connection.py`，移除冗余建表代码
- [ ] 1.5 编写数据迁移脚本（如需要）

## 2. Models 重构
- [ ] 2.1 创建 `BaseModel` 基类，抽取公共方法
- [ ] 2.2 按领域拆分 `models.py` 为多个文件
- [ ] 2.3 移除未使用的 Model 类
- [ ] 2.4 精简每个 Model 的字段

## 3. Repository 重构
- [ ] 3.1 创建泛型 `BaseRepository` 基类
- [ ] 3.2 重构现有 Repository 方法，继承基类
- [ ] 3.3 移除重复的 CRUD 代码

## 4. LLM Provider 重构
- [ ] 4.1 抽取公共 Provider 接口
- [ ] 4.2 重构 `OllamaProvider`、`OpenAIProvider`、`AnthropicProvider`
- [ ] 4.3 移除重复的 `chat()` 方法实现

## 5. API Routes 重构
- [ ] 5.1 拆分 `development.py` 为多个文件
- [ ] 5.2 移除未使用的路由
- [ ] 5.3 统一错误处理
- [ ] 5.4 精简路由逻辑

## 6. Services 重构
- [ ] 6.1 精简 `log_anomaly_detector.py`
- [ ] 6.2 精简 `ai_assistant.py`
- [ ] 6.3 移除重复的服务代码

## 7. 清理与验证
- [ ] 7.1 移除所有未使用的导入
- [ ] 7.2 移除死代码
- [ ] 7.3 运行完整测试验证
- [ ] 7.4 更新 README 和文档
