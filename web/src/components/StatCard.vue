<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 统计卡片组件 -->
<template>
  <t-card class="stat-card" hover-shadow>
    <div class="stat-content">
      <div v-if="icon || $slots.icon" class="stat-icon" :style="iconStyle">
        <slot name="icon">
          <component :is="icon" />
        </slot>
      </div>
      <div class="stat-info">
        <div class="stat-value" :style="valueStyle">
          <slot>{{ displayValue }}</slot>
        </div>
        <div class="stat-label">{{ label }}</div>
      </div>
    </div>
    <div v-if="$slots.extra" class="stat-extra">
      <slot name="extra" />
    </div>
    <t-progress 
      v-if="showProgress && typeof value === 'number'" 
      :percentage="Math.min(value, 100)" 
      :color="progressColor"
      :stroke-width="4"
      style="margin-top: 12px;"
    />
  </t-card>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { formatNumber, formatPercent } from '../utils'

interface Props {
  value?: number | string
  label: string
  icon?: Component
  gradient?: string
  format?: 'number' | 'percent' | 'none'
  showProgress?: boolean
  progressColor?: string | { from: string; to: string }
}

const props = withDefaults(defineProps<Props>(), {
  format: 'number',
  showProgress: false,
  gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
})

const iconStyle = computed(() => ({
  background: props.gradient
}))

const valueStyle = computed(() => {
  // 可以根据值动态设置颜色
  return {}
})

const displayValue = computed(() => {
  if (props.value === undefined || props.value === null) return '-'
  if (typeof props.value === 'string') return props.value
  
  switch (props.format) {
    case 'percent':
      return formatPercent(props.value)
    case 'number':
      return formatNumber(props.value)
    default:
      return String(props.value)
  }
})
</script>

<style scoped>
.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 4px;
}

.stat-extra {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
