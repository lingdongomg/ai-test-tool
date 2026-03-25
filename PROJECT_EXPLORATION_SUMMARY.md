# AI Test Tool - 项目全面探索报告

## 项目概述

**AI Test Tool** 是一个智能 API 测试工具，利用大语言模型（LLM）实现智能日志解析、自动测试用例生成、生产环境监控、RAG 知识库、多场景测试等功能。项目采用现代全栈架构（FastAPI + Vue 3）。

### 核心技术栈
- **后端**：FastAPI 0.115+、Python 3.13+、SQLite、ChromaDB（向量数据库）、LangChain 1.2+
- **前端**：Vue 3.4+、TypeScript 5.3+、Vite 5、TDesign Vue Next
- **LLM 支持**：Ollama（推荐）、OpenAI、Anthropic、Azure OpenAI

---

## 一、知识提取与日志处理的当前实现

### 1.1 日志解析引擎 (`parser/log_parser.py`)

**核心类**：`LogParser`

**功能**：
- AI 驱动的日志解析，支持任意格式（JSON、JSONL、纯文本）
- 支持流式处理大文件（分批解析）
- 两层级联策略：优先使用 AI 解析，失败时降级至规则解析

**解析流程**：
1. 分批读取日志文件（配置：最多 50 行/批或 6000 字符/批）
2. 每批调用 `llm_chain.analyze_logs()` 进行 AI 分析
3. 解析结果构建 `ParsedRequest` 对象（包含请求元数据、状态码、响应时间等）
4. 自动生成 curl 命令

**关键数据结构**：
```python
@dataclass
class ParsedRequest:
    request_id: str              # UUID
    timestamp: str
    method: str                  # GET, POST 等
    url: str                     # 完整 URL
    headers: dict[str, str]
    body: str | None
    query_params: dict[str, str]
    http_status: int             # 状态码
    response_time_ms: float      # 响应时间
    response_body: str | None
    category: str                # 请求分类
    has_error: bool
    error_message: str
    has_warning: bool
    warning_message: str
    curl_command: str            # 自动生成的 curl
    raw_logs: list[str]         # 原始日志行
    metadata: dict[str, Any]    # 扩展元数据
```

**规则解析降级**：
- JSON 格式检测和提取
- HTTP 方法模式匹配（GET、POST 等）
- 状态码提取（正则：`\|\s*(\d{3})\s*\|`）
- 响应时间提取（支持 ms/µs/us/s）
- 请求 ID 提取（UUID 格式）

**调用示例**：
```python
# 从项目根目录使用
from parser.log_parser import analyze_log_file

result = analyze_log_file("path/to/log.txt", max_lines=1000)
print(f"解析 {len(result.requests)} 个请求")
```

---

### 1.2 知识学习引擎 (`knowledge/learner.py`)

**核心类**：`KnowledgeLearner`

**三大知识提取方法**：

#### 1. `extract_from_log_analysis()` - 从日志解析提取知识
```
输入：解析的请求列表 + 任务 ID
→ 分析 HTTP 方法分布、状态码分布、Header 模式、URL 模式、错误模式
→ 多样化采样（优先错误请求、覆盖不同 URL 分组）
→ 调用 LLM 提取知识建议
返回：list[KnowledgeSuggestion]
```

**分析维度**：
- HTTP 方法分布（GET、POST、PUT 等计数）
- 响应状态码分布（4xx、5xx 等）
- Header 出现频率（高频 Header 提示认证方式等）
- URL 路径前缀分布
- 错误模式聚类
- 样例请求多样化采样（20 个）

#### 2. `extract_from_test_results()` - 从测试失败提取知识
```
输入：测试结果列表（包含失败信息）+ 执行 ID
→ 筛选失败测试
→ 构建失败分析文本
→ 调用 LLM 提取根本原因和防护知识
返回：list[KnowledgeSuggestion]
```

