<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 页面工具栏组件 -->
<template>
  <t-card class="page-toolbar">
    <div class="toolbar">
      <div class="toolbar-left">
        <!-- 搜索框 -->
        <t-input
          v-if="showSearch"
          v-model="searchModel"
          :placeholder="searchPlaceholder"
          clearable
          :style="{ width: searchWidth }"
          @enter="$emit('search')"
          @clear="$emit('search')"
        >
          <template #prefix-icon><SearchIcon /></template>
        </t-input>
        
        <!-- 筛选插槽 -->
        <slot name="filters" />
      </div>
      
      <div class="toolbar-right">
        <!-- 操作按钮插槽 -->
        <slot name="actions" />
      </div>
    </div>
  </t-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SearchIcon } from 'tdesign-icons-vue-next'

interface Props {
  search?: string
  searchPlaceholder?: string
  searchWidth?: string
  showSearch?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  searchPlaceholder: '请输入搜索内容',
  searchWidth: '240px',
  showSearch: true
})

const emit = defineEmits<{
  'update:search': [value: string]
  search: []
}>()

const searchModel = computed({
  get: () => props.search ?? '',
  set: (val) => emit('update:search', val)
})
</script>

<style scoped>
.page-toolbar {
  margin-bottom: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
