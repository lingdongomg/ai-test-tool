# AI Test Tool - 智能API测试工具

基于LLM的智能日志分析和自动化测试工具，可以自动解析日志、生成测试用例、执行测试并验证结果。

## 功能特性

- **AI智能日志解析**: AI自动分析任意格式的日志，提取API请求信息
- **智能分析报告**: 基于LLM生成专业的分析报告，发现隐藏问题
- **智能测试用例生成**: 自动生成正常、边界、异常测试用例
- **智能测试执行**: 异步并发执行测试，自动验证结果
- **多LLM支持**: 支持Ollama(本地)、OpenAI、Anthropic等多种LLM
- **MySQL数据持久化**: 所有分析结果、测试用例、报告存储到MySQL数据库
- **接口文档导入**: 支持 Swagger/OpenAPI 和 Postman Collection 格式导入
- **接口文档RAG**: 将接口文档作为知识库，增强AI分析准确性
- **标签管理**: 统一的接口标签体系，支持层级标签
- **测试场景**: 复杂场景测试，支持参数传递、断言验证、步骤编排
- **REST API服务**: 提供完整的后台API，支持前端集成
- **现代化前端**: Vue 3 + TDesign 构建的管理界面

## 快速开始

### 1. 安装后端依赖

```bash
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd web
npm install
```

### 3. 配置环境变量

复制示例配置文件并修改：

```bash
cp .example.env .env
```

编辑 `.env` 文件，填入实际配置：

```bash
# LLM配置
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b

# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_test_tool
```

### 4. 初始化数据库

```bash
# 方式1: 使用SQL文件
mysql -u root -p < ai_test_tool/database/schema.sql

# 方式2: 使用Python代码（自动创建数据库和表）
python -c "from ai_test_tool.database import get_db_manager; get_db_manager().init_database()"
```

### 5. 启动服务

**启动后端 API 服务：**

```bash
# 启动API服务
python server.py

# 指定端口
python server.py --port 8080

# 开发模式（自动重载）
python server.py --reload
```

**启动前端开发服务器：**

```bash
cd web
npm run dev
```

**访问地址：**
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs

**生产环境构建：**

```bash
cd web
npm run build
# 构建产物在 web/dist 目录
```

## 前端功能

前端提供完整的可视化管理界面，包括：

| 功能模块 | 说明 |
|---------|------|
| **概览仪表盘** | 统计数据、快捷操作、最近任务和执行记录 |
| **分析任务** | 上传日志文件、粘贴日志内容、查看分析进度和结果 |
| **接口管理** | 查看、搜索、筛选已导入的API接口 |
| **标签管理** | 创建、编辑、删除标签，支持层级结构 |
| **文档导入** | 导入 Swagger/OpenAPI 和 Postman Collection |
| **测试场景** | 创建测试场景、编排步骤、执行测试 |
| **测试用例** | 查看AI生成的测试用例、版本管理 |
| **执行记录** | 查看测试执行历史和详细结果 |
| **智能分析** | 覆盖率分析、文档对比、AI辅助分析 |

## 环境变量配置

所有配置通过 `.env` 文件管理，支持以下变量：

### LLM配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM提供商 (ollama/openai/anthropic/azure) | `ollama` |
| `LLM_MODEL` | 模型名称 | `qwen3:8b` |
| `LLM_API_KEY` | API密钥 | - |
| `LLM_API_BASE` | API基础URL | - |
| `LLM_TEMPERATURE` | 生成温度 | `0.3` |
| `LLM_MAX_TOKENS` | 最大token数 | `4096` |

### MySQL配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MYSQL_HOST` | 数据库主机 | `localhost` |
| `MYSQL_PORT` | 数据库端口 | `3306` |
| `MYSQL_USER` | 数据库用户 | `root` |
| `MYSQL_PASSWORD` | 数据库密码 | - |
| `MYSQL_DATABASE` | 数据库名称 | `ai_test_tool` |

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
| `TEST_RETRY_COUNT` | 失败重试次数 | `3` |
| `TEST_CONCURRENT_REQUESTS` | 并发请求数 | `5` |

