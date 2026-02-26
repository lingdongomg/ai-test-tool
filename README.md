# AI Test Tool - 智能API测试与日志分析平台

基于LLM的智能日志分析和自动化测试平台，集成多层推理引擎，可自动解析日志、智能分析根因、生成测试用例并执行验证。

## 核心特性

### 智能分析引擎

- **多层推理架构**: 智能路由 + CoT链式推理 + ReAct交互推理 + 因果图分析
- **24种分析策略**: 覆盖错误诊断、性能分析、安全审计、根因定位等场景
- **告警智能过滤**: 去重、聚合、抑制、降噪，减少告警疲劳
- **健康度评分**: 多维指标评估，趋势分析，生成健康报告
- **Context Engineering**: 上下文管理、Token计数、滑动窗口、上下文压缩
- **Reflection 引擎**: 输出验证与自我修正循环，提升分析质量

### API测试功能

- **AI智能日志解析**: 自动分析任意格式日志，提取API请求信息
- **智能测试用例生成**: 自动生成正常、边界、异常测试用例
- **智能测试执行**: 异步并发执行测试，自动验证结果
- **测试场景编排**: 支持参数传递、断言验证、步骤编排

### 平台能力

- **多LLM支持**: Ollama(本地)、OpenAI、Anthropic、Azure等
- **SQLite数据持久化**: 轻量级数据库，开箱即用
- **接口文档导入**: 支持 Swagger/OpenAPI 和 Postman Collection
- **知识库RAG**: 接口文档知识库，增强AI分析准确性
- **REST API服务**: 完整的后台API，支持前端集成
- **现代化前端**: Vue 3 + TDesign 构建的管理界面
- **Docker容器化**: 一条命令启动完整服务栈

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              输入层                                          │
│    日志内容 / 解析请求 / 统计指标 / 用户提示                                     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         智能路由分发器                                        │
│                                                                             │
│   ┌─────────────┐    ┌─────────────────┐    ┌──────────────────────────┐   │
│   │  场景识别器  │───▶│  策略注册表     │───▶│  路由决策 + 策略执行      │   │
│   │ (5种匹配法) │    │  (24种策略)     │    │  (优先级排序+回退机制)    │   │
│   └─────────────┘    └─────────────────┘    └──────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
        ┌───────────────┬───────┴───────┬───────────────┐
        ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  基础统计    │ │  CoT 推理    │ │ ReAct Agent  │ │  因果分析    │
│  策略 (7)    │ │  链式思考(4) │ │ 交互推理 (4) │ │  图推理 (4)  │
│              │ │              │ │  + SSE 流式  │ │              │
│ 纯统计分析   │ │ 步骤链分析   │ │ 工具调用循环  │ │ 因果图构建   │
│ 无需LLM     │ │ 可追溯推理   │ │ 7种内置工具  │ │ 传播追踪     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       └───────────────┬┴───────────────┬┘                │
                       ▼                ▼                  │
              ┌──────────────┐  ┌──────────────┐           │
              │   Context    │  │  Reflection  │           │
              │ Engineering  │  │    引擎      │           │
              │ 上下文管理   │  │ 验证+修正    │           │
              └──────────────┘  └──────────────┘           │
                       │                │                  │
        ┌──────────────┴────────────────┴──────────────────┘
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              输出层                                          │
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │  告警过滤    │    │  健康评分    │    │  RAG 知识库  │                 │
│   │  去重/聚合   │    │  多维指标    │    │  向量检索    │                 │
│   │  抑制/降噪   │    │  趋势分析    │    │  增强分析    │                 │
│   └──────────────┘    └──────────────┘    └──────────────┘                 │
│                                                                             │
│                    结果聚合 → 报告生成                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 智能路由分发器

路由分发器是分析系统的核心调度器，负责接收输入、识别场景、选择策略并执行分析。

**场景识别器 (`ScenarioDetector`)** 采用5种匹配方法综合识别分析场景：

