# AI Test Tool - 智能API测试与日志分析平台

基于LLM的智能日志分析和自动化测试平台，集成多层推理引擎，可自动解析日志、智能分析根因、生成测试用例并执行验证。

## 核心特性

### 智能分析引擎

- **多层推理架构**: 智能路由 + CoT链式推理 + ReAct交互推理 + 因果图分析
- **24种分析策略**: 覆盖错误诊断、性能分析、安全审计、根因定位等场景
- **告警智能过滤**: 去重、聚合、抑制、降噪，减少告警疲劳
- **健康度评分**: 多维指标评估，趋势分析，生成健康报告

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

## 智能推理引擎

本平台集成了先进的多层推理引擎，提供深度日志分析能力：

### 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        智能路由分发器                              │
│                    (场景识别 + 策略匹配)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   CoT 推理    │     │  ReAct Agent  │     │   因果分析    │
│  (链式思考)    │     │ (交互式推理)   │     │  (图推理)     │
└───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      结果聚合 + 报告生成                           │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  告警过滤     │     │  健康评分     │     │  趋势分析     │
└───────────────┘     └───────────────┘     └───────────────┘
```

### 模块说明

| 模块 | 功能 | 策略数 |
|------|------|--------|
| **智能路由** | 场景识别、策略匹配、负载均衡 | - |
| **CoT推理** | 链式思考，逐步分析错误、性能、安全问题 | 4 |
| **ReAct Agent** | 交互式推理，自主调用工具分析 | 4 |
| **因果分析** | 构建因果图，根因定位，影响评估 | 4 |
| **告警过滤** | 去重、聚合、抑制、规则引擎 | 2 |
| **健康评分** | 多维指标评分、趋势分析、报告生成 | 3 |
| **基础策略** | 错误、性能、安全、流量等基础分析 | 7 |

### 分析策略列表

<details>
<summary>点击展开全部24种策略</summary>

**基础策略 (7个)**
- `error_analysis_basic` - 基础错误分析
- `performance_analysis_basic` - 基础性能分析
- `security_analysis_basic` - 基础安全分析
- `traffic_analysis_basic` - 基础流量分析
- `api_coverage_basic` - API覆盖率分析
- `health_check_basic` - 基础健康检查
- `root_cause_basic` - 基础根因分析

**CoT链式推理 (4个)**
- `error_diagnosis_cot` - CoT错误诊断
- `performance_analysis_cot` - CoT性能分析
- `root_cause_cot` - CoT根因分析
- `security_audit_cot` - CoT安全审计

**ReAct交互推理 (4个)**
- `log_analysis_react` - ReAct日志分析
- `performance_debug_react` - ReAct性能调试
- `security_investigation_react` - ReAct安全调查
- `anomaly_hunting_react` - ReAct异常猎手

**因果图分析 (4个)**
- `causal_root_cause` - 因果根因分析
- `causal_impact_assessment` - 因果影响评估
- `causal_propagation_trace` - 因果传播追踪
- `causal_full_analysis` - 完整因果分析

**告警过滤 (2个)**
- `alert_filter_basic` - 基础告警过滤
- `alert_rule_engine` - 规则引擎告警处理

**健康评分 (3个)**
- `health_score_basic` - 基础健康度评分
- `health_report_full` - 完整健康报告
- `health_trend_analysis` - 健康趋势分析

</details>

## 快速开始

### 1. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd web && npm install
```

### 2. 配置环境变量

```bash
cp .example.env .env
```

编辑 `.env` 文件：

```bash
# LLM配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b

# 数据库配置（SQLite，无需额外配置）
DATABASE_PATH=data/ai_test_tool.db
```

### 3. 启动服务

```bash
# 启动后端API服务
python server.py

# 启动前端开发服务器
cd web && npm run dev
```

**访问地址：**
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs

## 使用示例

### 智能日志分析

```python
from ai_test_tool.routing import create_router

# 创建智能路由器
router = create_router()

# 分析日志
result = router.analyze(
    log_content="2024-01-15 10:30:45 ERROR Database connection timeout...",
    requests=[...],  # 可选：请求记录
    user_query="找出导致超时的根本原因"
)

print(result["strategy_used"])  # 使用的策略
print(result["analysis_result"])  # 分析结果
```

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

# 创建引擎
engine = HealthScoreEngine()

# 注册组件
engine.register_component("api", "API服务", "service")

# 添加指标
engine.add_metric("api", create_availability_metric(value=99.5))
engine.add_metric("api", create_error_rate_metric(value=0.5))

