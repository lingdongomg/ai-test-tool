<template>
  <div class="dashboard">
    <!-- 核心指标卡片 -->
    <t-row :gutter="[16, 16]">
      <t-col :xs="12" :sm="6" :md="6" :lg="3">
        <t-card class="stat-card" hover-shadow>
          <div class="stat-content">
            <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
              <ApiIcon />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.endpoints?.total || 0 }}</div>
              <div class="stat-label">接口总数</div>
            </div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6" :md="6" :lg="3">
        <t-card class="stat-card" hover-shadow>
          <div class="stat-content">
            <div class="stat-icon" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
              <CheckCircleIcon />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.test_coverage?.coverage_rate || 0 }}%</div>
              <div class="stat-label">测试覆盖率</div>
            </div>
          </div>
          <t-progress 
            :percentage="stats.test_coverage?.coverage_rate || 0" 
            :color="{ from: '#11998e', to: '#38ef7d' }"
            :stroke-width="4"
            style="margin-top: 12px;"
          />
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6" :md="6" :lg="3">
        <t-card class="stat-card" hover-shadow>
          <div class="stat-content">
            <div class="stat-icon" :style="healthIconStyle">
              <HeartIcon />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.health_status?.health_rate || 0 }}%</div>
              <div class="stat-label">线上健康度</div>
            </div>
          </div>
          <div class="health-detail">
            <t-tag theme="success" variant="light" size="small">
              健康 {{ stats.health_status?.healthy || 0 }}
            </t-tag>
            <t-tag theme="danger" variant="light" size="small" v-if="stats.health_status?.unhealthy">
              异常 {{ stats.health_status?.unhealthy }}
            </t-tag>
            <t-tag theme="warning" variant="light" size="small" v-if="stats.health_status?.critical">
              严重 {{ stats.health_status?.critical }}
            </t-tag>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6" :md="6" :lg="3">
        <t-card class="stat-card" hover-shadow>
          <div class="stat-content">
            <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
              <ErrorCircleIcon />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.recent_anomalies?.total_anomalies || 0 }}</div>
              <div class="stat-label">近7天异常</div>
            </div>
          </div>
          <div class="anomaly-detail" v-if="stats.recent_anomalies?.critical_count">
            <t-tag theme="danger" size="small">
              {{ stats.recent_anomalies.critical_count }} 个严重
            </t-tag>
          </div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 快捷操作 + AI 洞察 -->
    <t-row :gutter="[16, 16]" style="margin-top: 16px;">
      <t-col :xs="24" :md="12" :lg="8">
        <t-card title="快捷操作" class="quick-actions-card">
          <div class="quick-actions">
            <div 
              v-for="action in quickActions" 
              :key="action.id" 
              class="quick-action-item"
              @click="handleQuickAction(action)"
            >
              <div class="action-icon">
                <component :is="getActionIcon(action.icon)" />
              </div>
              <div class="action-info">
                <div class="action-title">{{ action.title }}</div>
                <div class="action-desc">{{ action.description }}</div>
              </div>
            </div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="24" :md="12" :lg="8">
        <t-card title="AI 洞察" class="insights-card">
          <template #actions>
            <t-button theme="primary" variant="text" size="small" @click="$router.push('/ai')">
              查看全部
            </t-button>
          </template>
          <div class="insights-list" v-if="insights.length">
            <div 
              v-for="insight in insights" 
              :key="insight.id" 
              class="insight-item"
              @click="handleInsightClick(insight)"
            >
              <t-tag 
                :theme="getSeverityTheme(insight.severity)" 
                size="small"
                style="margin-right: 8px;"
              >
                {{ getSeverityLabel(insight.severity) }}
              </t-tag>
              <span class="insight-title">{{ insight.title }}</span>
            </div>
          </div>
          <t-empty v-else description="暂无 AI 洞察" />
        </t-card>
      </t-col>
      <t-col :xs="24" :md="24" :lg="8">
        <t-card title="近期动态" class="activities-card">
          <div class="activities-list" v-if="activities.length">
            <div v-for="activity in activities" :key="activity.id" class="activity-item">
              <div class="activity-dot" :class="getActivityDotClass(activity)"></div>
              <div class="activity-content">
                <div class="activity-title">{{ activity.title }}</div>
                <div class="activity-time">{{ formatTime(activity.time) }}</div>
              </div>
            </div>
          </div>
          <t-empty v-else description="暂无动态" />
        </t-card>
      </t-col>
    </t-row>

    <!-- 趋势图表 -->
    <t-row :gutter="[16, 16]" style="margin-top: 16px;">
      <t-col :xs="24" :lg="12">
        <t-card title="健康状态趋势">
          <v-chart class="chart" :option="healthChartOption" autoresize />
        </t-card>
      </t-col>
      <t-col :xs="24" :lg="12">
        <t-card title="异常趋势">
          <v-chart class="chart" :option="anomalyChartOption" autoresize />
        </t-card>
      </t-col>
    </t-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ApiIcon, 
  CheckCircleIcon, 
  HeartIcon, 
  ErrorCircleIcon,
  FileImportIcon,
  CodeIcon,
  FileIcon,
  DashboardIcon,
  ChartIcon
} from 'tdesign-icons-vue-next'
import VChart from 'vue-echarts'
import { dashboardApi } from '../api/v2'