| 匹配方法 | 说明 | 示例 |
|---------|------|------|
| 关键词匹配 | 预定义关键词库 (中英文) | "error"、"超时"、"安全" |
| 正则模式 | 结构化日志模式识别 | `ERROR|FATAL`、`status[=:]\d{3}` |
| 阈值检测 | 基于统计指标判断 | 错误率>=10%、P99>=3s |
| LLM分类 | 低置信度时调用LLM辅助 | JSON格式返回场景类型+置信度 |
| 组合匹配 | 多源证据加权融合 | 关键词(40%) + 正则(60%) |

**路由决策流程：**

```
输入数据 → 场景识别 → 置信度排序 → 策略匹配 → 优先级选择 → 执行策略
                                                              │
                                               成功 → 返回结果
                                               失败 → 回退策略
```

### 推理引擎详解

#### CoT 链式推理

将复杂分析问题分解为步骤链，每步输出中间结果，支持完整追溯。

- **引擎**: `ChainOfThoughtEngine` — 执行推理链，管理步骤间依赖
- **构建器**: `ChainBuilder` — 流式API构建自定义推理链
- **内置链**: `ErrorDiagnosisChain`、`PerformanceAnalysisChain`、`RootCauseChain`、`SecurityAuditChain`
- **步骤类型**: 提取 → 分析 → 推理 → 总结

#### ReAct 交互推理

实现 Thought → Action → Observation 循环，支持 SSE 实时流式推送推理过程。

- **引擎**: `ReActEngine` — 管理推理循环，支持同步/流式执行
- **内置Agent**: `LogAnalysisAgent`、`PerformanceDebugAgent`、`SecurityInvestigationAgent`、`AnomalyHuntingAgent`
- **内置工具** (7种):

| 工具 | 功能 |
|------|------|
| `SearchLogsTool` | 搜索日志中的关键词 |
| `FilterRequestsTool` | 按条件筛选请求 |
| `CalculateStatsTool` | 计算统计指标 |
| `ExtractPatternsTool` | 提取日志模式 |
| `CompareTimePeriodsTool` | 对比不同时段数据 |
| `PythonExecTool` | 执行Python代码片段 |
| `WebSearchTool` | 搜索外部信息 |

#### 因果图分析

基于有向图进行根因定位、影响评估和传播追踪。

- **因果图**: `CausalGraph` — 节点(`CausalNode`) + 边(`CausalEdge`) 组成有向图
- **图构建器**: `CausalGraphBuilder` — 从事件自动构建因果图
- **分析器**: `CausalAnalyzer`(综合分析)、`RootCauseAnalyzer`(根因定位)、`ImpactAnalyzer`(影响评估)、`PropagationAnalyzer`(传播追踪)

### 辅助系统

#### Context Engineering

统一的上下文管理模块，为所有推理引擎提供上下文工程能力：

| 组件 | 功能 |
|------|------|
| `TokenCounter` | Token计数（估算/tiktoken精确计数） |
| `ContextWindow` | 滑动窗口管理，防止上下文溢出 |
| `MessageBuilder` | Messages列表构建器 |
| `ContextCompressor` | 上下文压缩，保留关键信息 |
| `FileContextStore` | 文件系统上下文持久化 |

#### Reflection 引擎

对LLM输出进行验证评估和自动修正，提升分析质量：

- `ReflectionEngine` 接收任务描述和LLM输出，调用LLM评估质量（评分、问题、建议）
- 若未通过评估，自动根据反馈修正输出，循环直到通过或达到最大轮次
- 可组合到任何推理流程中

#### RAG 知识库

基于 ChromaDB 向量数据库的检索增强生成系统：

- `KnowledgeStore` — 知识存储和管理
- `KnowledgeRetriever` — 语义检索器
- `RAGContextBuilder` — RAG上下文构建
- `KnowledgeLearner` — 知识自动学习

## 分析策略体系

### 9种场景类型

| 场景 | 标识 | 触发条件示例 |
|------|------|------------|
| 错误分析 | `error_analysis` | 日志含ERROR/FATAL、错误率>=10%、5xx>=5% |
| 性能分析 | `performance` | 含timeout/slow、P99>=3s、慢请求率>=10% |
| 安全分析 | `security` | 含injection/xss、4xx>=20%、认证失败率>=10% |
| 业务分析 | `business` | 含订单/支付/用户相关路径 |
| 异常检测 | `anomaly` | 含spike/drop、流量变化>=50%、错误突增>=2倍 |
| API覆盖率 | `api_coverage` | 含coverage/覆盖/未覆盖 |
| 流量分析 | `traffic` | 含qps/tps、请求量>=1000 |
| 根因分析 | `root_cause` | 含root cause/根因/排查/定位 |
| 健康检查 | `health_check` | 含health/健康/状态 |

