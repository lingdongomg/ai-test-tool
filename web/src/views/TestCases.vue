<template>
  <div class="test-cases-page">
    <!-- 统计卡片 -->
    <t-row :gutter="16" class="stat-cards">
      <t-col :span="3">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-value">{{ statistics.cases?.total || 0 }}</div>
          <div class="stat-label">总用例数</div>
        </t-card>
      </t-col>
      <t-col :span="3">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-value text-success">{{ statistics.cases?.enabled || 0 }}</div>
          <div class="stat-label">已启用</div>
        </t-card>
      </t-col>
      <t-col :span="3">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-value text-primary">{{ statistics.cases?.ai_generated || 0 }}</div>
          <div class="stat-label">AI生成</div>
        </t-card>
      </t-col>
      <t-col :span="3">
        <t-card :bordered="false" class="stat-card">
          <div class="stat-value text-warning">{{ statistics.recent_executions?.total_executions || 0 }}</div>
          <div class="stat-label">近7天执行</div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 主内容区 -->
    <t-card :bordered="false" class="main-card">
      <!-- 工具栏 -->
      <div class="toolbar">
        <t-space>
          <t-input v-model="searchKeyword" placeholder="搜索用例名称/URL" clearable style="width: 250px" @enter="loadTestCases">
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-select v-model="filterEndpoint" placeholder="按接口筛选" clearable filterable style="width: 200px" @change="loadTestCases">
            <t-option v-for="ep in endpoints" :key="ep.endpoint_id" :value="ep.endpoint_id" :label="`${ep.method} ${ep.path}`" />
          </t-select>
          <t-select v-model="filterCategory" placeholder="按类别筛选" clearable style="width: 120px" @change="loadTestCases">
            <t-option value="normal" label="正常用例" />
            <t-option value="boundary" label="边界用例" />
            <t-option value="exception" label="异常用例" />
            <t-option value="security" label="安全用例" />
          </t-select>
          <t-select v-model="filterPriority" placeholder="按优先级" clearable style="width: 120px" @change="loadTestCases">
            <t-option value="high" label="高" />
            <t-option value="medium" label="中" />
            <t-option value="low" label="低" />
          </t-select>
        </t-space>
        <t-space>
          <t-button theme="primary" @click="handleCreate">
            <template #icon><AddIcon /></template>
            新建用例
          </t-button>
          <t-button theme="success" :disabled="selectedKeys.length === 0" @click="handleExecuteSelected">
            <template #icon><PlayCircleIcon /></template>
            执行选中
          </t-button>
          <t-button @click="loadTestCases">
            <template #icon><RefreshIcon /></template>
          </t-button>
        </t-space>
      </div>

      <!-- 用例列表 -->
      <t-table
        :data="testCases"
        :columns="columns"
        row-key="case_id"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
        :selected-row-keys="selectedKeys"
        @select-change="handleSelectChange"
      >
        <template #endpoint_name="{ row }">
          <t-tag size="small" variant="light">{{ row.endpoint_name || '未关联' }}</t-tag>
        </template>
        <template #priority="{ row }">
          <t-tag :theme="getPriorityTheme(row.priority)" size="small">{{ getPriorityText(row.priority) }}</t-tag>
        </template>
        <template #category="{ row }">
          <t-tag size="small" variant="light">{{ getCategoryText(row.category) }}</t-tag>
        </template>
        <template #method="{ row }">
          <t-tag :theme="getMethodTheme(row.method)" size="small">{{ row.method }}</t-tag>
        </template>
        <template #is_enabled="{ row }">
          <t-switch v-model="row.is_enabled" size="small" @change="handleToggle(row)" />
        </template>
        <template #last_status="{ row }">
          <t-tag v-if="row.last_status" :theme="getStatusTheme(row.last_status)" size="small">
            {{ getStatusText(row.last_status) }}
          </t-tag>
          <span v-else class="text-placeholder">未执行</span>
        </template>
        <template #op="{ row }">
          <t-space size="small">
            <t-link theme="primary" @click="handleView(row)">查看</t-link>
            <t-link theme="primary" @click="handleEdit(row)">编辑</t-link>
            <t-link theme="success" @click="handleExecuteSingle(row)">执行</t-link>
            <t-popconfirm content="确定删除该用例吗？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>

      <!-- 批量操作栏 -->
      <div class="batch-actions" v-if="selectedKeys.length > 0">
        <t-space>
          <span>已选择 {{ selectedKeys.length }} 项</span>
          <t-button size="small" @click="handleBatchToggle(true)">批量启用</t-button>
          <t-button size="small" @click="handleBatchToggle(false)">批量禁用</t-button>
          <t-button size="small" theme="danger" @click="handleBatchDelete">批量删除</t-button>
        </t-space>
      </div>
    </t-card>

    <!-- 用例详情/编辑抽屉 -->
    <t-drawer v-model:visible="drawerVisible" :header="isEditing ? '编辑用例' : '用例详情'" size="700px" :footer="isEditing">
      <template v-if="currentCase">
        <t-form v-if="isEditing" ref="formRef" :data="editForm" :rules="formRules" label-width="100px">
          <t-form-item label="关联接口" name="endpoint_id">
            <t-select v-model="editForm.endpoint_id" filterable placeholder="选择关联接口">
              <t-option v-for="ep in endpoints" :key="ep.endpoint_id" :value="ep.endpoint_id" :label="`${ep.method} ${ep.path}`" />
            </t-select>
          </t-form-item>
          <t-form-item label="用例名称" name="name">
            <t-input v-model="editForm.name" placeholder="请输入用例名称" />
          </t-form-item>
          <t-form-item label="描述" name="description">
            <t-textarea v-model="editForm.description" placeholder="请输入用例描述" :autosize="{ minRows: 2 }" />
          </t-form-item>
          <t-row :gutter="16">
            <t-col :span="6">
              <t-form-item label="类别" name="category">
                <t-select v-model="editForm.category">
                  <t-option value="normal" label="正常用例" />
                  <t-option value="boundary" label="边界用例" />
                  <t-option value="exception" label="异常用例" />
                  <t-option value="security" label="安全用例" />
                </t-select>
              </t-form-item>
            </t-col>
            <t-col :span="6">
              <t-form-item label="优先级" name="priority">
                <t-select v-model="editForm.priority">
                  <t-option value="high" label="高" />
                  <t-option value="medium" label="中" />
                  <t-option value="low" label="低" />
                </t-select>
              </t-form-item>
            </t-col>
          </t-row>
          <t-row :gutter="16">
            <t-col :span="4">
              <t-form-item label="HTTP方法" name="method">
                <t-select v-model="editForm.method">
                  <t-option value="GET" label="GET" />
                  <t-option value="POST" label="POST" />
                  <t-option value="PUT" label="PUT" />
                  <t-option value="DELETE" label="DELETE" />
                  <t-option value="PATCH" label="PATCH" />
                </t-select>
              </t-form-item>
            </t-col>
            <t-col :span="8">
              <t-form-item label="URL" name="url">
                <t-input v-model="editForm.url" placeholder="/api/xxx" />
              </t-form-item>
            </t-col>
          </t-row>
          <t-form-item label="请求头">
            <t-textarea v-model="editForm.headers_str" placeholder='{"Content-Type": "application/json"}' :autosize="{ minRows: 2 }" />
          </t-form-item>
          <t-form-item label="查询参数">
            <t-textarea v-model="editForm.query_params_str" placeholder='{"page": "1", "size": "10"}' :autosize="{ minRows: 2 }" />
          </t-form-item>
          <t-form-item label="请求体">
            <t-textarea v-model="editForm.body_str" placeholder='{"key": "value"}' :autosize="{ minRows: 3 }" />
          </t-form-item>
          <t-row :gutter="16">
            <t-col :span="6">
              <t-form-item label="期望状态码" name="expected_status_code">
                <t-input-number v-model="editForm.expected_status_code" :min="100" :max="599" />
              </t-form-item>
            </t-col>
            <t-col :span="6">
              <t-form-item label="最大响应时间" name="max_response_time_ms">
                <t-input-number v-model="editForm.max_response_time_ms" :min="100" suffix="ms" />
              </t-form-item>
            </t-col>
          </t-row>
          <t-form-item label="期望响应">
            <t-textarea v-model="editForm.expected_response_str" placeholder='{"code": 0, "message": "success"}' :autosize="{ minRows: 3 }" />
          </t-form-item>
          <t-form-item label="标签">
            <t-tag-input v-model="editForm.tags" placeholder="输入后回车添加标签" />
          </t-form-item>
        </t-form>

        <!-- 查看模式 -->
        <template v-else>
          <t-descriptions :column="2">
            <t-descriptions-item label="用例ID">{{ currentCase.case_id }}</t-descriptions-item>
            <t-descriptions-item label="关联接口">{{ currentCase.endpoint_id || '-' }}</t-descriptions-item>
            <t-descriptions-item label="名称" :span="2">{{ currentCase.name }}</t-descriptions-item>
            <t-descriptions-item label="描述" :span="2">{{ currentCase.description || '-' }}</t-descriptions-item>
            <t-descriptions-item label="类别">
              <t-tag size="small">{{ getCategoryText(currentCase.category) }}</t-tag>
            </t-descriptions-item>
            <t-descriptions-item label="优先级">
              <t-tag :theme="getPriorityTheme(currentCase.priority)" size="small">{{ getPriorityText(currentCase.priority) }}</t-tag>
            </t-descriptions-item>
            <t-descriptions-item label="HTTP方法">
              <t-tag :theme="getMethodTheme(currentCase.method)" size="small">{{ currentCase.method }}</t-tag>
            </t-descriptions-item>
            <t-descriptions-item label="期望状态码">{{ currentCase.expected_status_code }}</t-descriptions-item>
            <t-descriptions-item label="URL" :span="2">{{ currentCase.url }}</t-descriptions-item>
            <t-descriptions-item label="最大响应时间">{{ currentCase.max_response_time_ms }}ms</t-descriptions-item>
            <t-descriptions-item label="是否启用">
              <t-tag :theme="currentCase.is_enabled ? 'success' : 'default'" size="small">
                {{ currentCase.is_enabled ? '已启用' : '已禁用' }}
              </t-tag>
            </t-descriptions-item>
          </t-descriptions>

          <t-divider>请求头</t-divider>
          <pre class="json-view">{{ formatJson(currentCase.headers) }}</pre>

          <t-divider>查询参数</t-divider>
          <pre class="json-view">{{ formatJson(currentCase.query_params) }}</pre>

          <t-divider>请求体</t-divider>
          <pre class="json-view">{{ formatJson(currentCase.body) }}</pre>

          <t-divider>期望响应</t-divider>
          <pre class="json-view">{{ formatJson(currentCase.expected_response) }}</pre>

          <t-divider>断言规则</t-divider>
          <pre class="json-view">{{ formatJson(currentCase.assertions) }}</pre>

          <t-divider>最近执行记录</t-divider>
          <t-table :data="currentCase.recent_results || []" :columns="resultColumns" size="small" />
        </template>
      </template>

      <template #footer v-if="isEditing">
        <t-button @click="drawerVisible = false">取消</t-button>
        <t-button theme="primary" @click="handleSave">保存</t-button>
      </template>
    </t-drawer>

    <!-- 执行对话框 -->
    <t-dialog v-model:visible="executeDialogVisible" header="执行测试" width="500px" @confirm="handleConfirmExecute">
      <t-form :data="executeForm" label-width="100px">
        <t-form-item label="测试目标URL" required>
          <t-input v-model="executeForm.base_url" placeholder="http://localhost:8080" />
        </t-form-item>
        <t-form-item label="环境">
          <t-select v-model="executeForm.environment" placeholder="选择环境" clearable>
            <t-option value="dev" label="开发环境" />
            <t-option value="test" label="测试环境" />
            <t-option value="prod" label="生产环境" />
          </t-select>
        </t-form-item>
        <t-form-item label="全局请求头">
          <t-textarea v-model="executeForm.headers_str" placeholder='{"Authorization": "Bearer xxx"}' :autosize="{ minRows: 2 }" />
        </t-form-item>
        <t-form-item label="全局变量">
          <t-textarea v-model="executeForm.variables_str" placeholder='{"userId": "123"}' :autosize="{ minRows: 2 }" />
        </t-form-item>
      </t-form>
      <t-alert theme="info" :message="`将执行 ${executeForm.case_ids.length} 个测试用例`" />
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { SearchIcon, AddIcon, RefreshIcon, PlayCircleIcon } from 'tdesign-icons-vue-next'
import { testCaseApi, endpointApi } from '../api'