# 获取健康状态
summary = engine.get_summary()
print(f"健康状态: {summary['status']}, 得分: {summary['score']}")

# 生成报告
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

## 项目结构

```
ai-test-tool/
├── server.py                 # API服务入口
├── requirements.txt          # Python依赖
├── .example.env              # 环境变量示例
├── data/                     # SQLite数据库目录
├── logs/                     # 日志文件目录
├── uploads/                  # 上传文件目录
├── tests/                    # 测试用例
├── web/                      # 前端项目（Vue 3 + TDesign）
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   ├── components/       # 通用组件
│   │   ├── composables/      # 组合式函数
│   │   └── api/              # API封装
│   └── ...
└── ai_test_tool/             # 后端核心包
    ├── core.py               # 主程序核心
    │
    │── 智能推理引擎 ──────────────────────────────
    ├── routing/              # 智能路由分发器
    │   ├── models.py         # 场景、策略模型
    │   ├── registry.py       # 策略注册表
    │   ├── router.py         # 路由分发器
    │   └── strategies.py     # 24种分析策略
    │
    ├── reasoning/            # CoT链式推理模块
    │   ├── models.py         # 推理步骤模型
    │   ├── engine.py         # 推理引擎
    │   └── chains.py         # 预定义推理链
    │
    ├── react/                # ReAct交互推理模块
    │   ├── models.py         # Thought-Action-Observation模型
    │   ├── tools.py          # 工具注册表
    │   ├── engine.py         # ReAct引擎
    │   └── agents.py         # 预定义Agent
    │
    ├── causal/               # 因果分析模块
    │   ├── models.py         # 因果图模型
    │   ├── builder.py        # 因果图构建器
    │   ├── engine.py         # 因果推理引擎
    │   └── analyzers.py      # 预定义分析器
    │
    ├── alerting/             # 告警智能过滤模块
    │   ├── models.py         # 告警、规则模型
    │   ├── engine.py         # 过滤引擎
    │   ├── filter.py         # 高级过滤器
    │   └── rules.py          # 规则引擎
    │
    ├── health/               # 健康度评分模块
    │   ├── models.py         # 健康指标模型
    │   ├── engine.py         # 评分引擎
    │   └── checker.py        # 健康检查器
    │
    │── 基础功能模块 ──────────────────────────────
    ├── api/                  # REST API模块
    │   ├── app.py            # FastAPI应用
    │   └── routes/           # API路由
    │
    ├── database/             # 数据库模块
    │   ├── connection.py     # SQLite连接
    │   ├── models.py         # 数据模型
    │   ├── repository.py     # 数据仓库
    │   └── schema.sql        # 建表SQL
    │
    ├── llm/                  # LLM抽象层
    │   ├── provider.py       # 多LLM支持
    │   ├── prompts.py        # Prompt模板
    │   └── chains.py         # LangChain处理链
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
    │   └── assertion_engine.py  # 断言引擎
    │
    ├── importer/             # 文档导入模块
    │   ├── swagger_parser.py # Swagger解析器
    │   └── postman_parser.py # Postman解析器
    │
    ├── knowledge/            # 知识库模块
    │   └── api_knowledge_base.py # 接口文档RAG
    │
    └── config/               # 配置管理
        └── settings.py       # 配置定义
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
| `LLM_MAX_TOKENS` | 最大token数 | `4096` |

### 数据库配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_PATH` | SQLite数据库路径 | `data/ai_test_tool.db` |

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
| **分析任务** | 上传日志、粘贴内容、查看分析进度和结果 |
| **接口管理** | 查看、搜索、筛选已导入的API接口 |
| **知识库** | 管理接口文档知识库，RAG增强分析 |
| **文档导入** | 导入 Swagger/OpenAPI 和 Postman Collection |
| **测试场景** | 创建测试场景、编排步骤、执行测试 |
| **测试用例** | 查看AI生成的测试用例、版本管理 |
| **执行记录** | 查看测试执行历史和详细结果 |

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `analysis_tasks` | 分析任务表 |
| `parsed_requests` | 解析请求表 |
| `test_cases` | 测试用例表 |
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
- Python 3.11+
- FastAPI
- SQLite / SQLAlchemy
- LangChain
- Pydantic

**前端**
- Vue 3
- TypeScript
- TDesign
- Vite
- Axios

**AI/ML**
- Ollama (本地LLM)
- OpenAI API
- Anthropic Claude

## License

MIT
