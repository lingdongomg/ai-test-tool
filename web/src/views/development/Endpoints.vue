<template>
  <div class="endpoints-page">
    <!-- 统计卡片 -->
    <t-row :gutter="[16, 16]" class="stats-row">
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ statistics.endpoints?.total || 0 }}</div>
            <div class="stat-label">接口总数</div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ statistics.test_cases?.total || 0 }}</div>
            <div class="stat-label">测试用例</div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ statistics.coverage?.coverage_rate || 0 }}%</div>
            <div class="stat-label">覆盖率</div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ statistics.recent_executions?.pass_rate || 0 }}%</div>
            <div class="stat-label">近7天通过率</div>
          </div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 工具栏 -->
    <t-card class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <t-input
            v-model="searchText"
            placeholder="搜索接口路径或描述"
            clearable
            style="width: 280px;"
            @enter="handleSearch"
          >
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-select
            v-model="methodFilter"
            placeholder="HTTP方法"
            clearable
            style="width: 120px;"
            @change="handleSearch"
          >
            <t-option value="GET">GET</t-option>
            <t-option value="POST">POST</t-option>
            <t-option value="PUT">PUT</t-option>
            <t-option value="DELETE">DELETE</t-option>
            <t-option value="PATCH">PATCH</t-option>
          </t-select>
          <t-select
            v-model="hasTestsFilter"
            placeholder="测试状态"
            clearable
            style="width: 120px;"
            @change="handleSearch"
          >
            <t-option :value="true">有测试用例</t-option>
            <t-option :value="false">无测试用例</t-option>
          </t-select>
        </div>
        <div class="toolbar-right">
          <t-button theme="primary" @click="handleBatchGenerate" :disabled="!selectedIds.length">
            <template #icon><AddIcon /></template>
            批量生成测试
          </t-button>
          <t-button @click="$router.push('/import')">
            <template #icon><FileImportIcon /></template>
            导入文档
          </t-button>
        </div>
      </div>
    </t-card>

    <!-- 接口列表 -->
    <t-card class="table-card">
      <t-table
        :data="endpoints"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        :selected-row-keys="selectedIds"
        row-key="endpoint_id"
        hover
        @page-change="handlePageChange"
        @select-change="handleSelectChange"
      >
        <template #method="{ row }">
          <t-tag :theme="getMethodTheme(row.method)" variant="light">
            {{ row.method }}
          </t-tag>
        </template>
        <template #path="{ row }">
          <div class="path-cell">
            <span class="path-text">{{ row.path }}</span>
            <span class="path-desc" v-if="row.description">{{ row.description }}</span>
          </div>
        </template>
        <template #test_case_count="{ row }">
          <t-tag v-if="row.test_case_count > 0" theme="success" variant="light">
            {{ row.test_case_count }} 个用例
          </t-tag>
          <t-tag v-else theme="default" variant="light">
            未覆盖
          </t-tag>
        </template>
        <template #tags="{ row }">
          <div class="tags-cell" v-if="row.tag_names">
            <t-tag 
              v-for="tag in row.tag_names.split(',')" 
              :key="tag" 
              size="small"
              variant="light"
            >
              {{ tag }}
            </t-tag>
          </div>
          <span v-else class="no-tags">-</span>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleViewDetail(row)">详情</t-link>
            <t-link theme="primary" @click="handleGenerateTests(row)">生成测试</t-link>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 生成测试对话框 -->
    <t-dialog
      v-model:visible="generateDialogVisible"
      header="生成测试用例"
      :confirm-btn="{ content: '开始生成', loading: generating }"
      @confirm="confirmGenerate"
    >
      <t-form :data="generateForm" label-width="100px">
        <t-form-item label="目标接口">
          <div v-if="generateTarget">
            <t-tag :theme="getMethodTheme(generateTarget.method)" variant="light" style="margin-right: 8px;">
              {{ generateTarget.method }}
            </t-tag>
            {{ generateTarget.path }}
          </div>
          <div v-else>
            已选择 {{ selectedIds.length }} 个接口
          </div>
        </t-form-item>
        <t-form-item label="测试类型">
          <t-checkbox-group v-model="generateForm.test_types">
            <t-checkbox value="normal">正常场景</t-checkbox>
            <t-checkbox value="boundary">边界测试</t-checkbox>
            <t-checkbox value="exception">异常测试</t-checkbox>
            <t-checkbox value="security">安全测试</t-checkbox>
          </t-checkbox-group>
        </t-form-item>
        <t-form-item label="AI 增强">
          <t-switch v-model="generateForm.use_ai" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">使用 AI 生成更智能的测试用例（较慢）</span>
        </t-form-item>
        <t-form-item label="跳过已有">
          <t-switch v-model="generateForm.skip_existing" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">跳过已有测试用例的接口</span>
        </t-form-item>
      </t-form>
      <t-alert v-if="generateForm.use_ai" theme="info" style="margin-top: 12px;">
        AI 生成需要一定时间，任务将在后台执行，您可以稍后查看结果。
      </t-alert>
    </t-dialog>

    <!-- 任务进度对话框 -->
    <t-dialog
      v-model:visible="taskDialogVisible"
      header="生成任务进度"
      :footer="false"
      :close-on-overlay-click="false"
    >
      <div class="task-progress">
        <t-loading v-if="currentTask?.status === 'pending' || currentTask?.status === 'running'" size="large" />
        <CheckCircleFilledIcon v-else-if="currentTask?.status === 'completed'" class="task-icon success" />
        <CloseCircleFilledIcon v-else-if="currentTask?.status === 'failed'" class="task-icon error" />
        
        <div class="task-status">
          <span v-if="currentTask?.status === 'pending'">任务等待中...</span>
          <span v-else-if="currentTask?.status === 'running'">正在生成测试用例...</span>
          <span v-else-if="currentTask?.status === 'completed'">生成完成！</span>
          <span v-else-if="currentTask?.status === 'failed'">生成失败</span>
        </div>
        
        <div class="task-detail" v-if="currentTask">
          <div v-if="currentTask.status === 'completed'">
            <p>成功处理 {{ currentTask.success_count }} 个接口</p>
            <p>共生成 {{ currentTask.total_cases_generated }} 个测试用例</p>
          </div>
          <div v-else-if="currentTask.status === 'failed'">
            <p class="error-msg">{{ currentTask.error_message }}</p>
          </div>
        </div>
        
        <t-button 
          v-if="currentTask?.status === 'completed' || currentTask?.status === 'failed'"
          theme="primary" 
          @click="closeTaskDialog"
          style="margin-top: 16px;"
        >
          确定
        </t-button>
      </div>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { SearchIcon, AddIcon, FileImportIcon, CheckCircleFilledIcon, CloseCircleFilledIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'

const router = useRouter()

// 数据
const endpoints = ref<any[]>([])
const statistics = ref<any>({})
const loading = ref(false)
const selectedIds = ref<string[]>([])

// 筛选
const searchText = ref('')
const methodFilter = ref('')
const hasTestsFilter = ref<boolean | null>(null)

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 生成测试
const generateDialogVisible = ref(false)
const generateTarget = ref<any>(null)
const generating = ref(false)
const generateForm = reactive({
  test_types: ['normal', 'boundary'],
  use_ai: true,
  skip_existing: true
})

// 任务进度
const taskDialogVisible = ref(false)
const currentTask = ref<any>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

// 表格列
const columns = [
  { colKey: 'row-select', type: 'multiple', width: 50 },
  { colKey: 'method', title: '方法', width: 100 },
  { colKey: 'path', title: '路径', ellipsis: true },
  { colKey: 'test_case_count', title: '测试用例', width: 120 },
  { colKey: 'tags', title: '标签', width: 200 },
  { colKey: 'op', title: '操作', width: 160, fixed: 'right' }
]

// 加载数据
const loadEndpoints = async () => {
  loading.value = true
  try {
    const res = await developmentApi.listEndpoints({
      search: searchText.value || undefined,
      method: methodFilter.value || undefined,
      has_tests: hasTestsFilter.value ?? undefined,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    endpoints.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载接口列表失败:', error)
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    statistics.value = await developmentApi.getStatistics()
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

onMounted(() => {
  loadEndpoints()
  loadStatistics()
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadEndpoints()
}

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadEndpoints()
}

// 选择
const handleSelectChange = (selectedRowKeys: string[]) => {
  selectedIds.value = selectedRowKeys
}

// 查看详情
const handleViewDetail = (row: any) => {
  router.push(`/development/endpoints/${row.endpoint_id}`)
}

// 生成测试
const handleGenerateTests = (row: any) => {
  generateTarget.value = row
  generateDialogVisible.value = true
}

const handleBatchGenerate = () => {
  generateTarget.value = null
  generateDialogVisible.value = true
}

// 轮询任务状态
const pollTaskStatus = async (taskId: string) => {
  try {
    const task = await developmentApi.getGenerateTaskStatus(taskId)
    currentTask.value = task
    
    if (task.status === 'completed' || task.status === 'failed') {
      // 任务完成，停止轮询
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
      // 刷新数据
      loadEndpoints()
      loadStatistics()
    }
  } catch (error) {
    console.error('查询任务状态失败:', error)
  }
}

const confirmGenerate = async () => {
  generating.value = true
  try {
    const endpointIds = generateTarget.value 
      ? [generateTarget.value.endpoint_id]
      : selectedIds.value
    
    const res = await developmentApi.generateTests({
      endpoint_ids: endpointIds,
      test_types: generateForm.test_types,
      use_ai: generateForm.use_ai,
      skip_existing: generateForm.skip_existing
    })
    
    // 关闭生成对话框，显示任务进度对话框
    generateDialogVisible.value = false
    taskDialogVisible.value = true
    currentTask.value = { status: 'pending', task_id: res.task_id }
    
    MessagePlugin.info('任务已创建，正在后台生成...')
    
    // 开始轮询任务状态
    pollTimer = setInterval(() => pollTaskStatus(res.task_id), 2000)
    
  } catch (error) {
    console.error('创建生成任务失败:', error)
  } finally {
    generating.value = false
  }
}

const closeTaskDialog = () => {
  taskDialogVisible.value = false
  currentTask.value = null
}

// 获取方法主题
const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    'GET': 'success',
    'POST': 'primary',
    'PUT': 'warning',
    'DELETE': 'danger',
    'PATCH': 'default'
  }
  return map[method] || 'default'
}
</script>

<style scoped>
.endpoints-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-card {
  text-align: center;
}

.stat-item {
  padding: 8px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
}

.stat-label {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 4px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-cell {
  display: flex;
  flex-direction: column;
}

.path-text {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}

.path-desc {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 2px;
}

.tags-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.no-tags {
  color: rgba(0, 0, 0, 0.2);
}

.task-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  text-align: center;
}

.task-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.task-icon.success {
  color: #52c41a;
}

.task-icon.error {
  color: #ff4d4f;
}

.task-status {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 12px;
}

.task-detail {
  color: rgba(0, 0, 0, 0.6);
  font-size: 14px;
}

.task-detail p {
  margin: 4px 0;
}

.error-msg {
  color: #ff4d4f;
}
</style>