#### 3. `extract_from_api_doc()` - 从 API 文档提取知识
```
输入：OpenAPI/Swagger 文档 + 源文件名
→ 提取安全配置、通用参数模式、通用 Header 模式
→ 调用 LLM 提取配置最佳实践
返回：list[KnowledgeSuggestion]
```

**知识建议数据结构**：
```python
@dataclass
class KnowledgeSuggestion:
    title: str                # 知识标题
    content: str             # 详细内容
    type: str                # project_config | business_rule | module_context | test_experience
    category: str            # 子分类
    scope: str               # 适用范围（如接口路径 /api/live/*）
    tags: list[str]         # 分类标签
    confidence: float        # 置信度 0-1
    source_ref: str         # 来源引用
    reason: str             # 提取原因
```

**LLM 提示词**：
- 定义 4 种知识类型的具体含义
- 要求返回 JSON 数组格式
- 强制要求包含置信度、提取原因
- 建议避免过度通用的知识

**置信度过滤**：
- 建议默认过滤置信度 < 0.3
- `auto_approve=True` 时，>= 0.8 的知识直接激活（`ACTIVE` 状态）
- 置信度 0.3-0.8 的知识进入 `PENDING` 审核

**已编写但无调用点的方法**：
- `extract_from_test_results()` - 需在执行完成后触发
- `extract_from_api_doc()` - 需在文档导入后触发

---

### 1.3 知识库存储层 (`knowledge/store.py`)

**核心类**：`KnowledgeStore`

**混合存储架构**：
- **SQLite**：元数据持久化（id、title、content、type、status、tags 等）
- **ChromaDB**：向量索引（语义搜索）

**核心方法**：

| 方法 | 功能 |
|------|------|
| `create()` | 创建知识条目，同时写入向量索引和历史记录 |
| `update()` | 更新知识，自动版本递增 |
| `search()` / `search_paginated()` | 按类型、状态、标签、范围、关键词搜索 |
| `get_by_scope()` | 获取特定范围的知识（如接口路径） |
| `get_pending()` | 获取待审核知识 |
| `approve()` / `reject()` | 审核知识（改变状态） |
| `rebuild_vector_index()` | 重建 ChromaDB 索引 |
| `create_from_suggestion()` | 从 KnowledgeSuggestion 创建知识 |

**知识条目模型**：
```python
@dataclass
class KnowledgeEntry:
    knowledge_id: str          # 唯一标识
    title: str
    content: str
    type: KnowledgeType        # 枚举：PROJECT_CONFIG, BUSINESS_RULE, MODULE_CONTEXT, TEST_EXPERIENCE
    category: str              # 子分类
    scope: str                 # 适用范围
    priority: int              # 优先级
    status: KnowledgeStatus    # ACTIVE, PENDING, ARCHIVED
    source: KnowledgeSource    # MANUAL, LOG_PARSING, TEST_EXECUTION, API_DOC, ...
    source_ref: str            # 来源引用（任务 ID、文件路径等）
    metadata: dict             # 扩展元数据
    tags: list[str]            # 标签
    created_at: datetime       # 创建时间
    updated_at: datetime       # 更新时间
    created_by: str            # 创建者
    version: int               # 版本号
```

**关联表**：
- `knowledge_tags` - 知识与标签的多对多关系
- `knowledge_history` - 版本历史记录
- `knowledge_usage` - 知识使用统计

**向量化过程**：
- 将 `title + content + tags` 合并作为 embedding 文本
- 调用 embedding 提供商（支持 Ollama、OpenAI 等）
- 存入 ChromaDB 的 `knowledge_embeddings` collection

---

### 1.4 知识检索与 RAG (`knowledge/retriever.py` 和 `knowledge/rag_builder.py`)

**核心类**：`KnowledgeRetriever`

**检索策略**（多层级）：

1. **语义搜索**（ChromaDB）
   - 输入查询文本 embedding
   - 返回余弦相似度最高的 K 个结果
   - 可设定最低阈值 `min_score`

