<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <t-dialog
    v-model:visible="dialogVisible"
    :header="isCopy ? '复制测试用例' : '编辑测试用例'"
    width="700px"
    :confirm-btn="{ content: '保存', loading: confirmLoading }"
    @confirm="handleConfirm"
  >
    <t-form :data="editForm" label-width="100px" label-align="top">
      <t-row :gutter="16">
        <t-col :span="12">
          <t-form-item label="用例名称" required>
            <t-input v-model="editForm.name" placeholder="请输入用例名称" />
          </t-form-item>
        </t-col>
        <t-col :span="6">
          <t-form-item label="类别">
            <t-select v-model="editForm.category" style="width: 100%;">
              <t-option value="normal">正常场景</t-option>
              <t-option value="boundary">边界测试</t-option>
              <t-option value="exception">异常测试</t-option>
              <t-option value="security">安全测试</t-option>
            </t-select>
          </t-form-item>
        </t-col>
        <t-col :span="6">
          <t-form-item label="优先级">
            <t-select v-model="editForm.priority" style="width: 100%;">
              <t-option value="high">高</t-option>
              <t-option value="medium">中</t-option>
              <t-option value="low">低</t-option>
            </t-select>
          </t-form-item>
        </t-col>
      </t-row>
      <t-form-item label="描述">
        <t-textarea v-model="editForm.description" placeholder="请输入用例描述" :rows="2" />
      </t-form-item>
      <t-row :gutter="16">
        <t-col :span="6">
          <t-form-item label="请求方法">
            <t-select v-model="editForm.method" style="width: 100%;">
              <t-option v-for="m in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']" :key="m" :value="m">{{ m }}</t-option>
            </t-select>
          </t-form-item>
        </t-col>
        <t-col :span="18">
          <t-form-item label="请求URL">
            <t-input v-model="editForm.url" placeholder="/api/v1/xxx" />
          </t-form-item>
        </t-col>
      </t-row>
      <t-row :gutter="16">
        <t-col :span="12">
          <t-form-item label="期望状态码">
            <t-input-number v-model="editForm.expected_status_code" :min="100" :max="599" style="width: 100%;" />
          </t-form-item>
        </t-col>
        <t-col :span="12">
          <t-form-item label="最大响应时间(ms)">
            <t-input-number v-model="editForm.max_response_time_ms" :min="100" :max="60000" style="width: 100%;" />
          </t-form-item>
        </t-col>
      </t-row>
      <t-form-item label="请求头 (JSON)">
        <t-textarea v-model="editForm.headersStr" placeholder='{"Content-Type": "application/json"}' :rows="3" style="font-family: monospace;" />
      </t-form-item>
      <t-form-item label="查询参数 (JSON)">
        <t-textarea v-model="editForm.queryParamsStr" placeholder='{"page": 1, "size": 10}' :rows="2" style="font-family: monospace;" />
      </t-form-item>
      <t-form-item label="请求体 (JSON)">
        <t-textarea v-model="editForm.bodyStr" placeholder='{"key": "value"}' :rows="5" style="font-family: monospace;" />
      </t-form-item>
    </t-form>
  </t-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { developmentApi } from '../../../api/v2'
import { safeParseJSON, safeStringifyJSON } from '../../../utils'

const props = defineProps<{
  visible: boolean
  data: any
  isCopy: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'saved': []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const confirmLoading = ref(false)

const editForm = reactive({
  name: '',
  description: '',
  category: 'normal',
  priority: 'medium',
  method: 'GET',
  url: '',
  expected_status_code: 200,
  max_response_time_ms: 3000,
  headersStr: '{}',
  bodyStr: '{}',
  queryParamsStr: '{}'
})

watch(() => props.data, (row) => {
  if (!row) return
  const isCopy = props.isCopy
  editForm.name = isCopy ? `${row.name} (副本)` : row.name || ''
  editForm.description = row.description || ''
  editForm.category = row.category || 'normal'
  editForm.priority = row.priority || 'medium'
  editForm.method = row.method || 'GET'
  editForm.url = row.url || ''
  editForm.expected_status_code = row.expected_status_code || 200
  editForm.max_response_time_ms = row.max_response_time_ms || 3000
  editForm.headersStr = safeStringifyJSON(row.headers)
  editForm.bodyStr = safeStringifyJSON(row.body)
  editForm.queryParamsStr = safeStringifyJSON(row.query_params)
}, { immediate: true })

const handleConfirm = async () => {
  if (!editForm.name.trim()) {
    MessagePlugin.warning('请输入用例名称')
    return
  }
  confirmLoading.value = true
  try {
    const data = {
      name: editForm.name,
      description: editForm.description,
      category: editForm.category,
      priority: editForm.priority,
      method: editForm.method,
      url: editForm.url,
      expected_status_code: editForm.expected_status_code,
      max_response_time_ms: editForm.max_response_time_ms,
      headers: safeParseJSON(editForm.headersStr, {}),
      body: safeParseJSON(editForm.bodyStr, null),
      query_params: safeParseJSON(editForm.queryParamsStr, {})
    }

    if (props.isCopy) {
      await developmentApi.copyTest(props.data.case_id, data)
      MessagePlugin.success('复制成功')
    } else {
      await developmentApi.updateTest(props.data.case_id, data)
      MessagePlugin.success('保存成功')
    }
    dialogVisible.value = false
    emit('saved')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    confirmLoading.value = false
  }
}
</script>
