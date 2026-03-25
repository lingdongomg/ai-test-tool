# AI Test Tool - 知识库架构可视化

## 整体架构流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                     日志/文档/测试结果输入                         │
└──────┬──────────────────────┬──────────────────────┬──────────────┘
       │                      │                      │
       ↓                      ↓                      ↓
   ┌────────────┐        ┌────────────┐       ┌──────────────┐
   │ LogParser  │        │ TestResult │       │  APIDocImporter │
   │ 日志解析    │        │ Parser     │       │  文档导入      │
   │(多格式支持) │        │            │       │               │
   └──────┬─────┘        └────────┬───┘       └────────┬───────┘
          │                       │                    │
          ↓                       ↓                    ↓
   ┌──────────────────────────────────────────────────────────┐
   │            KnowledgeLearner (知识学习引擎)                │
   ├──────────────────────────────────────────────────────────┤
   │ • extract_from_log_analysis()                            │
   │ • extract_from_test_results()   ⚠️ 无调用点              │
   │ • extract_from_api_doc()        ⚠️ 无调用点              │
   │                                                          │
   │ 分析维度:                                                │
   │  - HTTP方法/状态码分布                                   │
   │  - Header模式                                           │
   │  - URL模式                                              │
   │  - 错误模式                                              │
   │  - 多样化采样                                            │
   └──────────────────┬───────────────────────────────────────┘
                      │
                      ↓ KnowledgeSuggestion[]
        (title, content, type, confidence, tags, ...)
                      │
                      ↓ [置信度 < 0.3 过滤]
        ┌─────────────────────────────────┐
        │  KnowledgeStore.create()        │
        │  (混合存储: SQLite + ChromaDB)  │
        └─────────────────────────────────┘
             ↙              ↓              ↖
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │ knowledge_   │ │ knowledge_   │ │ knowledge_   │
   │ entries      │ │ history      │ │ tags         │
   │ (元数据)     │ │ (版本历史)   │ │ (多对多)     │
   └──────────────┘ └──────────────┘ └──────────────┘
        ↙
   ┌──────────────────────────────────┐
   │  ChromaDB Vector Collection      │
   │  knowledge_embeddings            │
   │  (语义搜索索引)                   │
   └──────────────────────────────────┘

   状态流转:
   confidence >= 0.8 + auto_approve=true → ACTIVE ✓
   0.3 ≤ confidence < 0.8 → PENDING (审核)
   confidence < 0.3 → 过滤(丢弃)

────────────────────────────────────────────────────

API 检索阶段:

   ┌──────────────────────┐
   │  KnowledgeRetriever  │
   └──────────┬───────────┘
              │
        ┌─────┴─────┬────────────┬──────────┐
        ↓           ↓            ↓          ↓
    [语义搜索] [关键词搜索] [范围过滤] [类型过滤]
    (ChromaDB) (SQLite)    (scope)   (type/status)
        │           │            │          │
        └─────┬─────┴────────────┴──────────┘
              ↓
    KnowledgeSearchResult[] (按相似度排序)
              │
              ↓
   ┌─────────────────────────────────┐
   │  RAGContextBuilder              │
   │  (构建AI Prompt的上下文)         │
   └────────────────┬────────────────┘
                    ↓
         RAGContext (格式化文本 + token估算)
                    │
                    ↓
         注入 LLM Prompt → 生成测试用例

────────────────────────────────────────────────────

两套知识库系统对比:

┌─────────────────────────┬─────────────────────────┐
│   ApiKnowledgeBase      │   KnowledgeStore        │
│  (analyzer/)            │  (knowledge/)           │
├─────────────────────────┼─────────────────────────┤
│ 存储: 内存              │ 存储: SQLite + ChromaDB │
│ 来源: API文档           │ 来源: 多源              │
│ 能力: URL匹配           │ 能力: 语义搜索          │
│ 缺点: 无持久化/审核     │ 优点: 完整生命周期      │
│                         │                         │
│ ⚠️ 需要整合到 retriever │ ✅ 生产就绪             │
└─────────────────────────┴─────────────────────────┘

