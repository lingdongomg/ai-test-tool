<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <t-row :gutter="16">
      <t-col :span="4">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
            <RocketIcon />
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalTasks }}</div>
            <div class="stat-label">分析任务</div>
          </div>
        </t-card>
      </t-col>
      <t-col :span="4">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
            <TaskIcon />
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.runningTasks }}</div>
            <div class="stat-label">运行中</div>
          </div>
        </t-card>
      </t-col>
      <t-col :span="4">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
            <ApiIcon />
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalEndpoints }}</div>
            <div class="stat-label">API接口</div>
          </div>
        </t-card>
      </t-col>
      <t-col :span="4">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)">
            <TagIcon />
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalTags }}</div>
            <div class="stat-label">标签数量</div>
          </div>
        </t-card>
      </t-col>
      <t-col :span="4">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%)">
            <PlayIcon />
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalScenarios }}</div>
            <div class="stat-label">测试场景</div>
          </div>
        </t-card>
      </t-col>
      <t-col :span="4">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)">
            <CheckCircleIcon />
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalExecutions }}</div>
            <div class="stat-label">执行次数</div>
          </div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 快捷操作 -->
    <t-card title="快捷操作" :bordered="false" class="mt-4">
      <t-space size="large">
        <t-button theme="primary" size="large" @click="$router.push('/tasks')">
          <template #icon><UploadIcon /></template>
          上传日志分析
        </t-button>
        <t-button variant="outline" size="large" @click="$router.push('/import')">
          <template #icon><FileImportIcon /></template>
          导入API文档
        </t-button>
        <t-button variant="outline" size="large" @click="$router.push('/scenarios')">
          <template #icon><AddIcon /></template>
          创建测试场景
        </t-button>
        <t-button variant="outline" size="large" @click="$router.push('/analysis')">
          <template #icon><ChartAnalyticsIcon /></template>
          智能分析
        </t-button>
      </t-space>
    </t-card>

    <t-row :gutter="16" class="mt-4">
      <t-col :span="12">
        <t-card title="标签分布" :bordered="false">
          <v-chart class="chart" :option="tagChartOption" autoresize />
        </t-card>
      </t-col>
      <t-col :span="12">
        <t-card title="任务状态分布" :bordered="false">
          <v-chart class="chart" :option="taskStatusChartOption" autoresize />
        </t-card>
      </t-col>
    </t-row>

    <t-row :gutter="16" class="mt-4">
      <!-- 最近任务 -->
      <t-col :span="12">
        <t-card title="最近分析任务" :bordered="false">
          <template #actions>
            <t-button variant="text" @click="$router.push('/tasks')">查看全部</t-button>
          </template>
          <t-table
            :data="recentTasks"
            :columns="taskColumns"
            row-key="task_id"
            :loading="loading"
            size="small"
            :hover="true"
          >
            <template #status="{ row }">
              <t-tag :theme="getTaskStatusTheme(row.status)" variant="light" size="small">
                <template #icon>
                  <LoadingIcon v-if="row.status === 'running'" class="animate-spin" />
                </template>
                {{ getTaskStatusText(row.status) }}
              </t-tag>
            </template>
            <template #operation="{ row }">
              <t-button variant="text" size="small" @click="$router.push(`/tasks/${row.task_id}`)">
                详情
              </t-button>
            </template>
          </t-table>
        </t-card>
      </t-col>
      
      <!-- 最近执行 -->
      <t-col :span="12">
        <t-card title="最近执行记录" :bordered="false">
          <template #actions>
            <t-button variant="text" @click="$router.push('/executions')">查看全部</t-button>
          </template>
          <t-table
            :data="recentExecutions"
            :columns="executionColumns"
            row-key="execution_id"
            :loading="loading"
            size="small"
            :hover="true"
          >
            <template #status="{ row }">
              <t-tag :theme="getStatusTheme(row.status)" variant="light" size="small">
                {{ row.status }}
              </t-tag>
            </template>
          </t-table>
        </t-card>
      </t-col>
    </t-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import VChart from 'vue-echarts'
