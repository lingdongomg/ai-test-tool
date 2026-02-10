<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="welcome-content">
        <h2 class="welcome-title">AI Test Tool</h2>
        <p class="welcome-desc">接口自动化测试与智能运维平台</p>
      </div>
      <div class="welcome-stats">
        <div class="welcome-stat-item">
          <span class="welcome-stat-value">{{ stats.endpoints?.total || 0 }}</span>
          <span class="welcome-stat-label">接口</span>
        </div>
        <div class="welcome-stat-divider"></div>
        <div class="welcome-stat-item">
          <span class="welcome-stat-value">{{ formatPercent(stats.test_coverage?.coverage_rate || 0) }}</span>
          <span class="welcome-stat-label">覆盖率</span>
        </div>
        <div class="welcome-stat-divider"></div>
        <div class="welcome-stat-item">
          <span class="welcome-stat-value">{{ formatPercent(stats.health_status?.health_rate || 0) }}</span>
          <span class="welcome-stat-label">健康度</span>
        </div>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <t-row :gutter="[20, 20]" style="margin-top: 24px;">
      <t-col :xs="12" :sm="6" :md="6" :lg="6">
        <StatCard
          :value="stats.endpoints?.total || 0"
          label="接口总数"
          gradient="linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)"
        >
          <template #icon><ApiIcon /></template>
        </StatCard>
      </t-col>
      <t-col :xs="12" :sm="6" :md="6" :lg="6">
        <StatCard
          :value="stats.test_coverage?.coverage_rate || 0"
          label="测试覆盖率"
          format="percent"
          gradient="linear-gradient(135deg, #10b981 0%, #34d399 100%)"
          show-progress
          :progress-color="{ from: '#10b981', to: '#34d399' }"
        >
          <template #icon><CheckCircleIcon /></template>
        </StatCard>
      </t-col>
      <t-col :xs="12" :sm="6" :md="6" :lg="6">
        <StatCard
          :value="stats.health_status?.health_rate || 0"
          label="线上健康度"
          format="percent"
          :gradient="healthGradient"
        >
          <template #icon><HeartIcon /></template>
          <template #extra>
            <t-tag theme="success" variant="light" size="small">健康 {{ stats.health_status?.healthy || 0 }}</t-tag>
            <t-tag v-if="stats.health_status?.unhealthy" theme="danger" variant="light" size="small">异常 {{ stats.health_status?.unhealthy }}</t-tag>
            <t-tag v-if="stats.health_status?.critical" theme="warning" variant="light" size="small">严重 {{ stats.health_status?.critical }}</t-tag>
          </template>
        </StatCard>
      </t-col>
      <t-col :xs="12" :sm="6" :md="6" :lg="6">
        <StatCard
          :value="stats.recent_anomalies?.total_anomalies || 0"
          label="近7天异常"
          gradient="linear-gradient(135deg, #f43f5e 0%, #fb7185 100%)"
        >
          <template #icon><ErrorCircleIcon /></template>
          <template v-if="stats.recent_anomalies?.critical_count" #extra>
            <t-tag theme="danger" size="small">{{ stats.recent_anomalies.critical_count }} 个严重</t-tag>
          </template>
        </StatCard>
      </t-col>
    </t-row>

    <!-- 快捷操作 + AI 洞察 + 近期动态 -->
    <div class="section-header" style="margin-top: 32px;">
      <div class="section-header-line"></div>
      <span class="section-header-text">工作台</span>
    </div>
    <t-row :gutter="[20, 20]" style="margin-top: 16px;">
      <t-col :xs="24" :md="12" :lg="8">
        <t-card title="快捷操作" class="equal-height-card">
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
              <div class="action-arrow">&#8250;</div>
            </div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="24" :md="12" :lg="8">
        <t-card title="AI 洞察" class="equal-height-card">
          <template #actions>
            <t-button theme="primary" variant="text" size="small" @click="$router.push('/ai')">查看全部</t-button>
          </template>
          <div class="insights-list" v-if="insights.length">
            <div v-for="insight in insights" :key="insight.id" class="insight-item" @click="$router.push('/ai')">
              <StatusTag type="severity" :value="insight.severity" size="small" style="margin-right: 8px;" />
              <span class="insight-title">{{ insight.title }}</span>
            </div>
          </div>
          <div v-else class="empty-state">
            <div class="empty-icon">&#128161;</div>
            <div class="empty-text">暂无 AI 洞察</div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="24" :md="24" :lg="8">
        <t-card title="近期动态" class="equal-height-card">
          <div class="activities-list" v-if="activities.length">
            <div v-for="activity in activities" :key="activity.id" class="activity-item">
              <div class="activity-dot" :class="getActivityDotClass(activity.type)"></div>
              <div class="activity-content">
                <div class="activity-title">{{ activity.title }}</div>
                <div class="activity-time">{{ formatRelativeTime(activity.time) }}</div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <div class="empty-icon">&#128196;</div>
            <div class="empty-text">暂无动态</div>
          </div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 趋势图表 -->
    <div class="section-header" style="margin-top: 32px;">
      <div class="section-header-line"></div>
      <span class="section-header-text">趋势分析</span>
    </div>
    <t-row :gutter="[20, 20]" style="margin-top: 16px;">
      <t-col :xs="24" :lg="12">
        <t-card title="健康状态趋势" class="chart-card">
          <v-chart class="chart" :option="healthChartOption" autoresize />
        </t-card>
      </t-col>
      <t-col :xs="24" :lg="12">
        <t-card title="异常趋势" class="chart-card">
          <v-chart class="chart" :option="anomalyChartOption" autoresize />
        </t-card>
      </t-col>
    </t-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { ApiIcon, CheckCircleIcon, HeartIcon, ErrorCircleIcon, FileImportIcon, CodeIcon, FileIcon, DashboardIcon, ChartIcon } from 'tdesign-icons-vue-next'
