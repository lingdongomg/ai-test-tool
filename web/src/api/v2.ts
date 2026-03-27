/**
 * API v2 - 新架构 API
 * 按三大场景组织，带完整类型注解
 */

import axios, { AxiosResponse, AxiosError } from 'axios'
import { MessagePlugin } from 'tdesign-vue-next'
import type {
  ApiEndpoint,
  TestCase,
  TestExecution,
  TestFolder,
  AnalysisTask,
  AnalysisReport,
  KnowledgeEntry,
} from '@/types/models'
import type {
  PaginatedResponse,
  ImportResponse,
  DiffResponse,
  ChatResponse,
  StatisticsResponse,
} from '@/types/api'

const api = axios.create({
  baseURL: '/api/v2',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error: AxiosError<{ detail?: string }>) => {
    console.error('API Error:', error)
    const message = error.response?.data?.detail || error.message || '请求失败'
    MessagePlugin.error(message)
    return Promise.reject(error)
  }
)

// ==================== Dashboard API ====================
export const dashboardApi = {
  getStats: (): Promise<Record<string, any>> => api.get('/dashboard/stats'),
  getActivities: (limit?: number): Promise<any[]> =>
    api.get('/dashboard/activities', { params: { limit } }),
  getInsights: (limit?: number): Promise<any[]> =>
    api.get('/dashboard/insights', { params: { limit } }),
  getQuickActions: (): Promise<any[]> => api.get('/dashboard/quick-actions'),
  getCoverageTrend: (days?: number): Promise<any> =>
    api.get('/dashboard/trends/coverage', { params: { days } }),
  getHealthTrend: (days?: number): Promise<any> =>
    api.get('/dashboard/trends/health', { params: { days } }),
  getAnomalyTrend: (days?: number): Promise<any> =>
    api.get('/dashboard/trends/anomalies', { params: { days } })
}

// ==================== 开发自测 API ====================
export const developmentApi = {
  // 接口管理
  listEndpoints: (params?: {
    search?: string; method?: string; tag_id?: string
    has_tests?: boolean; page?: number; page_size?: number
  }): Promise<PaginatedResponse<ApiEndpoint>> => api.get('/development/endpoints', { params }),

  getEndpoint: (endpointId: string): Promise<ApiEndpoint> =>
    api.get(`/development/endpoints/${endpointId}`),

  // 测试用例生成
  generateTests: (data: {
    endpoint_ids?: string[]; tag_filter?: string
    test_types?: string[]; use_ai?: boolean; skip_existing?: boolean
  }): Promise<{ task_id: string }> => api.post('/development/tests/generate', data),

  generateTestsForEndpoint: (endpointId: string, params?: {
    test_types?: string[]; use_ai?: boolean
  }): Promise<{ task_id: string }> => api.post(`/development/tests/generate/${endpointId}`, null, { params }),

  getGenerateTaskStatus: (taskId: string): Promise<AnalysisTask> =>
    api.get(`/development/tests/generate/${taskId}`),

  listGenerateTasks: (params?: {
    status?: string; page?: number; page_size?: number
  }): Promise<PaginatedResponse<AnalysisTask>> => api.get('/development/tests/generate-tasks', { params }),

  // 测试用例管理
  listTests: (params?: {
    endpoint_id?: string; category?: string; priority?: string
    is_enabled?: boolean; search?: string; folder_id?: string | null
    page?: number; page_size?: number
  }): Promise<PaginatedResponse<TestCase>> => api.get('/development/tests', { params }),

  getTest: (testCaseId: string): Promise<TestCase> =>
    api.get(`/development/tests/${testCaseId}`),

  updateTest: (testCaseId: string, data: Partial<TestCase>): Promise<TestCase> =>
    api.put(`/development/tests/${testCaseId}`, data),

  deleteTest: (testCaseId: string): Promise<void> =>
    api.delete(`/development/tests/${testCaseId}`),

  copyTest: (testCaseId: string, data?: Partial<TestCase>): Promise<TestCase> =>
    api.post(`/development/tests/${testCaseId}/copy`, data),

  setTestEnabled: (testCaseId: string, enabled: boolean): Promise<void> =>
    api.put(`/development/tests/${testCaseId}`, { is_enabled: enabled }),

  // 测试执行
  executeTests: (data: {
    test_case_ids?: string[]; endpoint_id?: string; tag_filter?: string
    base_url: string; environment?: string
  }): Promise<{ execution_id: string; total: number; passed: number; failed: number; pass_rate: number }> =>
    api.post('/development/tests/execute', data),

  // 执行记录
  listExecutions: (params?: {
    endpoint_id?: string; status?: string; page?: number; page_size?: number
  }): Promise<PaginatedResponse<TestExecution>> => api.get('/development/executions', { params }),

  getExecution: (executionId: string): Promise<TestExecution> =>
    api.get(`/development/executions/${executionId}`),

  getExecutionDetail: (executionId: string): Promise<TestExecution & { results: any[] }> =>
    api.get(`/development/executions/${executionId}`),

  listEnvironments: (): Promise<any[]> => api.get('/development/environments'),
  getStatistics: (): Promise<Record<string, any>> => api.get('/development/statistics'),

  // 文件夹管理
  listFolders: (): Promise<{ folders: TestFolder[]; uncategorized_count: number }> =>
    api.get('/development/folders'),

  createFolder: (data: {
    name: string; parent_id?: string | null; description?: string
  }): Promise<TestFolder> => api.post('/development/folders', data),

  updateFolder: (folderId: string, data: {
    name?: string; parent_id?: string | null; sort_order?: number; description?: string
  }): Promise<TestFolder> => api.put(`/development/folders/${folderId}`, data),

  deleteFolder: (folderId: string): Promise<void> =>
    api.delete(`/development/folders/${folderId}`),

  autoOrganize: (preview: boolean = true): Promise<any> =>
    api.post('/development/folders/auto-organize', null, { params: { preview } }),

  moveCases: (data: {
    case_ids: string[]; folder_id: string | null
  }): Promise<void> => api.put('/development/tests/move', data),
}