### 24种策略详解

#### 基础统计策略 (7个)

纯统计分析，不依赖LLM调用，执行速度快，适用于数据概览和报表场景。

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `error_analysis_basic` | 错误分类、错误率计算、状态码分布 | 错误分析 |
| `performance_analysis_basic` | 响应时间分布、慢请求识别、P50/P99 | 性能分析 |
| `security_analysis_basic` | 安全模式匹配、异常请求检测 | 安全分析 |
| `traffic_analysis_basic` | 流量统计、QPS计算、峰值识别 | 流量分析 |
| `api_coverage_basic` | 接口覆盖率计算、未覆盖接口列出 | API覆盖率 |
| `health_check_basic` | 服务可用性检查、基础健康指标 | 健康检查 |
| `root_cause_basic` | 基于统计的根因定位 | 根因分析 |

#### CoT 链式推理 (4个)

通过 `ChainOfThoughtEngine` 将问题分解为多步推理链，每步输出中间结果，完整可追溯。

| 策略 | 说明 | 推理链 |
|------|------|--------|
| `error_diagnosis_cot` | 逐步诊断错误根因 | 提取错误 → 分类归因 → 影响分析 → 建议 |
| `performance_analysis_cot` | 深度性能瓶颈分析 | 指标提取 → 瓶颈识别 → 原因分析 → 优化建议 |
| `root_cause_cot` | 多因素根因推理 | 症状收集 → 假设生成 → 验证排除 → 结论 |
| `security_audit_cot` | 安全风险审计 | 威胁识别 → 漏洞分析 → 风险评估 → 加固建议 |

#### ReAct 交互推理 (4个)

通过 `ReActEngine` 实现 Thought-Action-Observation 循环，LLM自主决定使用哪些工具探索数据。支持 SSE 流式实时推送推理过程。

| 策略 | 说明 | 核心工具 |
|------|------|---------|
| `log_analysis_react` | 自主探索日志中的异常模式 | SearchLogs, ExtractPatterns, CalculateStats |
| `performance_debug_react` | 交互式性能问题调试 | FilterRequests, CalculateStats, CompareTimePeriods |
| `security_investigation_react` | 安全事件调查取证 | SearchLogs, FilterRequests, ExtractPatterns |
| `anomaly_hunting_react` | 主动发现异常和偏差 | CalculateStats, CompareTimePeriods, ExtractPatterns |

#### 因果图分析 (4个)

通过 `CausalEngine` 构建因果图，在有向图上进行推理，适用于复杂系统故障的根因定位。

| 策略 | 说明 | 核心能力 |
|------|------|---------|
| `causal_root_cause` | 因果图根因定位 | 构建因果图 → 入度分析 → 根因节点识别 |
| `causal_impact_assessment` | 故障影响范围评估 | 从故障节点 → 下游传播 → 影响范围量化 |
| `causal_propagation_trace` | 因果传播链路追踪 | 完整传播路径 → 关键路径识别 |
| `causal_full_analysis` | 综合因果分析 | 根因 + 影响 + 传播 全量分析 |

#### 告警过滤 (2个)

| 策略 | 说明 | 核心能力 |
|------|------|---------|
| `alert_filter_basic` | 基础告警过滤 | 去重、聚合、优先级排序 |
| `alert_rule_engine` | 规则引擎告警处理 | 支持维护窗口、严重度升级、标签路由、工作时间等规则 |

#### 健康评分 (3个)

| 策略 | 说明 | 核心能力 |
|------|------|---------|
| `health_score_basic` | 基础健康度评分 | 多维指标(可用性/延迟/错误率/吞吐/饱和度)加权评分 |
| `health_report_full` | 完整健康报告 | 组件级评分 + 系统总评 + 问题列表 + 建议 |
| `health_trend_analysis` | 健康趋势分析 | 时序数据分析 + 趋势方向判断 + 预警 |

### 策略调度流程

