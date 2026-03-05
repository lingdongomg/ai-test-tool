<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <t-dialog
    v-model:visible="dialogVisible"
    header="执行测试"
    :confirm-btn="{ content: '执行', loading: confirmLoading }"
    @confirm="handleConfirm"
  >
    <t-form :data="executeForm" label-width="100px">
      <t-form-item label="服务器地址">
        <t-input v-model="executeForm.base_url" placeholder="http://localhost:8080" />
      </t-form-item>
      <t-form-item label="目标环境">
        <t-select v-model="executeForm.environment" style="width: 100%;">
          <t-option value="local">本地环境</t-option>
          <t-option value="test">测试环境</t-option>
          <t-option value="staging">预发环境</t-option>
        </t-select>
      </t-form-item>
    </t-form>
  </t-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { developmentApi } from '../../../api/v2'

const props = defineProps<{
  visible: boolean
  caseIds: string[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const confirmLoading = ref(false)

const executeForm = reactive({
  base_url: 'http://localhost:8080',
  environment: 'local'
})

const handleConfirm = async () => {
  confirmLoading.value = true
  try {
    const res = await developmentApi.executeTests({
      test_case_ids: props.caseIds,
      base_url: executeForm.base_url,
      environment: executeForm.environment
    }) as any
    MessagePlugin.success(`执行完成，通过: ${res.passed}/${res.total}，通过率: ${res.pass_rate}%`)
    dialogVisible.value = false
  } catch (error) {
    console.error('执行失败:', error)
  } finally {
    confirmLoading.value = false
  }
}
</script>
