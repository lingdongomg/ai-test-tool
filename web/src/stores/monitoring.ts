/**
 * 线上监控模块状态管理
 */

import { defineStore } from 'pinia'
import { monitoringApi } from '@/api/v2'
import type {
  PaginationParams,
  ExecutionStatus,
  TriggerType
} from '@/types'

// 健康检查结果类型
interface HealthCheckResult {
  execution_id: string
  name: string | null
  status: ExecutionStatus
  base_url: string | null
  environment: string | null
  total_cases: number
  passed_cases: number
  failed_cases: number
  error_cases: number
  duration_ms: number
  started_at: string | null
  completed_at: string | null
  created_at: string
}

// 告警类型
interface Alert {
  alert_id: string
  type: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  message: string
  source: string
  is_acknowledged: boolean
  acknowledged_at: string | null
  acknowledged_by: string | null
  created_at: string
}

// 调度任务类型
interface ScheduledJob {
  job_id: string
  name: string
  description: string | null
  schedule: string
  target_type: 'health_check' | 'test_batch'
  target_config: Record<string, unknown>
  is_enabled: boolean
  last_run_at: string | null
  next_run_at: string | null
  created_at: string
}

// 监控统计类型
interface MonitoringStatistics {
  health_checks: {
    total: number
    passed: number
    failed: number
    pass_rate: number
  }
  alerts: {
    total: number
    unacknowledged: number
    by_severity: Record<string, number>
  }
  scheduled_jobs: {
    total: number
    enabled: number
  }
}

// 筛选器类型
interface HealthCheckFilters {
  status: string
  environment: string
  dateRange: [string, string] | null
}

interface AlertFilters {
  type: string
  severity: string
  isAcknowledged: boolean | null
}

// State 类型
interface MonitoringState {
  // 健康检查列表
  healthChecks: HealthCheckResult[]
  healthChecksLoading: boolean
  healthChecksPagination: PaginationParams & { total: number }
  healthChecksFilters: HealthCheckFilters

  // 告警列表
  alerts: Alert[]
  alertsLoading: boolean
  alertsPagination: PaginationParams & { total: number }
  alertsFilters: AlertFilters

  // 调度任务列表
  scheduledJobs: ScheduledJob[]
  scheduledJobsLoading: boolean

  // 统计数据
  statistics: MonitoringStatistics | null
  statisticsLoading: boolean

  // 当前选中
  currentHealthCheck: HealthCheckResult | null
  currentAlert: Alert | null
}

