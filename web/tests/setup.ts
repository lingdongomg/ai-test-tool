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
  't-space': true,
  't-switch': true,
  't-loading': true,
  't-descriptions': true,
  't-descriptions-item': true,
  't-divider': true,
  't-drawer': true,
  't-checkbox': true,
  't-checkbox-group': true,
  // 模拟图标
  'search-icon': true,
  'refresh-icon': true,
  'add-icon': true,
  'error-circle-icon': true,
  'arrow-left-icon': true,
  'chat-icon': true,
  'file-import-icon': true,
  'play-icon': true,
  'check-circle-filled-icon': true,
  'close-circle-filled-icon': true,
}

// 模拟全局方法
config.global.mocks = {
  $t: (msg: string) => msg,
}
