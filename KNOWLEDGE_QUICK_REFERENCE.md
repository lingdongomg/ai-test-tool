# AI Test Tool 知识库模块 - 快速参考指南

## 📚 核心文件速查表

| 文件 | 类 | 主要功能 |
|------|-----|--------|
| `parser/log_parser.py` | `LogParser` | AI 日志解析 |
| `knowledge/learner.py` | `KnowledgeLearner` | 知识提取（3 种方法）|
| `knowledge/store.py` | `KnowledgeStore` | 知识存储（SQLite + ChromaDB）|
| `knowledge/retriever.py` | `KnowledgeRetriever` | 知识检索（多策略）|
| `knowledge/rag_builder.py` | `RAGContextBuilder` | RAG 上下文构建 |
| `analyzer/api_knowledge_base.py` | `ApiKnowledgeBase` | 接口知识库（内存）⚠️ 需整合 |
| `database/repositories/knowledge.py` | `KnowledgeRepository` | 数据库访问 |
| `api/routes/knowledge.py` | 路由处理 | RESTful API 端点 |

---

## 🔄 知识提取三步工作流

### Step 1: 解析输入
```python
# 日志解析
from parser.log_parser import LogParser
parser = LogParser(llm_chain=chain)
parsed_requests = parser.parse_file("app.log")  # Generator

# 或使用便捷函数
from parser.log_parser import analyze_log_file
result = analyze_log_file("app.log", max_lines=1000)
```

### Step 2: 提取知识建议
```python
from knowledge.learner import KnowledgeLearner
from knowledge.store import KnowledgeStore

store = KnowledgeStore()
learner = KnowledgeLearner(store)

# 从日志提取（已接入 ✓）
suggestions = learner.extract_from_log_analysis(parsed_requests)

# 从测试结果提取（⚠️ 无调用点）
suggestions = learner.extract_from_test_results(test_results)

# 从 API 文档提取（⚠️ 无调用点）
suggestions = learner.extract_from_api_doc(swagger_doc)
```

### Step 3: 存储与审核
```python
# 方式A: 自动保存与过滤
for suggestion in suggestions:
    if suggestion.confidence >= 0.3:
        item = store.create_from_suggestion(suggestion)
        if suggestion.confidence >= 0.8:
            store.approve([item.knowledge_id])

# 方式B: 使用便捷方法
created_ids = learner.learn_and_save(content, auto_approve=False)

# 方式C: 从文件学习
created_ids = learner.learn_from_task(task_id="task-123")
```

---

## 🔍 知识检索四步工作流

### Step 1: 构建检索上下文
```python
from knowledge.models import KnowledgeContext

context = KnowledgeContext(
    query="如何测试用户认证接口",
    types=["test_experience"],
    tags=["auth", "best-practice"],
    scope="/api/user",
    top_k=5,
    min_score=0.3
)
```

### Step 2: 执行多策略检索
```python
from knowledge.retriever import KnowledgeRetriever

retriever = KnowledgeRetriever(store)
results = retriever.retrieve(context)
# 返回 list[KnowledgeSearchResult]
# 每个结果包含: item, score, source
```

### Step 3: 构建 RAG 上下文
```python
from knowledge.rag_builder import RAGContextBuilder

builder = RAGContextBuilder()
rag_context = builder.build(results)
# 返回 RAGContext
# 包含: context_text, knowledge_items, token_count
```

### Step 4: 注入 LLM
```python
prompt = f"""
基于以下知识库信息：
{rag_context.context_text}

现在生成测试用例...
"""
response = llm.invoke(prompt)
```

---

## 📊 知识库数据模型

### ParsedRequest（日志解析结果）
```python
@dataclass
class ParsedRequest:
    request_id: str           # UUID
    timestamp: str            # 时间戳
    method: str              # GET/POST/PUT...
    url: str                 # 完整 URL
    headers: dict            # 请求头
    http_status: int         # 响应状态码
    response_time_ms: float  # 响应时间
    has_error: bool          # 是否有错误
    error_message: str       # 错误信息
    curl_command: str        # 自动生成的 curl
    metadata: dict           # 扩展元数据
```

### KnowledgeSuggestion（知识建议）
```python
@dataclass
class KnowledgeSuggestion:
    title: str               # 标题
    content: str             # 内容
    type: str                # project_config | business_rule | module_context | test_experience
    category: str            # 子分类
    scope: str               # 适用范围
    tags: list[str]          # 标签
    confidence: float        # 置信度 0-1 ⭐
    source_ref: str          # 来源引用
    reason: str              # 提取原因
```

### KnowledgeEntry（知识条目）
```python
@dataclass
class KnowledgeEntry:
    knowledge_id: str        # kb_xxxxx
    title: str
    content: str
    type: KnowledgeType      # 枚举
    status: KnowledgeStatus  # ACTIVE | PENDING | ARCHIVED
    priority: int            # 优先级
    tags: list[str]
    scope: str               # 适用范围
    source: KnowledgeSource  # manual | log_parsing | test_execution | api_doc...
    source_ref: str          # 来源 ID
    created_at: datetime
    updated_at: datetime
    version: int             # 版本号
```

### KnowledgeSearchResult（检索结果）
```python
@dataclass
class KnowledgeSearchResult:
    item: KnowledgeItem      # 知识条目
    score: float            # 相似度分数 0-1
    source: str             # 匹配来源: semantic | keyword | scope
```

### RAGContext（RAG 上下文）
```python
@dataclass
class RAGContext:
    context_text: str        # 格式化的上下文文本
    knowledge_items: list    # 原始知识条目
    token_count: int         # 估算 token 数
    is_empty: bool           # 是否为空
```

---

## 🎯 关键参数与常数

