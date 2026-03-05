<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <t-drawer
    v-model:visible="drawerVisible"
    header="测试用例详情"
    size="600px"
  >
    <template #footer>
      <t-space>
        <t-button @click="drawerVisible = false">关闭</t-button>
        <t-button theme="primary" @click="$emit('edit', currentCase)">编辑</t-button>
      </t-space>
    </template>
    <template v-if="currentCase">
      <t-descriptions :column="1" bordered>
        <t-descriptions-item label="用例名称">{{ currentCase.name }}</t-descriptions-item>
        <t-descriptions-item label="描述">{{ currentCase.description || '-' }}</t-descriptions-item>
        <t-descriptions-item label="类别">
          <StatusTag type="category" :value="currentCase.category" />
        </t-descriptions-item>
        <t-descriptions-item label="优先级">
          <StatusTag type="priority" :value="currentCase.priority" variant="outline" />
        </t-descriptions-item>
        <t-descriptions-item label="请求方法">{{ currentCase.method }}</t-descriptions-item>
        <t-descriptions-item label="请求URL">{{ currentCase.url }}</t-descriptions-item>
        <t-descriptions-item label="期望状态码">{{ currentCase.expected_status_code }}</t-descriptions-item>
      </t-descriptions>

      <t-divider>请求头</t-divider>
      <pre class="code-block">{{ safeStringifyJSON(currentCase.headers) }}</pre>

      <t-divider>请求体</t-divider>
      <pre class="code-block">{{ safeStringifyJSON(currentCase.body) }}</pre>
    </template>
  </t-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { StatusTag } from '../../../components'
import { safeStringifyJSON } from '../../../utils'

const props = defineProps<{
  visible: boolean
  data: any
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'edit': [row: any]
}>()

const drawerVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const currentCase = computed(() => props.data)
</script>

<style scoped>
.code-block {
  background: var(--td-bg-color-secondarycontainer);
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
}
</style>
