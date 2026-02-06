/**
 * 日志洞察模块状态管理
 */

import { defineStore } from 'pinia'
import { insightsApi, tasksApi } from '@/api/v2'
import type {
  AnalysisTask,
  ParsedRequest,
  AnalysisReport,
  TaskStatus,
  PaginationParams
} from '@/types'

// 筛选器类型
interface TaskFilters {
  status: TaskStatus | ''
  taskType: string
  search: string
}

interface RequestFilters {
  taskId: string
  method: string
  category: string
  hasError: boolean | null
  search: string
}

// 统计数据类型
interface InsightsStatistics {
  tasks: {
    total: number
    by_status: Record<string, number>
    by_type: Record<string, number>
  }
  requests: {
    total: number
    by_method: Record<string, number>
    error_count: number
    warning_count: number
  }
  reports: {
    total: number
    by_type: Record<string, number>
  }
}

// State 类型
interface InsightsState {
  // 任务列表
  tasks: AnalysisTask[]
  tasksLoading: boolean
  tasksPagination: PaginationParams & { total: number }
  tasksFilters: TaskFilters

  // 请求列表
  requests: ParsedRequest[]
  requestsLoading: boolean
  requestsPagination: PaginationParams & { total: number }
  requestsFilters: RequestFilters

  // 报告列表
  reports: AnalysisReport[]
  reportsLoading: boolean

  // 统计数据
  statistics: InsightsStatistics | null
  statisticsLoading: boolean

  // 当前选中
  currentTask: AnalysisTask | null
  currentRequest: ParsedRequest | null
  currentReport: AnalysisReport | null

  // 上传状态
  uploadProgress: number
  isUploading: boolean
}

export const useInsightsStore = defineStore('insights', {
  state: (): InsightsState => ({
    // 任务列表
    tasks: [],
    tasksLoading: false,
    tasksPagination: { page: 1, pageSize: 20, total: 0 },
    tasksFilters: {
      status: '',
      taskType: '',
      search: ''
    },

    // 请求列表
    requests: [],
    requestsLoading: false,
    requestsPagination: { page: 1, pageSize: 50, total: 0 },
    requestsFilters: {
      taskId: '',
      method: '',
      category: '',
      hasError: null,
      search: ''
    },

    // 报告列表
    reports: [],
    reportsLoading: false,

    // 统计数据
    statistics: null,
    statisticsLoading: false,

    // 当前选中
    currentTask: null,
    currentRequest: null,
    currentReport: null,

    // 上传状态
    uploadProgress: 0,
    isUploading: false
  }),

  getters: {
    // 运行中任务数
    runningTasks(): number {
      return this.statistics?.tasks?.by_status?.running ?? 0
    },

    // 已完成任务数
    completedTasks(): number {
      return this.statistics?.tasks?.by_status?.completed ?? 0
    },

    // 错误请求数
    errorRequests(): number {
      return this.statistics?.requests?.error_count ?? 0
    },

    // 总报告数
    totalReports(): number {
      return this.statistics?.reports?.total ?? 0
    }
  },

  actions: {
    // ==================== 任务相关 ====================

    async fetchTasks() {
      this.tasksLoading = true
      try {
        const params = {
          page: this.tasksPagination.page,
          page_size: this.tasksPagination.pageSize,
          status: this.tasksFilters.status || undefined,
          task_type: this.tasksFilters.taskType || undefined,
          search: this.tasksFilters.search || undefined
        }
        const result = await tasksApi.listTasks(params) as {
          items: AnalysisTask[]
          total: number
        }
        this.tasks = result.items
        this.tasksPagination.total = result.total
      } finally {
        this.tasksLoading = false
      }
    },

    async fetchTask(taskId: string) {
      try {
        this.currentTask = await tasksApi.getTask(taskId) as AnalysisTask
      } catch {
        this.currentTask = null
      }
    },

    async deleteTask(taskId: string) {
      await tasksApi.deleteTask(taskId)
      await this.fetchTasks()
    },

    setTaskFilter<K extends keyof TaskFilters>(key: K, value: TaskFilters[K]) {
      this.tasksFilters[key] = value
      this.tasksPagination.page = 1
      this.fetchTasks()
    },

    setTaskPage(page: number) {
      this.tasksPagination.page = page
      this.fetchTasks()
    },

    // ==================== 文件上传 ====================

    async uploadLogFile(file: File, options?: {
      name?: string
      description?: string
      taskType?: string
    }) {
      this.isUploading = true
      this.uploadProgress = 0

      try {
        const formData = new FormData()
        formData.append('file', file)
        if (options?.name) formData.append('name', options.name)
        if (options?.description) formData.append('description', options.description)
        if (options?.taskType) formData.append('task_type', options.taskType)

        const result = await insightsApi.uploadLogFile(formData, {
          onUploadProgress: (progressEvent: { loaded: number; total?: number }) => {
            if (progressEvent.total) {
              this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            }
          }
        })

        await this.fetchTasks()
        return result
      } finally {
        this.isUploading = false
        this.uploadProgress = 0
      }
    },

    // ==================== 请求相关 ====================

    async fetchRequests() {
      if (!this.requestsFilters.taskId) {
        this.requests = []
        return
      }

      this.requestsLoading = true
      try {
        const params = {
          page: this.requestsPagination.page,
          page_size: this.requestsPagination.pageSize,
          method: this.requestsFilters.method || undefined,
          category: this.requestsFilters.category || undefined,
          has_error: this.requestsFilters.hasError ?? undefined,
          search: this.requestsFilters.search || undefined
        }
        const result = await tasksApi.getTaskRequests(
          this.requestsFilters.taskId,
          params
        ) as {
          items: ParsedRequest[]
          total: number
        }
        this.requests = result.items
        this.requestsPagination.total = result.total
      } finally {
        this.requestsLoading = false
      }
    },

    setRequestFilter<K extends keyof RequestFilters>(key: K, value: RequestFilters[K]) {
      this.requestsFilters[key] = value
      this.requestsPagination.page = 1
      if (key === 'taskId' && value) {
        this.fetchRequests()
      }
    },

    setRequestPage(page: number) {
      this.requestsPagination.page = page
      this.fetchRequests()
    },

    // ==================== 报告相关 ====================

    async fetchReports(taskId: string) {
      this.reportsLoading = true
      try {
        const result = await tasksApi.getTaskReports(taskId) as {
          items: AnalysisReport[]
        }
        this.reports = result.items
      } finally {
        this.reportsLoading = false
      }
    },

    async generateReport(taskId: string, reportType?: string) {
      const result = await tasksApi.generateReport(taskId, { report_type: reportType })
      await this.fetchReports(taskId)
      return result
    },

    // ==================== 统计数据 ====================

    async fetchStatistics() {
      this.statisticsLoading = true
      try {
        this.statistics = await insightsApi.getStatistics() as InsightsStatistics
      } finally {
        this.statisticsLoading = false
      }
    },

    // ==================== 重置 ====================

    resetFilters() {
      this.tasksFilters = {
        status: '',
        taskType: '',
        search: ''
      }
      this.requestsFilters = {
        taskId: '',
        method: '',
        category: '',
        hasError: null,
        search: ''
      }
    },

    clearCurrentTask() {
      this.currentTask = null
      this.requests = []
      this.reports = []
      this.requestsFilters.taskId = ''
    }
  }
})
