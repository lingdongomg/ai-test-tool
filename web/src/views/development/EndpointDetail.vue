<template>
  <div class="endpoint-detail" v-loading="loading">
    <!-- 基本信息 -->
    <t-card class="info-card">
      <div class="endpoint-header">
        <div class="endpoint-title">
          <t-tag :theme="getMethodTheme(endpoint.method)" size="large">
            {{ endpoint.method }}
          </t-tag>
          <span class="endpoint-path">{{ endpoint.path }}</span>
        </div>
        <div class="endpoint-actions">
          <t-button theme="primary" @click="handleGenerateTests">
            <template #icon><AddIcon /></template>
            生成测试用例
          </t-button>
          <t-button @click="handleExecuteTests" :disabled="!testCases.length">
            <template #icon><PlayIcon /></template>
            执行测试
          </t-button>
        </div>
      </div>
      <t-descriptions :column="3" style="margin-top: 16px;">
        <t-descriptions-item label="接口ID">{{ endpoint.endpoint_id }}</t-descriptions-item>
        <t-descriptions-item label="描述">{{ endpoint.description || '-' }}</t-descriptions-item>
        <t-descriptions-item label="标签">
          <t-space v-if="tags.length">
            <t-tag v-for="tag in tags" :key="tag.id" variant="light">{{ tag.name }}</t-tag>
          </t-space>
          <span v-else>-</span>
        </t-descriptions-item>
        <t-descriptions-item label="测试用例数">{{ statistics.total_cases || 0 }}</t-descriptions-item>
        <t-descriptions-item label="近期通过率">{{ statistics.recent_pass_rate || 0 }}%</t-descriptions-item>
        <t-descriptions-item label="创建时间">{{ endpoint.created_at }}</t-descriptions-item>
      </t-descriptions>
    </t-card>

    <!-- 测试用例列表 -->
    <t-card title="测试用例" style="margin-top: 16px;">
      <template #actions>
        <t-button theme="primary" variant="text" size="small" @click="handleGenerateTests">
          <template #icon><AddIcon /></template>
          生成用例
        </t-button>
      </template>
      <t-table
        :data="testCases"
        :columns="caseColumns"
        :loading="casesLoading"
        row-key="test_case_id"
        hover
      >
        <template #category="{ row }">
          <t-tag :theme="getCategoryTheme(row.category)" variant="light" size="small">
            {{ getCategoryLabel(row.category) }}
          </t-tag>
        </template>
        <template #priority="{ row }">
          <t-tag :theme="getPriorityTheme(row.priority)" variant="outline" size="small">
            {{ row.priority }}
          </t-tag>
        </template>
        <template #is_enabled="{ row }">
          <t-switch 
            :value="row.is_enabled" 
            size="small"
            @change="(val: boolean) => handleToggleCase(row, val)"
          />
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleViewCase(row)">详情</t-link>
            <t-link theme="primary" @click="handleExecuteCase(row)">执行</t-link>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 最近执行记录 -->
    <t-card title="最近执行记录" style="margin-top: 16px;">
      <t-table
        :data="recentExecutions"
        :columns="executionColumns"
        row-key="id"
        hover
        size="small"
      >
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)" size="small">
            {{ getStatusLabel(row.status) }}
          </t-tag>
        </template>
        <template #response_time_ms="{ row }">
          {{ row.response_time_ms ? `${row.response_time_ms}ms` : '-' }}
        </template>
      </t-table>
      <t-empty v-if="!recentExecutions.length" description="暂无执行记录" />
    </t-card>

    <!-- 执行测试对话框 -->
    <t-dialog
      v-model:visible="executeDialogVisible"
      header="执行测试"
      :confirm-btn="{ content: '执行', loading: executing }"
      @confirm="confirmExecute"
    >
      <t-form :data="executeForm" label-width="100px">
        <t-form-item label="目标环境">
          <t-select v-model="executeForm.environment" style="width: 100%;">
            <t-option value="local">本地环境</t-option>
            <t-option value="test">测试环境</t-option>
            <t-option value="staging">预发环境</t-option>
            <t-option value="production">生产环境</t-option>
          </t-select>
        </t-form-item>
        <t-form-item label="服务器地址">
          <t-input v-model="executeForm.base_url" placeholder="http://localhost:8080" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon, PlayIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'

