<template>
  <div class="task-detail" v-loading="loading">
    <t-card>
      <t-descriptions :column="3" bordered>
        <t-descriptions-item label="任务ID">{{ task.task_id }}</t-descriptions-item>
        <t-descriptions-item label="任务名称">{{ task.name }}</t-descriptions-item>
        <t-descriptions-item label="状态">
          <t-tag :theme="getStatusTheme(task.status)">
            {{ getStatusLabel(task.status) }}
          </t-tag>
        </t-descriptions-item>
        <t-descriptions-item label="文件大小">{{ formatFileSize(task.log_file_size) }}</t-descriptions-item>
        <t-descriptions-item label="总行数">{{ task.total_lines || '-' }}</t-descriptions-item>
        <t-descriptions-item label="解析请求数">{{ task.total_requests || '-' }}</t-descriptions-item>
        <t-descriptions-item label="创建时间">{{ task.created_at }}</t-descriptions-item>
        <t-descriptions-item label="开始时间">{{ task.started_at || '-' }}</t-descriptions-item>
        <t-descriptions-item label="完成时间">{{ task.completed_at || '-' }}</t-descriptions-item>
      </t-descriptions>
    </t-card>

    <!-- 失败原因 -->
    <t-card v-if="task.status === 'failed'" title="失败原因" style="margin-top: 16px;">
      <t-alert theme="error" :message="getErrorTitle(task.error_message)" style="margin-bottom: 16px;" />
      <div class="error-detail-box">
        <pre>{{ task.error_message || '未知错误，请查看服务器日志' }}</pre>
      </div>
    </t-card>

    <t-card title="分析报告" style="margin-top: 16px;">
      <t-table
        :data="reports"
        :columns="reportColumns"
        row-key="id"
        hover
      >
        <template #op="{ row }">
          <t-link theme="primary" @click="handleViewReport(row)">查看报告</t-link>
        </template>
      </t-table>
      <t-empty v-if="!reports.length" description="暂无分析报告" />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { insightsApi } from '../../api/v2'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

// 数据
const loading = ref(false)
const task = ref<any>({})
const reports = ref<any[]>([])

// 报告列
const reportColumns = [
  { colKey: 'id', title: 'ID', width: 80 },
  { colKey: 'title', title: '报告标题', ellipsis: true },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'op', title: '操作', width: 100 }
]

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const res = await insightsApi.getTask(taskId)
    task.value = res.task || {}
    reports.value = res.reports || []
  } catch (error) {
    console.error('加载任务详情失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// 查看报告
const handleViewReport = (row: any) => {
  router.push(`/insights/reports/${row.id}`)
}

// 辅助函数
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

const formatFileSize = (size: number) => {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

const getErrorTitle = (error: string) => {
  if (!error) return '任务执行失败'
  const firstLine = error.split('\n')[0]
  return firstLine || '任务执行失败'
}
</script>

<style scoped>
.task-detail {
  max-width: 1000px;
}

.error-detail-box {
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 16px;
  max-height: 400px;
  overflow: auto;
}

.error-detail-box pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  line-height: 1.6;
  color: #c45656;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}
</style>
