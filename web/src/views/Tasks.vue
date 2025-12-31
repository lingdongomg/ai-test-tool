<template>
  <div class="tasks-page">
    <!-- 操作栏 -->
    <t-card :bordered="false" class="mb-4">
      <div class="flex justify-between items-center">
        <div class="flex gap-4">
          <t-button theme="primary" @click="showUploadDialog = true">
            <template #icon><UploadIcon /></template>
            上传日志文件
          </t-button>
          <t-button variant="outline" @click="showContentDialog = true">
            <template #icon><EditIcon /></template>
            粘贴日志内容
          </t-button>
        </div>
        <div class="flex gap-4 items-center">
          <t-select
            v-model="statusFilter"
            placeholder="状态筛选"
            clearable
            style="width: 150px"
            @change="loadTasks"
          >
            <t-option value="pending" label="等待中" />
            <t-option value="running" label="运行中" />
            <t-option value="completed" label="已完成" />
            <t-option value="failed" label="失败" />
          </t-select>
          <t-button variant="outline" @click="loadTasks">
            <template #icon><RefreshIcon /></template>
            刷新
          </t-button>
        </div>
      </div>
    </t-card>

    <!-- 任务列表 -->
    <t-card :bordered="false">
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
          <t-tag :theme="getStatusTheme(row.status)" variant="light">
            <template #icon>
              <LoadingIcon v-if="row.status === 'running'" class="animate-spin" />
              <CheckCircleIcon v-else-if="row.status === 'completed'" />
              <CloseCircleIcon v-else-if="row.status === 'failed'" />
              <TimeIcon v-else />
            </template>
            {{ getStatusText(row.status) }}
          </t-tag>
        </template>
        
        <template #progress="{ row }">
          <div v-if="row.total_lines > 0" class="flex items-center gap-2">
            <t-progress
              :percentage="Math.round((row.processed_lines / row.total_lines) * 100)"
              :status="row.status === 'failed' ? 'error' : row.status === 'completed' ? 'success' : 'active'"
              size="small"
              style="width: 120px"
            />
            <span class="text-xs text-gray-500">
              {{ row.processed_lines }}/{{ row.total_lines }}
            </span>
          </div>
          <span v-else class="text-gray-400">-</span>
        </template>

        <template #statistics="{ row }">
          <div class="flex gap-3 text-sm">
            <span v-if="row.total_requests" class="text-blue-600">
              <ApiIcon class="inline mr-1" />{{ row.total_requests }} 请求
            </span>
            <span v-if="row.total_test_cases" class="text-green-600">
              <TaskIcon class="inline mr-1" />{{ row.total_test_cases }} 用例
            </span>
            <span v-if="!row.total_requests && !row.total_test_cases" class="text-gray-400">-</span>
          </div>
        </template>

        <template #created_at="{ row }">
          <span class="text-gray-600">{{ formatTime(row.created_at) }}</span>
        </template>

        <template #operation="{ row }">
          <t-space size="small">
            <t-button theme="primary" variant="text" size="small" @click="goToDetail(row)">
              <template #icon><BrowseIcon /></template>
              详情
            </t-button>
            <t-button 
              v-if="row.status === 'completed'" 
              theme="success" 
              variant="text" 
              size="small" 
              @click="showRunTestDialog(row)"
            >
              <template #icon><PlayIcon /></template>
              执行测试
            </t-button>
            <t-button 
              v-if="row.status === 'running'" 
              theme="warning" 
              variant="text" 
              size="small" 
              @click="cancelTask(row)"
            >
              <template #icon><StopIcon /></template>
              取消
            </t-button>
            <t-popconfirm
              content="确定删除该任务及所有相关数据？"
              @confirm="deleteTask(row)"
            >
              <t-button theme="danger" variant="text" size="small">
                <template #icon><DeleteIcon /></template>
                删除
              </t-button>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 上传文件对话框 -->
    <t-dialog
      v-model:visible="showUploadDialog"
      header="上传日志文件"
      :confirm-btn="{ content: '开始分析', loading: uploading }"
      :cancel-btn="{ content: '取消' }"
      width="600px"
      @confirm="handleUpload"
    >
      <t-form :data="uploadForm" label-width="100px">
        <t-form-item label="任务名称">
          <t-input v-model="uploadForm.name" placeholder="可选，默认使用文件名" />
        </t-form-item>
        <t-form-item label="日志文件" required>
          <t-upload
            v-model="uploadForm.files"
            theme="file"
            accept=".json,.log,.txt"
            :max="1"
            :auto-upload="false"
          >
            <t-button variant="outline">
              <template #icon><UploadIcon /></template>
              选择文件
            </t-button>
          </t-upload>
          <div class="text-xs text-gray-500 mt-2">支持 .json, .log, .txt 格式</div>
        </t-form-item>
        <t-form-item label="最大行数">
          <t-input-number v-model="uploadForm.max_lines" :min="100" :max="100000" :step="1000" />
          <span class="text-xs text-gray-500 ml-2">限制解析的日志行数</span>
        </t-form-item>
        <t-form-item label="测试策略">
          <t-radio-group v-model="uploadForm.test_strategy">
            <t-radio value="comprehensive">全面测试</t-radio>
            <t-radio value="quick">快速测试</t-radio>
            <t-radio value="security">安全测试</t-radio>
          </t-radio-group>
        </t-form-item>
        <t-form-item label="执行模式">
          <t-switch v-model="uploadForm.async_mode">
            <template #label="{ value }">{{ value ? '异步执行' : '同步等待' }}</template>
          </t-switch>
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 粘贴内容对话框 -->
    <t-dialog
      v-model:visible="showContentDialog"
      header="粘贴日志内容"
      :confirm-btn="{ content: '开始分析', loading: analyzing }"
      :cancel-btn="{ content: '取消' }"
      width="700px"
      @confirm="handleAnalyzeContent"
    >
      <t-form :data="contentForm" label-width="100px">
        <t-form-item label="任务名称">
          <t-input v-model="contentForm.name" placeholder="可选" />
        </t-form-item>
        <t-form-item label="日志内容" required>
          <t-textarea
            v-model="contentForm.log_content"
            placeholder="粘贴日志内容，支持 JSON 数组或多行日志格式"
            :autosize="{ minRows: 10, maxRows: 20 }"
          />
        </t-form-item>
        <t-form-item label="测试策略">
          <t-radio-group v-model="contentForm.test_strategy">
            <t-radio value="comprehensive">全面测试</t-radio>
            <t-radio value="quick">快速测试</t-radio>
            <t-radio value="security">安全测试</t-radio>
          </t-radio-group>
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 执行测试对话框 -->
    <t-dialog
      v-model:visible="showTestDialog"
      header="执行测试"
      :confirm-btn="{ content: '开始测试', loading: testing }"
      :cancel-btn="{ content: '取消' }"
      width="500px"
      @confirm="handleRunTests"
    >
      <t-form :data="testForm" label-width="100px">
        <t-form-item label="目标 URL" required>
          <t-input v-model="testForm.base_url" placeholder="http://your-api.com" />
        </t-form-item>
        <t-form-item label="并发数">
          <t-input-number v-model="testForm.concurrent" :min="1" :max="20" />
        </t-form-item>
        <t-form-item label="执行模式">
          <t-switch v-model="testForm.async_mode">
            <template #label="{ value }">{{ value ? '异步执行' : '同步等待' }}</template>
          </t-switch>
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 任务详情抽屉 -->
    <t-drawer
      v-model:visible="showDetailDrawer"
      header="任务详情"
      size="large"
    >
      <template v-if="currentTask">
        <t-descriptions :column="2" bordered>
          <t-descriptions-item label="任务ID">
            <code>{{ currentTask.task_id }}</code>
          </t-descriptions-item>
          <t-descriptions-item label="任务名称">{{ currentTask.name || '-' }}</t-descriptions-item>
          <t-descriptions-item label="状态">
            <t-tag :theme="getStatusTheme(currentTask.status)" variant="light">
              {{ getStatusText(currentTask.status) }}
            </t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="日志文件">{{ currentTask.log_file_path || '-' }}</t-descriptions-item>
          <t-descriptions-item label="文件大小">
            {{ currentTask.log_file_size ? formatFileSize(currentTask.log_file_size) : '-' }}
          </t-descriptions-item>
          <t-descriptions-item label="总行数">{{ currentTask.total_lines || '-' }}</t-descriptions-item>
          <t-descriptions-item label="已处理">{{ currentTask.processed_lines || '-' }}</t-descriptions-item>
          <t-descriptions-item label="请求数">{{ currentTask.total_requests || '-' }}</t-descriptions-item>
          <t-descriptions-item label="测试用例">{{ currentTask.total_test_cases || '-' }}</t-descriptions-item>
          <t-descriptions-item label="创建时间">{{ formatTime(currentTask.created_at) }}</t-descriptions-item>
          <t-descriptions-item label="开始时间">{{ formatTime(currentTask.started_at) }}</t-descriptions-item>
          <t-descriptions-item label="完成时间">{{ formatTime(currentTask.completed_at) }}</t-descriptions-item>
        </t-descriptions>

        <t-divider>任务结果</t-divider>

        <div v-if="taskResult">
          <!-- 分析统计 -->
          <t-card v-if="taskResult.analysis" title="请求分析" class="mb-4" :bordered="false">
            <div class="grid grid-cols-4 gap-4">
              <t-statistic title="总请求数" :value="taskResult.analysis.total_requests || 0" />
              <t-statistic title="成功请求" :value="taskResult.analysis.success_count || 0" theme="success" />
              <t-statistic title="错误请求" :value="taskResult.analysis.error_count || 0" theme="danger" />
              <t-statistic title="成功率" :value="taskResult.analysis.success_rate || '0%'" />
            </div>
          </t-card>

          <!-- 验证结果 -->
          <t-card v-if="taskResult.validation" title="测试验证" class="mb-4" :bordered="false">
            <div class="grid grid-cols-5 gap-4">
              <t-statistic title="总用例" :value="taskResult.validation.total || 0" />
              <t-statistic title="通过" :value="taskResult.validation.passed || 0" theme="success" />
              <t-statistic title="失败" :value="taskResult.validation.failed || 0" theme="danger" />
              <t-statistic title="错误" :value="taskResult.validation.errors || 0" theme="warning" />
              <t-statistic title="通过率" :value="taskResult.validation.pass_rate || '0%'" />
            </div>
          </t-card>

          <!-- 报告列表 -->
          <t-card v-if="taskResult.reports_saved?.length" title="生成报告" :bordered="false">
            <t-tag v-for="report in taskResult.reports_saved" :key="report" class="mr-2 mb-2">
              {{ report }}
            </t-tag>
          </t-card>

          <!-- 错误信息 -->
          <t-alert v-if="taskResult.error_message" theme="error" :message="taskResult.error_message" class="mt-4" />
        </div>
        <div v-else class="text-center text-gray-500 py-8">
          <t-button @click="loadTaskResult">加载任务结果</t-button>
        </div>
      </template>
    </t-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { 
  UploadIcon, 
  EditIcon, 
  RefreshIcon, 
  BrowseIcon, 
  PlayIcon, 
  StopIcon, 
  DeleteIcon,
  CheckCircleIcon,
  CloseCircleIcon,
  TimeIcon,
  LoadingIcon,
  ApiIcon,
  TaskIcon
} from 'tdesign-icons-vue-next'
import { taskApi } from '@/api'