### 日志解析配置
```python
max_lines_per_batch = 50         # 每批最多 50 行
max_chars_per_batch = 6000       # 每批最多 6000 字符
```

### 置信度阈值
```python
confidence_filter = 0.3          # < 0.3 被丢弃
confidence_auto_approve = 0.8    # >= 0.8 自动激活 ACTIVE
```

### 检索配置
```python
default_top_k = 5                # 默认返回 5 个结果
default_min_score = 0.3          # 最低相似度阈值
```

### 采样策略
```python
max_samples = 20                 # LLM 分析最多 20 个样本
error_quota = 10                 # 其中最多 10 个是错误请求
```

---

## 🔗 API 端点快速查询

| 方法 | 端点 | 功能 | 参数 |
|------|------|------|------|
| POST | `/learn-from-file` | 上传日志学习 | file, auto_approve, max_lines |
| POST | `/learn-from-task` | 从分析任务学习 | task_id, auto_approve |
| POST | `/search` | 语义检索 | query, types, tags, scope, top_k, min_score |
| GET | `/pending` | 获取待审核 | limit |
| POST | `/review` | 批量审核 | knowledge_ids, action(approve\|reject) |
| GET | `/statistics` | 统计信息 | - |
| POST | `/rebuild-index` | 重建向量索引 | - |

---

## ⚠️ 已知问题与 TODO

### 问题1: 自动学习链路断裂
```python
# 已编写但无调用点的方法：
KnowledgeLearner.extract_from_test_results()  # ⚠️ 需在执行完成后触发
KnowledgeLearner.extract_from_api_doc()       # ⚠️ 需在导入后触发

# 解决方案：在以下位置添加调用
# - tests/test_executor.py (执行完成)
# - importer/doc_importer.py (导入后)
# - services/log_anomaly_detector.py (异常检测后)
# - routing/router.py (路由分析后)
```

### 问题2: 两套知识库系统割裂
```python
# 当前：
analyzer/api_knowledge_base.py    # 内存，URL 匹配能力
knowledge/                        # 持久化，语义搜索能力

# 需要整合：
# 将 ApiKnowledgeBase 的 URL 匹配作为 retriever 的一个策略
# 统一接口和数据流
```

### 问题3: AI 分析结论未入库
```python
# 当前：
services/intelligent_analysis.py  # 分析但不入库
services/ai_assistant.py          # 生成 insight 但不入库

# 需要：
# 定期同步分析结论为 pending 知识
# 用户审核后进入 knowledge_base
```

---

## 💡 使用场景示例

### 场景 A: 日志文件自动学习工作流
```python
# 1. 用户上传日志文件
# POST /api/v2/knowledge/learn-from-file
#   file: app.log
#   auto_approve: false
#   max_lines: 1000

# 2. 后端处理：
#   - LogParser 分批解析
#   - KnowledgeLearner 提取建议
#   - 置信度 >= 0.8 → ACTIVE ✓
#   - 置信度 0.3-0.8 → PENDING (用户审核)
#   - 置信度 < 0.3 → 过滤

# 3. 返回结果：
{
    "created_count": 15,
    "knowledge_ids": ["kb_xxx", ...],
    "items": [
        {
            "knowledge_id": "kb_xxx",
            "title": "用户认证需要 Authorization Header",
            "type": "project_config",
            "confidence": 0.92,
            "status": "active"  # 因为 >= 0.8 且 auto_approve=true
        },
        ...
    ]
}
```

### 场景 B: 测试生成时的 RAG 增强
```python
# 1. 用户要生成 /api/user/auth 的测试用例
query = "如何测试用户认证端点"

# 2. 调用检索：
context = KnowledgeContext(query=query, scope="/api/user")
results = retriever.retrieve(context)

# 3. 构建 RAG：
rag_context = builder.build(results)

# 4. 生成提示词：
prompt = f"""
参考知识：
{rag_context.context_text}

为 /api/user/auth 生成测试用例...
"""

# 5. LLM 生成更准确的测试用例
test_cases = llm.generate(prompt)
```

### 场景 C: 知识库管理与审核
```python
# 查看待审核知识
GET /api/v2/knowledge/pending?limit=50

# 批量审核
POST /api/v2/knowledge/review
{
    "knowledge_ids": ["kb_xxx", "kb_yyy"],
    "action": "approve"  # 或 "reject"
}

# 获取统计
GET /api/v2/knowledge/statistics
{
    "total": 100,
    "active": 80,
    "pending": 15,
    "archived": 5,
    "by_type": [
        {"type": "project_config", "count": 30},
        {"type": "test_experience", "count": 50},
        ...
    ]
}
```

---

## 🚀 下一步改进建议

### Priority 1: 完成自动学习链路
- [ ] 在 test executor 完成后触发 `extract_from_test_results()`
- [ ] 在 doc importer 完成后触发 `extract_from_api_doc()`
- [ ] 在异常检测后触发知识学习
- [ ] 前端 knowledge 页面增加"从文本学习"入口

### Priority 2: 系统统一
- [ ] 整合 ApiKnowledgeBase 到 retriever
- [ ] AI Insight 持久化到 knowledge_base
- [ ] 智能路由接入 RAG 检索

### Priority 3: 用户体验
- [ ] 知识评分与反馈机制
- [ ] 知识使用统计与热度排名
- [ ] 知识版本比较与回滚
- [ ] 自动去重与冲突解决

---

## 📖 参考文档位置

- 完整设计文档：`PROJECT_EXPLORATION_SUMMARY.md`
- 架构可视化：`ARCHITECTURE_OVERVIEW.md`
- 项目规范：`openspec/project.md`
- 最新改进提案：`openspec/changes/fix-platform-integrity-and-knowledge-loop/`