```
1. 输入数据（日志/请求/指标/提示）
        │
2. ScenarioDetector.detect()
   ├─ 用户提示检测（最高优先级）
   ├─ 日志内容检测（关键词+正则）
   ├─ 请求数据检测（统计阈值）
   ├─ 指标数据检测（阈值条件）
   ├─ 合并同类场景（加权平均置信度）
   ├─ LLM增强（可选，低置信度时）
   └─ 过滤低置信度 + 排序
        │
3. IntelligentRouter.route()
   ├─ 遍历top-N场景
   ├─ 从策略注册表查找匹配策略
   └─ 选择每个场景优先级最高的策略
        │
4. IntelligentRouter.execute()
   ├─ 依次执行所选策略
   ├─ 第一个成功即返回（默认）
   └─ 全部失败 → 启用回退策略
        │
5. 返回分析结果
```

## 快速开始

### 方式一：Docker 一键启动（推荐）

```bash
# 克隆项目
git clone <repo-url> && cd ai-test-tool

# 配置环境变量
cp .example.env .env
# 编辑 .env 设置 LLM_PROVIDER、LLM_MODEL 等

# 生产模式启动（前端 Nginx:80 + 后端 API:8000 内部）
docker compose up -d

# 或开发模式启动（支持热重载）
docker compose -f docker-compose.dev.yml up
```

**生产模式访问：**
- 前端界面: http://localhost （端口80，Nginx托管）
- API文档: http://localhost/docs （Nginx反代到后端）

**开发模式访问：**
- 前端界面: http://localhost:3000 （Vite HMR）
- API文档: http://localhost:8000/docs （后端直连）

> Docker 环境下连接宿主机 Ollama，在 `.env` 中设置 `LLM_API_BASE=http://host.docker.internal:11434`

### 方式二：手动安装

#### 1. 安装依赖

```bash
# 后端依赖（需要 Python 3.13+）
pip install -r requirements.txt

# 前端依赖（需要 Node.js 20+）
cd web && npm install
```

#### 2. 配置环境变量

```bash
cp .example.env .env
```

编辑 `.env` 文件：

```bash
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
```

#### 3. 启动服务

```bash
# 启动后端API服务（端口8000）
python server.py

# 启动前端开发服务器（端口3000）
cd web && npm run dev
```

**访问地址：**
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs

## 使用示例

### 智能路由分析

```python
from ai_test_tool.routing import create_router

# 创建智能路由器
router = create_router()

# 一站式路由和执行
decision, results = router.route_and_execute(
    log_content="2024-01-15 10:30:45 ERROR Database connection timeout...",
    requests=[...],        # 可选：解析后的请求列表
    user_hint="找出导致超时的根本原因"
)

# 查看路由决策
print(decision.reasoning)           # 路由推理过程
print(decision.selected_strategies) # 选中的策略

# 查看分析结果
for result in results:
    print(f"策略: {result.strategy_id}, 成功: {result.success}")
    print(f"结果: {result.data}")
```

### ReAct 流式分析 (SSE)

通过 `/api/v2/analysis/react/stream` 端点实时推送推理过程：

```bash
curl -N -X POST http://localhost:8000/api/v2/analysis/react/stream \
  -H "Content-Type: application/json" \
  -d '{
    "task": "分析日志中的错误模式并找出根因",
    "log_content": "...",
    "max_iterations": 10
  }'
```

SSE 事件类型：

| 事件 | 说明 |
|------|------|
| `started` | 分析任务开始 |
| `step_start` | 推理步骤开始 |
| `thought` | LLM 思考过程 |
| `action` | 执行工具调用 |
| `observation` | 工具返回结果 |
| `step_end` | 推理步骤结束 |
| `finished` | 分析完成，返回最终结果 |
| `error` | 发生错误 |

### 告警过滤

```python
from ai_test_tool.alerting import AlertFilter, Alert, AlertSeverity

# 创建过滤器
filter = AlertFilter()

# 创建告警
alerts = [
    Alert(alert_id="1", title="CPU高", severity=AlertSeverity.WARNING),
    Alert(alert_id="2", title="CPU高", severity=AlertSeverity.WARNING),  # 重复
    Alert(alert_id="3", title="内存不足", severity=AlertSeverity.CRITICAL),
]

# 执行过滤
result = filter.filter(alerts)
print(f"输入: {result.total_input}, 输出: {result.output_count}")
print(f"去重: {result.dedupe_count}, 分组: {len(result.alert_groups)}")
```

