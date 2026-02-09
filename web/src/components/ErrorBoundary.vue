<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 错误边界组件 - 捕获和展示错误 -->
<template>
  <div class="error-boundary">
    <slot v-if="!hasError" />

    <!-- 错误展示 -->
    <div v-else class="error-container">
      <div class="error-content">
        <div class="error-icon">
          <error-circle-icon size="64px" />
        </div>
        <h3 class="error-title">{{ errorTitle }}</h3>
        <p class="error-message">{{ errorMessage }}</p>

        <!-- 错误详情（开发环境） -->
        <t-collapse v-if="showDetails && errorDetails" class="error-details">
          <t-collapse-panel header="错误详情">
            <pre class="error-stack">{{ errorDetails }}</pre>
          </t-collapse-panel>
        </t-collapse>

        <!-- 操作按钮 -->
        <div class="error-actions">
          <t-button theme="primary" @click="handleRetry">
            <template #icon><refresh-icon /></template>
            重试
          </t-button>
          <t-button @click="handleGoBack">
            <template #icon><arrow-left-icon /></template>
            返回
          </t-button>
          <t-button v-if="showReport" variant="text" @click="handleReport">
            <template #icon><chat-icon /></template>
            报告问题
          </t-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onErrorCaptured, watch } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { ErrorCircleIcon, RefreshIcon, ArrowLeftIcon, ChatIcon } from 'tdesign-icons-vue-next'

interface Props {
  fallbackTitle?: string
  fallbackMessage?: string
  showDetails?: boolean
  showReport?: boolean
  onError?: (error: Error) => void
}

const props = withDefaults(defineProps<Props>(), {
  fallbackTitle: '出错了',
  fallbackMessage: '页面加载遇到问题，请重试或返回上一页',
  showDetails: import.meta.env.DEV,
  showReport: true
})

const emit = defineEmits<{
  (e: 'error', error: Error): void
  (e: 'retry'): void
}>()

const router = useRouter()
const hasError = ref(false)
const caughtError = ref<Error | null>(null)

// 计算属性
const errorTitle = computed(() => {
  if (!caughtError.value) return props.fallbackTitle

  // 根据错误类型返回不同标题
  const error = caughtError.value
  if (error.name === 'NetworkError' || error.message.includes('network')) {
    return '网络连接失败'
  }
  if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
    return '请求超时'
  }
  if (error.message.includes('404')) {
    return '资源不存在'
  }
  if (error.message.includes('403')) {
    return '没有访问权限'
  }
  if (error.message.includes('500')) {
    return '服务器错误'
  }

  return props.fallbackTitle
})

const errorMessage = computed(() => {
  if (!caughtError.value) return props.fallbackMessage

  const error = caughtError.value
  if (error.name === 'NetworkError' || error.message.includes('network')) {
    return '请检查您的网络连接后重试'
  }
  if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
    return '服务器响应时间过长，请稍后重试'
  }
  if (error.message.includes('404')) {
    return '请求的资源不存在，请检查地址是否正确'
  }
  if (error.message.includes('403')) {
    return '您没有权限访问此资源'
  }
  if (error.message.includes('500')) {
    return '服务器内部错误，请稍后重试或联系管理员'
  }

  return props.fallbackMessage
})

const errorDetails = computed(() => {
  if (!caughtError.value) return ''
  return caughtError.value.stack || caughtError.value.message
})

// 捕获错误
onErrorCaptured((error: Error) => {
  hasError.value = true
  caughtError.value = error

  // 调用回调
  props.onError?.(error)
  emit('error', error)

  // 记录错误日志
  console.error('[ErrorBoundary] Caught error:', error)

  // 阻止错误继续传播
  return false
})

// 操作处理
const handleRetry = () => {
  hasError.value = false
  caughtError.value = null
  emit('retry')
}

const handleGoBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

const handleReport = () => {
  // 可以实现错误报告功能
  MessagePlugin.info('感谢您的反馈，我们会尽快处理')

  // 可以发送错误报告到服务器
  if (caughtError.value) {
    console.log('[ErrorBoundary] Reporting error:', {
      message: caughtError.value.message,
      stack: caughtError.value.stack,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    })
  }
}

// 重置方法（供父组件调用）
const reset = () => {
  hasError.value = false
  caughtError.value = null
}

defineExpose({
  reset,
  hasError
})
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 40px 20px;
}

.error-content {
  text-align: center;
  max-width: 500px;
}

.error-icon {
  color: #e34d59;
  margin-bottom: 24px;
}

.error-title {
  font-size: 24px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
  margin: 0 0 12px;
}

.error-message {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.6);
  margin: 0 0 24px;
  line-height: 1.6;
}

.error-details {
  margin-bottom: 24px;
  text-align: left;
}

.error-stack {
  font-size: 12px;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: #666;
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