```

## 数据流与文件对应关系

```
输入层:
 ├─ parser/log_parser.py
 │  └─ ParsedRequest (URL, method, headers, status, ...)
 │
 ├─ database/models/knowledge.py
 │  └─ KnowledgeEntry (持久化模型)
 │
 └─ knowledge/models.py
    └─ KnowledgeSuggestion (学习建议模型)

处理层:
 ├─ knowledge/learner.py
 │  ├─ extract_from_log_analysis()       ✓ 已接入
 │  ├─ extract_from_test_results()       ⚠️ 无调用点
 │  └─ extract_from_api_doc()            ⚠️ 无调用点
 │
 └─ knowledge/store.py
    ├─ create() / update() / delete()
    ├─ search_paginated() (SQLite)
    ├─ rebuild_vector_index() (ChromaDB)
    └─ create_from_suggestion()

检索层:
 ├─ knowledge/retriever.py
 │  └─ retrieve(KnowledgeContext) → KnowledgeSearchResult[]
 │
 └─ knowledge/rag_builder.py
    └─ build(results) → RAGContext

API层:
 ├─ api/routes/knowledge.py
 │  ├─ POST /learn-from-file ✓
 │  ├─ POST /learn-from-task ✓
 │  ├─ POST /search ✓
 │  ├─ GET /pending ✓
 │  ├─ POST /review ✓
 │  └─ POST /rebuild-index ✓
 │
 └─ database/repositories/knowledge.py
    └─ 数据库访问层 (CRUD, 批量操作)

缺失的接入点:
 ├─ tests完成 → extract_from_test_results()
 ├─ docs导入 → extract_from_api_doc()
 ├─ 异常检测 → knowledge learning
 ├─ 路由分析 → save to knowledge
 └─ ApiKnowledgeBase → 整合到 retriever

```

## 知识生命周期

```
1️⃣  创建阶段 (CREATE)
    ↓
2️⃣  待审核 (PENDING) ← 置信度 0.3-0.8
    ├─ 用户审核: 批准 / 拒绝
    ├─ 自动激活: confidence >= 0.8 + auto_approve
    ↓
3️⃣  活跃 (ACTIVE)
    ├─ 可被 retriever 检索
    ├─ 用于增强 LLM Prompt
    ├─ 统计使用次数
    ↓
4️⃣  更新 (UPDATE)
    ├─ 版本递增
    ├─ 历史记录保存
    ↓
5️⃣  归档 (ARCHIVED)
    └─ 软删除，可恢复
```

## 关键配置参数

```python
# 日志解析
max_lines_per_batch = 50        # 批处理行数
max_chars_per_batch = 6000      # 批处理字符数

# 置信度
CONFIDENCE_FILTER = 0.3         # 过滤阈值
CONFIDENCE_AUTO_APPROVE = 0.8   # 自动激活阈值

# 检索
DEFAULT_TOP_K = 5               # 默认返回结果数
MIN_SCORE = 0.3                 # 最低相似度

# 采样
MAX_SAMPLES_FOR_LLM = 20        # LLM 分析的样本数
ERROR_QUOTA = MAX_SAMPLES // 2  # 错误请求优先级
```

## 知识类型树

```
KnowledgeType
├─ project_config (项目配置)
│  ├─ 认证方式 (OAuth, JWT, API Key, ...)
│  ├─ 通用 Header (User-Agent, Content-Type, ...)
│  └─ 环境变量 (BASE_URL, API_KEY, ...)
│
├─ business_rule (业务规则)
│  ├─ 参数约束 (必填字段, 格式, 取值范围, ...)
│  ├─ 业务逻辑 (状态转移, 排他性规则, ...)
│  └─ 限制条件 (频率限制, 配额, ...)
│
├─ module_context (模块上下文)
│  ├─ 功能描述 (模块名称, 职责, ...)
│  ├─ 依赖关系 (调用顺序, 前置条件, ...)
│  └─ 接口组织 (分组, 版本控制, ...)
│
└─ test_experience (测试经验)
   ├─ 常见错误 (5xx, 超时, 并发问题, ...)
   ├─ 边界情况 (空值, 极值, 特殊字符, ...)
   └─ 最佳实践 (测试顺序, 数据准备, ...)
```

