<template>
  <div class="requests-page">
    <!-- 统计卡片 -->
    <t-row :gutter="[16, 16]" class="stats-row">
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ statistics.requests?.total || 0 }}</div>
            <div class="stat-label">监控用例</div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value" style="color: #38ef7d;">{{ statistics.requests?.healthy || 0 }}</div>
            <div class="stat-label">健康</div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value" style="color: #f5576c;">{{ statistics.requests?.unhealthy || 0 }}</div>
            <div class="stat-label">异常</div>
          </div>
        </t-card>
      </t-col>
      <t-col :xs="12" :sm="6">
        <t-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ statistics.requests?.health_rate || 0 }}%</div>
            <div class="stat-label">健康率</div>
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
            placeholder="搜索URL"
            clearable
            style="width: 280px;"
            @enter="handleSearch"
          >
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-select
            v-model="statusFilter"
            placeholder="健康状态"
            clearable
            style="width: 120px;"
            @change="handleSearch"
          >
            <t-option value="healthy">健康</t-option>
            <t-option value="unhealthy">异常</t-option>
          </t-select>
        </div>
        <div class="toolbar-right">
          <t-button theme="primary" @click="handleAdd">
            <template #icon><AddIcon /></template>
            添加监控
          </t-button>
          <t-button @click="handleExtract">
            <template #icon><FileImportIcon /></template>
            从日志提取
          </t-button>
        </div>
      </div>
    </t-card>

    <!-- 监控列表 -->
    <t-card class="table-card">
      <t-table
        :data="requests"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        row-key="request_id"
        hover
        @page-change="handlePageChange"
      >
        <template #method="{ row }">
          <t-tag :theme="getMethodTheme(row.method)" variant="light" size="small">
            {{ row.method }}
          </t-tag>
        </template>
        <template #url="{ row }">
          <div class="url-cell">
            <span class="url-text">{{ row.url }}</span>
          </div>
        </template>
        <template #last_check_status="{ row }">
          <t-tag :theme="getHealthTheme(row.last_check_status)" v-if="row.last_check_status">
            {{ row.last_check_status === 'healthy' ? '健康' : '异常' }}
          </t-tag>
          <span v-else class="no-check">未检查</span>
        </template>
        <template #consecutive_failures="{ row }">
          <t-tag v-if="row.consecutive_failures >= 3" theme="danger" size="small">
            连续失败 {{ row.consecutive_failures }} 次
          </t-tag>
          <span v-else>{{ row.consecutive_failures || 0 }}</span>
        </template>
        <template #is_enabled="{ row }">
          <t-switch 
            :value="row.is_enabled" 
            size="small"
            @change="(val: boolean) => handleToggle(row, val)"
          />
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">详情</t-link>
            <t-link theme="primary" @click="handleCheck(row)">检查</t-link>
            <t-popconfirm content="确定删除？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 添加/编辑对话框 -->
    <t-dialog
      v-model:visible="editDialogVisible"
      :header="editMode === 'add' ? '添加监控请求' : '编辑监控请求'"
      :confirm-btn="{ content: '保存', loading: saving }"
      width="600px"
      @confirm="confirmSave"
    >
      <t-form :data="editForm" label-width="100px">
        <t-form-item label="HTTP方法" required>
          <t-select v-model="editForm.method" style="width: 120px;">
            <t-option value="GET">GET</t-option>
            <t-option value="POST">POST</t-option>
            <t-option value="PUT">PUT</t-option>
            <t-option value="DELETE">DELETE</t-option>
          </t-select>
        </t-form-item>
        <t-form-item label="请求URL" required>
          <t-input v-model="editForm.url" placeholder="https://api.example.com/endpoint" />
        </t-form-item>
        <t-form-item label="期望状态码">
          <t-input-number v-model="editForm.expected_status_code" :min="100" :max="599" />
        </t-form-item>
        <t-form-item label="请求头">
          <t-textarea v-model="editForm.headers_str" placeholder='{"Authorization": "Bearer xxx"}' :rows="3" />
        </t-form-item>
        <t-form-item label="请求体">
          <t-textarea v-model="editForm.body" placeholder="JSON格式请求体" :rows="3" />
        </t-form-item>
        <t-form-item label="标签">
          <t-input v-model="editForm.tags_str" placeholder="多个标签用逗号分隔" />
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 从日志提取对话框 -->
    <t-dialog
      v-model:visible="extractDialogVisible"
      header="从日志提取监控请求"
      :confirm-btn="{ content: '提取', loading: extracting }"
      @confirm="confirmExtract"
    >
      <t-form :data="extractForm" label-width="120px">
        <t-form-item label="日志分析任务" required>
          <t-select v-model="extractForm.task_id" style="width: 100%;" placeholder="选择已完成的分析任务">
            <t-option v-for="task in availableTasks" :key="task.task_id" :value="task.task_id">
              {{ task.name }} ({{ task.task_id }})
            </t-option>
          </t-select>
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
          <t-input v-model="extractForm.tags_str" placeholder="多个标签用逗号分隔，如：生产日志,重要接口" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { SearchIcon, AddIcon, FileImportIcon } from 'tdesign-icons-vue-next'
