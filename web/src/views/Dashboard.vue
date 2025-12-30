<template>
  <div class="dashboard">
    <t-row :gutter="16">
      <t-col :span="6">
        <t-card title="接口总数" :bordered="false">
          <div class="stat-value">{{ stats.totalEndpoints }}</div>
          <div class="stat-desc">已导入的API接口</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card title="标签数量" :bordered="false">
          <div class="stat-value">{{ stats.totalTags }}</div>
          <div class="stat-desc">接口分类标签</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card title="测试场景" :bordered="false">
          <div class="stat-value">{{ stats.totalScenarios }}</div>
          <div class="stat-desc">已创建的测试场景</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card title="执行次数" :bordered="false">
          <div class="stat-value">{{ stats.totalExecutions }}</div>
          <div class="stat-desc">场景执行总次数</div>
        </t-card>
      </t-col>
    </t-row>

    <t-row :gutter="16" class="mt-4">
      <t-col :span="12">
        <t-card title="标签分布" :bordered="false">
          <v-chart class="chart" :option="tagChartOption" autoresize />
        </t-card>
      </t-col>
      <t-col :span="12">
        <t-card title="执行统计" :bordered="false">
          <v-chart class="chart" :option="executionChartOption" autoresize />
        </t-card>
      </t-col>
    </t-row>

    <t-row :gutter="16" class="mt-4">
      <t-col :span="24">
        <t-card title="最近执行记录" :bordered="false">
          <t-table
            :data="recentExecutions"
            :columns="executionColumns"
            row-key="execution_id"
            :loading="loading"
            size="small"
          >
            <template #status="{ row }">
              <t-tag :theme="getStatusTheme(row.status)">{{ row.status }}</t-tag>
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
import { analysisApi, executionApi, tagApi, scenarioApi } from '../api'

const loading = ref(false)
const stats = ref({
  totalEndpoints: 0,
  totalTags: 0,
  totalScenarios: 0,
  totalExecutions: 0
})

const tagStats = ref<Record<string, number>>({})
const recentExecutions = ref<any[]>([])

const executionColumns = [
  { colKey: 'execution_id', title: '执行ID', width: 200 },
  { colKey: 'scenario_name', title: '场景名称' },
  { colKey: 'status', title: '状态', cell: 'status', width: 100 },
  { colKey: 'passed_steps', title: '通过/总数', width: 100 },
  { colKey: 'duration_ms', title: '耗时(ms)', width: 100 },
  { colKey: 'created_at', title: '执行时间', width: 180 }
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

const tagChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: Object.entries(tagStats.value).map(([name, value]) => ({ name, value }))
  }]
}))

const executionChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
  yAxis: { type: 'value' },
  series: [
    { name: '通过', type: 'bar', stack: 'total', data: [12, 15, 10, 18, 20, 8, 5] },
    { name: '失败', type: 'bar', stack: 'total', data: [2, 3, 1, 4, 2, 1, 0] }
  ]
}))

const loadData = async () => {
  loading.value = true
  
  const [kbStats, tags, scenarios, executions] = await Promise.all([
    analysisApi.knowledgeBaseStats().catch(() => ({ total_endpoints: 0, tag_statistics: {} })),
    tagApi.list().catch(() => []),
    scenarioApi.list({ size: 1 }).catch(() => ({ total: 0 })),
    executionApi.list({ size: 10 }).catch(() => ({ items: [], total: 0 }))
  ])

  stats.value = {
    totalEndpoints: (kbStats as any).total_endpoints || 0,
    totalTags: Array.isArray(tags) ? tags.length : 0,
    totalScenarios: (scenarios as any).total || 0,
    totalExecutions: (executions as any).total || 0
  }

  tagStats.value = (kbStats as any).tag_statistics || {}
  recentExecutions.value = (executions as any).items || []
  
  loading.value = false
}

onMounted(loadData)
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #0052d9;
}

.stat-desc {
  color: rgba(0, 0, 0, 0.4);
  margin-top: 8px;
}

.chart {
  height: 300px;
}

.mt-4 {
  margin-top: 16px;
}
</style>