interface TestCase {
  case_id: string
  endpoint_id: string
  endpoint_name?: string
  name: string
  description: string
  category: string
  priority: string
  method: string
  url: string
  headers: any
  body: any
  query_params: any
  expected_status_code: number
  expected_response: any
  assertions: any[]
  max_response_time_ms: number
  tags: string[]
  is_enabled: boolean
  is_ai_generated: boolean
  execution_count?: number
  last_status?: string
  recent_results?: any[]
}

interface Endpoint {
  endpoint_id: string
  name: string
  method: string
  path: string
}

const loading = ref(false)
const testCases = ref<TestCase[]>([])
const endpoints = ref<Endpoint[]>([])
const statistics = ref<any>({})
const searchKeyword = ref('')
const filterEndpoint = ref('')
const filterCategory = ref('')
const filterPriority = ref('')
const selectedKeys = ref<string[]>([])
const drawerVisible = ref(false)
const executeDialogVisible = ref(false)
const isEditing = ref(false)
const currentCase = ref<TestCase | null>(null)

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const editForm = reactive({
  endpoint_id: '',
  name: '',
  description: '',
  category: 'normal',
  priority: 'medium',
  method: 'GET',
  url: '',
  headers_str: '{}',
  body_str: '',
  query_params_str: '{}',
  expected_status_code: 200,
  expected_response_str: '{}',
  max_response_time_ms: 3000,
  tags: [] as string[]
})