const router = useRouter()

interface Task {
  task_id: string
  name: string
  status: string
  log_file_path?: string
  log_file_size?: number
  total_lines?: number
  processed_lines?: number
  total_requests?: number
  total_test_cases?: number
  error_message?: string
  created_at?: string
  started_at?: string
  completed_at?: string
}

interface TaskResult {
  task_id: string
  status: string
  parsed_requests?: number
  test_cases?: number
  test_results?: number
  analysis?: {
    total_requests: number
    success_count: number
    error_count: number
    success_rate: string
  }
  validation?: {
    total: number
    passed: number
    failed: number
    errors: number
    pass_rate: string
  }
  reports_saved?: string[]
  error_message?: string
}

const loading = ref(false)
const tasks = ref<Task[]>([])
const statusFilter = ref('')
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 对话框状态
const showUploadDialog = ref(false)
const showContentDialog = ref(false)
const showTestDialog = ref(false)
const showDetailDrawer = ref(false)

// 加载状态
const uploading = ref(false)
const analyzing = ref(false)
const testing = ref(false)

// 当前任务
const currentTask = ref<Task | null>(null)
const taskResult = ref<TaskResult | null>(null)
const currentTaskId = ref('')

// 表单数据
const uploadForm = reactive({
  name: '',
  files: [] as any[],
  max_lines: 10000,
  test_strategy: 'comprehensive',
  async_mode: true
})