import VChart from 'vue-echarts'
import { dashboardApi } from '../api/v2'
import { StatCard, StatusTag } from '../components'
import { formatRelativeTime, formatPercent } from '../utils'

const router = useRouter()

// =====================================================
// 数据
// =====================================================
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

// =====================================================
// 计算属性
// =====================================================

// 健康度渐变色
const healthGradient = computed(() => {
  const rate = stats.value.health_status?.health_rate || 0
  if (rate >= 90) return 'linear-gradient(135deg, #10b981 0%, #34d399 100%)'
  if (rate >= 70) return 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)'
  return 'linear-gradient(135deg, #f43f5e 0%, #fb7185 100%)'
})

// 健康趋势图表
const healthChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['成功率', '平均响应时间'], bottom: 0 },
  grid: { left: '3%', right: '4%', bottom: '12%', top: '10%', containLabel: true },
  xAxis: { type: 'category', data: healthTrend.value.map(d => d.date?.slice(5) || ''), axisTick: { show: false }, axisLine: { lineStyle: { color: '#e5e7eb' } }, axisLabel: { color: '#6b7280' } },
  yAxis: [
    { type: 'value', name: '成功率(%)', max: 100, splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } }, axisLabel: { color: '#6b7280' } },
    { type: 'value', name: '响应时间(ms)', splitLine: { show: false }, axisLabel: { color: '#6b7280' } }
  ],
  series: [
    {
      name: '成功率', type: 'line', smooth: true,
      data: healthTrend.value.map(d => d.success_rate || 0),
      itemStyle: { color: '#10b981' },
      lineStyle: { width: 2.5 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(16, 185, 129, 0.2)' }, { offset: 1, color: 'rgba(16, 185, 129, 0)' }]
        }
      }
    },
    { name: '平均响应时间', type: 'bar', yAxisIndex: 1, data: healthTrend.value.map(d => d.avg_time || 0), itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 24 }
  ]
}))

// 异常趋势图表
const anomalyChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['严重', '错误', '警告'], bottom: 0 },
  grid: { left: '3%', right: '4%', bottom: '12%', top: '10%', containLabel: true },
  xAxis: { type: 'category', data: anomalyTrend.value.map(d => d.date?.slice(5) || ''), axisTick: { show: false }, axisLine: { lineStyle: { color: '#e5e7eb' } }, axisLabel: { color: '#6b7280' } },
  yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } }, axisLabel: { color: '#6b7280' } },
  series: [
    { name: '严重', type: 'bar', stack: 'total', data: anomalyTrend.value.map(d => d.critical || 0), itemStyle: { color: '#f43f5e', borderRadius: [0, 0, 0, 0] }, barMaxWidth: 24 },
    { name: '错误', type: 'bar', stack: 'total', data: anomalyTrend.value.map(d => d.error || 0), itemStyle: { color: '#f59e0b' }, barMaxWidth: 24 },
    { name: '警告', type: 'bar', stack: 'total', data: anomalyTrend.value.map(d => d.warning || 0), itemStyle: { color: '#fbbf24', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 24 }
  ]
}))

