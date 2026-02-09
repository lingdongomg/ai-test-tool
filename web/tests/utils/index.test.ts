/**
 * 该文件内容使用AI生成，注意识别准确性
 * Utils 工具函数测试
 */

import { describe, it, expect } from 'vitest'
import {
  formatRelativeTime,
  formatDateTime,
  formatDuration,
  formatNumber,
  formatPercent,
  safeParseJSON,
  safeStringifyJSON,
  removeEmpty,
  getMethodTheme,
  getCategoryTheme,
  getStatusTheme,
  parseApiError,
  getHttpErrorMessage,
} from '../../src/utils'

describe('格式化函数', () => {
  describe('formatRelativeTime', () => {
    it('应该返回空字符串当输入为空', () => {
      expect(formatRelativeTime(null)).toBe('')
      expect(formatRelativeTime(undefined)).toBe('')
    })

    it('应该返回"刚刚"当时间在1分钟内', () => {
      const now = new Date()
      expect(formatRelativeTime(now)).toBe('刚刚')
    })

    it('应该正确格式化分钟前', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000)
      expect(formatRelativeTime(fiveMinutesAgo)).toMatch(/\d+ 分钟前/)
    })

    it('应该正确格式化小时前', () => {
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000)
      expect(formatRelativeTime(twoHoursAgo)).toMatch(/\d+ 小时前/)
    })

    it('应该正确格式化天前', () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000)
      expect(formatRelativeTime(threeDaysAgo)).toMatch(/\d+ 天前/)
    })
  })

  describe('formatDateTime', () => {
    it('应该返回"-"当输入为空', () => {
      expect(formatDateTime(null)).toBe('-')
      expect(formatDateTime(undefined)).toBe('-')
    })

    it('应该正确格式化日期时间', () => {
      const date = new Date('2024-01-15T10:30:00')
      const result = formatDateTime(date, 'datetime')
      expect(result).toContain('2024')
      expect(result).toContain('01')
      expect(result).toContain('15')
    })

    it('应该只格式化日期', () => {
      const date = new Date('2024-01-15T10:30:00')
      const result = formatDateTime(date, 'date')
      expect(result).toContain('2024')
      expect(result).not.toContain('10:30')
    })
  })

  describe('formatDuration', () => {
    it('应该返回"-"当输入为空', () => {
      expect(formatDuration(null)).toBe('-')
      expect(formatDuration(undefined)).toBe('-')
    })

    it('应该正确格式化毫秒', () => {
      expect(formatDuration(500)).toBe('500ms')
    })

    it('应该正确格式化秒', () => {
      expect(formatDuration(2500)).toBe('2.5s')
    })

    it('应该正确格式化分钟', () => {
      expect(formatDuration(125000)).toBe('2m 5s')
    })

    it('应该正确格式化小时', () => {
      expect(formatDuration(3725000)).toBe('1h 2m')
    })
  })

  describe('formatNumber', () => {
    it('应该返回"0"当输入为空', () => {
      expect(formatNumber(null)).toBe('0')
      expect(formatNumber(undefined)).toBe('0')
    })

    it('应该正确格式化数字', () => {
      expect(formatNumber(1234567)).toContain('1')
    })
  })

  describe('formatPercent', () => {
    it('应该返回"0%"当输入为空', () => {
      expect(formatPercent(null)).toBe('0%')
    })

    it('应该正确格式化百分比', () => {
      expect(formatPercent(75.5)).toBe('75.5%')
      expect(formatPercent(100)).toBe('100.0%')
    })

    it('应该支持自定义小数位', () => {
      expect(formatPercent(75.555, 2)).toBe('75.56%')
    })
  })
})

describe('JSON 处理函数', () => {
  describe('safeParseJSON', () => {
    it('应该返回默认值当输入为空', () => {
      expect(safeParseJSON(null, {})).toEqual({})
      expect(safeParseJSON(undefined, [])).toEqual([])
    })

    it('应该正确解析有效JSON', () => {
      expect(safeParseJSON('{"key": "value"}', {})).toEqual({ key: 'value' })
    })

    it('应该返回默认值当JSON无效', () => {
      expect(safeParseJSON('invalid json', { default: true })).toEqual({ default: true })
    })
  })

  describe('safeStringifyJSON', () => {
    it('应该正确序列化对象', () => {
      const result = safeStringifyJSON({ key: 'value' })
      expect(result).toContain('key')
      expect(result).toContain('value')
    })

    it('应该返回"{}"当序列化失败', () => {
      const circular: any = {}
      circular.self = circular
      expect(safeStringifyJSON(circular)).toBe('{}')
    })
  })

  describe('removeEmpty', () => {
    it('应该移除空值', () => {
      const obj = { a: 1, b: null, c: undefined, d: '', e: 'value' }
      const result = removeEmpty(obj)
      expect(result).toEqual({ a: 1, e: 'value' })
    })

    it('应该保留有值的属性', () => {
      const obj = { a: 0, b: false }
      const result = removeEmpty(obj)
      expect(result).toEqual({ a: 0, b: false })
    })
  })
})

describe('主题映射函数', () => {
  describe('getMethodTheme', () => {
    it('应该返回正确的主题', () => {
      expect(getMethodTheme('GET')).toBe('success')
      expect(getMethodTheme('POST')).toBe('primary')
      expect(getMethodTheme('DELETE')).toBe('danger')
    })

    it('应该返回默认主题当方法未知', () => {
      expect(getMethodTheme('UNKNOWN')).toBe('default')
    })
  })

  describe('getCategoryTheme', () => {
    it('应该返回正确的主题', () => {
      expect(getCategoryTheme('normal')).toBe('success')
      expect(getCategoryTheme('exception')).toBe('danger')
    })
  })

  describe('getStatusTheme', () => {
    it('应该返回正确的主题', () => {
      expect(getStatusTheme('success')).toBe('success')
      expect(getStatusTheme('failed')).toBe('danger')
      expect(getStatusTheme('pending')).toBe('default')
    })
  })
})

describe('API 错误处理', () => {
  describe('getHttpErrorMessage', () => {
    it('应该返回正确的错误信息', () => {
      expect(getHttpErrorMessage(400)).toBe('请求参数错误')
      expect(getHttpErrorMessage(401)).toBe('未授权，请重新登录')
      expect(getHttpErrorMessage(404)).toBe('请求的资源不存在')
      expect(getHttpErrorMessage(500)).toBe('服务器内部错误')
    })

    it('应该返回通用错误信息当状态码未知', () => {
      expect(getHttpErrorMessage(418)).toBe('HTTP 错误 418')
    })
  })

  describe('parseApiError', () => {
    it('应该正确识别网络错误', () => {
      const error = new TypeError('Failed to fetch')
      const result = parseApiError(error)
      expect(result.type).toBe('network')
      expect(result.message).toContain('网络')
    })

    it('应该正确识别超时错误', () => {
      const error = new DOMException('The operation was aborted', 'AbortError')
      const result = parseApiError(error)
      expect(result.type).toBe('timeout')
      expect(result.message).toContain('超时')
    })
  })
})