const route = useRoute()
const router = useRouter()
const endpointId = route.params.id as string

// 数据
const loading = ref(false)
const endpoint = ref<any>({})
const testCases = ref<any[]>([])
const tags = ref<any[]>([])
const recentExecutions = ref<any[]>([])
const statistics = ref<any>({})
const casesLoading = ref(false)

// 执行测试
const executeDialogVisible = ref(false)
const executing = ref(false)
const executeForm = reactive({
  environment: 'local',
  base_url: 'http://localhost:8080'
})

// 表格列
const caseColumns = [
  { colKey: 'name', title: '用例名称', ellipsis: true },
  { colKey: 'category', title: '类别', width: 100 },
  { colKey: 'priority', title: '优先级', width: 80 },
  { colKey: 'is_enabled', title: '启用', width: 80 },
  { colKey: 'op', title: '操作', width: 120 }
]

const executionColumns = [
  { colKey: 'executed_at', title: '执行时间', width: 180 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'response_time_ms', title: '响应时间', width: 100 },
  { colKey: 'status_code', title: '状态码', width: 80 }
]

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const res = await developmentApi.getEndpoint(endpointId)
    endpoint.value = res.endpoint || {}
    testCases.value = res.test_cases || []
    tags.value = res.tags || []
    recentExecutions.value = res.recent_executions || []
    statistics.value = res.statistics || {}
  } catch (error) {
    console.error('加载接口详情失败:', error)
    MessagePlugin.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// 生成测试用例
const handleGenerateTests = async () => {
  try {
    const res = await developmentApi.generateTestsForEndpoint(endpointId)
    MessagePlugin.success(res.message || `生成了 ${res.total_cases} 个测试用例`)
    loadData()
  } catch (error) {
    console.error('生成测试用例失败:', error)
  }
}

// 执行测试
const handleExecuteTests = () => {
  executeDialogVisible.value = true
}

const handleExecuteCase = (row: any) => {
  executeDialogVisible.value = true
}

const confirmExecute = async () => {
  executing.value = true
  try {
    const res = await developmentApi.executeTests({
      endpoint_id: endpointId,
      base_url: executeForm.base_url,
      environment: executeForm.environment
    })
    MessagePlugin.success(`执行完成，通过率: ${res.pass_rate}%`)
    executeDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('执行测试失败:', error)
  } finally {
    executing.value = false
  }
}

// 切换用例启用状态
const handleToggleCase = async (row: any, enabled: boolean) => {
  // TODO: 调用 API 切换状态
  row.is_enabled = enabled
}

// 查看用例详情
const handleViewCase = (row: any) => {
  // TODO: 打开用例详情抽屉
}

// 辅助函数
const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    'GET': 'success', 'POST': 'primary', 'PUT': 'warning', 
    'DELETE': 'danger', 'PATCH': 'default'
  }
  return map[method] || 'default'
}

const getCategoryTheme = (category: string) => {
  const map: Record<string, string> = {
    'normal': 'success', 'boundary': 'warning', 
    'exception': 'danger', 'security': 'primary'
  }
  return map[category] || 'default'
}

const getCategoryLabel = (category: string) => {
  const map: Record<string, string> = {
    'normal': '正常', 'boundary': '边界', 
    'exception': '异常', 'security': '安全'
  }
  return map[category] || category
}

const getPriorityTheme = (priority: string) => {
  const map: Record<string, string> = {
    'P0': 'danger', 'P1': 'warning', 'P2': 'primary', 'P3': 'default'
  }
  return map[priority] || 'default'
}

const getStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    'passed': 'success', 'failed': 'danger', 'skipped': 'default'
  }
  return map[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    'passed': '通过', 'failed': '失败', 'skipped': '跳过'
  }
  return map[status] || status
}
</script>

<style scoped>
.endpoint-detail {
  max-width: 1200px;
}

.endpoint-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.endpoint-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.endpoint-path {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 18px;
  font-weight: 500;
}

.endpoint-actions {
  display: flex;
  gap: 8px;
}
</style>