const contentForm = reactive({
  name: '',
  log_content: '',
  test_strategy: 'comprehensive',
  async_mode: true
})

const testForm = reactive({
  base_url: '',
  concurrent: 5,
  async_mode: true
})

// 表格列定义
const columns = [
  { colKey: 'name', title: '任务名称', width: 200, ellipsis: true },
  { colKey: 'status', title: '状态', width: 120 },
  { colKey: 'progress', title: '进度', width: 200 },
  { colKey: 'statistics', title: '统计', width: 200 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'operation', title: '操作', width: 280, fixed: 'right' }
]

// 自动刷新
let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  loadTasks()
  // 每10秒自动刷新
  refreshTimer = setInterval(() => {
    if (tasks.value.some(t => t.status === 'running' || t.status === 'pending')) {
      loadTasks()
    }
  }, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})

async function loadTasks() {
  loading.value = true
  try {
    const res: any = await taskApi.list({
      status: statusFilter.value || undefined,
      offset: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize
    })
    tasks.value = res.items || []
    pagination.total = res.total || 0
  } catch (error: any) {
    MessagePlugin.error('加载任务列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function handlePageChange({ current, pageSize }: { current: number; pageSize: number }) {
  pagination.current = current
  pagination.pageSize = pageSize
  loadTasks()
}

async function handleUpload() {
  if (!uploadForm.files.length) {
    MessagePlugin.warning('请选择日志文件')
    return
  }
  
  uploading.value = true
  try {
    const file = uploadForm.files[0].raw || uploadForm.files[0]
    await taskApi.uploadFile(file, {
      name: uploadForm.name || undefined,
      max_lines: uploadForm.max_lines,
      test_strategy: uploadForm.test_strategy,
      async_mode: uploadForm.async_mode
    })
    MessagePlugin.success('任务创建成功')
    showUploadDialog.value = false
    resetUploadForm()
    loadTasks()
  } catch (error: any) {
    MessagePlugin.error('上传失败: ' + (error.message || '未知错误'))
  } finally {
    uploading.value = false
  }
}

async function handleAnalyzeContent() {
  if (!contentForm.log_content.trim()) {
    MessagePlugin.warning('请输入日志内容')
    return
  }
  
  analyzing.value = true
  try {
    await taskApi.analyzeContent({
      log_content: contentForm.log_content,
      name: contentForm.name || undefined,
      test_strategy: contentForm.test_strategy,
      async_mode: contentForm.async_mode
    })
    MessagePlugin.success('任务创建成功')
    showContentDialog.value = false
    resetContentForm()
    loadTasks()
  } catch (error: any) {
    MessagePlugin.error('分析失败: ' + (error.message || '未知错误'))
  } finally {
    analyzing.value = false
  }
}

function showRunTestDialog(task: Task) {
  currentTaskId.value = task.task_id
  testForm.base_url = ''
  testForm.concurrent = 5
  testForm.async_mode = true
  showTestDialog.value = true
}

async function handleRunTests() {
  if (!testForm.base_url.trim()) {
    MessagePlugin.warning('请输入目标 URL')
    return
  }
  
  testing.value = true
  try {
    await taskApi.runTests(currentTaskId.value, {
      base_url: testForm.base_url,
      concurrent: testForm.concurrent,
      async_mode: testForm.async_mode
    })
    MessagePlugin.success('测试已启动')
    showTestDialog.value = false
    loadTasks()
  } catch (error: any) {
    MessagePlugin.error('执行测试失败: ' + (error.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

async function viewTask(task: Task) {
  currentTask.value = task
  taskResult.value = null
  showDetailDrawer.value = true
  await loadTaskResult()
}

function goToDetail(task: Task) {
  router.push({ name: 'TaskDetail', params: { id: task.task_id } })
}

async function loadTaskResult() {
  if (!currentTask.value) return
  
  try {
    const res: any = await taskApi.getResult(currentTask.value.task_id)
    taskResult.value = res
  } catch (error: any) {
    console.error('加载任务结果失败:', error)
  }
}

async function cancelTask(task: Task) {
  try {
    await taskApi.cancel(task.task_id)
    MessagePlugin.success('任务已取消')
    loadTasks()
  } catch (error: any) {
    MessagePlugin.error('取消失败: ' + (error.message || '未知错误'))
  }
}

async function deleteTask(task: Task) {
  try {
    await taskApi.delete(task.task_id)
    MessagePlugin.success('任务已删除')
    loadTasks()
  } catch (error: any) {
    MessagePlugin.error('删除失败: ' + (error.message || '未知错误'))
  }
}

function resetUploadForm() {
  uploadForm.name = ''
  uploadForm.files = []
  uploadForm.max_lines = 10000
  uploadForm.test_strategy = 'comprehensive'
  uploadForm.async_mode = true
}

function resetContentForm() {
  contentForm.name = ''
  contentForm.log_content = ''
  contentForm.test_strategy = 'comprehensive'
  contentForm.async_mode = true
}

function getStatusTheme(status: string) {
  const themes: Record<string, string> = {
    pending: 'default',
    running: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return themes[status] || 'default'
}

function getStatusText(status: string) {
  const texts: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

function formatTime(time?: string) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.tasks-page {
  max-width: 1400px;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