export const useMonitoringStore = defineStore('monitoring', {
  state: (): MonitoringState => ({
    // 健康检查列表
    healthChecks: [],
    healthChecksLoading: false,
    healthChecksPagination: { page: 1, pageSize: 20, total: 0 },
    healthChecksFilters: {
      status: '',
      environment: '',
      dateRange: null
    },

    // 告警列表
    alerts: [],
    alertsLoading: false,
    alertsPagination: { page: 1, pageSize: 20, total: 0 },
    alertsFilters: {
      type: '',
      severity: '',
      isAcknowledged: null
    },

    // 调度任务列表
    scheduledJobs: [],
    scheduledJobsLoading: false,

    // 统计数据
    statistics: null,
    statisticsLoading: false,

    // 当前选中
    currentHealthCheck: null,
    currentAlert: null
  }),

  getters: {
    // 通过率百分比
    passRate(): number {
      return this.statistics?.health_checks?.pass_rate ?? 0
    },

    // 未确认告警数
    unacknowledgedAlerts(): number {
      return this.statistics?.alerts?.unacknowledged ?? 0
    },

    // 严重告警数
    criticalAlerts(): number {
      return this.statistics?.alerts?.by_severity?.critical ?? 0
    },

    // 启用的调度任务数
    enabledJobs(): number {
      return this.statistics?.scheduled_jobs?.enabled ?? 0
    }
  },

  actions: {
    // ==================== 健康检查相关 ====================

    async fetchHealthChecks() {
      this.healthChecksLoading = true
      try {
        const params = {
          page: this.healthChecksPagination.page,
          page_size: this.healthChecksPagination.pageSize,
          status: this.healthChecksFilters.status || undefined,
          environment: this.healthChecksFilters.environment || undefined,
          start_date: this.healthChecksFilters.dateRange?.[0] || undefined,
          end_date: this.healthChecksFilters.dateRange?.[1] || undefined
        }
        const result = await monitoringApi.listHealthChecks(params) as {
          items: HealthCheckResult[]
          total: number
        }
        this.healthChecks = result.items
        this.healthChecksPagination.total = result.total
      } finally {
        this.healthChecksLoading = false
      }
    },

    async fetchHealthCheck(executionId: string) {
      try {
        this.currentHealthCheck = await monitoringApi.getHealthCheck(executionId) as HealthCheckResult
      } catch {
        this.currentHealthCheck = null
      }
    },

    async runHealthCheck(config?: { base_url?: string; environment?: string }) {
      const result = await monitoringApi.runHealthCheck(config)
      await this.fetchHealthChecks()
      return result
    },

    setHealthCheckFilter<K extends keyof HealthCheckFilters>(key: K, value: HealthCheckFilters[K]) {
      this.healthChecksFilters[key] = value
      this.healthChecksPagination.page = 1
      this.fetchHealthChecks()
    },

    setHealthCheckPage(page: number) {
      this.healthChecksPagination.page = page
      this.fetchHealthChecks()
    },

    // ==================== 告警相关 ====================

    async fetchAlerts() {
      this.alertsLoading = true
      try {
        const params = {
          page: this.alertsPagination.page,
          page_size: this.alertsPagination.pageSize,
          type: this.alertsFilters.type || undefined,
          severity: this.alertsFilters.severity || undefined,
          is_acknowledged: this.alertsFilters.isAcknowledged ?? undefined
        }
        const result = await monitoringApi.listAlerts(params) as {
          items: Alert[]
          total: number
        }
        this.alerts = result.items
        this.alertsPagination.total = result.total
      } finally {
        this.alertsLoading = false
      }
    },

    async acknowledgeAlert(alertId: string) {
      await monitoringApi.acknowledgeAlert(alertId)
      await Promise.all([
        this.fetchAlerts(),
        this.fetchStatistics()
      ])
    },

    async batchAcknowledgeAlerts(alertIds: string[]) {
      await monitoringApi.batchAcknowledgeAlerts(alertIds)
      await Promise.all([
        this.fetchAlerts(),
        this.fetchStatistics()
      ])
    },

    async deleteAlert(alertId: string) {
      await monitoringApi.deleteAlert(alertId)
      await this.fetchAlerts()
    },

    setAlertFilter<K extends keyof AlertFilters>(key: K, value: AlertFilters[K]) {
      this.alertsFilters[key] = value
      this.alertsPagination.page = 1
      this.fetchAlerts()
    },

    setAlertPage(page: number) {
      this.alertsPagination.page = page
      this.fetchAlerts()
    },

    // ==================== 调度任务相关 ====================

    async fetchScheduledJobs() {
      this.scheduledJobsLoading = true
      try {
        const result = await monitoringApi.listScheduledJobs() as {
          items: ScheduledJob[]
        }
        this.scheduledJobs = result.items
      } finally {
        this.scheduledJobsLoading = false
      }
    },

    async createScheduledJob(job: Partial<ScheduledJob>) {
      const result = await monitoringApi.createScheduledJob(job)
      await this.fetchScheduledJobs()
      return result
    },

    async updateScheduledJob(jobId: string, updates: Partial<ScheduledJob>) {
      await monitoringApi.updateScheduledJob(jobId, updates)
      await this.fetchScheduledJobs()
    },

    async deleteScheduledJob(jobId: string) {
      await monitoringApi.deleteScheduledJob(jobId)
      await this.fetchScheduledJobs()
    },

    async toggleScheduledJob(jobId: string, enabled: boolean) {
      await monitoringApi.setScheduledJobEnabled(jobId, enabled)
      await this.fetchScheduledJobs()
    },

    // ==================== 统计数据 ====================

    async fetchStatistics() {
      this.statisticsLoading = true
      try {
        this.statistics = await monitoringApi.getStatistics() as MonitoringStatistics
      } finally {
        this.statisticsLoading = false
      }
    },

    // ==================== 重置 ====================

    resetFilters() {
      this.healthChecksFilters = {
        status: '',
        environment: '',
        dateRange: null
      }
      this.alertsFilters = {
        type: '',
        severity: '',
        isAcknowledged: null
      }
    }
  }
})
