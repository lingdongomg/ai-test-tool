# 实现任务清单

## 1. 数据库层扩展
- [x] 1.1 在 `schema.sql` 中添加知识库相关表（knowledge_entries, knowledge_tags, knowledge_history, knowledge_usage）
- [x] 1.2 在 `models.py` 中添加知识数据模型类（KnowledgeEntry, KnowledgeTag, KnowledgeHistory, KnowledgeUsage）
- [x] 1.3 在 `repository.py` 中添加知识库CRUD操作方法
- [x] 1.4 在 `connection.py` 中添加表初始化逻辑（通过schema.sql自动创建）

## 2. 知识库核心模块
- [x] 2.1 创建 `ai_test_tool/knowledge/` 模块目录结构
- [x] 2.2 实现 `embeddings.py` - 向量化适配器（支持Ollama/OpenAI/本地模型/TF-IDF降级）
- [x] 2.3 实现 `store.py` - 知识存储层（SQLite + ChromaDB混合存储）
- [x] 2.4 实现 `retriever.py` - 混合检索器（关键词+语义+重排序）
- [x] 2.5 实现 `rag_builder.py` - RAG上下文构建器
- [x] 2.6 实现 `models.py` - 知识领域模型和DTO

## 3. 知识学习引擎
- [x] 3.1 在 `llm/prompts.py` 中添加知识提取提示词模板
- [x] 3.2 在 `llm/chains.py` 中添加 `KnowledgeExtractionChain`
- [x] 3.3 实现 `knowledge/learner.py` - 知识学习引擎（从日志/测试中提取）

## 4. 测试生成集成
- [x] 4.1 添加 `KnowledgeEnhancedTestGeneratorChain` - 知识增强测试生成
- [x] 4.2 添加 `TEST_CASE_GENERATION_WITH_KNOWLEDGE_PROMPT` - 知识增强提示词
- [x] 4.3 修改 `testing/test_case_generator.py` - 集成知识检索

## 5. 日志解析集成
- [x] 5.1 实现 `knowledge/learner.py` 的 `extract_from_log_analysis` 方法
- [x] 5.2 修改 `core.py` - 在解析流程中集成知识学习
- [x] 5.3 修改 `core.py` - 在测试结果验证后集成知识学习

## 6. API接口层
- [x] 6.1 创建 `api/routes/knowledge.py` - 知识库管理REST API
- [x] 6.2 在 `api/routes/__init__.py` 中注册知识库路由
- [x] 6.3 实现知识CRUD接口（列表/详情/创建/更新/删除）
- [x] 6.4 实现知识审核接口（确认/拒绝pending知识）
- [x] 6.5 实现知识检索测试接口（调试用）
- [x] 6.6 实现知识学习接口

## 7. 前端管理界面
- [x] 7.1 创建 `web/src/views/knowledge/KnowledgeList.vue` - 知识列表页
- [x] 7.2 知识编辑功能已集成在KnowledgeList.vue中
- [x] 7.3 创建 `web/src/views/knowledge/PendingReview.vue` - 待审核知识页
- [x] 7.4 更新路由配置
- [x] 7.5 创建 `web/src/views/knowledge/SearchTest.vue` - 知识检索测试页

## 8. 依赖和配置
- [x] 8.1 更新 `requirements.txt` - 添加chromadb、numpy、scikit-learn
- [x] 8.2 向量化适配器支持自动降级
- [x] 8.3 添加降级方案 - 当ChromaDB不可用时使用TF-IDF检索

## 9. 测试和文档
- [x] 9.1 编写知识库模块单元测试 (tests/test_knowledge.py)
- [x] 9.2 编写集成测试（知识学习→检索→应用）(tests/test_knowledge_integration.py)
- [x] 9.3 测试全部通过 (23 passed)
