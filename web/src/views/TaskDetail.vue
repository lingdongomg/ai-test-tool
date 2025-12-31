<template>
  <div class="task-detail-page">
    <!-- 返回按钮和标题 -->
    <div class="flex items-center gap-4 mb-4">
      <t-button variant="text" @click="goBack">
        <template #icon><ChevronLeftIcon /></template>
        返回
      </t-button>
      <h2 class="text-xl font-semibold">{{ task?.name || '任务详情' }}</h2>
      <t-tag :theme="getStatusTheme(task?.status)" variant="light" size="large">
        <template #icon>
          <LoadingIcon v-if="task?.status === 'running'" class="animate-spin" />
          <CheckCircleIcon v-else-if="task?.status === 'completed'" />
          <CloseCircleIcon v-else-if="task?.status === 'failed'" />
          <TimeIcon v-else />
        </template>
        {{ getStatusText(task?.status) }}
      </t-tag>
    </div>

    <t-loading :loading="loading" text="加载中...">
      <div v-if="task" class="grid grid-cols-3 gap-4">
        <!-- 左侧：基本信息 -->
        <div class="col-span-2 space-y-4">
          <!-- 基本信息卡片 -->
          <t-card title="基本信息" :bordered="false">
            <t-descriptions :column="2">
              <t-descriptions-item label="任务ID">
                <code class="bg-gray-100 px-2 py-1 rounded text-sm">{{ task.task_id }}</code>
                <t-button variant="text" size="small" @click="copyToClipboard(task.task_id)">
                  <template #icon><FileCopyIcon /></template>
                </t-button>
              </t-descriptions-item>
              <t-descriptions-item label="任务名称">{{ task.name || '-' }}</t-descriptions-item>
              <t-descriptions-item label="日志文件">{{ task.log_file_path || '-' }}</t-descriptions-item>
              <t-descriptions-item label="文件大小">
                {{ task.log_file_size ? formatFileSize(task.log_file_size) : '-' }}
              </t-descriptions-item>
              <t-descriptions-item label="创建时间">{{ formatTime(task.created_at) }}</t-descriptions-item>
              <t-descriptions-item label="开始时间">{{ formatTime(task.started_at) }}</t-descriptions-item>
              <t-descriptions-item label="完成时间">{{ formatTime(task.completed_at) }}</t-descriptions-item>
              <t-descriptions-item label="耗时">{{ calculateDuration() }}</t-descriptions-item>
            </t-descriptions>
          </t-card>

          <!-- 处理进度 -->
          <t-card title="处理进度" :bordered="false">
            <div class="space-y-4">
              <div>
                <div class="flex justify-between mb-2">
                  <span>日志解析</span>
                  <span>{{ task.processed_lines || 0 }} / {{ task.total_lines || 0 }} 行</span>
                </div>
                <t-progress
                  :percentage="task.total_lines ? Math.round((task.processed_lines || 0) / task.total_lines * 100) : 0"
                  :status="task.status === 'failed' ? 'error' : task.status === 'completed' ? 'success' : 'active'"
                />
              </div>
              
              <t-divider />
              
              <div class="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div class="text-3xl font-bold text-blue-600">{{ task.total_requests || 0 }}</div>
                  <div class="text-gray-500 mt-1">解析请求数</div>
                </div>
                <div>
                  <div class="text-3xl font-bold text-green-600">{{ task.total_test_cases || 0 }}</div>
                  <div class="text-gray-500 mt-1">测试用例数</div>
                </div>
                <div>
                  <div class="text-3xl font-bold text-purple-600">{{ taskResult?.test_results || 0 }}</div>
                  <div class="text-gray-500 mt-1">测试结果数</div>
                </div>
              </div>
            </div>
          </t-card>

          <!-- 分析结果 -->
          <t-card v-if="taskResult?.analysis" title="请求分析" :bordered="false">
            <div class="grid grid-cols-4 gap-4">
              <t-statistic title="总请求数" :value="taskResult.analysis.total_requests" />
              <t-statistic title="成功请求" :value="taskResult.analysis.success_count" theme="success" />
              <t-statistic title="错误请求" :value="taskResult.analysis.error_count" theme="danger" />
              <t-statistic title="成功率" :value="taskResult.analysis.success_rate" />
            </div>
          </t-card>

          <!-- 测试验证结果 -->
          <t-card v-if="taskResult?.validation" title="测试验证" :bordered="false">
            <div class="grid grid-cols-5 gap-4 mb-4">
              <t-statistic title="总用例" :value="taskResult.validation.total" />
              <t-statistic title="通过" :value="taskResult.validation.passed" theme="success" />
              <t-statistic title="失败" :value="taskResult.validation.failed" theme="danger" />
              <t-statistic title="错误" :value="taskResult.validation.errors" theme="warning" />
              <t-statistic title="通过率" :value="taskResult.validation.pass_rate" />
            </div>
            
            <!-- 饼图展示 -->
            <div class="h-64">
              <v-chart :option="validationChartOption" autoresize />
            </div>
          </t-card>

          <!-- 错误信息 -->
          <t-alert 
            v-if="task.error_message" 
            theme="error" 
            :message="task.error_message"
            title="错误信息"
          />
        </div>

        <!-- 右侧：操作面板 -->
        <div class="space-y-4">
          <!-- 快捷操作 -->
          <t-card title="操作" :bordered="false">
            <div class="space-y-3">
              <t-button 
                v-if="task.status === 'completed'" 
                theme="primary" 
                block 
                @click="showTestDialog = true"
              >
                <template #icon><PlayIcon /></template>
                执行测试
              </t-button>
              
              <t-button 
                v-if="task.status === 'completed'" 
                variant="outline" 
                block 
                @click="showGenerateDialog = true"
              >
                <template #icon><AddIcon /></template>
                生成测试用例
              </t-button>
              
              <t-button 
                v-if="task.status === 'running'" 
                theme="warning" 
                variant="outline"
                block 
                @click="cancelTask"
              >
                <template #icon><StopIcon /></template>
                取消任务
              </t-button>
              
              <t-button variant="outline" block @click="refreshTask">
                <template #icon><RefreshIcon /></template>
                刷新状态
              </t-button>
              
              <t-divider />
              
              <t-popconfirm
                content="确定删除该任务及所有相关数据？"
                @confirm="deleteTask"
              >
                <t-button theme="danger" variant="outline" block>
                  <template #icon><DeleteIcon /></template>
                  删除任务
                </t-button>
              </t-popconfirm>
            </div>
          </t-card>

          <!-- 生成的报告 -->
          <t-card v-if="taskResult?.reports_saved?.length" title="生成报告" :bordered="false">
            <div class="space-y-2">
              <div 
                v-for="report in taskResult.reports_saved" 
                :key="report"
                class="flex items-center justify-between p-2 bg-gray-50 rounded"
              >
                <span class="text-sm">{{ report }}</span>
                <t-button variant="text" size="small">
                  <template #icon><BrowseIcon /></template>
                </t-button>
              </div>
            </div>
          </t-card>

          <!-- 时间线 -->
          <t-card title="执行时间线" :bordered="false">
            <t-timeline>
              <t-timeline-item v-if="task.created_at" label="创建任务">
                {{ formatTime(task.created_at) }}
              </t-timeline-item>
              <t-timeline-item v-if="task.started_at" label="开始执行" theme="primary">
                {{ formatTime(task.started_at) }}
              </t-timeline-item>
              <t-timeline-item 
                v-if="task.completed_at" 
                :label="task.status === 'completed' ? '执行完成' : '执行失败'"
                :theme="task.status === 'completed' ? 'success' : 'error'"
              >
                {{ formatTime(task.completed_at) }}
              </t-timeline-item>
              <t-timeline-item 
                v-if="task.status === 'running'" 
                label="执行中..." 
                theme="primary"
                :dot="LoadingIcon"
              />
            </t-timeline>
          </t-card>
        </div>
      </div>

      <t-result v-else status="404" title="任务不存在" description="请检查任务ID是否正确">
        <template #extra>
          <t-button theme="primary" @click="goBack">返回任务列表</t-button>
        </template>
      </t-result>
    </t-loading>

    <!-- 执行测试对话框 -->
    <t-dialog
      v-model:visible="showTestDialog"
      header="执行测试"
      :confirm-btn="{ content: '开始测试', loading: testing }"
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

    <!-- 生成测试用例对话框 -->
    <t-dialog
      v-model:visible="showGenerateDialog"
      header="生成测试用例"
      :confirm-btn="{ content: '开始生成', loading: generating }"
      width="500px"
      @confirm="handleGenerateCases"
    >
      <t-form :data="generateForm" label-width="100px">
        <t-form-item label="测试策略">
          <t-radio-group v-model="generateForm.test_strategy">
            <t-radio value="comprehensive">全面测试</t-radio>
            <t-radio value="quick">快速测试</t-radio>
            <t-radio value="security">安全测试</t-radio>
          </t-radio-group>
        </t-form-item>
        <t-form-item label="执行模式">
          <t-switch v-model="generateForm.async_mode">
            <template #label="{ value }">{{ value ? '异步执行' : '同步等待' }}</template>
          </t-switch>
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import VChart from 'vue-echarts'
import { 
  ChevronLeftIcon,
  CheckCircleIcon,
  CloseCircleIcon,
  TimeIcon,
  LoadingIcon,
  FileCopyIcon,
  PlayIcon,
  AddIcon,
  StopIcon,
  RefreshIcon,
  DeleteIcon,
  BrowseIcon
} from 'tdesign-icons-vue-next'
import { taskApi } from '@/api'

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

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const task = ref<Task | null>(null)
const taskResult = ref<TaskResult | null>(null)

