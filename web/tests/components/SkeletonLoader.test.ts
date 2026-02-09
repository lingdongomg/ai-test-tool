/**
 * 该文件内容使用AI生成，注意识别准确性
 * SkeletonLoader 组件测试
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SkeletonLoader from '../../src/components/SkeletonLoader.vue'

describe('SkeletonLoader', () => {
  it('应该正确渲染默认骨架', () => {
    const wrapper = mount(SkeletonLoader)
    expect(wrapper.find('.skeleton-wrapper').exists()).toBe(true)
    expect(wrapper.find('.skeleton-item').exists()).toBe(true)
  })

  it('应该渲染统计卡片骨架', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { type: 'stat-card' }
    })
    expect(wrapper.find('.skeleton-stat-card').exists()).toBe(true)
    expect(wrapper.find('.skeleton-icon').exists()).toBe(true)
    expect(wrapper.find('.skeleton-value').exists()).toBe(true)
    expect(wrapper.find('.skeleton-label').exists()).toBe(true)
  })

  it('应该渲染表格骨架', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { type: 'table', rows: 5, columns: 4 }
    })
    expect(wrapper.find('.skeleton-table').exists()).toBe(true)
    expect(wrapper.find('.skeleton-table-header').exists()).toBe(true)
    expect(wrapper.findAll('.skeleton-table-row').length).toBe(5)
  })

  it('应该渲染列表骨架', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { type: 'list', rows: 3 }
    })
    expect(wrapper.find('.skeleton-list').exists()).toBe(true)
    expect(wrapper.findAll('.skeleton-list-item').length).toBe(3)
  })

  it('应该在showAvatar为true时显示头像骨架', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { type: 'list', showAvatar: true }
    })
    expect(wrapper.find('.skeleton-avatar').exists()).toBe(true)
  })

  it('应该渲染表单骨架', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { type: 'form', rows: 4 }
    })
    expect(wrapper.find('.skeleton-form').exists()).toBe(true)
    expect(wrapper.findAll('.skeleton-form-item').length).toBe(4)
  })

  it('应该渲染段落骨架', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { type: 'paragraph', rows: 3 }
    })
    expect(wrapper.find('.skeleton-paragraph').exists()).toBe(true)
    expect(wrapper.findAll('.skeleton-line').length).toBe(3)
  })

  it('应该应用动画类', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { animated: true }
    })
    expect(wrapper.find('.skeleton-animated').exists()).toBe(true)
  })

  it('应该在animated为false时不应用动画类', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { animated: false }
    })
    expect(wrapper.find('.skeleton-animated').exists()).toBe(false)
  })

  it('应该支持自定义宽高', () => {
    const wrapper = mount(SkeletonLoader, {
      props: { type: 'default', width: '200px', height: '50px' }
    })
    const skeleton = wrapper.find('.skeleton-default')
    expect(skeleton.attributes('style')).toContain('width: 200px')
    expect(skeleton.attributes('style')).toContain('height: 50px')
  })
})
