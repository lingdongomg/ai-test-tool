/**
 * 该文件内容使用AI生成，注意识别准确性
 * Vitest 测试配置
 */

import { config } from '@vue/test-utils'

// 全局配置
config.global.stubs = {
  // 模拟 TDesign 组件
  't-button': true,
  't-input': true,
  't-select': true,
  't-card': true,
  't-table': true,
  't-dialog': true,
  't-form': true,
  't-form-item': true,
  't-tag': true,
  't-pagination': true,
  't-alert': true,
  't-empty': true,
  't-progress': true,
  't-collapse': true,
  't-collapse-panel': true,
  't-row': true,
  't-col': true,
  't-textarea': true,
  't-input-number': true,
  't-slider': true,
  't-link': true,
  't-option': true,
  // 模拟图标
  'search-icon': true,
  'refresh-icon': true,
  'add-icon': true,
  'error-circle-icon': true,
  'arrow-left-icon': true,
  'chat-icon': true,
}

// 模拟全局方法
config.global.mocks = {
  $t: (msg: string) => msg,
}
