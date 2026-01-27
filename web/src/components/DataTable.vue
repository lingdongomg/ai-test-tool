<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 数据表格组件：整合分页、选择、加载状态 -->
<template>
  <t-card class="data-table-card">
    <t-table
      :data="data"
      :columns="columns"
      :loading="loading"
      :pagination="pagination"
      :selected-row-keys="selectedKeys"
      :row-key="rowKey"
      :hover="hover"
      @page-change="$emit('page-change', $event)"
      @select-change="$emit('select-change', $event)"
    >
      <template v-for="(_, name) in $slots" #[name]="slotProps">
        <slot :name="name" v-bind="slotProps" />
      </template>
    </t-table>
  </t-card>
</template>

<script setup lang="ts">
interface Column {
  colKey: string
  title?: string
  width?: number | string
  ellipsis?: boolean
  fixed?: 'left' | 'right'
  type?: 'multiple' | 'single'
}

interface Pagination {
  current: number
  pageSize: number
  total: number
}

interface Props {
  data: any[]
  columns: Column[]
  loading?: boolean
  pagination?: Pagination
  selectedKeys?: string[]
  rowKey?: string
  hover?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false,
  rowKey: 'id',
  hover: true
})

defineEmits<{
  'page-change': [pageInfo: any]
  'select-change': [keys: string[], records?: any]
}>()
</script>

<style scoped>
.data-table-card {
  /* 保持卡片样式 */
}
</style>
