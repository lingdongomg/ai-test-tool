<template>
  <div class="executions-page">
    <!-- 工具栏 -->
    <t-card class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <t-select
            v-model="statusFilter"
            placeholder="执行状态"
            clearable
            style="width: 120px;"
            @change="handleSearch"
          >
            <t-option value="passed">通过</t-option>
            <t-option value="failed">失败</t-option>
            <t-option value="running">运行中</t-option>
          </t-select>
        </div>
        <div class="toolbar-right">
          <t-button @click="loadExecutions">
            <template #icon><RefreshIcon /></template>
            刷新
          </t-button>
        </div>
      </div>
    </t-card>

    <!-- 执行记录列表 -->
    <t-card class="table-card">
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
        <template #pass_rate="{ row }">
          <t-progress 
            :percentage="row.pass_rate || 0" 
            :color="getProgressColor(row.pass_rate)"
            size="small"
            style="width: 100px;"
          />
          <span style="margin-left: 8px;">{{ row.pass_rate || 0 }}%</span>
        </template>
        <template #stats="{ row }">
          <t-space size="small">
            <t-tag theme="success" variant="light" size="small">通过 {{ row.passed || 0 }}</t-tag>
            <t-tag theme="danger" variant="light" size="small">失败 {{ row.failed || 0 }}</t-tag>
            <t-tag theme="default" variant="light" size="small">跳过 {{ row.skipped || 0 }}</t-tag>
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
      header="执行详情"
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
          <t-descriptions-item label="总用例数">{{ currentExecution.total }}</t-descriptions-item>
          <t-descriptions-item label="通过率">{{ currentExecution.pass_rate }}%</t-descriptions-item>
          <t-descriptions-item label="执行时间">{{ currentExecution.created_at }}</t-descriptions-item>
          <t-descriptions-item label="耗时">{{ currentExecution.duration_ms }}ms</t-descriptions-item>
        </t-descriptions>

        <t-divider>执行结果</t-divider>
        <t-table
          :data="currentExecution.results || []"
          :columns="resultColumns"
          size="small"
          row-key="test_case_id"
        >
          <template #status="{ row }">
            <t-tag :theme="getResultStatusTheme(row.status)" size="small">
              {{ row.status }}
            </t-tag>
          </template>
        </t-table>
      </template>
    </t-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { RefreshIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'

// 数据
const executions = ref<any[]>([])
const loading = ref(false)

// 筛选
const statusFilter = ref('')

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 详情
const detailDrawerVisible = ref(false)
const currentExecution = ref<any>(null)

// 表格列
const columns = [
  { colKey: 'execution_id', title: '执行ID', width: 120 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'pass_rate', title: '通过率', width: 180 },
  { colKey: 'stats', title: '统计', width: 240 },
  { colKey: 'created_at', title: '执行时间', width: 180 },
  { colKey: 'op', title: '操作', width: 100 }
]

const resultColumns = [
  { colKey: 'test_case_name', title: '用例名称', ellipsis: true },
  { colKey: 'status', title: '状态', width: 80 },
  { colKey: 'response_time_ms', title: '响应时间', width: 100 },
  { colKey: 'status_code', title: '状态码', width: 80 }
]

// 加载数据
const loadExecutions = async () => {
  loading.value = true
  try {
    const res = await developmentApi.listExecutions({
      status: statusFilter.value || undefined,
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

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadExecutions()
}

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadExecutions()
}

// 查看详情
const handleViewDetail = (row: any) => {
  currentExecution.value = row
  detailDrawerVisible.value = true
}

// 辅助函数
const getStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    'passed': 'success',
    'completed': 'success',
    'failed': 'danger',
    'running': 'warning',
    'pending': 'default'
  }
  return map[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    'passed': '通过',
    'completed': '完成',
    'failed': '失败',
    'running': '运行中',
    'pending': '等待中'
  }
  return map[status] || status
}

const getResultStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    'passed': 'success',
    'failed': 'danger',
    'skipped': 'default'
  }
  return map[status] || 'default'
}

const getProgressColor = (rate: number) => {
  if (rate >= 90) return '#38ef7d'
  if (rate >= 70) return '#ffd200'
  return '#f5576c'
}
</script>

<style scoped>
.executions-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
