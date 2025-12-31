import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 标签管理
export const tagApi = {
  list: (params?: { parent_id?: number }) => api.get('/tags', { params }),
  tree: () => api.get('/tags/tree/all'),
  create: (data: { name: string; description?: string; color?: string; parent_id?: number }) => 
    api.post('/tags', data),
  update: (id: number, data: { name?: string; description?: string; color?: string }) => 
    api.put(`/tags/${id}`, data),
  delete: (id: number) => api.delete(`/tags/${id}`)
}

// 接口管理
export const endpointApi = {
  list: (params?: { tag_id?: number; method?: string; search?: string; page?: number; size?: number }) => 
    api.get('/endpoints', { params }),
  get: (id: string) => api.get(`/endpoints/${id}`),
  create: (data: any) => api.post('/endpoints', data),
  update: (id: string, data: any) => api.put(`/endpoints/${id}`, data),
  delete: (id: string) => api.delete(`/endpoints/${id}`),
  addTag: (id: string, tagId: number) => api.post(`/endpoints/${id}/tags/${tagId}`),
  removeTag: (id: string, tagId: number) => api.delete(`/endpoints/${id}/tags/${tagId}`)
}

// 文档导入
export const importApi = {
  uploadFile: (file: File, docType: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('doc_type', docType)
    return api.post('/imports/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  importJson: (data: { content: any; doc_type: string; source_name?: string }) => 
    api.post('/imports/json', data),
  preview: (data: { content: any; doc_type: string }) => 
    api.post('/imports/preview', data)
}

// 测试场景
export const scenarioApi = {
  list: (params?: { page?: number; size?: number; is_enabled?: boolean }) => 
    api.get('/scenarios', { params }),
  get: (id: string) => api.get(`/scenarios/${id}`),
  create: (data: any) => api.post('/scenarios', data),
  update: (id: string, data: any) => api.put(`/scenarios/${id}`, data),
  delete: (id: string) => api.delete(`/scenarios/${id}`),
  execute: (id: string, data: { base_url: string; environment?: string; variables?: any }) => 
    api.post(`/scenarios/${id}/execute`, data)
}

// 执行记录
export const executionApi = {
  list: (params?: { scenario_id?: string; status?: string; page?: number; size?: number }) => 
    api.get('/executions', { params }),
  get: (id: string) => api.get(`/executions/${id}`),
  statistics: (params?: { scenario_id?: string; days?: number }) => 
    api.get('/executions/statistics', { params })
}

// 智能分析
export const analysisApi = {
  coverage: (data: { urls: string[]; methods?: string[] }) => 
    api.post('/analysis/coverage', data),
  docComparison: (data: { urls: string[]; methods?: string[]; include_ai_analysis?: boolean }) => 
    api.post('/analysis/doc-comparison', data),
  suggestTags: (data: { url: string; method?: string }) => 
    api.post('/analysis/suggest-tags', data),
  ragContext: (data: { urls: string[]; methods?: string[]; max_results?: number }) => 
    api.post('/analysis/rag-context', data),
  batchCategorize: (data: { urls: string[]; methods?: string[] }) => 
    api.post('/analysis/batch-categorize', data),
  knowledgeBaseStats: () => api.get('/analysis/knowledge-base/stats'),
  knowledgeBaseSummary: (maxCount?: number) => 
    api.get('/analysis/knowledge-base/summary', { params: { max_count: maxCount } })
}

// 分析任务管理
export const taskApi = {
  // 获取任务列表
  list: (params?: { status?: string; offset?: number; limit?: number }) => 
    api.get('/tasks', { params }),
  
  // 获取任务详情
  get: (taskId: string) => api.get(`/tasks/${taskId}`),
  
  // 获取任务结果
  getResult: (taskId: string) => api.get(`/tasks/${taskId}/result`),
  
  // 上传日志文件并分析
  uploadFile: (file: File, options?: { 
    name?: string; 
    max_lines?: number; 
    test_strategy?: string;
    async_mode?: boolean 
  }) => {
    const formData = new FormData()
    formData.append('file', file)
    if (options?.name) formData.append('name', options.name)
    if (options?.max_lines) formData.append('max_lines', String(options.max_lines))
    if (options?.test_strategy) formData.append('test_strategy', options.test_strategy)
    if (options?.async_mode !== undefined) formData.append('async_mode', String(options.async_mode))
    return api.post('/tasks/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  
  // 直接分析日志内容
  analyzeContent: (data: { 
    log_content: string; 
    name?: string; 
    max_lines?: number;
    test_strategy?: string;
    async_mode?: boolean 
  }) => api.post('/tasks/analyze-content', data),
  
  // 执行测试
  runTests: (taskId: string, data: { 
    base_url: string; 
    concurrent?: number;
    async_mode?: boolean 
  }) => api.post(`/tasks/${taskId}/run-tests`, data),
  
  // 生成测试用例
  generateCases: (taskId: string, data: { 
    test_strategy?: string;
    async_mode?: boolean 
  }) => api.post(`/tasks/${taskId}/generate-cases`, data),
  
  // 取消任务
  cancel: (taskId: string) => api.post(`/tasks/${taskId}/cancel`),
  
  // 删除任务
  delete: (taskId: string) => api.delete(`/tasks/${taskId}`)
}

export default api