import { monitoringApi, insightsApi } from '../../api/v2'

// 数据
const requests = ref<any[]>([])
const statistics = ref<any>({})
const loading = ref(false)
const availableTasks = ref<any[]>([])

// 筛选
const searchText = ref('')
const statusFilter = ref('')

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 编辑
const editDialogVisible = ref(false)
const editMode = ref<'add' | 'edit'>('add')
const saving = ref(false)
const editForm = reactive({
  request_id: '',
  method: 'GET',
  url: '',
  headers_str: '',
  body: '',
  expected_status_code: 200,
  tags_str: ''
})

// 提取
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
  { colKey: 'method', title: '方法', width: 80 },
  { colKey: 'url', title: 'URL', ellipsis: true },
  { colKey: 'last_check_status', title: '健康状态', width: 100 },
  { colKey: 'consecutive_failures', title: '连续失败', width: 120 },
  { colKey: 'last_check_at', title: '上次检查', width: 160 },
  { colKey: 'is_enabled', title: '启用', width: 80 },
  { colKey: 'op', title: '操作', width: 160, fixed: 'right' }
]

// 加载数据
const loadRequests = async () => {
  loading.value = true
  try {
    const res = await monitoringApi.listRequests({
      search: searchText.value || undefined,
      last_status: statusFilter.value || undefined,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    requests.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载监控请求失败:', error)
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    statistics.value = await monitoringApi.getStatistics()
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

const loadTasks = async () => {
  try {
    const res = await insightsApi.listTasks({ status: 'completed' })
    availableTasks.value = res.items || []
  } catch (error) {
    console.error('加载任务列表失败:', error)
  }
}

onMounted(() => {
  loadRequests()
  loadStatistics()
})

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadRequests()
}

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadRequests()
}

// 添加
const handleAdd = () => {
  editMode.value = 'add'
  Object.assign(editForm, {
    request_id: '',
    method: 'GET',
    url: '',
    headers_str: '',
    body: '',
    expected_status_code: 200,
    tags_str: ''
  })
  editDialogVisible.value = true
}

// 保存
const confirmSave = async () => {
  saving.value = true
  try {
    const data = {
      method: editForm.method,
      url: editForm.url,
      headers: editForm.headers_str ? JSON.parse(editForm.headers_str) : undefined,
      body: editForm.body || undefined,
      expected_status_code: editForm.expected_status_code,
      tags: editForm.tags_str ? editForm.tags_str.split(',').map(t => t.trim()) : undefined
    }
    
    if (editMode.value === 'add') {
      await monitoringApi.addRequest(data)
      MessagePlugin.success('添加成功')
    } else {
      await monitoringApi.updateRequest(editForm.request_id, data)
      MessagePlugin.success('更新成功')
    }
    
    editDialogVisible.value = false
    loadRequests()
    loadStatistics()
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 查看详情
const handleView = (row: any) => {
  MessagePlugin.info(`请求详情: ${row.method} ${row.url}（详情抽屉开发中）`)
}

// 执行检查
const handleCheck = async (row: any) => {
  try {
    MessagePlugin.loading('正在检查...')
    await monitoringApi.runHealthCheck({
      base_url: new URL(row.url).origin,
      request_ids: [row.request_id],
      use_ai_validation: true
    })
    MessagePlugin.success('检查完成')
    loadRequests()
  } catch (error) {
    console.error('检查失败:', error)
  }
}

// 切换启用
const handleToggle = async (row: any, enabled: boolean) => {
  try {
    await monitoringApi.toggleRequest(row.request_id, enabled)
    row.is_enabled = enabled
  } catch (error) {
    console.error('切换失败:', error)
  }
}

// 删除
const handleDelete = async (row: any) => {
  try {
    await monitoringApi.deleteRequest(row.request_id)
    MessagePlugin.success('删除成功')
    loadRequests()
    loadStatistics()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

// 从日志提取
const handleExtract = () => {
  loadTasks()
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
    loadRequests()
    loadStatistics()
  } catch (error) {
    console.error('提取失败:', error)
  } finally {
    extracting.value = false
  }
}

// 辅助函数
const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    'GET': 'success', 'POST': 'primary', 'PUT': 'warning', 
    'DELETE': 'danger', 'PATCH': 'default'
  }
  return map[method] || 'default'
}

const getHealthTheme = (status: string) => {
  return status === 'healthy' ? 'success' : 'danger'
}
</script>

<style scoped>
.requests-page {
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

.url-cell {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
}

.no-check {
  color: rgba(0, 0, 0, 0.3);
}
</style>
