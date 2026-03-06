# API 设计

## 通用约定

### 基础地址

```
开发环境: http://localhost:8080/api/v2
生产环境: https://{domain}/api/v2
```

### 认证方式

当前系统无认证机制。WebSocket 通道通过查询参数 `token` 进行简单鉴权（可选，预留扩展）。

### 通用响应格式

```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

### 分页格式

```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": []
}
```

### 通用错误码

| HTTP 状态码 | 含义 |
|-------------|------|
| 400 | 参数错误 / 业务校验失败 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 接口总览

| 方法 | 路径 | 说明 | 阶段 |
|------|------|------|------|
| POST | `/knowledge/learn-from-task` | 从已完成的分析任务中学习知识 | 一 |
| POST | `/knowledge/learn-from-file` | 上传日志文件直接学习知识 | 一 |
| GET | `/log-stream/sources` | 获取日志源列表 | 二 |
| POST | `/log-stream/sources` | 创建日志源 | 二 |
| PUT | `/log-stream/sources/{source_id}` | 更新日志源 | 二 |
| DELETE | `/log-stream/sources/{source_id}` | 删除日志源 | 二 |
| GET | `/log-stream/sources/{source_id}/stats` | 获取日志源统计 | 二 |
| WebSocket | `/ws/logs` | 实时日志推送通道 | 二 |

---

## 接口详细定义

### 1. 从分析任务学习知识

```
方法: POST
路径: /api/v2/knowledge/learn-from-task
说明: 从已完成的日志分析任务中提取知识
```

**请求参数**：

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| task_id | body | string | 是 | 日志分析任务 ID |
| auto_approve | body | boolean | 否 | 高置信度知识是否自动审核通过（默认 false） |

**请求示例**：

```json
{
  "task_id": "a1b2c3d4",
  "auto_approve": true
}
```

**响应示例**：

```json
{
  "success": true,
  "created_count": 3,
  "knowledge_ids": ["k001", "k002", "k003"],
  "items": [
    {
      "knowledge_id": "k001",
      "title": "认证Header必须包含Bearer Token",
      "type": "project_config",
      "confidence": 0.92,
      "status": "active"
    },
    {
      "knowledge_id": "k002",
      "title": "/api/live/* 接口要求game-id参数",
      "type": "business_rule",
      "confidence": 0.85,
      "status": "active"
    },
    {
      "knowledge_id": "k003",
      "title": "高频500错误出现在 /api/order/create",
      "type": "test_experience",
      "confidence": 0.68,
      "status": "pending"
    }
  ],
  "message": "从任务 a1b2c3d4 中提取了 3 条知识"
}
```

**业务错误**：

| HTTP 状态码 | 场景 |
|-------------|------|
| 404 | 任务不存在 |
| 400 | 任务状态不是 completed |
| 400 | 任务无解析请求数据 |

---

### 2. 上传日志文件学习知识

```
方法: POST
路径: /api/v2/knowledge/learn-from-file
说明: 上传日志文件，自动解析并提取知识
Content-Type: multipart/form-data
```

**请求参数**：

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| file | form-data | File | 是 | 日志文件（.log/.txt/.json） |
| auto_approve | form-data | boolean | 否 | 是否自动审核（默认 false） |
| source_ref | form-data | string | 否 | 来源说明（如"生产日志 2026-03"） |
| max_lines | form-data | integer | 否 | 最大解析行数（默认无限制） |

**响应示例**：

```json
{
  "success": true,
  "task_id": "x1y2z3",
  "file_name": "production.log",
  "file_size": 1048576,
  "parsed_requests": 42,
  "created_count": 5,
  "knowledge_ids": ["k010", "k011", "k012", "k013", "k014"],
  "items": [
    {
      "knowledge_id": "k010",
      "title": "所有接口使用 application/json",
      "type": "project_config",
      "confidence": 0.95,
      "status": "active"
    }
  ],
  "message": "从文件中解析 42 个请求，提取了 5 条知识"
}
```

**业务错误**：

| HTTP 状态码 | 场景 |
|-------------|------|
| 400 | 文件类型不支持（仅 .log/.txt/.json） |
| 400 | 文件大小超出限制（100MB） |

---

### 3. 获取日志源列表

```
方法: GET
路径: /api/v2/log-stream/sources
说明: 获取所有配置的实时日志源
```

**请求参数**：

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| is_enabled | query | boolean | 否 | 按启用状态筛选 |
| status | query | string | 否 | 按连接状态筛选（connected/disconnected） |

**响应示例**：

```json
{
  "total": 2,
  "items": [
    {
      "source_id": "src-001",
      "name": "生产环境日志",
      "description": "主服务生产环境的实时日志",
      "tags": ["production", "main-service"],
      "buffer_size": 100,
      "buffer_timeout_sec": 30,
      "auto_learn": true,
      "auto_approve_threshold": 0.8,
      "is_enabled": true,
      "status": "connected",
      "total_lines_received": 15420,
      "total_analyses_triggered": 154,
      "last_active_at": "2026-03-05T10:30:00Z",
      "created_at": "2026-03-01T08:00:00Z"
    }
  ]
}
```

---

### 4. 创建日志源

```
方法: POST
路径: /api/v2/log-stream/sources
说明: 创建新的实时日志源配置
```

**请求参数**：

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|
| name | body | string | 是 | 日志源名称 |
| description | body | string | 否 | 描述 |
| tags | body | string[] | 否 | 标签 |
| buffer_size | body | integer | 否 | 缓冲区行数阈值（默认 100） |
| buffer_timeout_sec | body | integer | 否 | 缓冲超时秒数（默认 30） |
| auto_learn | body | boolean | 否 | 自动学习开关（默认 true） |
| auto_approve_threshold | body | number | 否 | 自动审核阈值（默认 0.8） |

**请求示例**：

```json
{
  "name": "生产环境日志",
  "description": "主服务生产环境实时日志接入",
  "tags": ["production"],
  "buffer_size": 100,
  "buffer_timeout_sec": 30,
  "auto_learn": true,
  "auto_approve_threshold": 0.8
}
```

**响应示例**：

```json
{
  "success": true,
  "source_id": "src-001",
  "message": "日志源创建成功",
  "ws_url": "/ws/logs?source_id=src-001"
}
```

---

### 5. 更新日志源

```
方法: PUT
路径: /api/v2/log-stream/sources/{source_id}
说明: 更新日志源配置
```

**请求参数**：与创建相同字段，均为可选。

**响应示例**：

```json
{
  "success": true,
  "message": "日志源更新成功"
}
```

**业务错误**：

| HTTP 状态码 | 场景 |
|-------------|------|
| 404 | 日志源不存在 |

---

### 6. 删除日志源

```
方法: DELETE
路径: /api/v2/log-stream/sources/{source_id}
说明: 删除日志源（同时断开活跃连接）
```

**响应示例**：

```json
{
  "success": true,
  "message": "日志源已删除"
}
```

---

### 7. 获取日志源统计

```
方法: GET
路径: /api/v2/log-stream/sources/{source_id}/stats
说明: 获取单个日志源的详细统计信息
```

**响应示例**：

```json
{
  "source_id": "src-001",
  "name": "生产环境日志",
  "status": "connected",
  "total_lines_received": 15420,
  "total_analyses_triggered": 154,
  "total_knowledge_created": 23,
  "buffer_current_size": 45,
  "last_analysis_at": "2026-03-05T10:28:00Z",
  "last_active_at": "2026-03-05T10:30:00Z",
  "uptime_seconds": 3600
}
```

---

### 8. WebSocket 实时日志通道

```
协议: WebSocket
路径: /ws/logs
说明: 实时日志推送通道，客户端发送日志行，服务端缓冲并触发分析
```

**连接参数（查询参数）**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| source_id | string | 是 | 日志源 ID |
| token | string | 否 | 认证 token（预留） |

**连接示例**：

```
ws://localhost:8080/ws/logs?source_id=src-001
```

**客户端 → 服务端消息格式**：

```json
// 单行日志
{"type": "log", "line": "2026-03-05 10:30:00 INFO GET /api/users 200 12ms"}

