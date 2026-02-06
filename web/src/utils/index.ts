/**
 * 该文件内容使用AI生成，注意识别准确性
 * 公共工具函数
 */

// =====================================================
// 主题映射
// =====================================================

/** HTTP 方法 -> 主题颜色 */
export const METHOD_THEME: Record<string, string> = {
  GET: 'success',
  POST: 'primary',
  PUT: 'warning',
  DELETE: 'danger',
  PATCH: 'default'
}

/** 测试类别 -> 主题颜色 */
export const CATEGORY_THEME: Record<string, string> = {
  normal: 'success',
  boundary: 'warning',
  exception: 'danger',
  security: 'primary'
}

/** 测试类别 -> 中文标签 */
export const CATEGORY_LABEL: Record<string, string> = {
  normal: '正常',
  boundary: '边界',
  exception: '异常',
  security: '安全'
}

/** 优先级 -> 主题颜色 */
export const PRIORITY_THEME: Record<string, string> = {
  P0: 'danger',
  P1: 'warning',
  P2: 'primary',
  P3: 'default',
  high: 'danger',
  medium: 'warning',
  low: 'default'
}

/** 严重程度 -> 主题颜色 */
export const SEVERITY_THEME: Record<string, string> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'default',
  info: 'primary'
}

/** 严重程度 -> 中文标签 */
export const SEVERITY_LABEL: Record<string, string> = {
  critical: '严重',
  high: '高',
  medium: '中',
  low: '低',
  info: '信息'
}

/** 状态 -> 主题颜色 */
export const STATUS_THEME: Record<string, string> = {
  success: 'success',
  passed: 'success',
  completed: 'success',
  healthy: 'success',
  running: 'primary',
  pending: 'default',
  warning: 'warning',
  failed: 'danger',
  error: 'danger',
  unhealthy: 'danger'
}

// =====================================================
// 通用工具函数
// =====================================================

/**
 * 获取映射值（带默认值）
 */
export function getMapValue<T>(
  map: Record<string, T>,
  key: string | undefined | null,
  defaultValue: T
): T {
  return key ? (map[key] ?? defaultValue) : defaultValue
}

/** 获取 HTTP 方法主题 */
export const getMethodTheme = (method: string) => getMapValue(METHOD_THEME, method, 'default')

/** 获取类别主题 */
export const getCategoryTheme = (category: string) => getMapValue(CATEGORY_THEME, category, 'default')

/** 获取类别标签 */
export const getCategoryLabel = (category: string) => getMapValue(CATEGORY_LABEL, category, category)

/** 获取优先级主题 */
export const getPriorityTheme = (priority: string) => getMapValue(PRIORITY_THEME, priority, 'default')

/** 获取严重程度主题 */
export const getSeverityTheme = (severity: string) => getMapValue(SEVERITY_THEME, severity, 'default')

/** 获取严重程度标签 */
export const getSeverityLabel = (severity: string) => getMapValue(SEVERITY_LABEL, severity, severity)

/** 获取状态主题 */
export const getStatusTheme = (status: string) => getMapValue(STATUS_THEME, status, 'default')

// =====================================================
// 时间格式化
// =====================================================

/**
 * 格式化相对时间
 * @param time ISO 时间字符串或 Date 对象
 */
