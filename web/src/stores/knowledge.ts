/**
 * 知识库模块状态管理
 * 该文件内容使用AI生成，注意识别准确性
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
  entries: KnowledgeEntry[]
  loading: boolean
  pagination: PaginationParams & { total: number }
  filters: KnowledgeFilters
  pendingEntries: KnowledgeEntry[]
  pendingLoading: boolean
  statistics: KnowledgeStatistics | null
  statisticsLoading: boolean
  currentEntry: KnowledgeEntry | null
}

export const useKnowledgeStore = defineStore('knowledge', {
  state: (): KnowledgeState => ({
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
    pendingEntries: [],
    pendingLoading: false,
    statistics: null,
    statisticsLoading: false,
    currentEntry: null
  }),

  getters: {
    pendingCount(): number {
      return this.statistics?.pending_review ?? 0
    },
    typeCountMap(): Record<string, number> {
      return this.statistics?.by_type ?? {}
    },
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
        const result = await knowledgeApi.list(params) as {
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
        this.currentEntry = await knowledgeApi.get(knowledgeId) as KnowledgeEntry
      } catch {
        this.currentEntry = null
      }
    },

    async createEntry(entry: Partial<KnowledgeEntry>) {
      const result = await knowledgeApi.create(entry as any)
      await this.fetchEntries()
      return result
    },

    async updateEntry(knowledgeId: string, updates: Partial<KnowledgeEntry>) {
      await knowledgeApi.update(knowledgeId, updates)
      await this.fetchEntries()
    },

    async deleteEntry(knowledgeId: string) {
      await knowledgeApi.delete(knowledgeId)
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
        const result = await knowledgeApi.listPending({ limit: 100 }) as any
        this.pendingEntries = Array.isArray(result) ? result : (result.items ?? [])
      } finally {
        this.pendingLoading = false
      }
    },

    async approveEntry(knowledgeId: string) {
      await knowledgeApi.review({ knowledge_ids: [knowledgeId], action: 'approve' })
      await Promise.all([
        this.fetchPendingEntries(),
        this.fetchStatistics()
      ])
    },

    async rejectEntry(knowledgeId: string) {
      await knowledgeApi.review({ knowledge_ids: [knowledgeId], action: 'reject' })
      await Promise.all([
        this.fetchPendingEntries(),
        this.fetchStatistics()
      ])
    },

    async batchApprove(knowledgeIds: string[]) {
      await knowledgeApi.review({ knowledge_ids: knowledgeIds, action: 'approve' })
      await Promise.all([
        this.fetchPendingEntries(),
        this.fetchStatistics()
      ])
    },

    // ==================== 统计和搜索 ====================

    async fetchStatistics() {
      this.statisticsLoading = true
      try {
        this.statistics = await knowledgeApi.getStatistics() as KnowledgeStatistics
      } finally {
        this.statisticsLoading = false
      }
    },

    async searchKnowledge(query: string, limit?: number) {
      return await knowledgeApi.search({ query, top_k: limit })
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
