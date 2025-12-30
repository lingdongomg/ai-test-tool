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

## 核心优势

### AI驱动的日志解析
传统工具依赖硬编码的正则表达式，只能处理特定格式的日志。本工具使用AI智能分析：
- **无需预定义规则**: AI自动理解各种日志格式（GIN、Nginx、自定义格式等）
- **智能提取信息**: 自动识别请求方法、URL、参数、响应状态等
- **问题诊断**: AI分析错误和警告，给出修复建议
- **关联分析**: 识别同一请求的多行日志并合并

### 接口文档RAG增强
将接口文档作为RAG知识库，显著提升AI分析准确性：
- **智能分类**: 优先使用文档中的标签，保证分类一致性
- **文档对比**: 对比日志与文档，发现文档遗漏或过期问题
- **第三方识别**: 自动识别不在文档中的第三方接口
- **覆盖分析**: 统计接口调用覆盖率，发现未测试的接口

### 测试场景编排
参考 Testone 优测平台设计，支持复杂场景测试：
- **步骤编排**: 按顺序执行多个API请求
- **参数传递**: 从上一步响应提取变量供下一步使用
- **断言验证**: 支持多种断言类型（相等、包含、正则匹配等）
- **多种执行方式**: 手动执行、定时执行、API触发

### AI处理监控
- 实时显示AI处理状态和进度
- 详细的AI调用日志（使用`-v`参数）
- AI处理统计信息
- 日志文件输出到 `logs/` 目录，按日期命名

## 安装

```bash
pip install -r requirements.txt
```

## 环境变量配置

本工具通过系统环境变量进行配置。请在运行前设置以下环境变量：

### LLM配置（必须）

```bash
# Linux/macOS
export LLM_PROVIDER=ollama          # ollama, openai, anthropic
export LLM_MODEL=qwen3:8b           # 模型名称
export LLM_API_KEY=your_api_key     # API密钥 (OpenAI/Anthropic需要)
export LLM_API_BASE=                # API基础URL (可选)
export LLM_TEMPERATURE=0.3          # 生成温度
export LLM_MAX_TOKENS=4096          # 最大token数

# Windows PowerShell
$env:LLM_PROVIDER="ollama"
$env:LLM_MODEL="qwen3:8b"
```

### MySQL数据库配置（必须）

```bash
# Linux/macOS
export MYSQL_HOST=localhost         # 数据库主机
export MYSQL_PORT=3306              # 数据库端口
export MYSQL_USER=root              # 数据库用户名
export MYSQL_PASSWORD=your_password # 数据库密码
export MYSQL_DATABASE=ai_test_tool  # 数据库名称

# Windows PowerShell
$env:MYSQL_HOST="localhost"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_password"
$env:MYSQL_DATABASE="ai_test_tool"
```

### 持久化环境变量

建议将环境变量添加到 shell 配置文件中：

```bash
# Linux/macOS: 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export MYSQL_HOST=localhost' >> ~/.bashrc
echo 'export MYSQL_PORT=3306' >> ~/.bashrc
echo 'export MYSQL_USER=root' >> ~/.bashrc
echo 'export MYSQL_PASSWORD=your_password' >> ~/.bashrc
echo 'export MYSQL_DATABASE=ai_test_tool' >> ~/.bashrc
source ~/.bashrc
```

## 数据库初始化

在首次使用前，需要初始化MySQL数据库：

```bash
# 方式1: 使用SQL文件
mysql -u root -p < ai_test_tool/database/schema.sql

# 方式2: 使用Python代码（自动创建数据库和表）
python -c "from ai_test_tool.database import get_db_manager; get_db_manager().init_database()"
```

### 数据库表结构

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

## 快速开始

### 命令行使用

```bash
# AI智能分析日志
python run.py -f your_log.json

# 限制处理行数（用于测试或大文件）
python run.py -f your_log.json -m 10000

# 显示详细的AI处理日志
python run.py -f your_log.json -v
```

### 执行测试

