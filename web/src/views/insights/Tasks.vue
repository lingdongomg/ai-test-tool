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
        <template #name="{ row }">
          <div class="task-name">
            <t-tag 
              :theme="getTypeTheme(row.name)" 
              variant="light" 
              size="small"
              style="margin-right: 8px;"
            >
              {{ getTypeLabel(row.name) }}
            </t-tag>
            <span>{{ row.name }}</span>
          </div>
        </template>
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)">
            {{ getStatusLabel(row.status) }}
          </t-tag>
        </template>
        <template #total_requests="{ row }">
          {{ row.total_requests || '-' }}
        </template>
        <template #log_file_size="{ row }">
          {{ formatFileSize(row.log_file_size) }}
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">详情</t-link>
            <t-link 
              v-if="isRequestType(row.name) && row.status === 'completed' && row.total_requests > 0" 
              theme="primary" 
              @click="handleExtract(row)"
            >
              提取监控
            </t-link>
            <t-popconfirm content="确定删除？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 提取监控对话框 -->
    <t-dialog
      v-model:visible="extractDialogVisible"
      header="提取监控用例"
      :confirm-btn="{ content: '提取', loading: extracting }"
      @confirm="confirmExtract"
    >
      <t-form :data="extractForm" label-width="120px">
        <t-form-item label="任务ID">
          <t-input v-model="extractForm.task_id" disabled />
        </t-form-item>
        <t-form-item label="最小成功率">
          <div style="display: flex; align-items: center; width: 100%;">
            <t-slider v-model="extractForm.min_success_rate" :min="0" :max="1" :step="0.1" style="flex: 1;" />
            <span style="margin-left: 8px; min-width: 40px;">{{ (extractForm.min_success_rate * 100).toFixed(0) }}%</span>
          </div>
        </t-form-item>
        <t-form-item label="每接口最大数">
          <t-input-number v-model="extractForm.max_requests_per_endpoint" :min="1" :max="20" />
        </t-form-item>
        <t-form-item label="添加标签">
          <t-input v-model="extractForm.tags_str" placeholder="多个标签用逗号分隔" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon } from 'tdesign-icons-vue-next'
import { insightsApi, monitoringApi } from '../../api/v2'

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

// 提取对话框
const extractDialogVisible = ref(false)
const extracting = ref(false)
const extractForm = reactive({
  task_id: '',
  min_success_rate: 0.9,
  max_requests_per_endpoint: 5,
  tags_str: ''
})

// 表格列
const columns = [
  { colKey: 'task_id', title: '任务ID', width: 100 },
  { colKey: 'name', title: '任务名称', ellipsis: true },
  { colKey: 'total_requests', title: '请求数', width: 80 },
  { colKey: 'log_file_size', title: '文件大小', width: 100 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'op', title: '操作', width: 180 }
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

// 提取监控
const handleExtract = (row: any) => {
  extractForm.task_id = row.task_id
  extractForm.min_success_rate = 0.9
  extractForm.max_requests_per_endpoint = 5
  extractForm.tags_str = ''
  extractDialogVisible.value = true
}

const confirmExtract = async () => {
  extracting.value = true
  try {
    const tags = extractForm.tags_str ? extractForm.tags_str.split(',').map(t => t.trim()).filter(t => t) : undefined
    const res = await monitoringApi.extractFromLog({
      task_id: extractForm.task_id,
      min_success_rate: extractForm.min_success_rate,
      max_requests_per_endpoint: extractForm.max_requests_per_endpoint,
      tags
    })
    MessagePlugin.success(res.message || '提取成功')
    extractDialogVisible.value = false
  } catch (error) {
    console.error('提取失败:', error)
  } finally {
    extracting.value = false
  }
}

// 辅助函数
const isRequestType = (name: string) => {
  return name?.startsWith('请求提取')
}

const getTypeLabel = (name: string) => {
  return name?.startsWith('请求提取') ? '请求提取' : '异常检测'
}

const getTypeTheme = (name: string) => {
  return name?.startsWith('请求提取') ? 'primary' : 'warning'
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

.task-name {
  display: flex;
  align-items: center;
}
</style>