const formRules = {
  endpoint_id: [{ required: true, message: '请选择关联接口' }],
  name: [{ required: true, message: '请输入用例名称' }],
  method: [{ required: true, message: '请选择HTTP方法' }],
  url: [{ required: true, message: '请输入URL' }]
}

const executeForm = reactive({
  case_ids: [] as string[],
  endpoint_ids: [] as string[],
  base_url: '',
  environment: '',
  headers_str: '{}',
  variables_str: '{}'
})

const columns = [
  { colKey: 'row-select', type: 'multiple', width: 50 },
  { colKey: 'name', title: '用例名称', ellipsis: true, minWidth: 200 },
  { colKey: 'method', title: '方法', cell: 'method', width: 80 },
  { colKey: 'url', title: 'URL', ellipsis: true, width: 200 },
  { colKey: 'category', title: '类别', cell: 'category', width: 100 },
  { colKey: 'priority', title: '优先级', cell: 'priority', width: 80 },
  { colKey: 'is_enabled', title: '启用', cell: 'is_enabled', width: 80 },
  { colKey: 'execution_count', title: '执行次数', width: 80 },
  { colKey: 'last_status', title: '最近状态', cell: 'last_status', width: 100 },
  { colKey: 'op', title: '操作', cell: 'op', width: 180, fixed: 'right' }
]

