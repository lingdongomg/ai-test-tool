/**
 * 业务模型类型定义
 */

import type {
  HttpMethod,
  TestCategory,
  Priority,
  ExecutionStatus,
  TaskStatus,
  TestResultStatus,
  TriggerType,
  KnowledgeType,
  KnowledgeStatus,
  KnowledgeSource,
  EndpointSourceType
} from './common'

// =====================================================
// API 接口相关
// =====================================================

export interface ApiEndpoint {
  id?: number
  endpoint_id: string
  name: string
  description: string | null
  method: HttpMethod
  path: string
  summary: string | null
  parameters: Parameter[] | null
  request_body: RequestBody | null
  responses: ApiResponse[] | null
  security: Record<string, unknown> | null
  source_type: EndpointSourceType
  source_file: string | null
  is_deprecated: boolean
  tag_names?: string | null
  test_case_count?: number
  created_at: string
  updated_at: string
}

export interface Parameter {
  name: string
  in: 'query' | 'path' | 'header' | 'cookie'
  required: boolean
  description?: string
  schema?: SchemaType
  example?: unknown
}

export interface RequestBody {
  description?: string
  required?: boolean
  content: Record<string, MediaType>
}

export interface MediaType {
  schema?: SchemaType
  example?: unknown
  examples?: Record<string, ExampleObject>
}

export interface SchemaType {
  type?: string
  format?: string
  items?: SchemaType
  properties?: Record<string, SchemaType>
  required?: string[]
  description?: string
  example?: unknown
  enum?: unknown[]
  default?: unknown
  $ref?: string
}

export interface ExampleObject {
  summary?: string
  description?: string
  value?: unknown
}

export interface ApiResponse {
  status_code: number
  description: string
  content?: Record<string, MediaType>
}

export interface ApiTag {
  id: number
  name: string
  description: string
  color: string
  parent_id: number | null
  sort_order: number
  is_system: boolean
  created_at: string
  updated_at: string
}

// =====================================================
// 测试用例相关
// =====================================================