```bash
# 生成用例并执行测试（指定目标URL）
python run.py -f your_log.json --run-tests --base-url http://your-api.com

# 测试不同环境
python run.py -f your_log.json --run-tests --base-url http://dev.your-api.com    # 开发环境
python run.py -f your_log.json --run-tests --base-url http://test.your-api.com   # 测试环境
python run.py -f your_log.json --run-tests --base-url http://prod.your-api.com   # 生产环境

# 指定并发数
python run.py -f your_log.json --run-tests --base-url http://your-api.com --concurrent 10
```

### 启动API服务

```bash
# 启动API服务
python server.py

# 指定端口
python server.py --port 8080

# 开发模式（自动重载）
python server.py --reload

# 访问API文档
# http://localhost:8000/docs
```

## API服务

### API端点

| 路径 | 说明 |
|------|------|
| `GET /` | 健康检查 |
| `GET /docs` | Swagger API文档 |
| **标签管理** | |
| `GET /api/v1/tags` | 获取标签列表 |
| `POST /api/v1/tags` | 创建标签 |
| `PUT /api/v1/tags/{id}` | 更新标签 |
| `DELETE /api/v1/tags/{id}` | 删除标签 |
| `GET /api/v1/tags/tree/all` | 获取标签树 |
| **接口管理** | |
| `GET /api/v1/endpoints` | 获取接口列表 |
| `POST /api/v1/endpoints` | 创建接口 |
| `PUT /api/v1/endpoints/{id}` | 更新接口 |
| `DELETE /api/v1/endpoints/{id}` | 删除接口 |
| **文档导入** | |
| `POST /api/v1/imports/file` | 上传并导入接口文档 |
| `POST /api/v1/imports/json` | 导入JSON数据 |
| `POST /api/v1/imports/preview` | 预览导入结果 |
| **测试场景** | |
| `GET /api/v1/scenarios` | 获取场景列表 |
| `POST /api/v1/scenarios` | 创建场景 |
| `PUT /api/v1/scenarios/{id}` | 更新场景 |
| `DELETE /api/v1/scenarios/{id}` | 删除场景 |
| `POST /api/v1/scenarios/{id}/execute` | 执行场景 |
| **执行记录** | |
| `GET /api/v1/executions` | 获取执行记录 |
| `GET /api/v1/executions/{id}` | 获取执行详情 |
| `GET /api/v1/executions/statistics` | 获取执行统计 |
| **智能分析** | |
| `POST /api/v1/analysis/coverage` | 分析URL与文档覆盖情况 |
| `POST /api/v1/analysis/doc-comparison` | 文档对比分析（含AI） |
| `POST /api/v1/analysis/suggest-tags` | 根据URL建议标签 |
| `POST /api/v1/analysis/rag-context` | 获取RAG上下文 |
| `POST /api/v1/analysis/batch-categorize` | 批量分类URL |
| `GET /api/v1/analysis/knowledge-base/stats` | 知识库统计 |
| `GET /api/v1/analysis/knowledge-base/summary` | 知识库摘要 |

### 导入接口文档

支持 Swagger/OpenAPI 和 Postman Collection 格式：

```bash
# 导入 Swagger 文档
curl -X POST "http://localhost:8000/api/v1/imports/file" \
  -F "file=@swagger.json" \
  -F "doc_type=swagger"

# 导入 Postman Collection
curl -X POST "http://localhost:8000/api/v1/imports/file" \
  -F "file=@postman_collection.json" \
  -F "doc_type=postman"

# 自动检测格式
curl -X POST "http://localhost:8000/api/v1/imports/file" \
  -F "file=@api_doc.json" \
  -F "doc_type=auto"
```

### 创建测试场景

