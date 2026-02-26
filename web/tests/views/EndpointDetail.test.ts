/**
 * EndpointDetail 接口详情页面组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EndpointDetail from '../../src/views/development/EndpointDetail.vue'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: 'test-endpoint-1' }
  }),
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn()
  })
}))

// Mock tdesign-vue-next
vi.mock('tdesign-vue-next', () => ({
  MessagePlugin: {
    info: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  }
}))

// Mock tdesign-icons-vue-next
vi.mock('tdesign-icons-vue-next', () => ({
  AddIcon: { template: '<span />' },
  PlayIcon: { template: '<span />' }
}))

// Mock API
const mockGetEndpoint = vi.fn()
const mockGenerateTestsForEndpoint = vi.fn()
const mockExecuteTests = vi.fn()
const mockUpdateTest = vi.fn()
const mockCopyTest = vi.fn()

vi.mock('../../src/api/v2', () => ({
  developmentApi: {
    getEndpoint: (...args: any[]) => mockGetEndpoint(...args),
    generateTestsForEndpoint: (...args: any[]) => mockGenerateTestsForEndpoint(...args),
    executeTests: (...args: any[]) => mockExecuteTests(...args),
    updateTest: (...args: any[]) => mockUpdateTest(...args),
    copyTest: (...args: any[]) => mockCopyTest(...args)
  }
}))

const defaultEndpointData = {
  endpoint: {
    endpoint_id: 'test-endpoint-1',
    method: 'GET',
    path: '/api/users',
    name: 'List Users',
    description: 'Get all users',
    parameters: JSON.stringify([
      { name: 'page', in: 'query', type: 'integer', required: false, description: 'Page number' },
      { name: 'size', in: 'query', type: 'integer', required: false, description: 'Page size' }
    ]),
    request_body: null,
    responses: JSON.stringify({
      '200': { description: 'Success', schema: { type: 'array' } },
      '401': { description: 'Unauthorized' }
    }),
    created_at: '2025-01-01'
  },
  test_cases: [
    {
      case_id: 'tc-1', name: 'Normal list', category: 'normal', priority: 'medium',
      method: 'GET', url: '/api/users', is_enabled: 1,
      expected_status_code: 200, max_response_time_ms: 3000,
      headers: {}, body: null, query_params: { page: 1 }
    }
  ],
  tags: [{ id: 't1', name: 'user' }],
  recent_executions: [
    { id: 'ex1', executed_at: '2025-01-10', status: 'passed', response_time_ms: 120, status_code: 200 }
  ],
  statistics: { total_cases: 5, recent_pass_rate: 90 }
}

describe('EndpointDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetEndpoint.mockResolvedValue(defaultEndpointData)
  })

  const mountComponent = () => mount(EndpointDetail, {
    global: {
      stubs: {
        't-card': { template: '<div class="t-card-stub"><slot /><slot name="actions" /></div>' },
        't-row': { template: '<div><slot /></div>' },
        't-col': { template: '<div><slot /></div>' },
      }
    }
  })

  describe('初始化', () => {
    it('组件挂载后应加载接口详情', async () => {
      mountComponent()
      await flushPromises()

      expect(mockGetEndpoint).toHaveBeenCalledWith('test-endpoint-1')
    })

    it('应正确渲染基本结构', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.find('.endpoint-detail').exists()).toBe(true)
      expect(wrapper.find('.endpoint-header').exists()).toBe(true)
      expect(wrapper.find('.endpoint-path').text()).toBe('/api/users')
    })
  })

  describe('计算属性', () => {
    it('parsedParameters 应正确解析参数', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.parsedParameters.length).toBe(2)
      expect(vm.parsedParameters[0].name).toBe('page')
      expect(vm.parsedParameters[1].name).toBe('size')
    })

    it('parsedParameters 无参数时返回空数组', async () => {
      mockGetEndpoint.mockResolvedValueOnce({
        ...defaultEndpointData,
        endpoint: { ...defaultEndpointData.endpoint, parameters: null }
      })
      const wrapper = mountComponent()
      await flushPromises()

      expect((wrapper.vm as any).parsedParameters.length).toBe(0)
    })

    it('parsedParameters 非法 JSON 时返回空数组', async () => {
      mockGetEndpoint.mockResolvedValueOnce({
        ...defaultEndpointData,
        endpoint: { ...defaultEndpointData.endpoint, parameters: 'invalid json' }
      })
      const wrapper = mountComponent()
      await flushPromises()

      expect((wrapper.vm as any).parsedParameters.length).toBe(0)
    })

    it('parsedResponses 应正确解析', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(Object.keys(vm.parsedResponses)).toContain('200')
      expect(Object.keys(vm.parsedResponses)).toContain('401')
    })

    it('hasResponses 有响应时返回 true', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      expect((wrapper.vm as any).hasResponses).toBe(true)
    })

    it('hasResponses 无响应时返回 false', async () => {
      mockGetEndpoint.mockResolvedValueOnce({
        ...defaultEndpointData,
        endpoint: { ...defaultEndpointData.endpoint, responses: null }
      })
      const wrapper = mountComponent()
      await flushPromises()

      expect((wrapper.vm as any).hasResponses).toBe(false)
    })

    it('hasApiDefinition 有参数时返回 true', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      expect((wrapper.vm as any).hasApiDefinition).toBe(true)
    })

    it('hasApiDefinition 全空时返回 false', async () => {
      mockGetEndpoint.mockResolvedValueOnce({
        ...defaultEndpointData,
        endpoint: {
          ...defaultEndpointData.endpoint,
          parameters: null,
          request_body: null,
          responses: null
        }
      })
      const wrapper = mountComponent()
      await flushPromises()

      expect((wrapper.vm as any).hasApiDefinition).toBe(false)
    })

    it('requestBodySchema 应解析 OpenAPI 3.0 格式', async () => {
      mockGetEndpoint.mockResolvedValueOnce({
        ...defaultEndpointData,
        endpoint: {
          ...defaultEndpointData.endpoint,
          request_body: JSON.stringify({
            required: true,
            content: {
              'application/json': {
                schema: { type: 'object', properties: { name: { type: 'string' } } }
              }
            }
          })
        }
      })
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.requestBodySchema.type).toBe('object')
      expect(vm.requestBodyRequired).toBe(true)
    })

    it('requestBodySchema 应解析 Swagger 2.0 格式', async () => {
      mockGetEndpoint.mockResolvedValueOnce({
        ...defaultEndpointData,
        endpoint: {
          ...defaultEndpointData.endpoint,
          request_body: JSON.stringify({
            schema: { type: 'object', properties: { id: { type: 'integer' } } }
          })
        }
      })
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.requestBodySchema.type).toBe('object')
    })

    it('activeDefinitionPanels 应包含存在的面板', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.activeDefinitionPanels).toContain('parameters')
    })
  })

  describe('辅助函数', () => {
    it('getMethodTheme 应返回正确主题', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.getMethodTheme('GET')).toBe('success')
      expect(vm.getMethodTheme('POST')).toBe('primary')
      expect(vm.getMethodTheme('PUT')).toBe('warning')
      expect(vm.getMethodTheme('DELETE')).toBe('danger')
      expect(vm.getMethodTheme('PATCH')).toBe('default')
      expect(vm.getMethodTheme('OPTIONS')).toBe('default')
    })

    it('getCategoryTheme 应返回正确主题', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.getCategoryTheme('normal')).toBe('success')
      expect(vm.getCategoryTheme('boundary')).toBe('warning')
      expect(vm.getCategoryTheme('exception')).toBe('danger')
      expect(vm.getCategoryTheme('security')).toBe('primary')
      expect(vm.getCategoryTheme('unknown')).toBe('default')
    })

    it('getCategoryLabel 应返回中文标签', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.getCategoryLabel('normal')).toBe('正常')
      expect(vm.getCategoryLabel('boundary')).toBe('边界')
      expect(vm.getCategoryLabel('exception')).toBe('异常')
      expect(vm.getCategoryLabel('security')).toBe('安全')
      expect(vm.getCategoryLabel('custom')).toBe('custom')
    })

    it('getStatusCodeTheme 应返回正确主题', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.getStatusCodeTheme('200')).toBe('success')
      expect(vm.getStatusCodeTheme('301')).toBe('warning')
      expect(vm.getStatusCodeTheme('404')).toBe('danger')
      expect(vm.getStatusCodeTheme('500')).toBe('danger')
      expect(vm.getStatusCodeTheme('100')).toBe('default')
    })

    it('getStatusTheme 应返回正确主题', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.getStatusTheme('passed')).toBe('success')
      expect(vm.getStatusTheme('failed')).toBe('danger')
      expect(vm.getStatusTheme('skipped')).toBe('default')
      expect(vm.getStatusTheme('other')).toBe('default')
    })

    it('getStatusLabel 应返回中文标签', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.getStatusLabel('passed')).toBe('通过')
      expect(vm.getStatusLabel('failed')).toBe('失败')
      expect(vm.getStatusLabel('skipped')).toBe('跳过')
      expect(vm.getStatusLabel('other')).toBe('other')
    })

    it('formatJson 应格式化 JSON 对象', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.formatJson({ a: 1 })).toBe('{\n  "a": 1\n}')
    })

    it('formatJson 应格式化 JSON 字符串', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.formatJson('{"a":1}')).toBe('{\n  "a": 1\n}')
    })

    it('formatJson null 时返回 {}', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.formatJson(null)).toBe('{}')
    })

    it('formatJson 无效 JSON 字符串时原样返回', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      expect(vm.formatJson('not-json')).toBe('not-json')
    })
  })

  describe('交互操作', () => {
    it('handleViewCase 应打开详情抽屉', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const row = { case_id: 'tc-1', name: 'Test' }
      const vm = wrapper.vm as any
      vm.handleViewCase(row)

      expect(vm.detailDrawerVisible).toBe(true)
      expect(vm.currentCase).toEqual(row)
    })

    it('handleEditCase 应填充编辑表单', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const row = {
        case_id: 'tc-1', name: 'Test', description: 'desc',
        category: 'boundary', priority: 'high',
        method: 'POST', url: '/api/test',
        expected_status_code: 201, max_response_time_ms: 5000,
        headers: { 'X-Custom': 'val' }, body: { key: 'val' },
        query_params: { q: 'test' }
      }
      const vm = wrapper.vm as any
      vm.handleEditCase(row)

      expect(vm.editDialogVisible).toBe(true)
      expect(vm.isCreating).toBe(false)
      expect(vm.editForm.name).toBe('Test')
      expect(vm.editForm.category).toBe('boundary')
      expect(vm.editForm.method).toBe('POST')
    })

    it('handleEditCase null 时不执行', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      vm.handleEditCase(null)

      expect(vm.editDialogVisible).toBe(false)
    })

    it('handleCopyCase 应设置 isCreating 并在名称后加副本', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const row = {
        case_id: 'tc-1', name: 'Original',
        category: 'normal', priority: 'medium',
        method: 'GET', url: '/test',
        expected_status_code: 200, max_response_time_ms: 3000,
        headers: {}, body: null, query_params: {}
      }
      const vm = wrapper.vm as any
      vm.handleCopyCase(row)

      expect(vm.isCreating).toBe(true)
      expect(vm.editForm.name).toBe('Original (副本)')
    })

    it('handleExecuteTests 应打开执行对话框', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      vm.handleExecuteTests()

      expect(vm.executeDialogVisible).toBe(true)
    })
  })

  describe('API 调用', () => {
    it('加载失败时应显示错误', async () => {
      mockGetEndpoint.mockRejectedValueOnce(new Error('Network error'))
      const { MessagePlugin } = await import('tdesign-vue-next')

      mountComponent()
      await flushPromises()

      expect(MessagePlugin.error).toHaveBeenCalledWith('加载失败')
    })

    it('确认编辑时名称为空应给出警告', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      vm.editForm.name = '   '
      const { MessagePlugin } = await import('tdesign-vue-next')

      await vm.confirmEdit()

      expect(MessagePlugin.warning).toHaveBeenCalledWith('请输入用例名称')
    })

    it('确认编辑（更新模式）应调用 updateTest', async () => {
      mockUpdateTest.mockResolvedValueOnce({})
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      vm.isCreating = false
      vm.editingCaseId = 'tc-1'
      vm.editForm.name = 'Updated Name'
      vm.editDialogVisible = true

      await vm.confirmEdit()
      await flushPromises()

      expect(mockUpdateTest).toHaveBeenCalledWith('tc-1', expect.objectContaining({
        name: 'Updated Name'
      }))
    })

    it('确认编辑（复制模式）应调用 copyTest', async () => {
      mockCopyTest.mockResolvedValueOnce({})
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      vm.isCreating = true
      vm.editingCaseId = 'tc-1'
      vm.editForm.name = 'Copied'
      vm.editDialogVisible = true

      await vm.confirmEdit()
      await flushPromises()

      expect(mockCopyTest).toHaveBeenCalledWith('tc-1', expect.objectContaining({
        name: 'Copied'
      }))
    })

    it('confirmEdit 应解析 JSON 字符串字段', async () => {
      mockUpdateTest.mockResolvedValueOnce({})
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      vm.isCreating = false
      vm.editingCaseId = 'tc-1'
      vm.editForm.name = 'Test'
      vm.editForm.headersStr = '{"Content-Type": "application/json"}'
      vm.editForm.bodyStr = '{"key": "value"}'
      vm.editForm.queryParamsStr = '{"page": 1}'

      await vm.confirmEdit()
      await flushPromises()

      expect(mockUpdateTest).toHaveBeenCalledWith('tc-1', expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
        body: { key: 'value' },
        query_params: { page: 1 }
      }))
    })

    it('confirmEdit 无效 JSON 应回退到默认值', async () => {
      mockUpdateTest.mockResolvedValueOnce({})
      const wrapper = mountComponent()
      await flushPromises()

      const vm = wrapper.vm as any
      vm.isCreating = false
      vm.editingCaseId = 'tc-1'
      vm.editForm.name = 'Test'
      vm.editForm.headersStr = 'invalid'
      vm.editForm.bodyStr = 'invalid'
      vm.editForm.queryParamsStr = 'invalid'

      await vm.confirmEdit()
      await flushPromises()

      expect(mockUpdateTest).toHaveBeenCalledWith('tc-1', expect.objectContaining({
        headers: {},
        body: null,
        query_params: {}
      }))
    })
  })
})
