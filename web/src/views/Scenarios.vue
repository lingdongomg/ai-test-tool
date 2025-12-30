<template>
  <div class="scenarios-page">
    <t-card :bordered="false">
      <div class="toolbar">
        <t-space>
          <t-button theme="primary" @click="showCreateDialog">
            <template #icon><AddIcon /></template>
            新建场景
          </t-button>
          <t-button @click="loadScenarios">
            <template #icon><RefreshIcon /></template>
            刷新
          </t-button>
        </t-space>
      </div>

      <t-table
        :data="scenarios"
        :columns="columns"
        row-key="scenario_id"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
      >
        <template #is_enabled="{ row }">
          <t-switch v-model="row.is_enabled" @change="handleToggleEnabled(row)" />
        </template>
        <template #tags="{ row }">
          <t-space size="small">
            <t-tag v-for="tag in row.tags" :key="tag" size="small" variant="light">{{ tag }}</t-tag>
          </t-space>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">详情</t-link>
            <t-link theme="primary" @click="handleExecute(row)">执行</t-link>
            <t-link theme="primary" @click="handleEdit(row)">编辑</t-link>
            <t-popconfirm content="确定删除该场景吗？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 创建/编辑场景对话框 -->
    <t-dialog
      v-model:visible="dialogVisible"
      :header="isEdit ? '编辑场景' : '新建场景'"
      width="600px"
      @confirm="handleSubmit"
    >
      <t-form :data="formData" :rules="rules" ref="formRef">
        <t-form-item label="场景名称" name="name">
          <t-input v-model="formData.name" placeholder="请输入场景名称" />
        </t-form-item>
        <t-form-item label="描述" name="description">
          <t-textarea v-model="formData.description" placeholder="请输入描述" />
        </t-form-item>
        <t-form-item label="标签" name="tags">
          <t-select v-model="formData.tags" multiple placeholder="选择标签">
            <t-option v-for="tag in allTags" :key="tag" :value="tag" :label="tag" />
          </t-select>
        </t-form-item>
        <t-form-item label="失败重试">
          <t-switch v-model="formData.retry_on_failure" />
          <t-input-number
            v-if="formData.retry_on_failure"
            v-model="formData.max_retries"
            :min="1"
            :max="10"
            style="margin-left: 16px; width: 100px"
          />
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 执行对话框 -->
    <t-dialog
      v-model:visible="executeDialogVisible"
      header="执行场景"
      @confirm="handleConfirmExecute"
    >
      <t-form :data="executeForm">
        <t-form-item label="目标URL" required>
          <t-input v-model="executeForm.base_url" placeholder="http://your-api.com" />
        </t-form-item>
        <t-form-item label="环境">
          <t-select v-model="executeForm.environment" placeholder="选择环境">
            <t-option value="dev" label="开发环境" />
            <t-option value="test" label="测试环境" />
            <t-option value="prod" label="生产环境" />
          </t-select>
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon, RefreshIcon } from 'tdesign-icons-vue-next'
import { scenarioApi } from '../api'

interface Scenario {
  scenario_id: string
  name: string
  description: string
  tags: string[]
  is_enabled: boolean
  retry_on_failure: boolean
  max_retries: number
  created_at: string
}

const router = useRouter()
const loading = ref(false)
const scenarios = ref<Scenario[]>([])
const dialogVisible = ref(false)
const executeDialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<string | null>(null)
const executingScenario = ref<Scenario | null>(null)

const allTags = ref(['冒烟测试', '回归测试', '性能测试', '安全测试'])

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const formData = ref({
  name: '',
  description: '',
  tags: [] as string[],
  retry_on_failure: false,
  max_retries: 3
})

const executeForm = ref({
  base_url: 'http://localhost:8080',
  environment: 'test'
})

const rules = {
  name: [{ required: true, message: '请输入场景名称' }]
}

const formRef = ref()

const columns = [
  { colKey: 'name', title: '场景名称', width: 200 },
  { colKey: 'description', title: '描述', ellipsis: true },
  { colKey: 'tags', title: '标签', cell: 'tags', width: 200 },
  { colKey: 'is_enabled', title: '启用', cell: 'is_enabled', width: 80 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'op', title: '操作', cell: 'op', width: 200 }
]

const loadScenarios = async () => {
  loading.value = true
  const data = await scenarioApi.list({
    page: pagination.value.current,
    size: pagination.value.pageSize
  }) as any
  
  scenarios.value = data.items || []
  pagination.value.total = data.total || 0
  loading.value = false
}

const handlePageChange = (pageInfo: any) => {
  pagination.value.current = pageInfo.current
  loadScenarios()
}

const showCreateDialog = () => {
  isEdit.value = false
  editingId.value = null
  formData.value = { name: '', description: '', tags: [], retry_on_failure: false, max_retries: 3 }
  dialogVisible.value = true
}

const handleView = (row: Scenario) => {
  router.push({ name: 'ScenarioDetail', params: { id: row.scenario_id } })
}

const handleEdit = (row: Scenario) => {
  isEdit.value = true
  editingId.value = row.scenario_id
  formData.value = {
    name: row.name,
    description: row.description,
    tags: row.tags || [],
    retry_on_failure: row.retry_on_failure,
    max_retries: row.max_retries
  }
  dialogVisible.value = true
}

const handleExecute = (row: Scenario) => {
  executingScenario.value = row
  executeDialogVisible.value = true
}

const handleConfirmExecute = async () => {
  if (!executingScenario.value) return
  
  await scenarioApi.execute(executingScenario.value.scenario_id, executeForm.value)
  MessagePlugin.success('执行已开始')
  executeDialogVisible.value = false
}

const handleToggleEnabled = async (row: Scenario) => {
  await scenarioApi.update(row.scenario_id, { is_enabled: row.is_enabled })
  MessagePlugin.success(row.is_enabled ? '已启用' : '已禁用')
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate()
  if (valid !== true) return

  if (isEdit.value && editingId.value) {
    await scenarioApi.update(editingId.value, formData.value)
    MessagePlugin.success('更新成功')
  } else {
    await scenarioApi.create(formData.value)
    MessagePlugin.success('创建成功')
  }
  
  dialogVisible.value = false
  loadScenarios()
}

const handleDelete = async (row: Scenario) => {
  await scenarioApi.delete(row.scenario_id)
  MessagePlugin.success('删除成功')
  loadScenarios()
}

onMounted(loadScenarios)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>
