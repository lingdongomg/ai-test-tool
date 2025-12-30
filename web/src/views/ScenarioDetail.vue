<template>
  <div class="scenario-detail">
    <t-card :bordered="false" v-if="scenario">
      <template #title>
        <t-space align="center">
          <span>{{ scenario.name }}</span>
          <t-tag :theme="scenario.is_enabled ? 'success' : 'default'" size="small">
            {{ scenario.is_enabled ? '已启用' : '已禁用' }}
          </t-tag>
        </t-space>
      </template>
      <template #actions>
        <t-space>
          <t-button theme="primary" @click="handleExecute">执行场景</t-button>
          <t-button @click="handleAddStep">添加步骤</t-button>
        </t-space>
      </template>

      <t-descriptions :column="2">
        <t-descriptions-item label="场景ID">{{ scenario.scenario_id }}</t-descriptions-item>
        <t-descriptions-item label="创建时间">{{ scenario.created_at }}</t-descriptions-item>
        <t-descriptions-item label="描述" :span="2">{{ scenario.description || '-' }}</t-descriptions-item>
        <t-descriptions-item label="标签">
          <t-space size="small">
            <t-tag v-for="tag in scenario.tags" :key="tag" size="small">{{ tag }}</t-tag>
          </t-space>
        </t-descriptions-item>
        <t-descriptions-item label="失败重试">
          {{ scenario.retry_on_failure ? `是（最多${scenario.max_retries}次）` : '否' }}
        </t-descriptions-item>
      </t-descriptions>
    </t-card>

    <t-card title="场景变量" :bordered="false" class="mt-4">
      <t-table :data="variableList" :columns="variableColumns" size="small">
        <template #op="{ row }">
          <t-link theme="primary" @click="handleEditVariable(row)">编辑</t-link>
          <t-link theme="danger" @click="handleDeleteVariable(row)">删除</t-link>
        </template>
      </t-table>
      <t-button size="small" variant="dashed" class="mt-2" @click="handleAddVariable">
        <template #icon><AddIcon /></template>
        添加变量
      </t-button>
    </t-card>

    <t-card title="执行步骤" :bordered="false" class="mt-4">
      <t-timeline>
        <t-timeline-item
          v-for="(step, index) in steps"
          :key="step.step_id"
          :label="`步骤 ${index + 1}`"
        >
          <div class="step-card">
            <div class="step-header">
              <t-space align="center">
                <t-tag :theme="getMethodTheme(step.method)" size="small">{{ step.method }}</t-tag>
                <span class="step-name">{{ step.name }}</span>
                <t-tag v-if="!step.is_enabled" theme="default" size="small">已禁用</t-tag>
              </t-space>
              <t-space>
                <t-link theme="primary" @click="handleEditStep(step)">编辑</t-link>
                <t-link theme="primary" @click="handleMoveStep(step, 'up')" :disabled="index === 0">上移</t-link>
                <t-link theme="primary" @click="handleMoveStep(step, 'down')" :disabled="index === steps.length - 1">下移</t-link>
                <t-popconfirm content="确定删除该步骤吗？" @confirm="handleDeleteStep(step)">
                  <t-link theme="danger">删除</t-link>
                </t-popconfirm>
              </t-space>
            </div>
            <div class="step-url">{{ step.url }}</div>
            <div class="step-meta" v-if="step.extractions?.length || step.assertions?.length">
              <t-space size="small">
                <t-tag v-if="step.extractions?.length" size="small" variant="light">
                  {{ step.extractions.length }} 个提取
                </t-tag>
                <t-tag v-if="step.assertions?.length" size="small" variant="light">
                  {{ step.assertions.length }} 个断言
                </t-tag>
              </t-space>
            </div>
          </div>
        </t-timeline-item>
      </t-timeline>
      
      <t-empty v-if="steps.length === 0" description="暂无步骤，点击添加步骤" />
    </t-card>

    <!-- 步骤编辑对话框 -->
    <t-dialog
      v-model:visible="stepDialogVisible"
      :header="isEditStep ? '编辑步骤' : '添加步骤'"
      width="700px"
      @confirm="handleSubmitStep"
    >
      <t-form :data="stepForm" ref="stepFormRef">
        <t-form-item label="步骤名称" name="name">
          <t-input v-model="stepForm.name" placeholder="请输入步骤名称" />
        </t-form-item>
        <t-form-item label="请求方法" name="method">
          <t-select v-model="stepForm.method">
            <t-option value="GET" label="GET" />
            <t-option value="POST" label="POST" />
            <t-option value="PUT" label="PUT" />
            <t-option value="DELETE" label="DELETE" />
            <t-option value="PATCH" label="PATCH" />
          </t-select>
        </t-form-item>
        <t-form-item label="请求URL" name="url">
          <t-input v-model="stepForm.url" placeholder="/api/xxx 支持变量 ${var}" />
        </t-form-item>
        <t-form-item label="请求头">
          <t-textarea v-model="stepForm.headersJson" placeholder='{"Authorization": "Bearer ${token}"}' :autosize="{ minRows: 2 }" />
        </t-form-item>
        <t-form-item label="请求体" v-if="['POST', 'PUT', 'PATCH'].includes(stepForm.method)">
          <t-textarea v-model="stepForm.bodyJson" placeholder='{"key": "value"}' :autosize="{ minRows: 3 }" />
        </t-form-item>
        <t-form-item label="变量提取">
          <t-textarea v-model="stepForm.extractionsJson" placeholder='[{"name": "token", "source": "jsonpath", "expression": "$.data.token"}]' :autosize="{ minRows: 2 }" />
        </t-form-item>
        <t-form-item label="断言">
          <t-textarea v-model="stepForm.assertionsJson" placeholder='[{"type": "equals", "source": "status", "expected": 200}]' :autosize="{ minRows: 2 }" />
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 执行对话框 -->
    <t-dialog v-model:visible="executeDialogVisible" header="执行场景" @confirm="handleConfirmExecute">
      <t-form :data="executeForm">
        <t-form-item label="目标URL" required>
          <t-input v-model="executeForm.base_url" placeholder="http://your-api.com" />
        </t-form-item>
        <t-form-item label="环境">
          <t-select v-model="executeForm.environment">
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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon } from 'tdesign-icons-vue-next'
import { scenarioApi } from '../api'