const resultColumns = [
  { colKey: 'executed_at', title: '执行时间', width: 160 },
  { colKey: 'status', title: '状态', width: 80 },
  { colKey: 'actual_status_code', title: '状态码', width: 80 },
  { colKey: 'actual_response_time_ms', title: '响应时间', width: 100 }
]

const getPriorityTheme = (priority: string) => {
  const map: Record<string, string> = { high: 'danger', medium: 'warning', low: 'default' }
  return map[priority] || 'default'
}

const getPriorityText = (priority: string) => {
  const map: Record<string, string> = { high: '高', medium: '中', low: '低' }
  return map[priority] || priority
}

const getCategoryText = (category: string) => {
  const map: Record<string, string> = {
    normal: '正常用例', boundary: '边界用例', exception: '异常用例', security: '安全用例', performance: '性能用例'
  }
  return map[category] || category
}

const getMethodTheme = (method: string) => {
  const map: Record<string, string> = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'default' }
  return map[method] || 'default'
}

const getStatusTheme = (status: string) => {
  const map: Record<string, string> = { passed: 'success', failed: 'danger', error: 'warning', skipped: 'default' }
  return map[status] || 'default'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = { passed: '通过', failed: '失败', error: '错误', skipped: '跳过' }
  return map[status] || status
}

