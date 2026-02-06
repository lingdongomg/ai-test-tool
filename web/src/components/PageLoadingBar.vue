<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 页面加载指示器 - 顶部进度条 -->
<template>
  <Teleport to="body">
    <div v-show="isLoading" class="page-loading-bar" :class="{ 'loading-error': hasError }">
      <div class="loading-progress" :style="progressStyle"></div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

interface Props {
  loading?: boolean
  error?: boolean
  color?: string
  errorColor?: string
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: false,
  color: '#0052d9',
  errorColor: '#e34d59',
  height: 3
})

const isLoading = ref(false)
const hasError = ref(false)
const progress = ref(0)
let timer: ReturnType<typeof setInterval> | null = null
let finishTimer: ReturnType<typeof setTimeout> | null = null

const progressStyle = computed(() => ({
  width: `${progress.value}%`,
  height: `${props.height}px`,
  backgroundColor: hasError.value ? props.errorColor : props.color
}))

// 开始加载
const start = () => {
  isLoading.value = true
  hasError.value = false
  progress.value = 0

  // 清除之前的定时器
  if (timer) clearInterval(timer)
  if (finishTimer) clearTimeout(finishTimer)

  // 模拟进度
  timer = setInterval(() => {
    if (progress.value < 90) {
      // 前30%快，后面慢
      const increment = progress.value < 30 ? 10 : progress.value < 60 ? 5 : 2
      progress.value += Math.random() * increment
    }
  }, 200)
}

// 完成加载
const finish = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }

  // 快速完成到100%
  progress.value = 100

  // 延迟隐藏
  finishTimer = setTimeout(() => {
    isLoading.value = false
    progress.value = 0
  }, 300)
}

// 错误状态
const fail = () => {
  hasError.value = true
  finish()
}

// 监听props变化
watch(
  () => props.loading,
  (newVal) => {
    if (newVal) {
      start()
    } else {
      finish()
    }
  }
)

watch(
  () => props.error,
  (newVal) => {
    if (newVal) {
      fail()
    }
  }
)

onMounted(() => {
  if (props.loading) {
    start()
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (finishTimer) clearTimeout(finishTimer)
})

// 暴露方法供外部调用
defineExpose({
  start,
  finish,
  fail
})
</script>

<style scoped>
.page-loading-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  pointer-events: none;
}

.loading-progress {
  transition: width 0.2s ease-out;
  box-shadow: 0 0 10px currentColor;
}

.loading-error .loading-progress {
  animation: loading-error-shake 0.5s ease-in-out;
}

@keyframes loading-error-shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-5px);
  }
  75% {
    transform: translateX(5px);
  }
}
</style>
