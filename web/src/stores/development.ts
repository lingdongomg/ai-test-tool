/**
 * 开发自测模块状态管理
 */

import { defineStore } from 'pinia'
import { developmentApi } from '@/api/v2'
import type {
  ApiEndpoint,
  TestCase,
  TestExecution,
  PaginationParams,
  HttpMethod,
  TestCategory,
  Priority
} from '@/types'

// 筛选器类型
interface EndpointFilters {
  search: string
  method: string
  tagId: string
  hasTests: boolean | null
}

interface TestCaseFilters {
  endpointId: string
  category: string
  priority: string
  isEnabled: boolean | null
  search: string
}

// 统计数据类型
interface DevelopmentStatistics {
  total_endpoints: number
  endpoints_with_tests: number
  total_test_cases: number
  enabled_test_cases: number
  coverage_rate: number
  recent_executions: Array<{
    execution_id: string
    status: string
    passed_cases: number
    failed_cases: number
    created_at: string
  }>
}

// State 类型
interface DevelopmentState {
  // 接口列表
  endpoints: ApiEndpoint[]
  endpointsLoading: boolean
  endpointsPagination: PaginationParams & { total: number }
  endpointsFilters: EndpointFilters

  // 测试用例列表
  testCases: TestCase[]
  testCasesLoading: boolean
  testCasesPagination: PaginationParams & { total: number }
  testCasesFilters: TestCaseFilters

  // 测试执行列表
  executions: TestExecution[]
  executionsLoading: boolean
  executionsPagination: PaginationParams & { total: number }

  // 统计数据
  statistics: DevelopmentStatistics | null
  statisticsLoading: boolean

  // 当前选中
  currentEndpoint: ApiEndpoint | null
  currentTestCase: TestCase | null
  currentExecution: TestExecution | null
}