```bash
# 创建场景
curl -X POST "http://localhost:8000/api/v1/scenarios" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "用户登录流程",
    "description": "测试用户登录并获取信息",
    "variables": {"username": "test", "password": "123456"},
    "steps": [
      {
        "name": "登录",
        "method": "POST",
        "url": "/api/login",
        "body": {"username": "${username}", "password": "${password}"},
        "extractions": [
          {"name": "token", "source": "jsonpath", "expression": "$.data.token"}
        ],
        "assertions": [
          {"type": "equals", "source": "status", "expected": 200}
        ]
      },
      {
        "name": "获取用户信息",
        "method": "GET",
        "url": "/api/user/info",
        "headers": {"Authorization": "Bearer ${token}"},
        "assertions": [
          {"type": "equals", "source": "jsonpath", "expression": "$.code", "expected": 0}
        ]
      }
    ]
  }'

# 执行场景
curl -X POST "http://localhost:8000/api/v1/scenarios/{scenario_id}/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "http://your-api.com",
    "environment": "test"
  }'
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-f, --file` | 日志文件路径 | 必填 |
| `-m, --max-lines` | 最大处理行数 | 全部 |
| `-v, --verbose` | 显示详细的AI处理日志 | 禁用 |
| `--llm-provider` | LLM提供商(ollama/openai/anthropic) | `ollama` |
| `--llm-model` | LLM模型名称 | `qwen3:8b` |
| `--api-key` | LLM API密钥 | 无 |
| `--run-tests` | 执行生成的测试用例 | 不执行 |
| `--base-url` | 测试目标URL | `http://localhost:8080` |
| `--concurrent` | 并发请求数 | `5` |
| `--test-strategy` | 测试策略(comprehensive/quick/security) | `comprehensive` |

## 项目结构

```
ai-test-tool/
├── run.py                    # 命令行入口
├── server.py                 # API服务入口
├── requirements.txt          # 依赖
├── logs/                     # 日志文件目录（自动创建）
└── ai_test_tool/            # 核心包
    ├── __init__.py          # 包入口
    ├── core.py              # 主程序核心
    ├── config/              # 配置管理
    │   └── settings.py      # 配置定义
    ├── database/            # 数据库模块
    │   ├── connection.py    # 数据库连接
    │   ├── models.py        # 数据模型
    │   ├── repository.py    # 数据仓库
    │   └── schema.sql       # 建表SQL
    ├── api/                 # REST API模块
    │   ├── app.py           # FastAPI应用
    │   └── routes/          # API路由
    │       ├── tags.py      # 标签管理
    │       ├── endpoints.py # 接口管理
    │       ├── scenarios.py # 场景管理
    │       ├── executions.py# 执行记录
    │       ├── imports.py   # 文档导入
    │       └── analysis.py  # 智能分析（RAG）
    ├── importer/            # 文档导入模块
    │   ├── swagger_parser.py   # Swagger解析器
    │   ├── postman_parser.py   # Postman解析器
    │   └── doc_importer.py     # 统一导入器
    ├── scenario/            # 测试场景模块
    │   ├── executor.py      # 场景执行器
    │   ├── variable_resolver.py # 变量解析器
    │   ├── extractor.py     # 响应提取器
    │   └── assertion_engine.py  # 断言引擎
    ├── llm/                 # LLM抽象层
    │   ├── provider.py      # 多LLM支持
    │   ├── prompts.py       # AI Prompt模板
    │   └── chains.py        # LangChain处理链
    ├── parser/              # 日志解析
    │   ├── log_parser.py    # AI智能解析器
    │   └── format_detector.py # 格式检测
    ├── analyzer/            # 分析模块
    │   ├── request_analyzer.py  # 请求分析
    │   ├── report_generator.py  # 报告生成
    │   └── api_knowledge_base.py # 接口文档RAG知识库
    ├── testing/             # 测试模块
    │   ├── test_case_generator.py  # 用例生成
    │   ├── test_executor.py     # 测试执行
    │   └── result_validator.py  # 结果验证
    └── utils/               # 工具模块
        └── logger.py        # AI日志监控
```

## 编程方式使用

```python
from ai_test_tool.core import AITestTool

# 创建工具实例
tool = AITestTool(verbose=True)

try:
    # 解析日志
    requests = tool.parse_log_file("your_log.json", max_lines=10000)
    
    # 分析请求
    analysis = tool.analyze_requests()
    
    # 生成测试用例
    test_cases = tool.generate_test_cases()
    
    # 执行测试（可选）
    results = tool.run_tests(base_url="http://your-api.com")
    
    # 导出报告到数据库
    tool.export_all()
finally:
    # 关闭资源
    tool.close()
```