### 健康度评分

```python
from ai_test_tool.health import (
    HealthScoreEngine,
    create_availability_metric,
    create_error_rate_metric,
)

engine = HealthScoreEngine()
engine.register_component("api", "API服务", "service")
engine.add_metric("api", create_availability_metric(value=99.5))
engine.add_metric("api", create_error_rate_metric(value=0.5))

summary = engine.get_summary()
print(f"健康状态: {summary['status']}, 得分: {summary['score']}")

report = engine.generate_report()
print(report.summary)
```

### 因果分析

```python
from ai_test_tool.causal import RootCauseAnalyzer

analyzer = RootCauseAnalyzer()
result = analyzer.find_root_causes(
    log_content="...",
    symptoms=["请求超时", "错误率上升"]
)

print(f"根因: {result['primary_root_cause']}")
print(f"置信度: {result['confidence']}")
print(f"建议: {result['recommendations']}")
```

### Context Engineering

```python
from ai_test_tool.context import TokenCounter, ContextWindow, MessageBuilder

# Token 计数
counter = TokenCounter()
count = counter.count("分析这段日志...")

# 滑动窗口管理
window = ContextWindow(max_tokens=4096)
window.add(message)  # 自动淘汰旧消息防止溢出

# 构建消息列表
builder = MessageBuilder()
builder.system("你是日志分析专家")
builder.user("分析以下日志...")
messages = builder.build()
```

### Reflection 引擎

```python
from ai_test_tool.reflection import ReflectionEngine, ReflectionConfig

engine = ReflectionEngine()
result = engine.reflect_and_refine(
    task="分析日志中的错误模式",
    output="初步分析结果...",
    criteria="结果必须包含具体错误类型和修复建议"
)

print(f"评分: {result.score}, 通过: {result.passed}")
print(f"修正后输出: {result.refined_output}")
```

## 项目结构