export interface TestCase {
  id?: number
  case_id: string
  endpoint_id: string
  name: string
  description: string | null
  category: TestCategory
  priority: Priority
  method: HttpMethod
  url: string
  headers: Record<string, string> | null
  body: unknown
  query_params: Record<string, unknown> | null
  expected_status_code: number
  expected_response: unknown
  assertions: Assertion[] | null
  max_response_time_ms: number
  tags: string | null
  is_enabled: boolean
  is_ai_generated: boolean
  source_task_id: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface Assertion {
  type: 'status' | 'json_path' | 'header' | 'response_time' | 'contains' | 'regex'
  path?: string
  expected: unknown
  operator?: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'contains' | 'matches'
}

export interface TestCaseHistory {
  id: number
  case_id: string
  version: number
  change_type: 'create' | 'update' | 'delete' | 'restore' | 'enable' | 'disable'
  change_summary: string | null
  snapshot: string
  changed_fields: string | null
  changed_by: string | null
  created_at: string
}

// =====================================================
// 测试执行相关
// =====================================================

export interface TestExecution {
  id?: number
  execution_id: string
  name: string | null
  description: string | null
  execution_type: 'test' | 'health_check' | 'scenario'
  trigger_type: TriggerType
  status: ExecutionStatus
  base_url: string | null
  environment: string | null
  variables: Record<string, unknown> | null
  headers: Record<string, string> | null
  total_cases: number
  passed_cases: number
  failed_cases: number
  error_cases: number
  skipped_cases: number
  duration_ms: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface TestResult {
  id: number
  case_id: string
  execution_id: string
  result_type: 'test' | 'health_check' | 'scenario_step'
  status: TestResultStatus
  actual_status_code: number | null
  actual_response_time_ms: number | null
  actual_response_body: string | null
  actual_headers: Record<string, string> | null
  error_message: string | null
  assertion_results: AssertionResult[] | null
  ai_analysis: string | null
  executed_at: string
  created_at: string
}

export interface AssertionResult {
  type: string
  expected: unknown
  actual: unknown
  passed: boolean
  message?: string
}

// =====================================================
// 分析任务相关
// =====================================================

export interface AnalysisTask {
  id?: number
  task_id: string
  name: string
  description: string | null
  task_type: 'log_analysis' | 'test_generation' | 'report'
  log_file_path: string | null
  log_file_size: number | null
  status: TaskStatus
  total_lines: number
  processed_lines: number
  total_requests: number
  total_test_cases: number
  error_message: string | null
  metadata: Record<string, unknown> | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface ParsedRequest {
  id: number
  task_id: string
  request_id: string
  method: HttpMethod
  url: string
  category: string | null
  headers: Record<string, string> | null
  body: unknown
  query_params: Record<string, unknown> | null
  http_status: number | null
  response_time_ms: number | null
  response_body: string | null
  has_error: boolean
  error_message: string | null
  has_warning: boolean
  warning_message: string | null
  curl_command: string | null
  timestamp: string | null
  raw_logs: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface AnalysisReport {
  id: number
  task_id: string
  report_type: 'analysis' | 'test' | 'summary' | 'insight'
  title: string
  content: string
  format: 'markdown' | 'html' | 'json'
  statistics: Record<string, unknown> | null
  issues: Issue[] | null
  recommendations: string[] | null
  severity: 'high' | 'medium' | 'low'
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface Issue {
  type: string
  severity: 'high' | 'medium' | 'low'
  message: string
  details?: Record<string, unknown>
}

// =====================================================
// 知识库相关
// =====================================================

export interface KnowledgeEntry {
  id?: number
  knowledge_id: string
  type: KnowledgeType
  category: string
  title: string
  content: string
  scope: string
  priority: number
  status: KnowledgeStatus
  source: KnowledgeSource
  source_ref: string
  metadata: Record<string, unknown>
  tags: string[]
  created_at: string
  updated_at: string
  created_by: string
  version: number
}

export interface KnowledgeHistory {
  id: number
  knowledge_id: string
  version: number
  content: string
  title: string
  changed_by: string
  changed_at: string
  change_type: 'create' | 'update' | 'archive'
}

export interface KnowledgeUsage {
  id: number
  usage_id: string
  knowledge_id: string
  used_in: string
  context: string
  helpful: number
  used_at: string
}

// =====================================================
// 测试场景相关
// =====================================================

export interface TestScenario {
  id?: number
  scenario_id: string
  name: string
  description: string | null
  tags: string | null
  variables: Record<string, unknown> | null
  setup_hooks: string[] | null
  teardown_hooks: string[] | null
  retry_on_failure: boolean
  max_retries: number
  is_enabled: boolean
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface ScenarioStep {
  id?: number
  scenario_id: string
  step_id: string
  step_order: number
  name: string
  description: string | null
  step_type: 'request' | 'wait' | 'condition' | 'loop' | 'extract' | 'assert'
  method: HttpMethod | null
  url: string | null
  headers: Record<string, string> | null
  body: unknown
  query_params: Record<string, unknown> | null
  extractions: Extraction[] | null
  assertions: Assertion[] | null
  wait_time_ms: number
  condition: string | null
  loop_config: LoopConfig | null
  timeout_ms: number
  continue_on_failure: boolean
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface Extraction {
  name: string
  source: 'json_path' | 'header' | 'regex' | 'cookie'
  path: string
}

export interface LoopConfig {
  type: 'count' | 'data' | 'condition'
  count?: number
  data?: unknown[]
  condition?: string
}

export interface ScenarioExecution {
  id?: number
  execution_id: string
  scenario_id: string
  trigger_type: TriggerType
  status: 'pending' | 'running' | 'passed' | 'failed' | 'cancelled'
  base_url: string | null
  environment: string | null
  variables: Record<string, unknown> | null
  total_steps: number
  passed_steps: number
  failed_steps: number
  skipped_steps: number
  duration_ms: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface StepResult {
  id: number
  execution_id: string
  step_id: string
  step_order: number
  status: TestResultStatus
  request_url: string | null
  request_headers: Record<string, string> | null
  request_body: unknown
  response_status_code: number | null
  response_headers: Record<string, string> | null
  response_body: string | null
  response_time_ms: number | null
  extracted_variables: Record<string, unknown> | null
  assertion_results: AssertionResult[] | null
  error_message: string | null
  executed_at: string
}