// ==================== 线上监控 API ====================
export const monitoringApi = {
  listRequests: (params?: {
    tag?: string; is_enabled?: boolean; last_status?: string
    search?: string; page?: number; page_size?: number
  }): Promise<PaginatedResponse<any>> => api.get('/monitoring/requests', { params }),

  getRequest: (requestId: string): Promise<any> =>
    api.get(`/monitoring/requests/${requestId}`),

  addRequest: (data: {
    method: string; url: string; headers?: Record<string, string>
    body?: string; query_params?: Record<string, string>
    expected_status_code?: number; expected_response_pattern?: string
    tags?: string[]; description?: string
  }): Promise<any> => api.post('/monitoring/requests', data),

  updateRequest: (requestId: string, data: any): Promise<any> =>
    api.put(`/monitoring/requests/${requestId}`, data),

  deleteRequest: (requestId: string): Promise<void> =>
    api.delete(`/monitoring/requests/${requestId}`),

  toggleRequest: (requestId: string, isEnabled: boolean): Promise<void> =>
    api.patch(`/monitoring/requests/${requestId}/toggle`, null, { params: { is_enabled: isEnabled } }),

  extractFromLog: (data: {
    task_id: string; min_success_rate?: number
    max_requests_per_endpoint?: number; tags?: string[]
  }): Promise<any> => api.post('/monitoring/requests/extract', data),

  runHealthCheck: (data: {
    base_url: string; request_ids?: string[]; tag_filter?: string
    use_ai_validation?: boolean; timeout_seconds?: number; parallel?: number
  }): Promise<any> => api.post('/monitoring/health-check', data),

  listHealthCheckExecutions: (params?: {
    status?: string; trigger_type?: string; page?: number; page_size?: number
  }): Promise<PaginatedResponse<any>> => api.get('/monitoring/health-check/executions', { params }),

  getHealthCheckExecution: (executionId: string): Promise<any> =>
    api.get(`/monitoring/health-check/executions/${executionId}`),

  getSummary: (days?: number): Promise<any> =>
    api.get('/monitoring/summary', { params: { days } }),

  getStatistics: (): Promise<Record<string, any>> => api.get('/monitoring/statistics'),

  getScheduleConfig: (): Promise<any> => api.get('/monitoring/schedule'),
  updateScheduleConfig: (config: any): Promise<any> => api.put('/monitoring/schedule', config),

  listAlerts: (params?: {
    is_resolved?: boolean; page?: number; page_size?: number
  }): Promise<PaginatedResponse<any>> => api.get('/monitoring/alerts', { params }),

  resolveAlert: (alertId: string): Promise<void> =>
    api.patch(`/monitoring/alerts/${alertId}/resolve`)
}