```
ai-test-tool/
├── server.py                 # API服务入口
├── requirements.txt          # Python依赖
├── .example.env              # 环境变量示例
│
├── Dockerfile.backend        # 后端镜像构建
├── Dockerfile.frontend       # 前端镜像构建（多阶段: Node构建 + Nginx运行）
├── docker-compose.yml        # 生产部署编排
├── docker-compose.dev.yml    # 开发环境编排
├── nginx.conf                # Nginx配置（静态托管 + API反代）
├── .dockerignore             # 构建上下文排除
│
├── data/                     # SQLite数据库目录
├── logs/                     # 日志文件目录
├── uploads/                  # 上传文件目录
├── tests/                    # 测试用例
│
├── web/                      # 前端项目（Vue 3 + TDesign）
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   │   ├── Dashboard.vue
│   │   │   ├── development/  # 开发自测（接口管理、测试用例、执行记录）
│   │   │   ├── monitoring/   # 线上监控（告警、健康检查、请求、历史）
│   │   │   ├── insights/     # 日志洞察（分析任务、报告、上传）
│   │   │   ├── ai/           # AI助手
│   │   │   ├── knowledge/    # 知识库（列表、待审核、语义搜索）
│   │   │   └── settings/     # 设置（文档导入）
│   │   ├── components/       # 通用组件（DataTable, StatCard, StatusTag...）
│   │   ├── composables/      # 组合式函数
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── api/              # API封装（v2.ts）
│   │   ├── router/           # Vue Router
│   │   ├── types/            # TypeScript 类型定义
│   │   └── utils/            # 工具函数
│   └── ...
│
└── ai_test_tool/             # 后端核心包
    ├── core.py               # 主程序核心
    │
    │── 智能推理引擎 ──────────────────────────────
    ├── routing/              # 智能路由分发器
    │   ├── models.py         # 场景类型、策略模型、路由决策
    │   ├── detector.py       # 场景识别器（5种匹配方法）
    │   ├── registry.py       # 策略注册表 + @strategy 装饰器
    │   ├── router.py         # 路由分发器（route → execute → fallback）
    │   └── strategies/       # 24种分析策略
    │       ├── error.py      # 基础错误分析
    │       ├── performance.py # 基础性能分析
    │       ├── security.py   # 基础安全分析
    │       ├── api.py        # 流量/覆盖率/健康检查
    │       ├── root_cause.py # 基础根因分析
    │       ├── cot.py        # CoT 链式推理策略
    │       ├── react.py      # ReAct 交互推理策略
    │       ├── causal.py     # 因果分析策略
    │       ├── alert.py      # 告警过滤策略
    │       └── health.py     # 健康评分策略
    │
    ├── reasoning/            # CoT链式推理模块
    │   ├── models.py         # 推理步骤、链配置、链结果
    │   ├── engine.py         # ChainOfThoughtEngine
    │   ├── chains.py         # 预定义推理链（4种）
    │   └── builder.py        # ChainBuilder 流式构建器
    │
    ├── react/                # ReAct交互推理模块
    │   ├── models.py         # Thought-Action-Observation 模型
    │   ├── tools.py          # 工具注册表 + 7种内置工具
    │   ├── engine.py         # ReActEngine（同步+流式SSE）
    │   └── agents.py         # 预定义Agent（4种）
    │
    ├── causal/               # 因果分析模块
    │   ├── models.py         # 因果图、因果链、分析结果
    │   ├── builder.py        # CausalGraphBuilder
    │   ├── engine.py         # CausalEngine
    │   └── analyzers.py      # 4种分析器（根因/影响/传播/综合）
    │
    ├── alerting/             # 告警智能过滤模块
    │   ├── models.py         # 告警、规则、过滤结果
    │   ├── engine.py         # AlertFilterEngine
    │   ├── filter.py         # AlertFilter 高级过滤器
    │   └── rules.py          # 规则引擎 + 预定义规则
    │
    ├── health/               # 健康度评分模块
    │   ├── models.py         # 健康指标、组件健康、系统健康
    │   ├── engine.py         # HealthScoreEngine + 指标工厂
    │   └── checker.py        # HealthChecker + ComponentHealthBuilder
    │
    ├── context/              # Context Engineering 模块
    │   ├── token_counter.py  # Token 计数
    │   ├── context_window.py # 滑动窗口管理
    │   ├── message_builder.py # Messages 构建器
    │   ├── compressor.py     # 上下文压缩
    │   └── file_store.py     # 文件上下文持久化
    │
    ├── reflection/           # Reflection 引擎
    │   ├── models.py         # 反思结果、修正输出、配置
    │   └── engine.py         # ReflectionEngine（验证+修正循环）
    │
    │── 基础功能模块 ──────────────────────────────
    ├── services/             # 业务服务层
    │   ├── intelligent_analysis.py  # 智能分析服务（路由封装）
    │   ├── ai_assistant.py          # AI助手服务
    │   ├── endpoint_test_generator.py # 接口测试生成
    │   ├── log_anomaly_detector.py  # 日志异常检测
    │   └── production_monitor.py    # 生产监控
    │
    ├── api/                  # REST API模块
    │   ├── app.py            # FastAPI应用
    │   └── routes/           # API路由（dashboard, development, monitoring,
    │                         #   insights, ai_assistant, imports, tasks,
    │                         #   knowledge, analysis）
    │
    ├── database/             # 数据库模块
    │   ├── connection.py     # SQLite连接管理
    │   ├── models.py         # 数据模型
    │   ├── repository.py     # Repository模式
    │   └── schema.sql        # 建表SQL
    │
    ├── llm/                  # LLM抽象层
    │   ├── provider.py       # 多LLM支持（Ollama/OpenAI/Anthropic/Azure）
    │   ├── prompts.py        # Prompt模板
    │   └── chains.py         # LangChain处理链
    │
    ├── knowledge/            # 知识库模块
    │   ├── store.py          # 向量存储
    │   ├── embeddings.py     # 嵌入模型
    │   ├── retriever.py      # 语义检索器
    │   ├── rag_builder.py    # RAG上下文构建
    │   └── learner.py        # 知识自动学习
    │
    ├── parser/               # 日志解析
    │   ├── log_parser.py     # AI智能解析器
    │   └── format_detector.py # 格式检测
    │
    ├── analyzer/             # 分析模块
    │   ├── request_analyzer.py  # 请求分析
    │   └── report_generator.py  # 报告生成
    │
    ├── testing/              # 测试模块
    │   ├── test_case_generator.py  # 用例生成
    │   ├── test_executor.py     # 测试执行
    │   └── result_validator.py  # 结果验证
    │
    ├── scenario/             # 测试场景模块
    │   ├── executor.py       # 场景执行器
    │   ├── variable_resolver.py # 变量解析
    │   ├── extractor.py      # 数据提取
    │   └── assertion_engine.py  # 断言引擎
    │
    ├── importer/             # 文档导入模块
    │   ├── swagger_parser.py # Swagger/OpenAPI解析器
    │   ├── postman_parser.py # Postman解析器
    │   └── doc_importer.py   # 文档导入
    │
    ├── config/               # 配置管理
    │   └── settings.py       # Pydantic配置模型
    │
    ├── exceptions.py         # 统一异常定义
    └── utils/                # 工具函数
        └── logger.py         # 日志工具
```

