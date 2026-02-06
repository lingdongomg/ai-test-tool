/**
 * 知识库模块状态管理
 */

import { defineStore } from 'pinia'
import { knowledgeApi } from '@/api/v2'
import type {
  KnowledgeEntry,
  KnowledgeType,
  KnowledgeStatus,
  PaginationParams
} from '@/types'

// 筛选器类型
interface KnowledgeFilters {
  type: KnowledgeType | ''
  status: KnowledgeStatus | ''
  tags: string[]
  scope: string
  keyword: string
}

// 统计数据类型
interface KnowledgeStatistics {
  total: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  by_source: Record<string, number>
  pending_review: number
}

// State 类型
interface KnowledgeState {
  // 知识列表
  entries: KnowledgeEntry[]
  loading: boolean
  pagination: PaginationParams & { total: number }
  filters: KnowledgeFilters

  // 待审核列表
  pendingEntries: KnowledgeEntry[]
  pendingLoading: boolean

  // 统计数据
  statistics: KnowledgeStatistics | null
  statisticsLoading: boolean

  // 当前选中
  currentEntry: KnowledgeEntry | null

  // 所有标签
  allTags: string[]
}

export const useKnowledgeStore = defineStore('knowledge', {
  state: (): KnowledgeState => ({
    // 知识列表
    entries: [],
    loading: false,
    pagination: { page: 1, pageSize: 20, total: 0 },
    filters: {
      type: '',
      status: '',
      tags: [],
      scope: '',
      keyword: ''
    },

    // 待审核列表
    pendingEntries: [],
    pendingLoading: false,

    // 统计数据
    statistics: null,
    statisticsLoading: false,

    // 当前选中
    currentEntry: null,

    // 所有标签
    allTags: []
  }),

  getters: {
    // 待审核数量
    pendingCount(): number {
      return this.statistics?.pending_review ?? 0
    },

    // 各类型数量
    typeCountMap(): Record<string, number> {
      return this.statistics?.by_type ?? {}
    },

    // 活跃知识数量
    activeCount(): number {
      return this.statistics?.by_status?.active ?? 0
    }
  },

  actions: {
    // ==================== 知识列表 ====================

    async fetchEntries() {
      this.loading = true
      try {
        const params = {
          page: this.pagination.page,
          page_size: this.pagination.pageSize,
          type: this.filters.type || undefined,
          status: this.filters.status || undefined,
          tags: this.filters.tags.length > 0 ? this.filters.tags.join(',') : undefined,
          scope: this.filters.scope || undefined,
          keyword: this.filters.keyword || undefined
        }
        const result = await knowledgeApi.listEntries(params) as {
          items: KnowledgeEntry[]
          total: number
        }
        this.entries = result.items
        this.pagination.total = result.total
      } finally {
        this.loading = false
      }
    },

    async fetchEntry(knowledgeId: string) {
      try {
        this.currentEntry = await knowledgeApi.getEntry(knowledgeId) as KnowledgeEntry
      } catch {
        this.currentEntry = null
      }
    },

    async createEntry(entry: Partial<KnowledgeEntry>) {
      const result = await knowledgeApi.createEntry(entry)
      await this.fetchEntries()
      return result
    },

    async updateEntry(knowledgeId: string, updates: Partial<KnowledgeEntry>) {
      await knowledgeApi.updateEntry(knowledgeId, updates)
      await this.fetchEntries()
    },

    async deleteEntry(knowledgeId: string) {
      await knowledgeApi.deleteEntry(knowledgeId)
      await this.fetchEntries()
    },

    async archiveEntry(knowledgeId: string) {
      await knowledgeApi.archiveEntry(knowledgeId)
      await this.fetchEntries()
    },

    setFilter<K extends keyof KnowledgeFilters>(key: K, value: KnowledgeFilters[K]) {
      this.filters[key] = value
      this.pagination.page = 1
      this.fetchEntries()
    },

    setPage(page: number) {
      this.pagination.page = page
      this.fetchEntries()
    },

    // ==================== 待审核 ====================

    async fetchPendingEntries() {
      this.pendingLoading = true
      try {
        const result = await knowledgeApi.listPending({ page_size: 100 }) as {
          items: KnowledgeEntry[]
          total: number
        }
        this.pendingEntries = result.items
      } finally {
        this.pendingLoading = false
      }
    },

    async approveEntry(knowledgeId: string) {
      await knowledgeApi.approve(knowledgeId)
      await Promise.all([
        this.fetchPendingEntries(),
        this.fetchStatistics()
      ])
    },

    async rejectEntry(knowledgeId: string, reason?: string) {
      await knowledgeApi.reject(knowledgeId, reason)
      await Promise.all([
        this.fetchPendingEntries(),
        this.fetchStatistics()
      ])
    },

    async batchApprove(knowledgeIds: string[]) {
      await knowledgeApi.batchApprove(knowledgeIds)
      await Promise.all([
        this.fetchPendingEntries(),
        this.fetchStatistics()
      ])
    },

    // ==================== 统计和标签 ====================

    async fetchStatistics() {
      this.statisticsLoading = true
      try {
        this.statistics = await knowledgeApi.getStatistics() as KnowledgeStatistics
      } finally {
        this.statisticsLoading = false
      }
    },

    async fetchAllTags() {
      try {
        const result = await knowledgeApi.getAllTags() as { tags: string[] }
        this.allTags = result.tags
      } catch {
        this.allTags = []
      }
    },

    // ==================== 搜索 ====================

    async searchKnowledge(query: string, limit?: number) {
      return await knowledgeApi.search(query, limit)
    },

    // ==================== 重置 ====================

    resetFilters() {
      this.filters = {
        type: '',
        status: '',
        tags: [],
        scope: '',
        keyword: ''
      }
      this.pagination.page = 1
    }
  }
})