2. **关键词搜索**（SQLite LIKE）
   - 在 title/content 中模糊匹配
   - 在 tags 中精确匹配

3. **范围过滤**（Scope）
   - 按接口路径、功能模块筛选
   - 支持前缀匹配

4. **类型/状态过滤**
   - 限制返回活跃的知识条目
   - 按知识类型筛选

**检索上下文**：
```python
@dataclass
class KnowledgeContext:
    query: str                 # 查询文本
    types: list[str]          # 限制知识类型
    tags: list[str]           # 限制标签
    scope: str                # 限制范围
    top_k: int                # 返回数量
    min_score: float          # 最低相似度阈值
```

**RAG 上下文构建**：
```python
@dataclass
class RAGContext:
    context_text: str         # 格式化的上下文文本
    knowledge_items: list[KnowledgeItem]  # 原始条目
    token_count: int          # 估算 token 数
```

---

### 1.5 接口知识库 (`analyzer/api_knowledge_base.py`)

**现状**：两套平行的知识库系统
- **内存知识库** (`api_knowledge_base.py`)：针对 API 文档，支持 URL 匹配和覆盖分析
- **持久化知识库** (`knowledge/` 模块)：RAG 增强，支持语义搜索和审核流程

**接口知识库功能**：

| 方法 | 功能 |
|------|------|
| `load_from_endpoints()` | 从 API 端点列表加载 |
| `search_by_url()` | 根据请求 URL 搜索匹配接口（多层级匹配：精确、规范化路径、路径段） |
| `search_by_tag()` | 按标签搜索 |
| `build_rag_context()` | 为一组 URL 构建 RAG 上下文 |
| `analyze_coverage()` | 分析日志 URL 与接口文档的覆盖率 |
| `sync_to_knowledge_store()` | 将内存知识同步到持久化存储 |

**匹配策略**：
1. 精确路径匹配（100 分）
2. 规范化路径匹配（80 分）- 如将 `/user/123` 匹配到 `/user/{id}`
3. 路径段模糊匹配（最多 60 分）

**覆盖分析输出**：
```python
{
    "total_log_urls": 150,
    "matched_count": 140,
    "unmatched_count": 10,
    "match_rate": "93.3%",
    "total_doc_endpoints": 50,
    "called_endpoints": 45,
    "uncalled_endpoints": 5,
    "doc_coverage": "90%",
    "unmatched_urls": [...],      # 可能是第三方接口
    "uncalled_endpoints_list": [...],
    "matched_details": [...]
}
```

---

## 二、知识库相关的 API 端点

**路由前缀**：`/api/v2/knowledge`

### 2.1 CRUD 操作

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/` | 列出知识（支持分页、筛选） |
| GET | `/{knowledge_id}` | 获取单个知识详情 |
| POST | `/` | 创建知识 |
| PUT | `/{knowledge_id}` | 更新知识 |
| DELETE | `/{knowledge_id}` | 删除/归档知识 |

### 2.2 待审核与审核

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/pending` | 列出待审核知识 |
| POST | `/review` | 批量审核（approve/reject） |

### 2.3 检索与学习

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/search` | 语义检索知识 |
| POST | `/learn` | 从文本学习知识 |
| POST | `/learn-from-task` | 从分析任务学习知识 |
| POST | `/learn-from-file` | 上传日志文件学习知识 |

### 2.4 工具与统计

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/statistics` | 获取知识库统计 |
| POST | `/rebuild-index` | 重建向量索引 |

---

## 三、知识库结构与数据库设计

### 3.1 核心表结构