// 对话框状态
const showTestDialog = ref(false)
const showGenerateDialog = ref(false)
const testing = ref(false)
const generating = ref(false)

// 表单数据
const testForm = reactive({
  base_url: '',
  concurrent: 5,
  async_mode: true
})

const generateForm = reactive({
  test_strategy: 'comprehensive',
  async_mode: true
})

// 自动刷新
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 验证结果饼图配置
const validationChartOption = computed(() => {
  if (!taskResult.value?.validation) return {}
  
  const v = taskResult.value.validation
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%', left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 16, fontWeight: 'bold' }
      },
      labelLine: { show: false },
      data: [
        { value: v.passed, name: '通过', itemStyle: { color: '#52c41a' } },
        { value: v.failed, name: '失败', itemStyle: { color: '#ff4d4f' } },
        { value: v.errors, name: '错误', itemStyle: { color: '#faad14' } }
      ]
    }]
  }
})

onMounted(async () => {
  await loadTask()
  
  // 如果任务正在运行，启动自动刷新
  if (task.value?.status === 'running' || task.value?.status === 'pending') {
    refreshTimer = setInterval(loadTask, 5000)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})

async function loadTask() {
  const taskId = route.params.id as string
  if (!taskId) {
    loading.value = false
    return
  }
  
  try {
    const res: any = await taskApi.get(taskId)
    task.value = res
    
    // 加载任务结果
    if (res.status === 'completed' || res.status === 'failed') {
      const resultRes: any = await taskApi.getResult(taskId)
      taskResult.value = resultRes
      
      // 停止自动刷新
      if (refreshTimer) {
        clearInterval(refreshTimer)
        refreshTimer = null
      }
    }
  } catch (error: any) {
    console.error('加载任务失败:', error)
    task.value = null
  } finally {
    loading.value = false
  }
}

async function refreshTask() {
  await loadTask()
  MessagePlugin.success('刷新成功')
}

async function handleRunTests() {
  if (!testForm.base_url.trim()) {
    MessagePlugin.warning('请输入目标 URL')
    return
  }
  
  testing.value = true
  try {
    await taskApi.runTests(task.value!.task_id, {
      base_url: testForm.base_url,
      concurrent: testForm.concurrent,
      async_mode: testForm.async_mode
    })
    MessagePlugin.success('测试已启动')
    showTestDialog.value = false
    await loadTask()
  } catch (error: any) {
    MessagePlugin.error('执行测试失败: ' + (error.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

async function handleGenerateCases() {
  generating.value = true
  try {
    await taskApi.generateCases(task.value!.task_id, {
      test_strategy: generateForm.test_strategy,
      async_mode: generateForm.async_mode
    })
    MessagePlugin.success('测试用例生成已启动')
    showGenerateDialog.value = false
    await loadTask()
  } catch (error: any) {
    MessagePlugin.error('生成失败: ' + (error.message || '未知错误'))
  } finally {
    generating.value = false
  }
}

async function cancelTask() {
  try {
    await taskApi.cancel(task.value!.task_id)
    MessagePlugin.success('任务已取消')
    await loadTask()
  } catch (error: any) {
    MessagePlugin.error('取消失败: ' + (error.message || '未知错误'))
  }
}

async function deleteTask() {
  try {
    await taskApi.delete(task.value!.task_id)
    MessagePlugin.success('任务已删除')
    goBack()
  } catch (error: any) {
    MessagePlugin.error('删除失败: ' + (error.message || '未知错误'))
  }
}

function goBack() {
  router.push({ name: 'Tasks' })
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  MessagePlugin.success('已复制到剪贴板')
}

function getStatusTheme(status?: string) {
  const themes: Record<string, string> = {
    pending: 'default',
    running: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return themes[status || ''] || 'default'
}

function getStatusText(status?: string) {
  const texts: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status || ''] || status || '-'
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

function calculateDuration() {
  if (!task.value?.started_at) return '-'
  
  const start = new Date(task.value.started_at).getTime()
  const end = task.value.completed_at 
    ? new Date(task.value.completed_at).getTime() 
    : Date.now()
  
  const duration = Math.round((end - start) / 1000)
  
  if (duration < 60) return `${duration} 秒`
  if (duration < 3600) return `${Math.floor(duration / 60)} 分 ${duration % 60} 秒`
  return `${Math.floor(duration / 3600)} 小时 ${Math.floor((duration % 3600) / 60)} 分`
}
</script>

<style scoped>
.task-detail-page {
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
