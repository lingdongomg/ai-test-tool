<template>
  <div class="alerts-page">
    <t-card>
      <template #title>
        <div class="card-title">
          <span>告警管理</span>
          <t-tag v-if="unresolvedCount > 0" theme="danger" size="small">
            {{ unresolvedCount }} 个未处理
          </t-tag>
        </div>
      </template>
      <template #actions>
        <t-radio-group v-model="statusFilter" variant="default-filled" @change="handleSearch">
          <t-radio-button value="">全部</t-radio-button>
          <t-radio-button :value="false">未处理</t-radio-button>
          <t-radio-button :value="true">已处理</t-radio-button>
        </t-radio-group>
      </template>
      
      <t-table
        :data="alerts"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        row-key="insight_id"
        hover
        @page-change="handlePageChange"
      >
        <template #severity="{ row }">
          <t-tag :theme="getSeverityTheme(row.severity)" size="small">
            {{ getSeverityLabel(row.severity) }}
          </t-tag>
        </template>
        <template #is_resolved="{ row }">
          <t-tag :theme="row.is_resolved ? 'success' : 'warning'" variant="light" size="small">
            {{ row.is_resolved ? '已处理' : '未处理' }}
          </t-tag>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">详情</t-link>
            <t-link 
              v-if="!row.is_resolved" 
              theme="primary" 
              @click="handleResolve(row)"
            >
              标记处理
            </t-link>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 详情抽屉 -->
    <t-drawer
      v-model:visible="detailDrawerVisible"
      header="告警详情"
      size="500px"
    >
      <template v-if="currentAlert">
        <t-descriptions :column="1" bordered>
          <t-descriptions-item label="告警标题">{{ currentAlert.title }}</t-descriptions-item>
          <t-descriptions-item label="严重程度">
            <t-tag :theme="getSeverityTheme(currentAlert.severity)">
              {{ getSeverityLabel(currentAlert.severity) }}
            </t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="状态">
            <t-tag :theme="currentAlert.is_resolved ? 'success' : 'warning'" variant="light">
              {{ currentAlert.is_resolved ? '已处理' : '未处理' }}
            </t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="创建时间">{{ currentAlert.created_at }}</t-descriptions-item>
          <t-descriptions-item label="处理时间" v-if="currentAlert.resolved_at">
            {{ currentAlert.resolved_at }}
          </t-descriptions-item>
        </t-descriptions>
        
        <t-divider>描述</t-divider>
        <p>{{ currentAlert.description || '无描述' }}</p>
        
        <t-divider>建议</t-divider>
        <ul v-if="currentAlert.recommendations">
          <li v-for="(rec, index) in currentAlert.recommendations" :key="index">{{ rec }}</li>
        </ul>
        <p v-else>暂无建议</p>
        
        <div style="margin-top: 24px;" v-if="!currentAlert.is_resolved">
          <t-button theme="primary" block @click="handleResolve(currentAlert)">
            标记为已处理
          </t-button>
        </div>
      </template>
    </t-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { monitoringApi } from '../../api/v2'

// 数据
const alerts = ref<any[]>([])
const loading = ref(false)

// 筛选
const statusFilter = ref<boolean | ''>('')

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 详情
const detailDrawerVisible = ref(false)
const currentAlert = ref<any>(null)

// 未处理数量
const unresolvedCount = computed(() => {
  return alerts.value.filter(a => !a.is_resolved).length
})

// 表格列
const columns = [
  { colKey: 'title', title: '告警标题', ellipsis: true },
  { colKey: 'severity', title: '严重程度', width: 100 },
  { colKey: 'is_resolved', title: '状态', width: 100 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'op', title: '操作', width: 140 }
]

// 加载数据
const loadAlerts = async () => {
  loading.value = true
  try {
    const res = await monitoringApi.listAlerts({
      is_resolved: statusFilter.value === '' ? undefined : statusFilter.value,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    alerts.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载告警失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadAlerts)

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadAlerts()
}

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadAlerts()
}

// 查看详情
const handleView = (row: any) => {
  currentAlert.value = row
  detailDrawerVisible.value = true
}

// 标记处理
const handleResolve = async (row: any) => {
  try {
    await monitoringApi.resolveAlert(row.insight_id)
    MessagePlugin.success('已标记为处理')
    row.is_resolved = true
    if (detailDrawerVisible.value) {
      currentAlert.value.is_resolved = true
    }
  } catch (error) {
    console.error('标记失败:', error)
  }
}

// 辅助函数
const getSeverityTheme = (severity: string) => {
  const map: Record<string, string> = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'default'
  }
  return map[severity] || 'default'
}

const getSeverityLabel = (severity: string) => {
  const map: Record<string, string> = {
    'high': '高',
    'medium': '中',
    'low': '低'
  }
  return map[severity] || severity
}
</script>

<style scoped>
.alerts-page {
  max-width: 1000px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