**`knowledge_entries`** - 知识主表
```sql
CREATE TABLE knowledge_entries (
    id INTEGER PRIMARY KEY,
    knowledge_id TEXT UNIQUE,
    type TEXT,                    -- project_config, business_rule, module_context, test_experience
    category TEXT,
    title TEXT,
    content TEXT,
    scope TEXT,                   -- 适用范围（如 /api/live/*）
    priority INTEGER,
    status TEXT,                  -- active, pending, archived
    source TEXT,                  -- manual, log_parsing, test_execution, api_doc, ...
    source_ref TEXT,              -- 来源引用
    metadata TEXT,                -- JSON
    created_by TEXT,
    version INTEGER,
    created_at DATETIME,
    updated_at DATETIME
);
```

**`knowledge_tags`** - 标签关联
```sql
CREATE TABLE knowledge_tags (
    knowledge_id TEXT,
    tag TEXT,
    PRIMARY KEY (knowledge_id, tag)
);
```

**`knowledge_history`** - 版本历史
```sql
CREATE TABLE knowledge_history (
    id INTEGER PRIMARY KEY,
    knowledge_id TEXT,
    version INTEGER,
    title TEXT,
    content TEXT,
    change_type TEXT,             -- create, update, delete, approve, reject
    changed_by TEXT,
    changed_at DATETIME
);
```

**`knowledge_usage`** - 使用统计
```sql
CREATE TABLE knowledge_usage (
    usage_id TEXT PRIMARY KEY,
    knowledge_id TEXT,
    used_in TEXT,                 -- 使用场景
    context TEXT,                 -- 使用上下文
    helpful INTEGER,              -- 1=有帮助, 0=未评价, -1=无帮助
    used_at DATETIME
);
```

### 3.2 知识类型分类

| 类型 | 说明 | 示例 |
|------|------|------|
| `project_config` | 项目配置知识 | 认证方式、通用 Header、环境变量 |
| `business_rule` | 业务规则知识 | 特定模块的参数要求、业务逻辑约束 |
| `module_context` | 模块上下文知识 | 模块功能描述、依赖关系 |
| `test_experience` | 测试经验知识 | 常见错误、边界情况、最佳实践 |

### 3.3 知识来源追踪

| 来源 | 说明 |
|------|------|
| `manual` | 手动创建 |
| `log_parsing` | 日志解析 |
| `test_execution` | 测试执行结果 |
| `api_doc` | API 文档导入 |
| `log_file_learning` | 日志文件学习 |
| `api_knowledge_base_sync` | API 知识库同步 |

---

## 四、配置参数与常数

### 4.1 日志解析配置

```python
# parser/log_parser.py
self.max_chars_per_batch = 6000   # 每批次最大字符数
self.max_lines_per_batch = 50     # 每批次最大行数
```

### 4.2 知识提取提示词

**预设 Prompt**：
```
知识类型说明、输出格式、注意事项、示例
```

**LLM 要求输出 JSON 数组**，每条知识包含：
- `title`, `content`, `type`, `category`, `scope`, `tags`
- `confidence` (0-1)
- `reason` (提取原因)

### 4.3 置信度阈值

- **过滤阈值**：0.3（< 0.3 的建议被丢弃）
- **自动激活阈值**：0.8（>= 0.8 的知识直接进入 ACTIVE）
- **手动审核**：0.3-0.8 的知识进入 PENDING 状态

### 4.4 检索参数

```python
@dataclass
class KnowledgeContext:
    top_k: int = 5              # 默认返回 5 个结果
    min_score: float = 0.3      # 最低相似度阈值
```

---

## 五、知识库使用流程

### 5.1 从日志文件自动学习

```
1. 用户上传 .log/.txt/.json 文件 → POST /api/v2/knowledge/learn-from-file
   ↓
2. LogParser 分批解析 → ParsedRequest 列表
   ↓
3. KnowledgeLearner.extract_from_log_analysis()
   - 分析 HTTP 方法、状态码、Header 模式
   - 多样化采样请求
   - 调用 LLM 提取知识建议
   ↓
4. 按置信度过滤 & 创建知识条目
   - 置信度 >= 0.8 + auto_approve=true → ACTIVE
   - 其他 → PENDING（需人工审核）
   ↓
5. 返回 created_count, knowledge_ids, 详情
```