// 批量日志
{"type": "batch", "lines": ["line1", "line2", "line3"]}

// 心跳
{"type": "ping"}
```

**服务端 → 客户端消息格式**：

```json
// 心跳响应
{"type": "pong"}

// 分析触发通知
{"type": "analysis_triggered", "buffer_size": 100, "task_id": "abc123"}

// 知识提取通知
{"type": "knowledge_created", "count": 3, "knowledge_ids": ["k1", "k2", "k3"]}

// 错误通知
{"type": "error", "message": "buffer overflow, force flushing"}
```

**关闭码**：

| 关闭码 | 含义 |
|--------|------|
| 4001 | 认证失败 |
| 4002 | source_id 无效或未启用 |
| 4003 | 超出最大连接数限制 |

---

## 数据模型

### LogSource（日志源）

```typescript
interface LogSource {
  source_id: string
  name: string
  description: string
  tags: string[]
  buffer_size: number         // 缓冲区行数阈值
  buffer_timeout_sec: number  // 缓冲超时秒数
  auto_learn: boolean         // 是否自动学习
  auto_approve_threshold: number  // 自动审核阈值
  is_enabled: boolean
  status: 'connected' | 'disconnected'
  total_lines_received: number
  total_analyses_triggered: number
  last_active_at: string | null
  created_at: string
  updated_at: string
}
```

### LearnFromTaskRequest

```typescript
interface LearnFromTaskRequest {
  task_id: string
  auto_approve?: boolean
}
```

### LearnResult（学习结果）

```typescript
interface LearnResultItem {
  knowledge_id: string
  title: string
  type: string
  confidence: number
  status: 'active' | 'pending'
}

interface LearnResult {
  success: boolean
  created_count: number
  knowledge_ids: string[]
  items: LearnResultItem[]
  message: string
}
```

### 已有的分析任务选择器所需数据

```typescript
// 复用已有的 insightsApi.listTasks 接口
// 筛选条件: status = "completed"
interface TaskOption {
  task_id: string
  name: string
  total_requests: number
  created_at: string
}
```
