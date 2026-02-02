/**
 * 该文件内容使用AI生成，注意识别准确性
 * Vue Composables - 可复用的组合式函数
 */

import { ref, reactive, computed, watch, type Ref } from 'vue'

// =====================================================
// 分页 Composable
// =====================================================

export interface PaginationState {
  current: number
  pageSize: number
  total: number
}

export interface UsePaginationOptions {
  defaultPageSize?: number
  onPageChange?: (pagination: PaginationState) => void
}

/**
 * 分页逻辑
 */
export function usePagination(options: UsePaginationOptions = {}) {
  const { defaultPageSize = 20, onPageChange } = options

  const pagination = reactive<PaginationState>({
    current: 1,
    pageSize: defaultPageSize,
    total: 0
  })

  /** 处理分页变化 */
  const handlePageChange = (pageInfo: { current?: number; pageSize?: number }) => {
    if (pageInfo.current) pagination.current = pageInfo.current
    if (pageInfo.pageSize) pagination.pageSize = pageInfo.pageSize
    onPageChange?.(pagination)
  }

  /** 重置到第一页 */
  const resetPage = () => {
    pagination.current = 1
  }

  /** 设置总数 */
  const setTotal = (total: number) => {
    pagination.total = total
  }

  return {
    pagination,
    handlePageChange,
    resetPage,
    setTotal
  }
}

// =====================================================
// 表格选择 Composable
// =====================================================

export interface UseTableSelectionOptions<T> {
  rowKey?: keyof T | string
}

/**
 * 表格多选逻辑
 */
export function useTableSelection<T extends Record<string, any>>(
  options: UseTableSelectionOptions<T> = {}
) {
  const { rowKey = 'id' } = options

  const selectedIds = ref<string[]>([]) as Ref<string[]>
  const selectedRows = ref<T[]>([]) as Ref<T[]>

  /** 处理选择变化 */
  const handleSelectChange = (keys: string[], records?: { selectedRowData: T[] }) => {
    selectedIds.value = keys
    if (records?.selectedRowData) {
      selectedRows.value = records.selectedRowData
    }
  }

  /** 清空选择 */
  const clearSelection = () => {
    selectedIds.value = []
    selectedRows.value = []
  }

  /** 是否有选中项 */
  const hasSelection = computed(() => selectedIds.value.length > 0)

  /** 选中数量 */
  const selectionCount = computed(() => selectedIds.value.length)

  return {
    selectedIds,
    selectedRows,
    handleSelectChange,
    clearSelection,
    hasSelection,
    selectionCount
  }
}

// =====================================================
// 加载状态 Composable
// =====================================================

/**
 * 加载状态管理
 */
export function useLoading(initial = false) {
  const loading = ref(initial)

  /** 执行异步操作并管理加载状态 */
  const withLoading = async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
    loading.value = true
    try {
      return await fn()
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    withLoading
  }
}

// =====================================================
// 搜索筛选 Composable
// =====================================================

export interface UseFiltersOptions<T extends Record<string, any>> {
  defaultFilters?: T
  onFilterChange?: (filters: T) => void
}

/**
 * 搜索筛选逻辑
 */
export function useFilters<T extends Record<string, any>>(
  options: UseFiltersOptions<T> = {}
) {
  const { defaultFilters = {} as T, onFilterChange } = options

  const filters = reactive<T>({ ...defaultFilters })

  /** 重置筛选 */
  const resetFilters = () => {
    Object.assign(filters, defaultFilters)
    onFilterChange?.(filters)
  }

  /** 应用筛选 */
  const applyFilters = () => {
    onFilterChange?.(filters)
  }

  /** 获取非空筛选条件 */
  const getActiveFilters = computed(() => {
    const result: Partial<T> = {}
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== '') {
        (result as any)[key] = value
      }
    }
    return result
  })

  return {
    filters,
    resetFilters,
    applyFilters,
    getActiveFilters
  }
}

