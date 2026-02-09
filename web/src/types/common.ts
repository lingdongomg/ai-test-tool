/**
 * 通用类型定义
 */

// HTTP 方法
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'OPTIONS' | 'HEAD'

// 测试用例分类
export type TestCategory = 'normal' | 'boundary' | 'exception' | 'performance' | 'security'

// 优先级
export type Priority = 'high' | 'medium' | 'low'

// 执行状态
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'cancelled' | 'failed'

// 任务状态
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

// 测试结果状态
export type TestResultStatus = 'passed' | 'failed' | 'error' | 'skipped'

// 触发类型
export type TriggerType = 'manual' | 'scheduled' | 'pipeline' | 'api'

// 知识类型
export type KnowledgeType = 'project_config' | 'business_rule' | 'module_context' | 'test_experience'

// 知识状态
export type KnowledgeStatus = 'active' | 'pending' | 'archived'

// 知识来源
export type KnowledgeSource = 'manual' | 'log_learning' | 'test_learning'

// 接口来源类型
export type EndpointSourceType = 'swagger' | 'postman' | 'manual'

// 分页参数
export interface PaginationParams {
  page: number
  pageSize: number
}

// 分页结果
export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

// 时间范围
export interface TimeRange {
  start: string
  end: string
}

// 键值对
export interface KeyValue<T = string> {
  key: string
  value: T
}

// ID 类型
export type ID = string | number