const formatJson = (obj: any) => {
  if (!obj) return '-'
  if (typeof obj === 'string') {
    try {
      return JSON.stringify(JSON.parse(obj), null, 2)
    } catch {
      return obj
    }
  }
  return JSON.stringify(obj, null, 2)
}

const loadTestCases = async () => {
  loading.value = true
  try {
    const res: any = await testCaseApi.list({
      endpoint_id: filterEndpoint.value || undefined,
      category: filterCategory.value || undefined,
      priority: filterPriority.value || undefined,
      search: searchKeyword.value || undefined,
      page: pagination.value.current,
      page_size: pagination.value.pageSize
    })
    testCases.value = res.items || []
    pagination.value.total = res.total || 0
  } catch (error) {
    console.error('加载测试用例失败:', error)
  } finally {
    loading.value = false
  }
}

const loadEndpoints = async () => {
  try {
    const res: any = await endpointApi.list({ size: 1000 })
    endpoints.value = res.items || []
  } catch (error) {
    console.error('加载接口列表失败:', error)
  }
}

const loadStatistics = async () => {
  try {
    const res: any = await testCaseApi.statistics()
    statistics.value = res
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

const handlePageChange = (pageInfo: any) => {
  pagination.value.current = pageInfo.current
  pagination.value.pageSize = pageInfo.pageSize
  loadTestCases()
}

const handleSelectChange = (keys: string[]) => {
  selectedKeys.value = keys
}

const handleView = async (row: TestCase) => {
  isEditing.value = false
  try {
    const res: any = await testCaseApi.get(row.case_id)
    currentCase.value = res
  } catch {
    currentCase.value = row
  }
  drawerVisible.value = true
}

const handleEdit = (row: TestCase) => {
  isEditing.value = true
  currentCase.value = row
  Object.assign(editForm, {
    endpoint_id: row.endpoint_id,
    name: row.name,
    description: row.description || '',
    category: row.category,
    priority: row.priority,
    method: row.method,
    url: row.url,
    headers_str: JSON.stringify(row.headers || {}, null, 2),
    body_str: row.body ? JSON.stringify(row.body, null, 2) : '',
    query_params_str: JSON.stringify(row.query_params || {}, null, 2),
    expected_status_code: row.expected_status_code,
    expected_response_str: JSON.stringify(row.expected_response || {}, null, 2),
    max_response_time_ms: row.max_response_time_ms,
    tags: row.tags || []
  })
  drawerVisible.value = true
}

const handleCreate = () => {
  isEditing.value = true
  currentCase.value = null
  Object.assign(editForm, {
    endpoint_id: '',
    name: '',
    description: '',
    category: 'normal',
    priority: 'medium',
    method: 'GET',
    url: '',
    headers_str: '{}',
    body_str: '',
    query_params_str: '{}',
    expected_status_code: 200,
    expected_response_str: '{}',
    max_response_time_ms: 3000,
    tags: []
  })
  drawerVisible.value = true
}

const handleSave = async () => {
  try {
    const data = {
      endpoint_id: editForm.endpoint_id,
      name: editForm.name,
      description: editForm.description,
      category: editForm.category,
      priority: editForm.priority,
      method: editForm.method,
      url: editForm.url,
      headers: JSON.parse(editForm.headers_str || '{}'),
      body: editForm.body_str ? JSON.parse(editForm.body_str) : null,
      query_params: JSON.parse(editForm.query_params_str || '{}'),
      expected_status_code: editForm.expected_status_code,
      expected_response: JSON.parse(editForm.expected_response_str || '{}'),
      max_response_time_ms: editForm.max_response_time_ms,
      tags: editForm.tags
    }

    if (currentCase.value) {
      await testCaseApi.update(currentCase.value.case_id, data)
      MessagePlugin.success('更新成功')
    } else {
      await testCaseApi.create(data)
      MessagePlugin.success('创建成功')
    }
    drawerVisible.value = false
    loadTestCases()
    loadStatistics()
  } catch (error: any) {
    MessagePlugin.error(error.message || '保存失败')
  }
}

const handleDelete = async (row: TestCase) => {
  try {
    await testCaseApi.delete(row.case_id)
    MessagePlugin.success('删除成功')
    loadTestCases()
    loadStatistics()
  } catch (error) {
    MessagePlugin.error('删除失败')
  }
}

const handleToggle = async (row: TestCase) => {
  try {
    await testCaseApi.toggle(row.case_id)
  } catch (error) {
    row.is_enabled = !row.is_enabled
    MessagePlugin.error('操作失败')
  }
}

const handleBatchToggle = async (enabled: boolean) => {
  for (const caseId of selectedKeys.value) {
    const tc = testCases.value.find(t => t.case_id === caseId)
    if (tc && tc.is_enabled !== enabled) {
      await testCaseApi.toggle(caseId)
    }
  }
  MessagePlugin.success(enabled ? '批量启用成功' : '批量禁用成功')
  selectedKeys.value = []
  loadTestCases()
}

const handleBatchDelete = async () => {
  for (const caseId of selectedKeys.value) {
    await testCaseApi.delete(caseId)
  }
  MessagePlugin.success('批量删除成功')
  selectedKeys.value = []
  loadTestCases()
  loadStatistics()
}

const handleExecuteSingle = (row: TestCase) => {
  executeForm.case_ids = [row.case_id]
  executeForm.endpoint_ids = []
  executeDialogVisible.value = true
}

const handleExecuteSelected = () => {
  executeForm.case_ids = [...selectedKeys.value]
  executeForm.endpoint_ids = []
  executeDialogVisible.value = true
}

const handleConfirmExecute = async () => {
  if (!executeForm.base_url) {
    MessagePlugin.warning('请输入测试目标URL')
    return
  }

  try {
    const res: any = await testCaseApi.execute({
      case_ids: executeForm.case_ids,
      endpoint_ids: executeForm.endpoint_ids,
      base_url: executeForm.base_url,
      environment: executeForm.environment,
      headers: JSON.parse(executeForm.headers_str || '{}'),
      variables: JSON.parse(executeForm.variables_str || '{}')
    })
    MessagePlugin.success(`测试执行已启动，执行ID: ${res.execution_id}`)
    executeDialogVisible.value = false
    selectedKeys.value = []
  } catch (error: any) {
    MessagePlugin.error(error.message || '执行失败')
  }
}

onMounted(() => {
  loadTestCases()
  loadEndpoints()
  loadStatistics()
})
</script>

<style scoped>
.stat-cards {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 4px;
}

.text-success { color: #00a870; }
.text-primary { color: #0052d9; }
.text-warning { color: #ed7b2f; }

.main-card {
  min-height: calc(100vh - 200px);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.batch-actions {
  margin-top: 16px;
  padding: 12px;
  background: #f0f5ff;
  border-radius: 4px;
}

.json-view {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow: auto;
  max-height: 200px;
  margin: 0;
}

.text-placeholder {
  color: rgba(0, 0, 0, 0.25);
}
</style>
