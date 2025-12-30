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

export default api