// ==================== 日志洞察 API ====================
export const insightsApi = {
  uploadLog: (file: File, params?: {
    analysis_type?: string; detect_types?: string
    include_ai_analysis?: boolean; max_lines?: number | null
  }): Promise<AnalysisTask> => {
    const formData = new FormData()
    formData.append('file', file)
    if (params?.analysis_type) formData.append('analysis_type', params.analysis_type)
    if (params?.detect_types) formData.append('detect_types', params.detect_types)
    if (params?.include_ai_analysis !== undefined) {
      formData.append('include_ai_analysis', String(params.include_ai_analysis))
    }
    if (params?.max_lines) formData.append('max_lines', String(params.max_lines))
    return api.post('/insights/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000 // 上传超时 5 分钟
    })
  },

  analyzeLog: (data: {
    task_id?: string; log_content?: string
    include_ai_analysis?: boolean; detect_types?: string[]
  }): Promise<any> => api.post('/insights/analyze', data),

  listTasks: (params?: {
    status?: string; page?: number; page_size?: number
  }): Promise<PaginatedResponse<AnalysisTask>> => api.get('/insights/tasks', { params }),

  getTask: (taskId: string): Promise<AnalysisTask> => api.get(`/insights/tasks/${taskId}`),
  deleteTask: (taskId: string): Promise<void> => api.delete(`/insights/tasks/${taskId}`),

  detectAnomalies: (data: {
    task_id?: string; log_content?: string
    include_ai_analysis?: boolean; detect_types?: string[]
  }): Promise<any> => api.post('/insights/detect', data),

  listReports: (params?: {
    task_id?: string; severity?: string; page?: number; page_size?: number
  }): Promise<PaginatedResponse<AnalysisReport>> => api.get('/insights/reports', { params }),

  getReport: (reportId: number): Promise<AnalysisReport> => api.get(`/insights/reports/${reportId}`),

  downloadReport: (reportId: number, format?: string): Promise<Blob> =>
    api.get(`/insights/reports/${reportId}/download`, { params: { format }, responseType: 'blob' }),

  getTrends: (days?: number): Promise<any> => api.get('/insights/trends', { params: { days } }),
  getStatistics: (): Promise<Record<string, any>> => api.get('/insights/statistics')
}

// ==================== AI 助手 API ====================
export const aiApi = {
  chat: (data: {
    message: string; context?: Record<string, any>; session_id?: string
  }): Promise<ChatResponse> => api.post('/ai/chat', data),

  generateMock: (data: {
    endpoint_id: string; count?: number; scenario?: string
  }): Promise<any> => api.post('/ai/generate/mock', data),

  generateCode: (data: {
    endpoint_id: string; language?: string; framework?: string; include_comments?: boolean
  }): Promise<{ code: string }> => api.post('/ai/generate/code', data),

  analyzePerformance: (data: {
    type: string; target_id?: string; days?: number
  }): Promise<any> => api.post('/ai/analyze/performance', data),

  analyzeCoverage: (): Promise<any> => api.post('/ai/analyze/coverage'),
  analyzeRisk: (): Promise<any> => api.post('/ai/analyze/risk'),

  getRecommendations: (params?: {
    type?: string; limit?: number
  }): Promise<any[]> => api.get('/ai/recommendations', { params }),

  listInsights: (params?: {
    type?: string; severity?: string; is_resolved?: boolean
    page?: number; page_size?: number
  }): Promise<PaginatedResponse<any>> => api.get('/ai/insights', { params }),

  getInsight: (insightId: string): Promise<any> => api.get(`/ai/insights/${insightId}`),
  resolveInsight: (insightId: string): Promise<void> => api.patch(`/ai/insights/${insightId}/resolve`),
  deleteInsight: (insightId: string): Promise<void> => api.delete(`/ai/insights/${insightId}`),
  getStatistics: (): Promise<Record<string, any>> => api.get('/ai/statistics')
}