### 5.2 从测试失败学习（规划中）

```
测试执行完成 → KnowledgeLearner.extract_from_test_results()
   ↓ 分析失败原因
知识建议 → 存储 → 审核
```

### 5.3 从 API 文档学习（规划中）

```
导入 Swagger/OpenAPI → KnowledgeLearner.extract_from_api_doc()
   ↓ 提取安全配置、通用参数
知识建议 → 存储 → 审核
```

### 5.4 AI 生成测试时使用知识

```
1. 解析测试需求、API 文档
2. 调用 KnowledgeRetriever 获取相关知识
3. 构建 RAG 上下文
4. 注入 LLM Prompt → 生成更准确的测试用例
```

---

## 六、当前存在的问题与改进方向

### 6.1 已发现的问题（来自最新 PR 提案）

1. **知识库自动学习链路断裂**
   - `extract_from_test_results()` 无调用点（需在执行完成后触发）
   - `extract_from_api_doc()` 无调用点（需在导入后触发）
   - 异常检测完成后未触发知识学习
   - 智能路由分析结论未保存为知识

2. **两套知识库系统割裂**
   - `analyzer/api_knowledge_base.py`（内存）和 `knowledge/` 模块（持久化）完全隔离
   - API 知识库的 URL 匹配能力未集成到 RAG 检索中
   - 重复实现，维护成本高

3. **知识学习的未使用方法**
   - 即使编写了，也因为无调用入口而不生效

### 6.2 改进方案（从 change proposals 看）

**Phase 1: 知识库自动学习闭环**
- 测试执行完成后触发 `extract_from_test_results()`
- API 文档导入后触发 `extract_from_api_doc()`
- 异常检测完成后触发知识学习
- 智能路由分析结论保存为 pending 知识
- 前端增加"从文本学习"和"重建索引"入口

**Phase 2: 架构统一**
- 统一两套知识库系统
- 将 API 知识库的 URL 匹配能力整合为 retriever 策略
- AI Insight 统一持久化
- 智能路由策略接入知识检索

---

## 七、扩展与优化建议

### 7.1 特性增强

1. **知识评分与反馈**
   - 用户标记知识是否有帮助
   - 根据使用反馈调整优先级和置信度
   - 构建反馈闭环

2. **知识版本管理**
   - 支持知识版本比较
   - 支持版本回滚
   - 完整的修改历史审计

3. **知识演进分析**
   - 统计知识使用频率
   - 分析知识对测试用例质量的影响
   - 自动清理无用知识

4. **多源知识融合**
   - 合并相同或相似的知识条目
   - 自动去重
   - 冲突检测与解决

### 7.2 性能优化

1. **向量索引优化**
   - 增量 embedding（避免全量重建）
   - 定期清理过期知识
   - 索引分片存储

2. **检索优化**
   - 缓存热点查询
   - 多层级索引加速
   - 异步批量检索

3. **存储优化**
   - 知识内容压缩存储
   - 按时间分表
   - 冷热数据分离

---

## 八、代码组织总结

### 8.1 核心模块树

```
ai_test_tool/
├── parser/
│   └── log_parser.py           # 日志解析引擎
├── knowledge/
│   ├── __init__.py             # 公开接口
│   ├── models.py               # 数据模型（KnowledgeItem, KnowledgeSuggestion 等）
│   ├── store.py                # 存储层（SQLite + ChromaDB）
│   ├── retriever.py            # 检索层（多策略检索）
│   ├── learner.py              # 学习引擎（3 种提取方法）
│   ├── embeddings.py           # Embedding 提供商
│   ├── rag_builder.py          # RAG 上下文构建
│   └── url_matcher.py          # URL 匹配（可选）
├── analyzer/
│   └── api_knowledge_base.py   # 接口知识库（内存，需整合）
├── database/
│   ├── models/
│   │   └── knowledge.py        # 数据库模型
│   └── repositories/
│       └── knowledge.py        # 数据库访问层
├── api/
│   └── routes/
│       └── knowledge.py        # RESTful API
└── llm/
    └── chains.py               # LLM 链（LogAnalysisChain 等）
```