import { 
  RocketIcon, 
  TaskIcon, 
  ApiIcon, 
  TagIcon, 
  PlayIcon, 
  CheckCircleIcon,
  UploadIcon,
  FileImportIcon,
  AddIcon,
  ChartAnalyticsIcon,
  LoadingIcon
} from 'tdesign-icons-vue-next'
import { analysisApi, executionApi, tagApi, scenarioApi, taskApi } from '../api'

const loading = ref(false)
const stats = ref({
  totalTasks: 0,
  runningTasks: 0,
  totalEndpoints: 0,
  totalTags: 0,
  totalScenarios: 0,
  totalExecutions: 0
})

const tagStats = ref<Record<string, number>>({})
const taskStatusStats = ref<Record<string, number>>({})
const recentTasks = ref<any[]>([])
const recentExecutions = ref<any[]>([])

const taskColumns = [
  { colKey: 'name', title: '任务名称', ellipsis: true },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'total_requests', title: '请求数', width: 80 },
  { colKey: 'operation', title: '操作', width: 80 }
]

const executionColumns = [
  { colKey: 'scenario_name', title: '场景名称', ellipsis: true },
  { colKey: 'status', title: '状态', width: 80 },
  { colKey: 'passed_steps', title: '通过/总数', width: 90 },
  { colKey: 'duration_ms', title: '耗时(ms)', width: 90 }
]

const getStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    passed: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'default'
  }
  return map[status] || 'default'
}

const getTaskStatusTheme = (status: string) => {
  const themes: Record<string, string> = {
    pending: 'default',
    running: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return themes[status] || 'default'
}

const getTaskStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const tagChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: '5%', left: 'center' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
    labelLine: { show: false },
    data: Object.entries(tagStats.value).map(([name, value]) => ({ name, value }))
  }]
}))

const taskStatusChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: '5%', left: 'center' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
    labelLine: { show: false },
    data: [
      { value: taskStatusStats.value.completed || 0, name: '已完成', itemStyle: { color: '#52c41a' } },
      { value: taskStatusStats.value.running || 0, name: '运行中', itemStyle: { color: '#1890ff' } },
      { value: taskStatusStats.value.pending || 0, name: '等待中', itemStyle: { color: '#d9d9d9' } },
      { value: taskStatusStats.value.failed || 0, name: '失败', itemStyle: { color: '#ff4d4f' } }
    ].filter(d => d.value > 0)
  }]
}))

const loadData = async () => {
  loading.value = true
  
  try {
    const [kbStats, tags, scenarios, executions, tasks] = await Promise.all([
      analysisApi.knowledgeBaseStats().catch(() => ({ total_endpoints: 0, tag_statistics: {} })),
      tagApi.list().catch(() => []),
      scenarioApi.list({ size: 1 }).catch(() => ({ total: 0 })),
      executionApi.list({ size: 5 }).catch(() => ({ items: [], total: 0 })),
      taskApi.list({ limit: 5 }).catch(() => ({ items: [], total: 0 }))
    ])

    // 统计任务状态
    const allTasks: any = await taskApi.list({ limit: 100 }).catch(() => ({ items: [], total: 0 }))
    const taskItems = (allTasks as any).items || []
    const statusCount: Record<string, number> = { pending: 0, running: 0, completed: 0, failed: 0 }
    taskItems.forEach((t: any) => {
      if (statusCount[t.status] !== undefined) statusCount[t.status]++
    })
    taskStatusStats.value = statusCount

    stats.value = {
      totalTasks: (allTasks as any).total || 0,
      runningTasks: statusCount.running || 0,
      totalEndpoints: (kbStats as any).total_endpoints || 0,
      totalTags: Array.isArray(tags) ? tags.length : 0,
      totalScenarios: (scenarios as any).total || 0,
      totalExecutions: (executions as any).total || 0
    }

    tagStats.value = (kbStats as any).tag_statistics || {}
    recentTasks.value = (tasks as any).items || []
    recentExecutions.value = (executions as any).items || []
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 16px;
}

.stat-card :deep(.t-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
  line-height: 1.2;
}

.stat-label {
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
  margin-top: 4px;
}

.chart {
  height: 280px;
}

.mt-4 {
  margin-top: 16px;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
