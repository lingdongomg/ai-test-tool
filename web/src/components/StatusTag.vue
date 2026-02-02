<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 状态标签组件集合 -->
<template>
  <t-tag 
    :theme="theme" 
    :variant="variant" 
    :size="size"
  >
    <slot>{{ displayLabel }}</slot>
  </t-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { 
  getMethodTheme, 
  getCategoryTheme, 
  getCategoryLabel,
  getPriorityTheme,
  getSeverityTheme,
  getSeverityLabel,
  getStatusTheme
} from '../utils'

type TagType = 'method' | 'category' | 'priority' | 'severity' | 'status' | 'custom'

interface Props {
  type?: TagType
  value: string
  variant?: 'light' | 'outline' | 'dark'
  size?: 'small' | 'medium' | 'large'
  customTheme?: string
  customLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'custom',
  variant: 'light',
  size: 'medium'
})

const theme = computed(() => {
  if (props.customTheme) return props.customTheme
  
  switch (props.type) {
    case 'method':
      return getMethodTheme(props.value)
    case 'category':
      return getCategoryTheme(props.value)
    case 'priority':
      return getPriorityTheme(props.value)
    case 'severity':
      return getSeverityTheme(props.value)
    case 'status':
      return getStatusTheme(props.value)
    default:
      return 'default'
  }
})

const displayLabel = computed(() => {
  if (props.customLabel) return props.customLabel
  
  switch (props.type) {
    case 'category':
      return getCategoryLabel(props.value)
    case 'severity':
      return getSeverityLabel(props.value)
    default:
      return props.value
  }
})
</script>
