# 知识库系统技术设计

## Context

### 背景
AI测试工具在生成单测时，需要了解项目特定的业务知识和配置信息。这些知识包括：
- 认证方式（如header中的TOKEN）
- 业务模块规则（如直播电商需要game-id）
- 测试环境配置（如demo游戏ID=123456）
- 历史测试经验（如某接口常见的边界情况）

### 约束条件
- 必须支持离线运行（不依赖外部向量数据库服务）
- 知识库需要持久化存储
- 检索延迟必须控制在合理范围内（<500ms）
- 与现有的SQLite数据库架构兼容

## Goals / Non-Goals

### Goals
- 构建可持久化的本地知识库
- 支持语义级别的知识检索
- 实现从日志/测试中自动学习知识
- 无缝集成到测试生成流程

### Non-Goals
- 不构建云端知识同步功能
- 不实现多用户协作知识共享
- 不构建知识图谱（本期聚焦文本知识）

## Decisions

### Decision 1: 知识存储方案
**选择**: SQLite + ChromaDB混合存储

**理由**:
- SQLite存储知识元数据、分类、状态等结构化信息
- ChromaDB存储向量索引，支持语义检索
- ChromaDB支持本地持久化，无需外部服务
- 两者配合可实现高效的混合检索

**替代方案**:
- 纯SQLite + FTS5全文搜索：简单但不支持语义相似度
- Milvus/Weaviate：功能强大但部署复杂

### Decision 2: 知识分类体系
**选择**: 四级分类 + 标签系统

```
知识类型 (type):
├── project_config   # 项目配置知识
│   ├── auth         # 认证相关
│   ├── environment  # 环境配置
│   └── dependency   # 依赖服务
├── business_rule    # 业务规则知识
│   ├── module       # 模块特定规则
│   └── domain       # 领域通用规则
├── module_context   # 模块上下文知识
│   └── {module_name}# 按模块组织
└── test_experience  # 测试经验知识
    ├── common_issue # 常见问题
    └── best_practice# 最佳实践

标签 (tags): 自由标签，用于灵活过滤
```

### Decision 3: 知识检索策略
**选择**: 混合检索 = 关键词匹配 + 语义相似度 + 重排序

```python
def retrieve_knowledge(query: str, context: dict) -> List[Knowledge]:
    # 1. 关键词预筛选（高效）
    candidates = keyword_filter(query, context.get('tags'), context.get('type'))
    
    # 2. 语义相似度排序（精准）
    query_vector = embed(query)
    scored = [(k, cosine_similarity(query_vector, k.vector)) for k in candidates]
    
    # 3. 上下文重排序（相关性）
    reranked = rerank_by_context(scored, context)
    
    return reranked[:top_k]
```

### Decision 4: 知识学习机制
**选择**: LLM提取 + 人工确认

```
日志解析流程:
日志 → LogParser → 解析结果 
                      ↓
              KnowledgeLearner (LLM)
                      ↓
              知识建议 (pending状态)
                      ↓
              用户确认/修改/拒绝
                      ↓
              入库 (active状态)
```

**理由**: 
- 全自动学习可能产生错误知识
- 人工确认保证知识质量
- pending状态支持批量审核

### Decision 5: Embedding模型
**选择**: 支持多种模型，优先使用本地模型

优先级：
1. 现有LLM Provider的embedding接口（Ollama/OpenAI）
2. sentence-transformers本地模型（离线场景）
3. 简单的TF-IDF向量化（降级方案）

## Data Model

### 知识表结构

```sql
-- 知识条目表
CREATE TABLE knowledge_entries (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,              -- project_config|business_rule|module_context|test_experience
    category TEXT,                   -- 子分类
    title TEXT NOT NULL,             -- 知识标题
    content TEXT NOT NULL,           -- 知识内容
    scope TEXT,                      -- 适用范围（模块名、接口路径等）
    priority INTEGER DEFAULT 0,      -- 优先级（越高越重要）
    status TEXT DEFAULT 'active',    -- active|pending|archived
    source TEXT,                     -- 知识来源（manual|log_learning|test_learning）
    source_ref TEXT,                 -- 来源引用（日志ID、测试ID等）
    metadata TEXT,                   -- JSON格式的额外信息
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT,
    version INTEGER DEFAULT 1
);

-- 知识标签关联表
CREATE TABLE knowledge_tags (
    knowledge_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (knowledge_id, tag),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_entries(id)
);

-- 知识版本历史表
CREATE TABLE knowledge_history (
    id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    changed_by TEXT,
    changed_at TEXT NOT NULL,
    change_type TEXT,               -- create|update|archive
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_entries(id)
);

-- 知识应用记录表（用于统计和优化）
CREATE TABLE knowledge_usage (
    id TEXT PRIMARY KEY,
    knowledge_id TEXT NOT NULL,
    used_in TEXT NOT NULL,          -- test_generation|log_analysis|...
    context TEXT,                   -- 使用上下文
    helpful INTEGER,                -- 用户反馈：1有帮助, 0无帮助, -1有害
    used_at TEXT NOT NULL,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_entries(id)
);
```

## Architecture

### 模块结构

```
ai_test_tool/
└── knowledge/                      # 知识库模块
    ├── __init__.py
    ├── models.py                   # 知识数据模型
    ├── store.py                    # 知识存储层（SQLite + ChromaDB）
    ├── retriever.py                # 知识检索器
    ├── learner.py                  # 知识学习引擎
    ├── embeddings.py               # 向量化适配器
    └── rag_builder.py              # RAG上下文构建器
```

### 集成点

```python
# 测试生成时集成
class TestCaseGenerator:
    def generate_from_requests(self, requests, ...):
        # 检索相关知识
        knowledge_context = self.knowledge_retriever.retrieve(
            query=request.url,
            context={
                'type': ['project_config', 'business_rule'],
                'tags': [request.module],
            }
        )
        
        # 构建RAG上下文
        rag_context = self.rag_builder.build(knowledge_context)
        
        # 传入LLM生成
        return self.llm_chain.generate(request, rag_context=rag_context)

# 日志解析时学习
class LogParser:
    def parse_file(self, file_path, ...):
        results = self._do_parse(file_path)
        
        # 尝试学习新知识
        if self.enable_learning:
            suggestions = self.knowledge_learner.extract_from_logs(results)
            self._save_pending_knowledge(suggestions)
        
        return results
```

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| ChromaDB依赖增加部署复杂度 | 中 | 提供纯SQLite降级方案 |
| Embedding模型体积大 | 中 | 支持使用现有LLM Provider的embedding |
| 知识质量难以保证 | 高 | 人工确认机制 + 使用反馈循环 |
| 检索性能 | 低 | 预过滤 + 缓存热点知识 |

## Migration Plan

1. **Phase 1**: 添加知识表结构，实现基础CRUD
2. **Phase 2**: 集成ChromaDB，实现语义检索
3. **Phase 3**: 实现知识学习引擎
4. **Phase 4**: 集成到测试生成流程
5. **Phase 5**: 前端管理界面

可渐进式发布，每个阶段独立可用。

## Open Questions

- [ ] 是否需要支持知识导入/导出（JSON/YAML格式）？
- [ ] 知识的自动过期/清理策略？
- [ ] 是否需要知识之间的关联关系？
