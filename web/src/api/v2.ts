/**
 * API v2 - 新架构 API
 * 按三大场景组织
 */

import axios, { AxiosResponse, AxiosError } from 'axios'
import { MessagePlugin } from 'tdesign-vue-next'

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
  // 获取核心统计数据
  getStats: () => api.get('/dashboard/stats'),
  
  // 获取近期动态
  getActivities: (limit?: number) => 
    api.get('/dashboard/activities', { params: { limit } }),
  
  // 获取 AI 洞察
  getInsights: (limit?: number) => 
    api.get('/dashboard/insights', { params: { limit } }),
  
  // 获取快捷操作
  getQuickActions: () => api.get('/dashboard/quick-actions'),
  
  // 趋势数据
  getCoverageTrend: (days?: number) => 
    api.get('/dashboard/trends/coverage', { params: { days } }),
  getHealthTrend: (days?: number) => 
    api.get('/dashboard/trends/health', { params: { days } }),
  getAnomalyTrend: (days?: number) => 
    api.get('/dashboard/trends/anomalies', { params: { days } })
}

// ==================== 开发自测 API ====================
export const developmentApi = {
  // 接口管理
  listEndpoints: (params?: {
    search?: string
    method?: string
    tag_id?: string
    has_tests?: boolean
    page?: number
    page_size?: number
  }) => api.get('/development/endpoints', { params }),
  
  getEndpoint: (endpointId: string) => 
    api.get(`/development/endpoints/${endpointId}`),
  
  // 测试用例生成（异步任务）
  generateTests: (data: {
    endpoint_ids?: string[]
    tag_filter?: string
    test_types?: string[]
    use_ai?: boolean
    skip_existing?: boolean
  }) => api.post('/development/tests/generate', data),
  
  generateTestsForEndpoint: (endpointId: string, params?: {
    test_types?: string[]
    use_ai?: boolean
  }) => api.post(`/development/tests/generate/${endpointId}`, null, { params }),
  
  // 查询生成任务状态
  getGenerateTaskStatus: (taskId: string) => 
    api.get(`/development/tests/generate/${taskId}`),
  
  // 获取生成任务列表
  listGenerateTasks: (params?: {
    status?: string
    page?: number
    page_size?: number
  }) => api.get('/development/tests/generate-tasks', { params }),
  
  // 测试用例管理
  listTests: (params?: {
    endpoint_id?: string
    category?: string
    priority?: string
    is_enabled?: boolean
    search?: string
    page?: number
    page_size?: number
  }) => api.get('/development/tests', { params }),
  
  getTest: (testCaseId: string) => 
    api.get(`/development/tests/${testCaseId}`),
  
  updateTest: (testCaseId: string, data: {
    name?: string
    description?: string
    category?: string
    priority?: string
    headers?: Record<string, any>
    body?: Record<string, any>
    query_params?: Record<string, any>
    expected_status_code?: number
    expected_response?: Record<string, any>
    assertions?: any[]
    max_response_time_ms?: number
    is_enabled?: boolean
  }) => api.put(`/development/tests/${testCaseId}`, data),
  
  deleteTest: (testCaseId: string) => 
    api.delete(`/development/tests/${testCaseId}`),
  
  // 复制测试用例
  copyTest: (testCaseId: string, data?: {
    name?: string
    description?: string
    category?: string
    priority?: string
    method?: string
    url?: string
    headers?: Record<string, any>
    body?: Record<string, any>
    query_params?: Record<string, any>
    expected_status_code?: number
    max_response_time_ms?: number
  }) => api.post(`/development/tests/${testCaseId}/copy`, data),
  
  // 测试执行
  executeTests: (data: {
    test_case_ids?: string[]
    endpoint_id?: string
    tag_filter?: string
    base_url: string
    environment?: string
  }) => api.post('/development/tests/execute', data),
  
  // 执行记录
  listExecutions: (params?: {
    endpoint_id?: string
    status?: string
    page?: number
    page_size?: number
  }) => api.get('/development/executions', { params }),
  
  // 环境配置
  listEnvironments: () => api.get('/development/environments'),
  
  // 统计数据
  getStatistics: () => api.get('/development/statistics')
}

// ==================== 线上监控 API ====================
export const monitoringApi = {
  // 监控请求管理
  listRequests: (params?: {
    tag?: string
    is_enabled?: boolean
    last_status?: string
    search?: string
    page?: number
    page_size?: number
  }) => api.get('/monitoring/requests', { params }),
  
  getRequest: (requestId: string) => 
    api.get(`/monitoring/requests/${requestId}`),
  
  addRequest: (data: {
    method: string
    url: string
    headers?: Record<string, string>
    body?: string
    query_params?: Record<string, string>
    expected_status_code?: number
    expected_response_pattern?: string
    tags?: string[]
    description?: string
  }) => api.post('/monitoring/requests', data),
  
  updateRequest: (requestId: string, data: any) => 
    api.put(`/monitoring/requests/${requestId}`, data),
  
  deleteRequest: (requestId: string) => 
    api.delete(`/monitoring/requests/${requestId}`),
  
  toggleRequest: (requestId: string, isEnabled: boolean) => 
    api.patch(`/monitoring/requests/${requestId}/toggle`, null, { params: { is_enabled: isEnabled } }),
  
  // 从日志提取
  extractFromLog: (data: {
    task_id: string
    min_success_rate?: number
    max_requests_per_endpoint?: number
    tags?: string[]
  }) => api.post('/monitoring/requests/extract', data),
  
  // 健康检查
  runHealthCheck: (data: {
    base_url: string
    request_ids?: string[]
    tag_filter?: string
    use_ai_validation?: boolean
    timeout_seconds?: number
    parallel?: number
  }) => api.post('/monitoring/health-check', data),
  
  listHealthCheckExecutions: (params?: {
    status?: string
    trigger_type?: string
    page?: number
    page_size?: number
  }) => api.get('/monitoring/health-check/executions', { params }),
  
  getHealthCheckExecution: (executionId: string) => 
    api.get(`/monitoring/health-check/executions/${executionId}`),
  
  // 健康摘要
  getSummary: (days?: number) => 
    api.get('/monitoring/summary', { params: { days } }),
  
  // 统计数据
  getStatistics: () => api.get('/monitoring/statistics'),
  
  // 定时任务配置
  getScheduleConfig: () => api.get('/monitoring/schedule'),
  updateScheduleConfig: (config: any) => api.put('/monitoring/schedule', config),
  
  // 告警
  listAlerts: (params?: {
    is_resolved?: boolean
    page?: number
    page_size?: number
  }) => api.get('/monitoring/alerts', { params }),
  
  resolveAlert: (alertId: string) => 
    api.patch(`/monitoring/alerts/${alertId}/resolve`)
}