// =====================================================
// 对话框 Composable
// =====================================================

/**
 * 对话框状态管理
 */
export function useDialog<T = any>() {
  const visible = ref(false)
  const loading = ref(false)
  const data = ref<T | null>(null) as Ref<T | null>

  /** 打开对话框 */
  const open = (initialData?: T) => {
    data.value = initialData ?? null
    visible.value = true
  }

  /** 关闭对话框 */
  const close = () => {
    visible.value = false
    loading.value = false
  }

  /** 执行确认操作 */
  const confirm = async <R>(fn: () => Promise<R>): Promise<R | undefined> => {
    loading.value = true
    try {
      const result = await fn()
      close()
      return result
    } catch (error) {
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    visible,
    loading,
    data,
    open,
    close,
    confirm
  }
}

// =====================================================
// 列表数据 Composable
// =====================================================

export interface UseListOptions<T, P extends Record<string, any>> {
  fetchFn: (params: P & { page: number; page_size: number }) => Promise<{ items: T[]; total: number }>
  defaultParams?: Partial<P>
  pageSize?: number
  immediate?: boolean
}

/**
 * 列表数据管理（整合分页、加载、筛选）
 */
export function useList<T, P extends Record<string, any> = Record<string, any>>(
  options: UseListOptions<T, P>
) {
  const { fetchFn, defaultParams = {}, pageSize = 20, immediate = true } = options

  const items = ref<T[]>([]) as Ref<T[]>
  const { loading, withLoading } = useLoading()
  const { pagination, handlePageChange, resetPage, setTotal } = usePagination({
    defaultPageSize: pageSize,
    onPageChange: () => load()
  })
  const { filters, resetFilters, getActiveFilters } = useFilters<P>({
    defaultFilters: defaultParams as P,
    onFilterChange: () => {
      resetPage()
      load()
    }
  })

  /** 加载数据 */
  const load = async () => {
    await withLoading(async () => {
      const params = {
        ...getActiveFilters.value,
        page: pagination.current,
        page_size: pagination.pageSize
      } as P & { page: number; page_size: number }

      const res = await fetchFn(params)
      items.value = res.items || []
      setTotal(res.total || 0)
    })
  }

  /** 刷新（保持当前页） */
  const refresh = () => load()

  /** 重新加载（重置到第一页） */
  const reload = () => {
    resetPage()
    load()
  }

  /** 搜索（重置到第一页） */
  const search = () => {
    resetPage()
    load()
  }

  // 立即加载
  if (immediate) {
    load()
  }

  return {
    items,
    loading,
    pagination,
    filters,
    handlePageChange,
    load,
    refresh,
    reload,
    search,
    resetFilters
  }
}

// =====================================================
// 任务轮询 Composable
// =====================================================

export interface UsePollingOptions {
  interval?: number
  maxAttempts?: number
  stopCondition?: (data: any) => boolean
}

/**
 * 轮询任务状态
 */
export function usePolling(options: UsePollingOptions = {}) {
  const { interval = 2000, maxAttempts = 100, stopCondition } = options

  let timer: ReturnType<typeof setInterval> | null = null
  let attempts = 0
  const isPolling = ref(false)
  const data = ref<any>(null)

  /** 开始轮询 */
  const start = async (fetchFn: () => Promise<any>) => {
    attempts = 0
    isPolling.value = true

    const poll = async () => {
      try {
        data.value = await fetchFn()
        attempts++

        if (stopCondition?.(data.value) || attempts >= maxAttempts) {
          stop()
        }
      } catch (error) {
        stop()
        throw error
      }
    }

    // 立即执行一次
    await poll()

    // 如果没有停止，继续轮询
    if (isPolling.value) {
      timer = setInterval(poll, interval)
    }
  }

  /** 停止轮询 */
  const stop = () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    isPolling.value = false
  }

  return {
    isPolling,
    data,
    start,
    stop
  }
}
