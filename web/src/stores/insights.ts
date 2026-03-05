/**
 * 日志洞察模块状态管理
 * 该文件内容使用AI生成，注意识别准确性
 */

import { defineStore } from 'pinia'
import { insightsApi } from '@/api/v2'
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

  // 报告列表
  reports: AnalysisReport[]
  reportsLoading: boolean

  // 统计数据
  statistics: InsightsStatistics | null
  statisticsLoading: boolean

  // 当前选中
  currentTask: AnalysisTask | null
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

    // 报告列表
    reports: [],
    reportsLoading: false,

    // 统计数据
    statistics: null,
    statisticsLoading: false,

    // 当前选中
    currentTask: null,
    currentReport: null,

    // 上传状态
    uploadProgress: 0,
    isUploading: false
  }),

  getters: {
    runningTasks(): number {
      return this.statistics?.tasks?.by_status?.running ?? 0
    },
    completedTasks(): number {
      return this.statistics?.tasks?.by_status?.completed ?? 0
    },
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
          status: this.tasksFilters.status || undefined
        }
        const result = await insightsApi.listTasks(params) as {
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
        this.currentTask = await insightsApi.getTask(taskId) as AnalysisTask
      } catch {
        this.currentTask = null
      }
    },

    async deleteTask(taskId: string) {
      await insightsApi.deleteTask(taskId)
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
      analysis_type?: string
      detect_types?: string
      include_ai_analysis?: boolean
      max_lines?: number | null
    }) {
      this.isUploading = true
      this.uploadProgress = 0

      try {
        const result = await insightsApi.uploadLog(file, options)
        await this.fetchTasks()
        return result
      } finally {
        this.isUploading = false
        this.uploadProgress = 0
      }
    },

    // ==================== 报告相关 ====================

    async fetchReports(taskId?: string) {
      this.reportsLoading = true
      try {
        const result = await insightsApi.listReports({ task_id: taskId }) as {
          items: AnalysisReport[]
          total: number
        }
        this.reports = result.items
      } finally {
        this.reportsLoading = false
      }
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
    },

    clearCurrentTask() {
      this.currentTask = null
      this.reports = []
    }
  }
})