## 环境变量配置

### LLM配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM提供商 (ollama/openai/anthropic/azure) | `ollama` |
| `LLM_MODEL` | 模型名称 | `qwen3:8b` |
| `LLM_API_KEY` | API密钥 | - |
| `LLM_API_BASE` | API基础URL | - |
| `LLM_TEMPERATURE` | 生成温度 | `0.3` |
| `LLM_MAX_TOKENS` | 最大token数 | `8192` |

### 数据库配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SQLITE_DB_PATH` | SQLite数据库路径 | `data/ai_test_tool.db` |

### 服务配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SERVER_HOST` | 监听地址 | `0.0.0.0` |
| `SERVER_PORT` | 监听端口 | `8000` |

### 测试配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TEST_BASE_URL` | 默认测试目标URL | `http://localhost:8080` |
| `TEST_TIMEOUT` | 请求超时时间(秒) | `30` |
| `TEST_CONCURRENT_REQUESTS` | 并发请求数 | `5` |

## 前端功能

| 功能模块 | 说明 |
|---------|------|
| **概览仪表盘** | 统计数据、快捷操作、最近任务和执行记录 |
| **日志洞察** | 上传日志、粘贴内容、查看分析任务进度和报告 |
| **接口管理** | 查看、搜索、筛选已导入的API接口 |
| **知识库** | 管理接口文档知识库，待审核内容，语义搜索测试 |
| **文档导入** | 导入 Swagger/OpenAPI 和 Postman Collection |
| **测试用例** | 查看AI生成的测试用例 |
| **执行记录** | 查看测试执行历史和详细结果 |
| **线上监控** | 告警管理、健康检查、请求监控、历史记录 |
| **AI助手** | 智能对话式分析助手 |

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `analysis_tasks` | 分析任务表 |
| `parsed_requests` | 解析请求表 |
| `test_cases` | 测试用例表 |
| `test_case_history` | 测试用例变更历史 |
| `test_executions` | 测试执行批次 |
| `test_results` | 测试结果表 |
| `analysis_reports` | 分析报告表 |
| `api_tags` | 接口标签表 |
| `api_endpoints` | 接口端点表 |
| `api_endpoint_tags` | 接口-标签关联表 |
| `test_scenarios` | 测试场景表 |
| `scenario_steps` | 场景步骤表 |
| `scenario_executions` | 场景执行记录表 |
| `step_results` | 步骤执行结果表 |

## 技术栈

**后端**
- Python 3.13+
- FastAPI + Uvicorn
- SQLite（零配置）
- LangChain 1.2+
- Pydantic 2.12+
- ChromaDB（向量数据库）

**前端**
- Vue 3.4+ (Composition API + `<script setup>`)
- TypeScript 5.3+
- TDesign Vue Next
- Vite 5
- Pinia（状态管理）
- ECharts（图表）
- Axios

**AI/ML**
- Ollama (本地LLM，推荐)
- OpenAI API
- Anthropic Claude
- Azure OpenAI

**部署**
- Docker + Docker Compose
- Nginx（反向代理 + 静态托管）

## License

MIT