## 项目结构

```
ai-test-tool/
├── server.py                 # API服务入口
├── requirements.txt          # Python依赖
├── .example.env              # 环境变量示例
├── logs/                     # 日志文件目录（自动创建）
├── uploads/                  # 上传文件目录（自动创建）
├── web/                      # 前端项目（Vue 3 + TDesign）
│   ├── package.json          # 前端依赖配置
│   ├── vite.config.ts        # Vite构建配置
│   ├── tsconfig.json         # TypeScript配置
│   └── src/                  # 前端源码
│       ├── main.ts           # 入口文件
│       ├── App.vue           # 根组件（导航布局）
│       ├── api/              # API封装
│       │   └── index.ts      # Axios请求封装
│       ├── router/           # 路由配置
│       │   └── index.ts      # Vue Router配置
│       └── views/            # 页面组件
│           ├── Dashboard.vue     # 概览仪表盘
│           ├── Tasks.vue         # 分析任务列表
│           ├── TaskDetail.vue    # 任务详情
│           ├── Endpoints.vue     # 接口管理
│           ├── Tags.vue          # 标签管理
│           ├── Import.vue        # 文档导入
│           ├── Scenarios.vue     # 测试场景列表
│           ├── ScenarioDetail.vue# 场景详情
│           ├── TestCases.vue     # 测试用例
│           ├── Executions.vue    # 执行记录
│           └── Analysis.vue      # 智能分析
└── ai_test_tool/             # 后端核心包
    ├── __init__.py           # 包入口
    ├── core.py               # 主程序核心
    ├── config/               # 配置管理
    │   └── settings.py       # 配置定义
    ├── database/             # 数据库模块
    │   ├── connection.py     # 数据库连接
    │   ├── models.py         # 数据模型
    │   ├── repository.py     # 数据仓库
    │   └── schema.sql        # 建表SQL
    ├── api/                  # REST API模块
    │   ├── app.py            # FastAPI应用
    │   └── routes/           # API路由
    │       ├── tasks.py      # 分析任务
    │       ├── tags.py       # 标签管理
    │       ├── endpoints.py  # 接口管理
    │       ├── scenarios.py  # 场景管理
    │       ├── executions.py # 执行记录
    │       ├── imports.py    # 文档导入
    │       └── analysis.py   # 智能分析
    ├── importer/             # 文档导入模块
    │   ├── swagger_parser.py # Swagger解析器
    │   ├── postman_parser.py # Postman解析器
    │   └── doc_importer.py   # 统一导入器
    ├── scenario/             # 测试场景模块
    │   ├── executor.py       # 场景执行器
    │   ├── variable_resolver.py # 变量解析器
    │   ├── extractor.py      # 响应提取器
    │   └── assertion_engine.py  # 断言引擎
    ├── llm/                  # LLM抽象层
    │   ├── provider.py       # 多LLM支持
    │   ├── prompts.py        # AI Prompt模板
    │   └── chains.py         # LangChain处理链
    ├── parser/               # 日志解析
    │   ├── log_parser.py     # AI智能解析器
    │   └── format_detector.py # 格式检测
    ├── analyzer/             # 分析模块
    │   ├── request_analyzer.py  # 请求分析
    │   ├── report_generator.py  # 报告生成
    │   └── api_knowledge_base.py # 接口文档RAG知识库
    ├── testing/              # 测试模块
    │   ├── test_case_generator.py  # 用例生成
    │   ├── test_executor.py     # 测试执行
    │   └── result_validator.py  # 结果验证
    └── utils/                # 工具模块
        └── logger.py         # AI日志监控
```

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
| `scheduled_tasks` | 定时任务表 |

## License

MIT