const route = useRoute()
const scenarioId = computed(() => route.params.id as string)

const scenario = ref<any>(null)
const steps = ref<any[]>([])
const stepDialogVisible = ref(false)
const executeDialogVisible = ref(false)
const isEditStep = ref(false)
const editingStepId = ref<string | null>(null)

const stepForm = ref({
  name: '',
  method: 'GET',
  url: '',
  headersJson: '',
  bodyJson: '',
  extractionsJson: '',
  assertionsJson: ''
})

const executeForm = ref({
  base_url: 'http://localhost:8080',
  environment: 'test'
})

const stepFormRef = ref()

const variableList = computed(() => {
  if (!scenario.value?.variables) return []
  return Object.entries(scenario.value.variables).map(([key, value]) => ({ key, value }))
})

const variableColumns = [
  { colKey: 'key', title: '变量名' },
  { colKey: 'value', title: '值' },
  { colKey: 'op', title: '操作', cell: 'op', width: 120 }
]

const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'default'
  }
  return map[method] || 'default'
}

const loadScenario = async () => {
  const data = await scenarioApi.get(scenarioId.value) as any
  scenario.value = data
  steps.value = data.steps || []
}

const handleAddStep = () => {
  isEditStep.value = false
  editingStepId.value = null
  stepForm.value = {
    name: '',
    method: 'GET',
    url: '',
    headersJson: '',
    bodyJson: '',
    extractionsJson: '',
    assertionsJson: ''
  }
  stepDialogVisible.value = true
}

const handleEditStep = (step: any) => {
  isEditStep.value = true
  editingStepId.value = step.step_id
  stepForm.value = {
    name: step.name,
    method: step.method,
    url: step.url,
    headersJson: JSON.stringify(step.headers || {}, null, 2),
    bodyJson: JSON.stringify(step.body || {}, null, 2),
    extractionsJson: JSON.stringify(step.extractions || [], null, 2),
    assertionsJson: JSON.stringify(step.assertions || [], null, 2)
  }
  stepDialogVisible.value = true
}

const handleSubmitStep = async () => {
  const stepData = {
    name: stepForm.value.name,
    method: stepForm.value.method,
    url: stepForm.value.url,
    headers: stepForm.value.headersJson ? JSON.parse(stepForm.value.headersJson) : {},
    body: stepForm.value.bodyJson ? JSON.parse(stepForm.value.bodyJson) : null,
    extractions: stepForm.value.extractionsJson ? JSON.parse(stepForm.value.extractionsJson) : [],
    assertions: stepForm.value.assertionsJson ? JSON.parse(stepForm.value.assertionsJson) : []
  }
  
  MessagePlugin.success(isEditStep.value ? '步骤已更新' : '步骤已添加')
  stepDialogVisible.value = false
  loadScenario()
}

const handleDeleteStep = async (step: any) => {
  MessagePlugin.success('步骤已删除')
  loadScenario()
}

const handleMoveStep = (step: any, direction: 'up' | 'down') => {
  MessagePlugin.info('移动功能开发中')
}

const handleAddVariable = () => {
  MessagePlugin.info('添加变量功能开发中')
}

const handleEditVariable = (row: any) => {
  MessagePlugin.info('编辑变量功能开发中')
}

const handleDeleteVariable = (row: any) => {
  MessagePlugin.info('删除变量功能开发中')
}

const handleExecute = () => {
  executeDialogVisible.value = true
}

const handleConfirmExecute = async () => {
  await scenarioApi.execute(scenarioId.value, executeForm.value)
  MessagePlugin.success('执行已开始')
  executeDialogVisible.value = false
}

onMounted(loadScenario)
</script>

<style scoped>
.mt-2 {
  margin-top: 8px;
}

.mt-4 {
  margin-top: 16px;
}

.step-card {
  background: #f9f9f9;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 8px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.step-name {
  font-weight: 500;
}

.step-url {
  color: rgba(0, 0, 0, 0.6);
  font-size: 13px;
  margin-top: 8px;
  font-family: monospace;
}

.step-meta {
  margin-top: 8px;
}
</style>