export const useDevelopmentStore = defineStore('development', {
  state: (): DevelopmentState => ({
    // 接口列表
    endpoints: [],
    endpointsLoading: false,
    endpointsPagination: { page: 1, pageSize: 20, total: 0 },
    endpointsFilters: {
      search: '',
      method: '',
      tagId: '',
      hasTests: null
    },

    // 测试用例列表
    testCases: [],
    testCasesLoading: false,
    testCasesPagination: { page: 1, pageSize: 20, total: 0 },
    testCasesFilters: {
      endpointId: '',
      category: '',
      priority: '',
      isEnabled: null,
      search: ''
    },

    // 测试执行列表
    executions: [],
    executionsLoading: false,
    executionsPagination: { page: 1, pageSize: 20, total: 0 },

    // 统计数据
    statistics: null,
    statisticsLoading: false,

    // 当前选中
    currentEndpoint: null,
    currentTestCase: null,
    currentExecution: null
  }),

  getters: {
    // 覆盖率百分比
    coveragePercent(): number {
      if (!this.statistics) return 0
      return Math.round(this.statistics.coverage_rate * 100)
    },

    // 有测试用例的接口数
    endpointsWithTests(): number {
      return this.statistics?.endpoints_with_tests ?? 0
    },

    // 启用的测试用例数
    enabledTestCases(): number {
      return this.statistics?.enabled_test_cases ?? 0
    }
  },

  actions: {
    // ==================== 接口相关 ====================

    async fetchEndpoints() {
      this.endpointsLoading = true
      try {
        const params = {
          page: this.endpointsPagination.page,
          page_size: this.endpointsPagination.pageSize,
          search: this.endpointsFilters.search || undefined,
          method: this.endpointsFilters.method || undefined,
          tag_id: this.endpointsFilters.tagId || undefined,
          has_tests: this.endpointsFilters.hasTests ?? undefined
        }
        const result = await developmentApi.listEndpoints(params) as {
          items: ApiEndpoint[]
          total: number
        }
        this.endpoints = result.items
        this.endpointsPagination.total = result.total
      } finally {
        this.endpointsLoading = false
      }
    },

    async fetchEndpoint(endpointId: string) {
      try {
        this.currentEndpoint = await developmentApi.getEndpoint(endpointId) as ApiEndpoint
      } catch {
        this.currentEndpoint = null
      }
    },

    setEndpointFilter<K extends keyof EndpointFilters>(key: K, value: EndpointFilters[K]) {
      this.endpointsFilters[key] = value
      this.endpointsPagination.page = 1
      this.fetchEndpoints()
    },

    setEndpointPage(page: number) {
      this.endpointsPagination.page = page
      this.fetchEndpoints()
    },

    // ==================== 测试用例相关 ====================

    async fetchTestCases() {
      this.testCasesLoading = true
      try {
        const params = {
          page: this.testCasesPagination.page,
          page_size: this.testCasesPagination.pageSize,
          endpoint_id: this.testCasesFilters.endpointId || undefined,
          category: this.testCasesFilters.category || undefined,
          priority: this.testCasesFilters.priority || undefined,
          is_enabled: this.testCasesFilters.isEnabled ?? undefined,
          search: this.testCasesFilters.search || undefined
        }
        const result = await developmentApi.listTests(params) as {
          items: TestCase[]
          total: number
        }
        this.testCases = result.items
        this.testCasesPagination.total = result.total
      } finally {
        this.testCasesLoading = false
      }
    },

    async fetchTestCase(caseId: string) {
      try {
        this.currentTestCase = await developmentApi.getTest(caseId) as TestCase
      } catch {
        this.currentTestCase = null
      }
    },

    async updateTestCase(caseId: string, updates: Partial<TestCase>) {
      await developmentApi.updateTest(caseId, updates)
      await this.fetchTestCases()
    },

    async deleteTestCase(caseId: string) {
      await developmentApi.deleteTest(caseId)
      await this.fetchTestCases()
    },

    async toggleTestCaseEnabled(caseId: string, enabled: boolean) {
      await developmentApi.setTestEnabled(caseId, enabled)
      await this.fetchTestCases()
    },

    setTestCaseFilter<K extends keyof TestCaseFilters>(key: K, value: TestCaseFilters[K]) {
      this.testCasesFilters[key] = value
      this.testCasesPagination.page = 1
      this.fetchTestCases()
    },

    setTestCasePage(page: number) {
      this.testCasesPagination.page = page
      this.fetchTestCases()
    },

    // ==================== 测试执行相关 ====================

    async fetchExecutions() {
      this.executionsLoading = true
      try {
        const params = {
          page: this.executionsPagination.page,
          page_size: this.executionsPagination.pageSize
        }
        const result = await developmentApi.listExecutions(params) as {
          items: TestExecution[]
          total: number
        }
        this.executions = result.items
        this.executionsPagination.total = result.total
      } finally {
        this.executionsLoading = false
      }
    },

    async fetchExecution(executionId: string) {
      try {
        this.currentExecution = await developmentApi.getExecution(executionId) as TestExecution
      } catch {
        this.currentExecution = null
      }
    },

    async runTests(caseIds: string[], baseUrl?: string, environment?: string) {
      const result = await developmentApi.runTests({
        case_ids: caseIds,
        base_url: baseUrl,
        environment
      })
      await this.fetchExecutions()
      return result
    },

    setExecutionPage(page: number) {
      this.executionsPagination.page = page
      this.fetchExecutions()
    },

    // ==================== 统计数据 ====================

    async fetchStatistics() {
      this.statisticsLoading = true
      try {
        this.statistics = await developmentApi.getStatistics() as DevelopmentStatistics
      } finally {
        this.statisticsLoading = false
      }
    },

    // ==================== 重置 ====================

    resetFilters() {
      this.endpointsFilters = {
        search: '',
        method: '',
        tagId: '',
        hasTests: null
      }
      this.testCasesFilters = {
        endpointId: '',
        category: '',
        priority: '',
        isEnabled: null,
        search: ''
      }
    }
  }
})