const router = useRouter()

// 数据
const stats = ref<any>({})
const quickActions = ref<any[]>([])
const insights = ref<any[]>([])
const activities = ref<any[]>([])
const healthTrend = ref<any[]>([])
const anomalyTrend = ref<any[]>([])

// 加载数据
const loadData = async () => {
  try {
    const [statsRes, actionsRes, insightsRes, activitiesRes, healthRes, anomalyRes] = await Promise.all([
      dashboardApi.getStats(),
      dashboardApi.getQuickActions(),
      dashboardApi.getInsights(5),
      dashboardApi.getActivities(8),
      dashboardApi.getHealthTrend(7),
      dashboardApi.getAnomalyTrend(7)
    ])
    
    stats.value = statsRes
    quickActions.value = actionsRes.actions || []
    insights.value = insightsRes.insights || []
    activities.value = activitiesRes.activities || []
    healthTrend.value = healthRes.data || []
    anomalyTrend.value = anomalyRes.data || []
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

onMounted(loadData)

// 健康度图标样式
const healthIconStyle = computed(() => {
  const rate = stats.value.health_status?.health_rate || 0
  if (rate >= 90) return 'background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);'
  if (rate >= 70) return 'background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);'
  return 'background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);'
})

// 健康趋势图表配置
const healthChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis'
  },
  legend: {
    data: ['成功率', '平均响应时间']
  },
  xAxis: {
    type: 'category',
    data: healthTrend.value.map(d => d.date?.slice(5) || '')
  },
  yAxis: [
    { type: 'value', name: '成功率(%)', max: 100 },
    { type: 'value', name: '响应时间(ms)' }
  ],
  series: [
    {
      name: '成功率',
      type: 'line',
      smooth: true,
      data: healthTrend.value.map(d => d.success_rate || 0),
      itemStyle: { color: '#38ef7d' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(56, 239, 125, 0.3)' },
            { offset: 1, color: 'rgba(56, 239, 125, 0)' }
          ]
        }
      }
    },
    {
      name: '平均响应时间',
      type: 'bar',
      yAxisIndex: 1,
      data: healthTrend.value.map(d => d.avg_time || 0),
      itemStyle: { color: '#667eea' }
    }
  ]
}))

// 异常趋势图表配置
const anomalyChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis'
  },
  legend: {
    data: ['严重', '错误', '警告']
  },
  xAxis: {
    type: 'category',
    data: anomalyTrend.value.map(d => d.date?.slice(5) || '')
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: '严重',
      type: 'bar',
      stack: 'total',
      data: anomalyTrend.value.map(d => d.critical || 0),
      itemStyle: { color: '#f5576c' }
    },
    {
      name: '错误',
      type: 'bar',
      stack: 'total',
      data: anomalyTrend.value.map(d => d.error || 0),
      itemStyle: { color: '#f7971e' }
    },
    {
      name: '警告',
      type: 'bar',
      stack: 'total',
      data: anomalyTrend.value.map(d => d.warning || 0),
      itemStyle: { color: '#ffd200' }
    }
  ]
}))

// 获取操作图标
const getActionIcon = (icon: string) => {
  const iconMap: Record<string, any> = {
    'upload': FileImportIcon,
    'code': CodeIcon,
    'file-text': FileIcon,
    'activity': DashboardIcon,
    'file-chart': ChartIcon
  }
  return iconMap[icon] || FileIcon
}

// 处理快捷操作
const handleQuickAction = (action: any) => {
  if (action.route) {
    router.push(action.route)
  }
}

// 处理洞察点击
const handleInsightClick = (insight: any) => {
  router.push('/ai')
}

// 获取严重程度主题
const getSeverityTheme = (severity: string) => {
  const map: Record<string, string> = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'default'
  }
  return map[severity] || 'default'
}

// 获取严重程度标签
const getSeverityLabel = (severity: string) => {
  const map: Record<string, string> = {
    'high': '高',
    'medium': '中',
    'low': '低'
  }
  return map[severity] || severity
}

// 获取动态点样式
const getActivityDotClass = (activity: any) => {
  const typeMap: Record<string, string> = {
    'execution': 'dot-blue',
    'health_check': 'dot-green',
    'anomaly_report': 'dot-red',
    'ai_insight': 'dot-purple'
  }
  return typeMap[activity.type] || 'dot-gray'
}

// 格式化时间
const formatTime = (time: string) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return `${Math.floor(diff / 86400000)} 天前`
}
</script>

<style scoped>
.dashboard {
  max-width: 1600px;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 4px;
}

.health-detail,
.anomaly-detail {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #f5f7fa;
}

.quick-action-item:hover {
  background: #e8f4ff;
  transform: translateX(4px);
}

.action-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
}

.action-info {
  flex: 1;
}

.action-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.9);
}

.action-desc {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 2px;
}

.insights-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.insight-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.insight-item:hover {
  background: #f5f7fa;
}

.insight-title {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.7);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activities-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.dot-blue { background: #667eea; }
.dot-green { background: #38ef7d; }
.dot-red { background: #f5576c; }
.dot-purple { background: #764ba2; }
.dot-gray { background: #999; }

.activity-content {
  flex: 1;
}

.activity-title {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.7);
}

.activity-time {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 2px;
}

.chart {
  height: 300px;
}
</style>