// ==================== 日志洞察 API ====================
export const insightsApi = {
  // 日志上传
  uploadLog: (file: File, params?: {
    analysis_type?: string  // anomaly | request
    detect_types?: string
    include_ai_analysis?: boolean
    max_lines?: number | null
  }) => {
    const formData = new FormData()
    formData.append('file', file)
    if (params?.analysis_type) formData.append('analysis_type', params.analysis_type)
    if (params?.detect_types) formData.append('detect_types', params.detect_types)
    if (params?.include_ai_analysis !== undefined) {
      formData.append('include_ai_analysis', String(params.include_ai_analysis))
    }
    if (params?.max_lines) formData.append('max_lines', String(params.max_lines))
    return api.post('/insights/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  // 分析日志
  analyzeLog: (data: {
    task_id?: string
    log_content?: string
    include_ai_analysis?: boolean
    detect_types?: string[]
  }) => api.post('/insights/analyze', data),
  
  // 分析任务
  listTasks: (params?: {
    status?: string
    page?: number
    page_size?: number
  }) => api.get('/insights/tasks', { params }),
  
  getTask: (taskId: string) => api.get(`/insights/tasks/${taskId}`),
  
  deleteTask: (taskId: string) => api.delete(`/insights/tasks/${taskId}`),
  
  // 异常检测
  detectAnomalies: (data: {
    task_id?: string
    log_content?: string
    include_ai_analysis?: boolean
    detect_types?: string[]
  }) => api.post('/insights/detect', data),
  
  // 报告管理
  listReports: (params?: {
    task_id?: string
    severity?: string
    page?: number
    page_size?: number
  }) => api.get('/insights/reports', { params }),
  
  getReport: (reportId: number) => api.get(`/insights/reports/${reportId}`),
  
  downloadReport: (reportId: number, format?: string) => 
    api.get(`/insights/reports/${reportId}/download`, { 
      params: { format },
      responseType: 'blob'
    }),
  
  // 趋势
  getTrends: (days?: number) => api.get('/insights/trends', { params: { days } }),
  
  // 统计
  getStatistics: () => api.get('/insights/statistics')
}

// ==================== AI 助手 API ====================
export const aiApi = {
  // 对话
  chat: (data: {
    message: string
    context?: Record<string, any>
    session_id?: string
  }) => api.post('/ai/chat', data),
  
  // 生成 Mock 数据
  generateMock: (data: {
    endpoint_id: string
    count?: number
    scenario?: string
  }) => api.post('/ai/generate/mock', data),
  
  // 生成测试代码
  generateCode: (data: {
    endpoint_id: string
    language?: string
    framework?: string
    include_comments?: boolean
  }) => api.post('/ai/generate/code', data),
  
  // 智能分析
  analyzePerformance: (data: {
    type: string
    target_id?: string
    days?: number
  }) => api.post('/ai/analyze/performance', data),
  
  analyzeCoverage: () => api.post('/ai/analyze/coverage'),
  
  analyzeRisk: () => api.post('/ai/analyze/risk'),
  
  // 智能建议
  getRecommendations: (params?: {
    type?: string
    limit?: number
  }) => api.get('/ai/recommendations', { params }),
  
  // 洞察管理
  listInsights: (params?: {
    type?: string
    severity?: string
    is_resolved?: boolean
    page?: number
    page_size?: number
  }) => api.get('/ai/insights', { params }),
  
  getInsight: (insightId: string) => api.get(`/ai/insights/${insightId}`),
  
  resolveInsight: (insightId: string) => 
    api.patch(`/ai/insights/${insightId}/resolve`),
  
  deleteInsight: (insightId: string) => 
    api.delete(`/ai/insights/${insightId}`),
  
  // 统计
  getStatistics: () => api.get('/ai/statistics')
}

// ==================== 文档导入 API ====================
export const importApi = {
  // 上传文件导入
  uploadFile: (file: File, docType?: string, updateStrategy?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (docType) formData.append('doc_type', docType)
    if (updateStrategy) formData.append('update_strategy', updateStrategy)
    return api.post('/imports/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  // JSON 数据导入
  importJson: (data: {
    data: any
    doc_type?: string
    source_name?: string
    save_to_db?: boolean
    update_strategy?: string
  }) => api.post('/imports/json', data),
  
  // 预览导入
  preview: (file: File, docType?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (docType) formData.append('doc_type', docType)
    return api.post('/imports/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  // 对比差异
  diff: (file: File, docType?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (docType) formData.append('doc_type', docType)
    return api.post('/imports/diff', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  // 获取支持的格式
  getSupportedFormats: () => api.get('/imports/supported-formats')
}

export default api