### 8.2 重要类与接口

| 类 | 文件 | 职责 |
|-----|------|------|
| `LogParser` | `parser/log_parser.py` | 日志解析 |
| `KnowledgeLearner` | `knowledge/learner.py` | 知识提取 |
| `KnowledgeStore` | `knowledge/store.py` | 知识存储 |
| `KnowledgeRetriever` | `knowledge/retriever.py` | 知识检索 |
| `RAGContextBuilder` | `knowledge/rag_builder.py` | RAG 上下文 |
| `ApiKnowledgeBase` | `analyzer/api_knowledge_base.py` | 接口知识库 |
| `KnowledgeRepository` | `database/repositories/knowledge.py` | 数据库访问 |

---

## 九、执行示例代码

### 9.1 解析日志文件

```python
from ai_test_tool.parser.log_parser import analyze_log_file

result = analyze_log_file("logs/app.log", max_lines=1000)
print(f"解析 {len(result.requests)} 个请求")
for req in result.requests[:5]:
    print(f"  {req.method} {req.url} → {req.http_status}")
```

### 9.2 从日志提取知识

```python
from ai_test_tool.knowledge.learner import KnowledgeLearner
from ai_test_tool.knowledge.store import KnowledgeStore

store = KnowledgeStore()
learner = KnowledgeLearner(store)

# 从日志解析结果提取知识
suggestions = learner.extract_from_log_analysis(parsed_requests)
print(f"提取 {len(suggestions)} 条知识建议")
for s in suggestions[:3]:
    print(f"  [{s.confidence}] {s.title} ({s.type})")

# 保存知识
created_ids = learner.learn_and_save(content, source_ref="manual", auto_approve=False)
```

### 9.3 检索知识

```python
from ai_test_tool.knowledge.retriever import KnowledgeRetriever
from ai_test_tool.knowledge.models import KnowledgeContext

retriever = KnowledgeRetriever(store)
context = KnowledgeContext(
    query="如何测试用户认证接口",
    types=["test_experience"],
    top_k=5,
    min_score=0.3
)
results = retriever.retrieve(context)
for r in results:
    print(f"  [{r.score:.2f}] {r.item.title}")
```

### 9.4 构建 RAG 上下文

```python
from ai_test_tool.knowledge.rag_builder import RAGContextBuilder

rag_builder = RAGContextBuilder()
rag_context = rag_builder.build(results)
print(f"RAG 上下文长度: {len(rag_context.context_text)} 字符")
print(f"Token 估算: {rag_context.token_count}")

# 使用 RAG 上下文注入 LLM Prompt
prompt = f"""
基于以下知识库信息：

{rag_context.context_text}

现在生成测试用例...
"""
```

---

## 十、总结

该项目已实现了一个**完整的知识库系统**，具有：

✅ **多源知识提取**：日志、测试结果、API 文档
✅ **混合存储**：SQLite 元数据 + ChromaDB 向量
✅ **多策略检索**：语义 + 关键词 + 范围过滤
✅ **质量管理**：置信度过滤、审核流程、版本历史
✅ **RESTful API**：完整的 CRUD、检索、审核接口

但仍存在的问题：
⚠️ **学习链路断裂**：3 个提取方法中有 2 个无调用点
⚠️ **系统割裂**：两套知识库系统未整合
⚠️ **自动化不足**：AI 分析结论未入库，路由策略未使用知识

**后续工作**应聚焦于：
1. 补齐自动学习触发点（测试完成、文档导入、异常检测）
2. 统一两套知识库系统
3. 智能路由接入 RAG 检索
4. 完善前端知识库管理界面
