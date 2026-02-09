/**
 * 该文件内容使用AI生成，注意识别准确性
 * ErrorBoundary 组件测试
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, defineComponent, h } from 'vue'
import ErrorBoundary from '../../src/components/ErrorBoundary.vue'

// 模拟 vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    back: vi.fn(),
    push: vi.fn()
  })
}))

// 模拟 TDesign
vi.mock('tdesign-vue-next', () => ({
  MessagePlugin: {
    info: vi.fn()
  }
}))

describe('ErrorBoundary', () => {
  it('应该正确渲染子内容', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: '<div class="child-content">正常内容</div>'
      },
      global: {
        stubs: {
          't-button': true,
          't-collapse': true,
          't-collapse-panel': true,
          'error-circle-icon': true,
          'refresh-icon': true,
          'arrow-left-icon': true,
          'chat-icon': true
        }
      }
    })
    expect(wrapper.find('.child-content').exists()).toBe(true)
    expect(wrapper.find('.error-container').exists()).toBe(false)
  })

  it('应该有正确的默认props', () => {
    const wrapper = mount(ErrorBoundary, {
      global: {
        stubs: {
          't-button': true,
          't-collapse': true,
          't-collapse-panel': true,
          'error-circle-icon': true,
          'refresh-icon': true,
          'arrow-left-icon': true,
          'chat-icon': true
        }
      }
    })
    expect(wrapper.props('fallbackTitle')).toBe('出错了')
    expect(wrapper.props('showReport')).toBe(true)
  })

  it('应该暴露reset方法', () => {
    const wrapper = mount(ErrorBoundary, {
      global: {
        stubs: {
          't-button': true,
          't-collapse': true,
          't-collapse-panel': true,
          'error-circle-icon': true,
          'refresh-icon': true,
          'arrow-left-icon': true,
          'chat-icon': true
        }
      }
    })
    expect(typeof wrapper.vm.reset).toBe('function')
  })

  it('应该暴露hasError状态', () => {
    const wrapper = mount(ErrorBoundary, {
      global: {
        stubs: {
          't-button': true,
          't-collapse': true,
          't-collapse-panel': true,
          'error-circle-icon': true,
          'refresh-icon': true,
          'arrow-left-icon': true,
          'chat-icon': true
        }
      }
    })
    expect(wrapper.vm.hasError).toBe(false)
  })
})
