<template>
  <div class="tasks-page">
    <t-card>
      <template #actions>
        <t-button theme="primary" @click="$router.push('/insights/upload')">
          <template #icon><AddIcon /></template>
          新建分析
        </t-button>
      </template>
      
      <t-table
        :data="tasks"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        row-key="task_id"
        hover
        @page-change="handlePageChange"
      >
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)">
            {{ getStatusLabel(row.status) }}
          </t-tag>
        </template>
        <template #log_file_size="{ row }">
          {{ formatFileSize(row.log_file_size) }}
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">详情</t-link>
            <t-popconfirm content="确定删除？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon } from 'tdesign-icons-vue-next'
import { insightsApi } from '../../api/v2'

const router = useRouter()

// 数据
const tasks = ref<any[]>([])
const loading = ref(false)

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 表格列
const columns = [
  { colKey: 'task_id', title: '任务ID', width: 100 },
  { colKey: 'name', title: '任务名称', ellipsis: true },
  { colKey: 'log_file_path', title: '文件路径', width: 250, ellipsis: true },
  { colKey: 'log_file_size', title: '文件大小', width: 100 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'op', title: '操作', width: 120 }
]

// 加载数据
const loadTasks = async () => {
  loading.value = true
  try {
    const res = await insightsApi.listTasks({
      page: pagination.current,
      page_size: pagination.pageSize
    })
    tasks.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载任务列表失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadTasks()
}

// 查看详情
const handleView = (row: any) => {
  router.push(`/insights/tasks/${row.task_id}`)
}

// 删除
const handleDelete = async (row: any) => {
  try {
    await insightsApi.deleteTask(row.task_id)
    MessagePlugin.success('删除成功')
    loadTasks()
  } catch (error) {
    console.error('删除失败:', error)
  }
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
</script>

<style scoped>
.tasks-page {
  max-width: 1200px;
}
</style>