export function formatRelativeTime(time: string | Date | undefined | null): string {
  if (!time) return ''
  
  const date = typeof time === 'string' ? new Date(time) : time
  const now = Date.now()
  const diff = now - date.getTime()
  
  if (diff < 0) return '刚刚'
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)} 小时前`
  if (diff < 604800_000) return `${Math.floor(diff / 86400_000)} 天前`
  
  return date.toLocaleDateString('zh-CN')
}

/**
 * 格式化日期时间
 * @param time ISO 时间字符串或 Date 对象
 * @param format 格式：'datetime' | 'date' | 'time'
 */
export function formatDateTime(
  time: string | Date | undefined | null,
  format: 'datetime' | 'date' | 'time' = 'datetime'
): string {
  if (!time) return '-'
  
  const date = typeof time === 'string' ? new Date(time) : time
  const options: Intl.DateTimeFormatOptions = {}
  
  if (format === 'datetime' || format === 'date') {
    options.year = 'numeric'
    options.month = '2-digit'
    options.day = '2-digit'
  }
  if (format === 'datetime' || format === 'time') {
    options.hour = '2-digit'
    options.minute = '2-digit'
    options.second = '2-digit'
  }
  
  return date.toLocaleString('zh-CN', options)
}

/**
 * 格式化持续时间（毫秒）
 */
export function formatDuration(ms: number | undefined | null): string {
  if (ms == null) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  if (ms < 3600_000) return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
  return `${Math.floor(ms / 3600_000)}h ${Math.floor((ms % 3600_000) / 60_000)}m`
}

// =====================================================
// 数据处理
// =====================================================

/**
 * 安全解析 JSON
 */
export function safeParseJSON<T = any>(
  str: string | undefined | null,
  defaultValue: T
): T {
  if (!str) return defaultValue
  try {
    return JSON.parse(str) as T
  } catch {
    return defaultValue
  }
}

/**
 * 安全序列化 JSON
 */
export function safeStringifyJSON(
  obj: any,
  indent: number = 2
): string {
  try {
    return JSON.stringify(obj, null, indent)
  } catch {
    return '{}'
  }
}

/**
 * 去除对象中的空值
 */
export function removeEmpty<T extends object>(obj: T): Partial<T> {
  const result: Partial<T> = {}
  for (const [key, value] of Object.entries(obj)) {
    if (value !== undefined && value !== null && value !== '') {
      (result as any)[key] = value
    }
  }
  return result
}

// =====================================================
// 数字格式化
// =====================================================

/**
 * 格式化百分比
 */
export function formatPercent(
  value: number | undefined | null,
  decimals: number = 1
): string {
  if (value == null) return '0%'
  return `${value.toFixed(decimals)}%`
}

/**
 * 格式化数字（带千分位）
 */
export function formatNumber(value: number | undefined | null): string {
  if (value == null) return '0'
  return value.toLocaleString('zh-CN')
}

// =====================================================
// API 请求工具
// =====================================================

/** API 错误类型 */
export type ApiErrorType = 'network' | 'timeout' | 'server' | 'client' | 'unknown'

/** API 错误接口 */
export interface ApiError {
  type: ApiErrorType
  message: string
  status?: number
  details?: string
}

/**
 * 判断错误类型
 */
export function getApiErrorType(error: unknown): ApiErrorType {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return 'network'
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'timeout'
  }
  if (error instanceof Error) {
    if (error.message.includes('timeout') || error.message.includes('Timeout')) {
      return 'timeout'
    }
    if (error.message.includes('network') || error.message.includes('Network')) {
      return 'network'
    }
  }
  return 'unknown'
}

/**
 * 解析 API 错误
 */
export function parseApiError(error: unknown, response?: Response): ApiError {
  const type = getApiErrorType(error)

  if (type === 'network') {
    return {
      type: 'network',
      message: '网络连接失败，请检查网络后重试'
    }
  }

  if (type === 'timeout') {
    return {
      type: 'timeout',
      message: '请求超时，服务器响应时间过长'
    }
  }

  if (response) {
    const status = response.status
    if (status >= 500) {
      return {
        type: 'server',
        status,
        message: '服务器错误，请稍后重试'
      }
    }
    if (status >= 400) {
      return {
        type: 'client',
        status,
        message: getHttpErrorMessage(status)
      }
    }
  }

  return {
    type: 'unknown',
    message: error instanceof Error ? error.message : '未知错误',
    details: error instanceof Error ? error.stack : undefined
  }
}

/**
 * 获取 HTTP 错误信息
 */
export function getHttpErrorMessage(status: number): string {
  const messages: Record<number, string> = {
    400: '请求参数错误',
    401: '未授权，请重新登录',
    403: '没有访问权限',
    404: '请求的资源不存在',
    405: '不支持的请求方法',
    408: '请求超时',
    409: '资源冲突',
    413: '请求体过大',
    422: '请求数据验证失败',
    429: '请求过于频繁，请稍后重试',
    500: '服务器内部错误',
    502: '网关错误',
    503: '服务暂时不可用',
    504: '网关超时'
  }
  return messages[status] || `HTTP 错误 ${status}`
}

/**
 * 带超时的 fetch 请求
 */
export async function fetchWithTimeout(
  url: string,
  options: RequestInit & { timeout?: number } = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal
    })
    return response
  } finally {
    clearTimeout(timeoutId)
  }
}

/**
 * API 请求封装
 */
export async function apiRequest<T = any>(
  url: string,
  options: RequestInit & { timeout?: number } = {}
): Promise<{ data: T | null; error: ApiError | null }> {
  try {
    const response = await fetchWithTimeout(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    })

    if (!response.ok) {
      return {
        data: null,
        error: parseApiError(new Error(`HTTP ${response.status}`), response)
      }
    }

    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    return {
      data: null,
      error: parseApiError(error)
    }
  }
}
