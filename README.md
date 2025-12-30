# AI Test Tool - 智能API测试工具

基于LLM的智能日志分析和自动化测试工具，可以自动解析日志、生成测试用例、执行测试并验证结果。

## 功能特性

- **AI智能日志解析**: AI自动分析任意格式的日志，提取API请求信息
- **智能分析报告**: 基于LLM生成专业的分析报告，发现隐藏问题
- **智能测试用例生成**: 自动生成正常、边界、异常测试用例
- **智能测试执行**: 异步并发执行测试，自动验证结果
- **多LLM支持**: 支持Ollama(本地)、OpenAI、Anthropic等多种LLM
- **自动生成curl命令**: 每个请求自动生成可执行的curl命令
- **MySQL数据持久化**: 支持将分析结果存储到MySQL数据库

## 核心优势

### AI驱动的日志解析
传统工具依赖硬编码的正则表达式，只能处理特定格式的日志。本工具使用AI智能分析：
- **无需预定义规则**: AI自动理解各种日志格式（GIN、Nginx、自定义格式等）
- **智能提取信息**: 自动识别请求方法、URL、参数、响应状态等
- **问题诊断**: AI分析错误和警告，给出修复建议
- **关联分析**: 识别同一请求的多行日志并合并

### AI处理监控
- 实时显示AI处理状态和进度
- 详细的AI调用日志（使用`-v`参数）
- AI处理统计信息

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### 基本使用

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
# 生成用例并执行测试
python run.py -f your_log.json --run-tests --base-url http://your-api.com

# 指定并发数
python run.py -f your_log.json --run-tests --base-url http://your-api.com --concurrent 10
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-f, --file` | 日志文件路径 | 必填 |
| `-m, --max-lines` | 最大处理行数 | 全部 |
| `-o, --output` | 输出目录 | `./output` |
| `-v, --verbose` | 显示详细的AI处理日志 | 禁用 |
| `--llm-provider` | LLM提供商(ollama/openai/anthropic) | `ollama` |
| `--llm-model` | LLM模型名称 | `qwen3:8b` |
| `--api-key` | LLM API密钥 | 无 |
| `--run-tests` | 执行生成的测试用例 | 不执行 |
| `--base-url` | 测试目标URL | `http://localhost:8080` |
| `--concurrent` | 并发请求数 | `5` |
| `--test-strategy` | 测试策略(comprehensive/quick/security) | `comprehensive` |

## 输出文件

| 文件 | 说明 |
|------|------|
| `api_requests.csv` | 解析出的所有API请求（含curl命令） |
| `test_cases.csv` | 生成的测试用例 |
| `test_cases.sh` | curl命令脚本 |
| `analysis_report.md` | AI分析报告 |

## 数据库支持

本工具支持将分析结果持久化到MySQL数据库，方便后续的数据管理和API接口开发。

### 配置数据库

在`.env`文件中配置MySQL连接信息：

```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_test_tool
```

### 初始化数据库

```bash
# 方式1: 使用SQL文件
mysql -u root -p < ai_test_tool/database/schema.sql

# 方式2: 使用Python代码
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
| `test_case_tags` | 用例标签表 |
| `test_case_groups` | 用例分组表 |

## CSV字段说明

### api_requests.csv

| 字段 | 说明 |
|------|------|
| url | 接口URL |
| method | HTTP方法 |
| category | 接口分类（AI智能分类） |
| http_status | HTTP状态码 |
| response_time_ms | 响应时间(ms) |
| has_error | 是否有错误 |
| error_message | 错误信息 |
| has_warning | 是否有警告 |
| warning_message | 警告信息 |
| curl_command | 完整的curl命令 |
| headers | 请求头 |
| body | 请求体 |
| timestamp | 时间戳 |
| request_id | 请求ID |

## 配置

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

主要配置项：
- `LLM_PROVIDER`: LLM提供商（ollama/openai/anthropic）
- `LLM_MODEL`: 模型名称
- `LLM_API_KEY`: API密钥（OpenAI/Anthropic需要）
- `MYSQL_*`: MySQL数据库配置

## 项目结构

```
ai-test-tool/
├── run.py                    # 命令行入口
├── requirements.txt          # 依赖
├── .env.example             # 环境配置示例
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
    ├── llm/                 # LLM抽象层
    │   ├── provider.py      # 多LLM支持
    │   ├── prompts.py       # AI Prompt模板
    │   └── chains.py        # LangChain处理链
    ├── parser/              # 日志解析
    │   ├── log_parser.py    # AI智能解析器
    │   └── format_detector.py # 格式检测
    ├── analyzer/            # 分析模块
    │   ├── request_analyzer.py  # 请求分析
    │   └── report_generator.py  # 报告生成
    ├── testing/             # 测试模块
    │   ├── test_case_generator.py  # 用例生成
    │   ├── test_executor.py     # 测试执行
    │   └── result_validator.py  # 结果验证
    ├── exporter/            # 导出模块
    │   ├── csv_exporter.py
    │   └── curl_exporter.py
    └── utils/               # 工具模块
        └── logger.py        # AI日志监控
```

## 编程方式使用

```python
from ai_test_tool.core import AITestTool

# 创建工具实例
tool = AITestTool(verbose=True)

# 解析日志
requests = tool.parse_log_file("your_log.json", max_lines=10000)

# 分析请求
analysis = tool.analyze_requests()

# 生成测试用例
test_cases = tool.generate_test_cases()

# 执行测试
results = tool.run_tests(base_url="http://your-api.com")

# 导出结果
tool.export_all("./output")
```

## 数据库操作示例

```python
from ai_test_tool.database import (
    get_db_manager,
    TaskRepository,
    RequestRepository,
    TestCaseRepository
)

# 初始化数据库
db = get_db_manager()
db.init_database()

# 创建任务
task_repo = TaskRepository()
task = AnalysisTask(
    task_id="task_001",
    name="日志分析任务",
    log_file_path="/path/to/log.json"
)
task_repo.create(task)

# 查询测试用例
tc_repo = TestCaseRepository()
cases = tc_repo.get_by_task("task_001")

# 按标签查询
cases = tc_repo.get_by_tag("task_001", "normal")

# 更新用例
tc_repo.update("task_001", "TC0001", {"is_enabled": False})

# 添加标签
tc_repo.add_tag("task_001", "TC0001", "regression")
```

## 未来规划

- [ ] RESTful API接口
- [ ] Web前端界面
- [ ] 测试用例版本管理
- [ ] 测试报告可视化
- [ ] 支持更多LLM提供商
- [ ] 分布式测试执行

## License

MIT