// =====================================================
// 工具函数
// =====================================================

// 图标映射
const ICON_MAP: Record<string, Component> = {
  'upload': FileImportIcon,
  'code': CodeIcon,
  'file-text': FileIcon,
  'activity': DashboardIcon,
  'file-chart': ChartIcon
}

const getActionIcon = (icon: string) => ICON_MAP[icon] || FileIcon

// 动态点样式
const ACTIVITY_DOT_MAP: Record<string, string> = {
  'execution': 'dot-blue',
  'health_check': 'dot-green',
  'anomaly_report': 'dot-red',
  'ai_insight': 'dot-purple'
}

const getActivityDotClass = (type: string) => ACTIVITY_DOT_MAP[type] || 'dot-gray'

// 快捷操作
const handleQuickAction = (action: any) => {
  if (action.route) router.push(action.route)
}
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

/* 欢迎横幅 */
.welcome-banner {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #6366f1 100%);
  border-radius: 18px;
  padding: 32px 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #fff;
  position: relative;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(79, 70, 229, 0.25);
}

.welcome-banner::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.welcome-banner::after {
  content: '';
  position: absolute;
  bottom: -30%;
  left: 20%;
  width: 250px;
  height: 250px;
  background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
  border-radius: 50%;
}

.welcome-content {
  position: relative;
  z-index: 1;
}

.welcome-title {
  margin: 0 0 6px 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.welcome-desc {
  margin: 0;
  font-size: 14px;
  opacity: 0.8;
  font-weight: 400;
}

.welcome-stats {
  display: flex;
  align-items: center;
  gap: 0;
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 16px 28px;
  backdrop-filter: blur(8px);
}

.welcome-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 20px;
}

.welcome-stat-value {
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.welcome-stat-label {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 4px;
}

.welcome-stat-divider {
  width: 1px;
  height: 36px;
  background: rgba(255, 255, 255, 0.2);
}

/* 区域标题 */
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-header-line {
  width: 4px;
  height: 18px;
  border-radius: 2px;
  background: linear-gradient(180deg, #6366f1, #8b5cf6);
}

.section-header-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

/* 等高卡片 */
.equal-height-card {
  height: 100%;
}

/* 快捷操作 */
.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-action-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  cursor: pointer;
  background: var(--bg-color);
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.quick-action-item:hover {
  background: var(--primary-light);
  border-color: #c7d2fe;
  transform: translateX(4px);
}

.quick-action-item:hover .action-arrow {
  opacity: 1;
  transform: translateX(2px);
}

.action-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 17px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.action-info {
  flex: 1;
}

.action-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.action-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.action-arrow {
  font-size: 18px;
  color: var(--text-tertiary);
  opacity: 0;
  transition: all var(--transition-fast);
  font-weight: 300;
}

/* AI 洞察 */
.insights-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.insight-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.insight-item:hover {
  background: var(--bg-color);
}

.insight-title {
  font-size: 14px;
  color: var(--text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-tertiary);
}

.empty-icon {
  font-size: 36px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
}

/* 近期动态 */
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
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.03);
}

.dot-blue { background: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15); }
.dot-green { background: #10b981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15); }
.dot-red { background: #f43f5e; box-shadow: 0 0 0 3px rgba(244, 63, 94, 0.15); }
.dot-purple { background: #8b5cf6; box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15); }
.dot-gray { background: #94a3b8; box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.15); }

.activity-content {
  flex: 1;
}

.activity-title {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.activity-time {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

/* 图表卡片 */
.chart-card {
  overflow: hidden;
}

.chart {
  height: 320px;
}

/* 响应式 */
@media (max-width: 768px) {
  .welcome-banner {
    flex-direction: column;
    gap: 20px;
    padding: 24px 20px;
    align-items: flex-start;
  }

  .welcome-stats {
    width: 100%;
    justify-content: center;
    padding: 12px 16px;
  }

  .welcome-stat-item {
    padding: 0 12px;
  }

  .welcome-stat-value {
    font-size: 18px;
  }
}
</style>
