/**
 * API 响应类型定义
 */

import type { PaginatedResult } from './common'

// API 响应基础结构
export interface ApiResponse<T = unknown> {
  data?: T
  message?: string
  code?: string
}

// 分页响应
export interface PaginatedResponse<T> extends PaginatedResult<T> {
  // 别名兼容后端返回格式
  page_size?: number
}

// API 错误响应
export interface ApiError {
  code: string
  message: string
  field?: string
  details?: Record<string, unknown>
}

// 统计数据响应
export interface StatisticsResponse {
  endpoints: EndpointStatistics
  tests: TestStatistics
  executions: ExecutionStatistics
  knowledge?: KnowledgeStatistics
}

export interface EndpointStatistics {
  total: number
  by_method: Record<string, number>
  by_tag: Record<string, number>
  deprecated_count: number
  with_tests: number
  without_tests: number
}

export interface TestStatistics {
  total: number
  by_category: Record<string, number>
  by_priority: Record<string, number>
  enabled_count: number
  disabled_count: number
  ai_generated_count: number
}

export interface ExecutionStatistics {
  total: number
  by_status: Record<string, number>
  by_trigger_type: Record<string, number>
  recent_executions: RecentExecution[]
  pass_rate: number
  avg_duration_ms: number
}

export interface RecentExecution {
  execution_id: string
  name: string | null
  status: string
  total_cases: number
  passed_cases: number
  failed_cases: number
  created_at: string
}

export interface KnowledgeStatistics {
  total: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  by_source: Record<string, number>
  pending_review: number
}

// 导入响应
export interface ImportResponse {
  success: boolean
  message: string
  endpoint_count: number
  tag_count: number
  endpoints?: Array<{
    endpoint_id: string
    name: string
    method: string
    path: string
  }>
  tags?: string[]
  errors?: string[]
  created_count: number
  updated_count: number
  skipped_count: number
  deleted_count: number
}

// 差异对比响应
export interface DiffResponse {
  total_new: number
  total_updated: number
  total_unchanged: number
  total_deleted: number
  diffs: DiffItem[]
}

export interface DiffItem {
  endpoint_id: string
  method: string
  path: string
  name: string
  status: 'new' | 'updated' | 'unchanged' | 'deleted'
  changes: string[]
}

// AI 聊天响应
export interface ChatResponse {
  response: string
  sources?: string[]
  suggestions?: string[]
}

// 健康检查响应
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy'
  checks?: Record<string, {
    status: string
    message?: string
  }>
}
