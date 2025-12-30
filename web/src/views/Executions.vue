<template>
  <div class="executions-page">
    <t-card :bordered="false">
      <div class="toolbar">
        <t-space>
          <t-select v-model="filterStatus" placeholder="执行状态" clearable style="width: 120px">
            <t-option value="passed" label="通过" />
            <t-option value="failed" label="失败" />
            <t-option value="running" label="运行中" />
            <t-option value="pending" label="等待中" />
          </t-select>
          <t-button @click="loadExecutions">
            <template #icon><RefreshIcon /></template>
            刷新
          </t-button>
        </t-space>
      </div>

      <t-table
        :data="executions"
        :columns="columns"
        row-key="execution_id"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
      >
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)">{{ getStatusText(row.status) }}</t-tag>
        </template>
        <template #progress="{ row }">
          <t-progress
            :percentage="getProgress(row)"
            :status="row.status === 'failed' ? 'error' : 'success'"
            size="small"
          />
          <span class="progress-text">{{ row.passed_steps }}/{{ row.total_steps }}</span>
        </template>
        <template #op="{ row }">
          <t-link theme="primary" @click="handleViewDetail(row)">查看详情</t-link>
        </template>
      </t-table>
    </t-card>

    <!-- 执行详情抽屉 -->
    <t-drawer v-model:visible="drawerVisible" header="执行详情" size="700px">
      <template v-if="currentExecution">
        <t-descriptions :column="2">
          <t-descriptions-item label="执行ID">{{ currentExecution.execution_id }}</t-descriptions-item>
          <t-descriptions-item label="场景">{{ currentExecution.scenario_name }}</t-descriptions-item>
          <t-descriptions-item label="状态">
            <t-tag :theme="getStatusTheme(currentExecution.status)">{{ getStatusText(currentExecution.status) }}</t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="触发方式">{{ currentExecution.trigger_type }}</t-descriptions-item>
          <t-descriptions-item label="目标URL">{{ currentExecution.base_url }}</t-descriptions-item>
          <t-descriptions-item label="环境">{{ currentExecution.environment || '-' }}</t-descriptions-item>
          <t-descriptions-item label="开始时间">{{ currentExecution.started_at }}</t-descriptions-item>
          <t-descriptions-item label="完成时间">{{ currentExecution.completed_at || '-' }}</t-descriptions-item>
          <t-descriptions-item label="总耗时">{{ currentExecution.duration_ms }}ms</t-descriptions-item>
          <t-descriptions-item label="步骤统计">
            通过: {{ currentExecution.passed_steps }} / 
            失败: {{ currentExecution.failed_steps }} / 
            跳过: {{ currentExecution.skipped_steps }}
          </t-descriptions-item>
        </t-descriptions>

        <t-divider>步骤执行结果</t-divider>
        
        <t-collapse>
          <t-collapse-panel
            v-for="(step, index) in stepResults"
            :key="step.step_id"
            :header="`步骤 ${index + 1}: ${step.step_name || step.step_id}`"
          >
            <template #headerRightContent>
              <t-tag :theme="getStepStatusTheme(step.status)" size="small">{{ step.status }}</t-tag>
            </template>
            
            <t-descriptions :column="1" size="small">
              <t-descriptions-item label="请求URL">{{ step.request_url }}</t-descriptions-item>
              <t-descriptions-item label="响应状态码">{{ step.response_status_code }}</t-descriptions-item>
              <t-descriptions-item label="响应时间">{{ step.response_time_ms }}ms</t-descriptions-item>
              <t-descriptions-item label="错误信息" v-if="step.error_message">
                <t-alert theme="error" :message="step.error_message" />
              </t-descriptions-item>
            </t-descriptions>

            <t-divider>请求详情</t-divider>
            <pre class="json-view">{{ formatJson(step.request_headers) }}</pre>
            <pre class="json-view" v-if="step.request_body">{{ step.request_body }}</pre>

            <t-divider>响应详情</t-divider>
            <pre class="json-view">{{ step.response_body?.substring(0, 1000) }}</pre>

            <t-divider v-if="step.assertion_results?.length">断言结果</t-divider>
            <t-table
              v-if="step.assertion_results?.length"
              :data="step.assertion_results"
              :columns="assertionColumns"
              size="small"
              :pagination="false"
            >
              <template #passed="{ row }">
                <t-tag :theme="row.passed ? 'success' : 'danger'" size="small">
                  {{ row.passed ? '通过' : '失败' }}
                </t-tag>
              </template>
            </t-table>
          </t-collapse-panel>
        </t-collapse>
      </template>
    </t-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RefreshIcon } from 'tdesign-icons-vue-next'
import { executionApi } from '../api'

const loading = ref(false)
const executions = ref<any[]>([])
const filterStatus = ref('')
const drawerVisible = ref(false)
const currentExecution = ref<any>(null)
const stepResults = ref<any[]>([])

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { colKey: 'execution_id', title: '执行ID', width: 200, ellipsis: true },
  { colKey: 'scenario_name', title: '场景名称' },
  { colKey: 'status', title: '状态', cell: 'status', width: 100 },
  { colKey: 'progress', title: '进度', cell: 'progress', width: 180 },
  { colKey: 'duration_ms', title: '耗时(ms)', width: 100 },
  { colKey: 'trigger_type', title: '触发方式', width: 100 },
  { colKey: 'started_at', title: '开始时间', width: 180 },
  { colKey: 'op', title: '操作', cell: 'op', width: 100 }
]

const assertionColumns = [
  { colKey: 'type', title: '类型', width: 100 },
  { colKey: 'expression', title: '表达式' },
  { colKey: 'expected', title: '期望值', width: 120 },
  { colKey: 'actual', title: '实际值', width: 120 },
  { colKey: 'passed', title: '结果', cell: 'passed', width: 80 }
]

const getStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    passed: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'default',
    cancelled: 'default'
  }
  return map[status] || 'default'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    passed: '通过',
    failed: '失败',
    running: '运行中',
    pending: '等待中',
    cancelled: '已取消'
  }
  return map[status] || status
}

const getStepStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    passed: 'success',
    failed: 'danger',
    error: 'danger',
    skipped: 'default'
  }
  return map[status] || 'default'
}

const getProgress = (row: any) => {
  if (!row.total_steps) return 0
  return Math.round((row.passed_steps / row.total_steps) * 100)
}

const formatJson = (obj: any) => {
  if (!obj) return ''
  if (typeof obj === 'string') {
    return JSON.stringify(JSON.parse(obj), null, 2)
  }
  return JSON.stringify(obj, null, 2)
}

const loadExecutions = async () => {
  loading.value = true
  const data = await executionApi.list({
    status: filterStatus.value || undefined,
    page: pagination.value.current,
    size: pagination.value.pageSize
  }) as any
  
  executions.value = data.items || []
  pagination.value.total = data.total || 0
  loading.value = false
}

const handlePageChange = (pageInfo: any) => {
  pagination.value.current = pageInfo.current
  loadExecutions()
}

const handleViewDetail = async (row: any) => {
  const data = await executionApi.get(row.execution_id) as any
  currentExecution.value = data
  stepResults.value = data.step_results || []
  drawerVisible.value = true
}

onMounted(loadExecutions)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}

.progress-text {
  margin-left: 8px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
}

.json-view {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow: auto;
  max-height: 200px;
  margin: 8px 0;
}
</style>
