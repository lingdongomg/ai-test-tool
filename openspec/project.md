# Project Context

## Purpose
AI Test Tool 是一个智能 API 测试工具，利用大语言模型（LLM）实现：
- **智能日志解析**：AI 驱动的日志分析，支持任意格式
- **自动测试用例生成**：基于 API 文档和日志自动生成测试用例
- **生产环境监控**：实时健康检查和异常检测
- **RAG 知识库**：增强 AI 响应的准确性和上下文理解
- **多场景测试**：支持复杂业务场景的端到端测试

## Tech Stack

### Backend (Python 3.13+)
- **Web Framework**: FastAPI (async API server)
- **Server**: Uvicorn (ASGI)
- **AI/ML**: LangChain, LangChain-Ollama, ChromaDB (向量数据库)
- **Database**: SQLite
- **Validation**: Pydantic v2
- **HTTP Client**: httpx, aiohttp

### Frontend (TypeScript)
- **Framework**: Vue 3 (Composition API + `<script setup>`)
- **Build Tool**: Vite 5
- **UI Library**: TDesign Vue Next
- **State Management**: Pinia
- **Charts**: ECharts (vue-echarts)
- **HTTP Client**: Axios
- **Styling**: TailwindCSS

## Project Conventions

### Code Style

**Python:**
- 使用 Python 3.12+ 类型提示语法 (`str | None` 而非 `Optional[str]`)
- 使用 `@dataclass` 定义数据模型
- 使用 Pydantic `BaseModel` 进行配置和验证
- 异步函数使用 `async/await`
- 数据库游标使用 `@contextmanager`
- 枚举类继承自 Python `Enum`

**TypeScript/Vue:**
- 所有组件使用 `<script setup>` 语法
- 启用 TypeScript 严格模式
- 路径别名：`@/` 映射到 `src/`
- 组件、composables、utilities 分离

**命名规范:**
- Python: snake_case (变量/函数), PascalCase (类)
- TypeScript: camelCase (变量/函数), PascalCase (类/组件)
- API 路由: kebab-case

### Architecture Patterns

**后端架构:**
- **分层架构**: routes → services → repository → database
- **Repository Pattern**: 每个实体独立 repository
- **Provider Pattern**: LLM 提供者抽象层，支持 Ollama/OpenAI/Anthropic/Azure
- **线程安全**: 使用 `threading.local()` 管理数据库连接

**前端架构:**
- **Views**: 页面级组件，按功能模块组织
- **Composables**: 可复用的组合式函数
- **Components**: 通用 UI 组件
- **Stores**: Pinia 状态管理

**API 设计:**
- RESTful API，路由前缀 `/api/v2/`
- Pydantic 模型验证请求/响应
- 长时间任务使用 BackgroundTasks 异步处理

### Testing Strategy
- 测试目录: `tests/`
- 测试框架: pytest (推荐)
- API 测试: FastAPI TestClient
- 前端测试: Vitest (推荐)

### Git Workflow
- 主开发分支: `dev`
- 提交信息格式: `<type>: <description>` (中文描述)
- 常用类型: `feat`, `fix`, `refactor`, `docs`, `chore`
- 示例: `feat: 实现异步测试用例生成与日志请求提取`

## Domain Context

### 核心概念
- **Endpoint (接口)**: API 端点，包含 URL、方法、参数等信息
- **Test Case (测试用例)**: 针对接口的测试，包含输入数据和预期结果
- **Execution Record (执行记录)**: 测试执行的结果和日志
- **Analysis Task (分析任务)**: 日志分析任务，异步执行
- **Knowledge Base (知识库)**: RAG 系统使用的文档和向量存储

### LLM 集成
- 支持多种 LLM 提供者（Ollama 本地模型、OpenAI、Anthropic、Azure）
- 使用 LangChain 进行 prompt 管理和链式调用
- ChromaDB 存储向量嵌入，支持语义搜索

## Important Constraints
- **数据库**: 已从 MySQL 迁移至 SQLite，零配置部署
- **LLM 依赖**: 需要配置 LLM 提供者（推荐 Ollama 本地部署）
- **CORS**: 开发模式下允许所有来源（生产环境需限制）
- **环境配置**: 通过 `.env` 文件配置，使用 python-dotenv 加载

## External Dependencies

### LLM Services
- **Ollama**: 本地 LLM 服务 (推荐)
- **OpenAI API**: GPT 系列模型
- **Anthropic API**: Claude 系列模型
- **Azure OpenAI**: 企业级 Azure 服务

### Vector Database
- **ChromaDB**: 本地向量数据库，用于 RAG 知识库

### 开发服务
- **Backend**: `python server.py --port 8000 --reload`
- **Frontend**: `npm run dev` (端口 3000，代理 API 到 8080)
