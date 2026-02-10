<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 统计卡片组件 -->
<template>
  <div class="stat-card" :style="cardStyle">
    <div class="stat-card-accent" :style="accentStyle"></div>
    <div class="stat-card-body">
      <div class="stat-content">
        <div class="stat-info">
          <div class="stat-label">{{ label }}</div>
          <div class="stat-value">
            <slot>{{ displayValue }}</slot>
          </div>
        </div>
        <div v-if="icon || $slots.icon" class="stat-icon" :style="iconStyle">
          <slot name="icon">
            <component :is="icon" />
          </slot>
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
        style="margin-top: 14px;"
      />
    </div>
  </div>
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

const cardStyle = computed(() => ({}))

const accentStyle = computed(() => ({
  background: props.gradient
}))

const iconStyle = computed(() => ({
  background: props.gradient
}))

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
  background: #fff;
  border-radius: 14px;
  border: 1px solid var(--border-color);
  box-shadow: var(--card-shadow);
  overflow: hidden;
  transition: all var(--transition-normal);
  position: relative;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--card-shadow-hover);
}

.stat-card-accent {
  height: 4px;
  width: 100%;
}

.stat-card-body {
  padding: 20px 22px 18px;
}

.stat-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 22px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-tertiary);
  margin-bottom: 8px;
  letter-spacing: 0.02em;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.stat-extra {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
