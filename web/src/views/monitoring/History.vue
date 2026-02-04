<template>
  <div class="history-page">
    <t-card>
      <t-table
        :data="executions"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        row-key="execution_id"
        hover
        @page-change="handlePageChange"
      >
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)">
            {{ getStatusLabel(row.status) }}
          </t-tag>
        </template>
        <template #health_rate="{ row }">
          <t-progress 
            :percentage="getHealthRate(row)" 
            :color="getProgressColor(getHealthRate(row))"
            size="small"
            style="width: 80px; display: inline-block;"
          />
          <span style="margin-left: 8px;">{{ getHealthRate(row) }}%</span>
        </template>
        <template #stats="{ row }">
          <t-space size="small">
            <t-tag theme="success" variant="light" size="small">健康 {{ row.healthy_count || 0 }}</t-tag>
            <t-tag theme="danger" variant="light" size="small">异常 {{ row.unhealthy_count || 0 }}</t-tag>
          </t-space>
        </template>
        <template #op="{ row }">
          <t-link theme="primary" @click="handleViewDetail(row)">查看详情</t-link>
        </template>
      </t-table>
    </t-card>

    <!-- 详情抽屉 -->
    <t-drawer
      v-model:visible="detailDrawerVisible"
      header="检查详情"
      size="700px"
    >
      <template v-if="currentExecution">
        <t-descriptions :column="2" bordered>
          <t-descriptions-item label="执行ID">{{ currentExecution.execution_id }}</t-descriptions-item>
          <t-descriptions-item label="状态">
            <t-tag :theme="getStatusTheme(currentExecution.status)">
              {{ getStatusLabel(currentExecution.status) }}
            </t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="总请求数">{{ currentExecution.total_requests }}</t-descriptions-item>
          <t-descriptions-item label="健康率">{{ getHealthRate(currentExecution) }}%</t-descriptions-item>
          <t-descriptions-item label="触发方式">{{ currentExecution.trigger_type }}</t-descriptions-item>
          <t-descriptions-item label="执行时间">{{ currentExecution.created_at }}</t-descriptions-item>
        </t-descriptions>

        <t-divider>检查结果</t-divider>
        <t-table
          :data="detailResults"
          :columns="detailColumns"
          size="small"
          row-key="id"
        >
          <template #success="{ row }">
            <t-tag :theme="row.success ? 'success' : 'danger'" size="small">
              {{ row.success ? '健康' : '异常' }}
            </t-tag>
          </template>
        </t-table>
      </template>
    </t-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { monitoringApi } from '../../api/v2'

// 数据
const executions = ref<any[]>([])
const loading = ref(false)

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 详情
const detailDrawerVisible = ref(false)
const currentExecution = ref<any>(null)
const detailResults = ref<any[]>([])

// 表格列
const columns = [
  { colKey: 'execution_id', title: '执行ID', width: 120 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'health_rate', title: '健康率', width: 160 },
  { colKey: 'stats', title: '统计', width: 200 },
  { colKey: 'trigger_type', title: '触发方式', width: 100 },
  { colKey: 'created_at', title: '执行时间', width: 180 },
  { colKey: 'op', title: '操作', width: 100 }
]

const detailColumns = [
  { colKey: 'method', title: '方法', width: 80 },
  { colKey: 'url', title: 'URL', ellipsis: true },
  { colKey: 'success', title: '状态', width: 80 },
  { colKey: 'status_code', title: '状态码', width: 80 },
  { colKey: 'response_time_ms', title: '响应时间', width: 100 }
]

// 加载数据
const loadExecutions = async () => {
  loading.value = true
  try {
    const res = await monitoringApi.listHealthCheckExecutions({
      page: pagination.current,
      page_size: pagination.pageSize
    })
    executions.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载执行记录失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadExecutions)

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadExecutions()
}

// 查看详情
const handleViewDetail = async (row: any) => {
  currentExecution.value = row
  detailDrawerVisible.value = true
  
  try {
    const res = await monitoringApi.getHealthCheckExecution(row.execution_id)
    detailResults.value = res.results || []
  } catch (error) {
    console.error('加载详情失败:', error)
  }
}

// 辅助函数
const getHealthRate = (row: any) => {
  const total = (row.healthy_count || 0) + (row.unhealthy_count || 0)
  if (total === 0) return 0
  return Math.round((row.healthy_count || 0) / total * 100)
}

const getStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    'completed': 'success',
    'running': 'warning',
    'failed': 'danger',
    'pending': 'default'
  }
  return map[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    'completed': '完成',
    'running': '运行中',
    'failed': '失败',
    'pending': '等待中'
  }
  return map[status] || status
}

const getProgressColor = (rate: number) => {
  if (rate >= 90) return '#38ef7d'
  if (rate >= 70) return '#ffd200'
  return '#f5576c'
}
</script>

<style scoped>
.history-page {
  max-width: 1200px;
}
</style>