### 使用文档导入器

```python
from ai_test_tool.importer import DocImporter

importer = DocImporter()

# 导入 Swagger 文档
result = importer.import_file("swagger.json", doc_type="swagger")
print(f"导入 {result.endpoint_count} 个接口，{result.tag_count} 个标签")

# 导入 Postman Collection
result = importer.import_file("collection.json", doc_type="postman")

# 自动检测格式
result = importer.import_file("api_doc.json", doc_type="auto")
```

### 使用场景执行器

```python
import asyncio
from ai_test_tool.scenario import ScenarioExecutor
from ai_test_tool.database.models import TestScenario, ScenarioStep, StepType

# 创建场景
scenario = TestScenario(
    scenario_id="test_login",
    name="登录流程测试",
    variables={"username": "test", "password": "123456"}
)

# 添加步骤
scenario.steps = [
    ScenarioStep(
        scenario_id="test_login",
        step_id="step_1",
        step_order=1,
        name="登录",
        step_type=StepType.REQUEST,
        method="POST",
        url="/api/login",
        body={"username": "${username}", "password": "${password}"},
        extractions=[
            {"name": "token", "source": "jsonpath", "expression": "$.data.token"}
        ],
        assertions=[
            {"type": "equals", "source": "status", "expected": 200}
        ]
    )
]

# 执行场景
executor = ScenarioExecutor(base_url="http://your-api.com")
result = asyncio.run(executor.execute_scenario(scenario))

print(f"执行结果: {result.status.value}")
print(f"通过: {result.passed_steps}/{result.total_steps}")
```

### 使用接口文档RAG

```python
from ai_test_tool.analyzer import ApiKnowledgeBase, RequestAnalyzer
from ai_test_tool.importer import DocImporter
from ai_test_tool.llm.chains import LogAnalysisChain
from ai_test_tool.llm.provider import get_llm_provider

# 1. 导入接口文档
importer = DocImporter()
result = importer.import_file("swagger.json", doc_type="swagger")
print(f"导入 {result.endpoint_count} 个接口")

# 2. 构建知识库
kb = ApiKnowledgeBase()
kb.load_from_endpoints(result.endpoints, result.tags)

# 3. 分析覆盖情况
urls = ["/api/v1/users", "/api/v1/orders", "/external/payment"]
coverage = kb.analyze_coverage(urls)
print(f"匹配率: {coverage['match_rate']}")
print(f"未匹配URL（可能是第三方）: {coverage['unmatched_urls']}")

# 4. 使用RAG增强AI分析
provider = get_llm_provider()
chain = LogAnalysisChain(provider)

# 构建RAG上下文
rag_context = kb.build_rag_context(urls)

# AI分类（使用文档知识）
requests_data = [{"url": url, "method": "GET"} for url in urls]
result = chain.categorize_requests(requests_data, api_doc_context=rag_context)

# 分类结果会更准确，第三方接口会被标识
for item in result.get("categorized_requests", []):
    print(f"{item['url']} -> {item['category']} (来源: {item.get('source', 'unknown')})")

# 5. 文档对比分析
comparison = chain.compare_with_api_doc(
    kb.get_endpoints_summary(),
    coverage
)
print("文档问题:", comparison.get("doc_completeness", {}))
print("改进建议:", comparison.get("recommendations", []))
```

### 智能分析API使用

```bash
# 分析URL覆盖情况
curl -X POST "http://localhost:8000/api/v1/analysis/coverage" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["/api/v1/users", "/api/v1/orders", "/external/payment"],
    "methods": ["GET", "POST", "POST"]
  }'

# 文档对比分析（含AI分析）
curl -X POST "http://localhost:8000/api/v1/analysis/doc-comparison" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["/api/v1/users", "/api/v1/orders"],
    "include_ai_analysis": true
  }'

# 批量分类URL
curl -X POST "http://localhost:8000/api/v1/analysis/batch-categorize" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["/api/v1/dx/product/list", "/api/v1/dx/order/create"]
  }'

# 获取知识库统计
curl "http://localhost:8000/api/v1/analysis/knowledge-base/stats"
```

## License

MIT
