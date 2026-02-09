<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 骨架屏组件 - 用于加载状态展示 -->
<template>
  <div class="skeleton-wrapper" :class="{ 'skeleton-animated': animated }">
    <!-- 统计卡片骨架 -->
    <template v-if="type === 'stat-card'">
      <t-card class="skeleton-stat-card">
        <div class="skeleton-stat-content">
          <div class="skeleton-icon skeleton-item"></div>
          <div class="skeleton-info">
            <div class="skeleton-value skeleton-item"></div>
            <div class="skeleton-label skeleton-item"></div>
          </div>
        </div>
      </t-card>
    </template>

    <!-- 表格骨架 -->
    <template v-else-if="type === 'table'">
      <div class="skeleton-table">
        <div class="skeleton-table-header skeleton-item"></div>
        <div v-for="i in rows" :key="i" class="skeleton-table-row">
          <div
            v-for="j in columns"
            :key="j"
            class="skeleton-table-cell skeleton-item"
            :style="{ width: getCellWidth(j) }"
          ></div>
        </div>
      </div>
    </template>

    <!-- 列表骨架 -->
    <template v-else-if="type === 'list'">
      <div class="skeleton-list">
        <div v-for="i in rows" :key="i" class="skeleton-list-item">
          <div v-if="showAvatar" class="skeleton-avatar skeleton-item"></div>
          <div class="skeleton-list-content">
            <div class="skeleton-title skeleton-item"></div>
            <div class="skeleton-description skeleton-item"></div>
          </div>
        </div>
      </div>
    </template>

    <!-- 表单骨架 -->
    <template v-else-if="type === 'form'">
      <div class="skeleton-form">
        <div v-for="i in rows" :key="i" class="skeleton-form-item">
          <div class="skeleton-form-label skeleton-item"></div>
          <div class="skeleton-form-input skeleton-item"></div>
        </div>
      </div>
    </template>

    <!-- 文本段落骨架 -->
    <template v-else-if="type === 'paragraph'">
      <div class="skeleton-paragraph">
        <div
          v-for="i in rows"
          :key="i"
          class="skeleton-line skeleton-item"
          :style="{ width: getLineWidth(i) }"
        ></div>
      </div>
    </template>

    <!-- 单行骨架 -->
    <template v-else>
      <div class="skeleton-item skeleton-default" :style="customStyle"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  type?: 'stat-card' | 'table' | 'list' | 'form' | 'paragraph' | 'default'
  rows?: number
  columns?: number
  animated?: boolean
  showAvatar?: boolean
  width?: string
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'default',
  rows: 3,
  columns: 4,
  animated: true,
  showAvatar: false,
  width: '100%',
  height: '20px'
})

const customStyle = computed(() => ({
  width: props.width,
  height: props.height
}))

const getCellWidth = (index: number) => {
  const widths = ['15%', '25%', '20%', '15%', '15%', '10%']
  return widths[(index - 1) % widths.length]
}

const getLineWidth = (index: number) => {
  if (index === props.rows) return '60%'
  return '100%'
}
</script>

<style scoped>
.skeleton-wrapper {
  width: 100%;
}

.skeleton-item {
  background: linear-gradient(90deg, #f2f2f2 25%, #e6e6e6 50%, #f2f2f2 75%);
  background-size: 200% 100%;
  border-radius: 4px;
}

.skeleton-animated .skeleton-item {
  animation: skeleton-loading 1.5s infinite;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* 统计卡片骨架 */
.skeleton-stat-card {
  height: 120px;
}

.skeleton-stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.skeleton-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
}

.skeleton-value {
  width: 60%;
  height: 32px;
  margin-bottom: 8px;
}

.skeleton-label {
  width: 40%;
  height: 16px;
}

/* 表格骨架 */
.skeleton-table {
  width: 100%;
}

.skeleton-table-header {
  height: 48px;
  margin-bottom: 8px;
}

.skeleton-table-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.skeleton-table-cell {
  height: 40px;
}

/* 列表骨架 */
.skeleton-list {
  width: 100%;
}

.skeleton-list-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.skeleton-list-item:last-child {
  border-bottom: none;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
}

.skeleton-title {
  width: 50%;
  height: 20px;
  margin-bottom: 8px;
}

.skeleton-description {
  width: 80%;
  height: 16px;
}

/* 表单骨架 */
.skeleton-form {
  width: 100%;
}

.skeleton-form-item {
  margin-bottom: 20px;
}

.skeleton-form-label {
  width: 80px;
  height: 16px;
  margin-bottom: 8px;
}

.skeleton-form-input {
  width: 100%;
  height: 32px;
}

/* 段落骨架 */
.skeleton-paragraph {
  width: 100%;
}

.skeleton-line {
  height: 16px;
  margin-bottom: 12px;
}

.skeleton-line:last-child {
  margin-bottom: 0;
}

/* 默认骨架 */
.skeleton-default {
  display: block;
}
</style>