// ==================== 知识库 API ====================
export const knowledgeApi = {
  list: (params?: {
    type?: string; status?: string; tags?: string; scope?: string
    keyword?: string; page?: number; page_size?: number
  }): Promise<PaginatedResponse<KnowledgeEntry>> => api.get('/knowledge', { params }),

  listPending: (params?: { limit?: number }): Promise<KnowledgeEntry[]> =>
    api.get('/knowledge/pending', { params }),

  getStatistics: (): Promise<Record<string, any>> => api.get('/knowledge/statistics'),

  get: (knowledgeId: string): Promise<KnowledgeEntry> => api.get(`/knowledge/${knowledgeId}`),

  create: (data: {
    title: string; content: string; type?: string; category?: string
    scope?: string; priority?: number; tags?: string[]; metadata?: Record<string, any>
  }): Promise<KnowledgeEntry> => api.post('/knowledge', data),

  update: (knowledgeId: string, data: Partial<KnowledgeEntry>): Promise<KnowledgeEntry> =>
    api.put(`/knowledge/${knowledgeId}`, data),

  delete: (knowledgeId: string): Promise<void> => api.delete(`/knowledge/${knowledgeId}`),

  review: (data: {
    knowledge_ids: string[]; action: 'approve' | 'reject'
  }): Promise<{ processed: number }> => api.post('/knowledge/review', data),

  search: (data: {
    query: string; types?: string[]; tags?: string[]
    scope?: string; top_k?: number; min_score?: number
  }): Promise<any[]> => api.post('/knowledge/search', data),

  learn: (data: {
    content: string; source_ref?: string; auto_approve?: boolean
  }): Promise<KnowledgeEntry> => api.post('/knowledge/learn', data),

  learnFromTask: (data: {
    task_id: string; auto_approve?: boolean
  }): Promise<any> => api.post('/knowledge/learn-from-task', data),

  learnFromFile: (file: File, params?: {
    auto_approve?: boolean; source_ref?: string; max_lines?: number
  }): Promise<any> => {
    const formData = new FormData()
    formData.append('file', file)
    if (params?.auto_approve !== undefined) formData.append('auto_approve', String(params.auto_approve))
    if (params?.source_ref) formData.append('source_ref', params.source_ref)
    if (params?.max_lines) formData.append('max_lines', String(params.max_lines))
    return api.post('/knowledge/learn-from-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000
    })
  },

  rebuildIndex: (): Promise<{ message: string }> => api.post('/knowledge/rebuild-index'),
}

// ==================== 文档导入 API ====================
export const importApi = {
  uploadFile: (file: File, docType?: string, updateStrategy?: string): Promise<ImportResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    if (docType) formData.append('doc_type', docType)
    if (updateStrategy) formData.append('update_strategy', updateStrategy)
    return api.post('/imports/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  importJson: (data: {
    data: any; doc_type?: string; source_name?: string
    save_to_db?: boolean; update_strategy?: string
  }): Promise<ImportResponse> => api.post('/imports/json', data),

  preview: (file: File, docType?: string): Promise<any> => {
    const formData = new FormData()
    formData.append('file', file)
    if (docType) formData.append('doc_type', docType)
    return api.post('/imports/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  diff: (file: File, docType?: string): Promise<DiffResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    if (docType) formData.append('doc_type', docType)
    return api.post('/imports/diff', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  getSupportedFormats: (): Promise<any> => api.get('/imports/supported-formats')
}

// ==================== 实时日志流 API ====================
export const logStreamApi = {
  listSources: (params?: {
    is_enabled?: boolean; status?: string
  }): Promise<any> => api.get('/log-stream/sources', { params }),

  createSource: (data: {
    name: string; description?: string; tags?: string[]
    buffer_size?: number; buffer_timeout_sec?: number
    auto_learn?: boolean; auto_approve_threshold?: number
  }): Promise<any> => api.post('/log-stream/sources', data),

  updateSource: (sourceId: string, data: any): Promise<any> =>
    api.put(`/log-stream/sources/${sourceId}`, data),

  deleteSource: (sourceId: string): Promise<void> =>
    api.delete(`/log-stream/sources/${sourceId}`),

  getSourceStats: (sourceId: string): Promise<any> =>
    api.get(`/log-stream/sources/${sourceId}/stats`),

  // 告警 API
  listAlerts: (params?: {
    source_id?: string; hours?: number; limit?: number
  }): Promise<any> => api.get('/log-stream/alerts', { params }),

  acknowledgeAlert: (alertId: string): Promise<any> =>
    api.post(`/log-stream/alerts/${alertId}/acknowledge`),
}

export default api
