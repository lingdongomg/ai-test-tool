<template>
  <div class="tests-page">
    <!-- 工具栏 -->
    <t-card class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <t-input
            v-model="searchText"
            placeholder="搜索测试用例"
            clearable
            style="width: 240px;"
            @enter="handleSearch"
          >
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-select
            v-model="categoryFilter"
            placeholder="用例类别"
            clearable
            style="width: 120px;"
            @change="handleSearch"
          >
            <t-option value="normal">正常场景</t-option>
            <t-option value="boundary">边界测试</t-option>
            <t-option value="exception">异常测试</t-option>
            <t-option value="security">安全测试</t-option>
          </t-select>
          <t-select
            v-model="priorityFilter"
            placeholder="优先级"
            clearable
            style="width: 100px;"
            @change="handleSearch"
          >
            <t-option value="P0">P0</t-option>
            <t-option value="P1">P1</t-option>
            <t-option value="P2">P2</t-option>
            <t-option value="P3">P3</t-option>
          </t-select>
        </div>
        <div class="toolbar-right">
          <t-button 
            theme="primary" 
            @click="handleBatchExecute" 
            :disabled="!selectedIds.length"
          >
            <template #icon><PlayIcon /></template>
            执行选中 ({{ selectedIds.length }})
          </t-button>
        </div>
      </div>
    </t-card>

    <!-- 测试用例列表 -->
    <t-card class="table-card">
      <t-table
        :data="testCases"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        :selected-row-keys="selectedIds"
        row-key="case_id"
        hover
        @page-change="handlePageChange"
        @select-change="handleSelectChange"
      >
        <template #endpoint="{ row }">
          <div class="endpoint-cell">
            <t-tag :theme="getMethodTheme(row.endpoint_method)" size="small" variant="light">
              {{ row.endpoint_method }}
            </t-tag>
            <span class="endpoint-path">{{ row.endpoint_path }}</span>
          </div>
        </template>
        <template #category="{ row }">
          <t-tag :theme="getCategoryTheme(row.category)" variant="light" size="small">
            {{ getCategoryLabel(row.category) }}
          </t-tag>
        </template>
        <template #priority="{ row }">
          <t-tag :theme="getPriorityTheme(row.priority)" variant="outline" size="small">
            {{ row.priority }}
          </t-tag>
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
            <t-link theme="primary" @click="handleEdit(row)">编辑</t-link>
            <t-link theme="primary" @click="handleCopy(row)">复制</t-link>
            <t-link theme="primary" @click="handleExecute(row)">执行</t-link>
            <t-popconfirm content="确定删除该测试用例？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 执行对话框 -->
    <t-dialog
      v-model:visible="executeDialogVisible"
      header="执行测试"
      :confirm-btn="{ content: '执行', loading: executing }"
      @confirm="confirmExecute"
    >
      <t-form :data="executeForm" label-width="100px">
        <t-form-item label="服务器地址">
          <t-input v-model="executeForm.base_url" placeholder="http://localhost:8080" />
        </t-form-item>
        <t-form-item label="目标环境">
          <t-select v-model="executeForm.environment" style="width: 100%;">
            <t-option value="local">本地环境</t-option>
            <t-option value="test">测试环境</t-option>
            <t-option value="staging">预发环境</t-option>
          </t-select>
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 详情抽屉 -->
    <t-drawer
      v-model:visible="detailDrawerVisible"
      header="测试用例详情"
      size="600px"
    >
      <template #footer>
        <t-space>
          <t-button @click="detailDrawerVisible = false">关闭</t-button>
          <t-button theme="primary" @click="handleEdit(currentCase)">编辑</t-button>
        </t-space>
      </template>
      <template v-if="currentCase">
        <t-descriptions :column="1" bordered>
          <t-descriptions-item label="用例名称">{{ currentCase.name }}</t-descriptions-item>
          <t-descriptions-item label="描述">{{ currentCase.description || '-' }}</t-descriptions-item>
          <t-descriptions-item label="类别">
            <t-tag :theme="getCategoryTheme(currentCase.category)" variant="light">
              {{ getCategoryLabel(currentCase.category) }}
            </t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="优先级">
            <t-tag :theme="getPriorityTheme(currentCase.priority)" variant="outline">
              {{ currentCase.priority }}
            </t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="请求方法">{{ currentCase.method }}</t-descriptions-item>
          <t-descriptions-item label="请求URL">{{ currentCase.url }}</t-descriptions-item>
          <t-descriptions-item label="期望状态码">{{ currentCase.expected_status_code }}</t-descriptions-item>
        </t-descriptions>
        
        <t-divider>请求头</t-divider>
        <pre class="code-block">{{ JSON.stringify(currentCase.headers, null, 2) || '{}' }}</pre>
        
        <t-divider>请求体</t-divider>
        <pre class="code-block">{{ JSON.stringify(currentCase.body, null, 2) || '{}' }}</pre>
      </template>
    </t-drawer>

    <!-- 编辑对话框 -->
    <t-dialog
      v-model:visible="editDialogVisible"
      :header="isCreating ? '复制测试用例' : '编辑测试用例'"
      width="700px"
      :confirm-btn="{ content: '保存', loading: saving }"
      @confirm="confirmEdit"
    >
      <t-form :data="editForm" label-width="100px" label-align="top">
        <t-row :gutter="16">
          <t-col :span="12">
            <t-form-item label="用例名称" required>
              <t-input v-model="editForm.name" placeholder="请输入用例名称" />
            </t-form-item>
          </t-col>
          <t-col :span="6">
            <t-form-item label="类别">
              <t-select v-model="editForm.category" style="width: 100%;">
                <t-option value="normal">正常场景</t-option>
                <t-option value="boundary">边界测试</t-option>
                <t-option value="exception">异常测试</t-option>
                <t-option value="security">安全测试</t-option>
              </t-select>
            </t-form-item>
          </t-col>
          <t-col :span="6">
            <t-form-item label="优先级">
              <t-select v-model="editForm.priority" style="width: 100%;">
                <t-option value="high">高</t-option>
                <t-option value="medium">中</t-option>
                <t-option value="low">低</t-option>
              </t-select>
            </t-form-item>
          </t-col>
        </t-row>
        <t-form-item label="描述">
          <t-textarea v-model="editForm.description" placeholder="请输入用例描述" :rows="2" />
        </t-form-item>
        <t-row :gutter="16">
          <t-col :span="6">
            <t-form-item label="请求方法">
              <t-select v-model="editForm.method" style="width: 100%;">
                <t-option value="GET">GET</t-option>
                <t-option value="POST">POST</t-option>
                <t-option value="PUT">PUT</t-option>
                <t-option value="DELETE">DELETE</t-option>
                <t-option value="PATCH">PATCH</t-option>
              </t-select>
            </t-form-item>
          </t-col>
          <t-col :span="18">
            <t-form-item label="请求URL">
              <t-input v-model="editForm.url" placeholder="/api/v1/xxx" />
            </t-form-item>
          </t-col>
        </t-row>
        <t-row :gutter="16">
          <t-col :span="12">
            <t-form-item label="期望状态码">
              <t-input-number v-model="editForm.expected_status_code" :min="100" :max="599" style="width: 100%;" />
            </t-form-item>
          </t-col>
          <t-col :span="12">
            <t-form-item label="最大响应时间(ms)">
              <t-input-number v-model="editForm.max_response_time_ms" :min="100" :max="60000" style="width: 100%;" />
            </t-form-item>
          </t-col>
        </t-row>
        <t-form-item label="请求头 (JSON)">
          <t-textarea 
            v-model="editForm.headersStr" 
            placeholder='{"Content-Type": "application/json"}' 
            :rows="3"
            style="font-family: monospace;"
          />
        </t-form-item>
        <t-form-item label="查询参数 (JSON)">
          <t-textarea 
            v-model="editForm.queryParamsStr" 
            placeholder='{"page": 1, "size": 10}' 
            :rows="2"
            style="font-family: monospace;"
          />
        </t-form-item>
        <t-form-item label="请求体 (JSON)">
          <t-textarea 
            v-model="editForm.bodyStr" 
            placeholder='{"key": "value"}' 
            :rows="5"
            style="font-family: monospace;"
          />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { SearchIcon, PlayIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'

// 数据
const testCases = ref<any[]>([])
const loading = ref(false)
const selectedIds = ref<string[]>([])

// 筛选
const searchText = ref('')
const categoryFilter = ref('')
const priorityFilter = ref('')

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 执行
const executeDialogVisible = ref(false)
const executing = ref(false)
const executeTargetIds = ref<string[]>([])
const executeForm = reactive({
  base_url: 'http://localhost:8080',
  environment: 'local'
})

// 详情
const detailDrawerVisible = ref(false)
const currentCase = ref<any>(null)

// 编辑
const editDialogVisible = ref(false)
const saving = ref(false)
const editingCaseId = ref('')
const isCreating = ref(false)  // 是否为复制创建新用例
const editForm = reactive({
  name: '',
  description: '',
  category: '',
  priority: '',
  method: 'GET',
  url: '',
  expected_status_code: 200,
  max_response_time_ms: 3000,
  headersStr: '{}',
  bodyStr: '{}',
  queryParamsStr: '{}'
})

// 表格列
const columns = [
  { colKey: 'row-select', type: 'multiple', width: 50 },
  { colKey: 'name', title: '用例名称', ellipsis: true },
  { colKey: 'endpoint', title: '关联接口', width: 250 },
  { colKey: 'category', title: '类别', width: 100 },
  { colKey: 'priority', title: '优先级', width: 80 },
  { colKey: 'is_enabled', title: '启用', width: 80 },
  { colKey: 'op', title: '操作', width: 240, fixed: 'right' }
]

// 加载数据
const loadTestCases = async () => {
  loading.value = true
  try {
    const res = await developmentApi.listTests({
      search: searchText.value || undefined,
      category: categoryFilter.value || undefined,
      priority: priorityFilter.value || undefined,
      page: pagination.current,
      page_size: pagination.pageSize
    })
    testCases.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载测试用例失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadTestCases)

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadTestCases()
}

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadTestCases()
}

// 选择
const handleSelectChange = (keys: string[]) => {
  selectedIds.value = keys
}

// 切换启用
const handleToggle = async (row: any, enabled: boolean) => {
  try {
    await developmentApi.updateTest(row.case_id, { is_enabled: enabled })
    row.is_enabled = enabled ? 1 : 0
    MessagePlugin.success(enabled ? '已启用' : '已禁用')
  } catch (error) {
    console.error('切换状态失败:', error)
  }
}

// 查看详情
const handleView = (row: any) => {
  currentCase.value = row
  detailDrawerVisible.value = true
}

// 编辑
const handleEdit = (row: any) => {
  isCreating.value = false
  editingCaseId.value = row.case_id
  editForm.name = row.name || ''
  editForm.description = row.description || ''
  editForm.category = row.category || 'normal'
  editForm.priority = row.priority || 'medium'
  editForm.method = row.method || 'GET'
  editForm.url = row.url || ''
  editForm.expected_status_code = row.expected_status_code || 200
  editForm.max_response_time_ms = row.max_response_time_ms || 3000
  editForm.headersStr = JSON.stringify(row.headers || {}, null, 2)
  editForm.bodyStr = JSON.stringify(row.body || {}, null, 2)
  editForm.queryParamsStr = JSON.stringify(row.query_params || {}, null, 2)
  detailDrawerVisible.value = false
  editDialogVisible.value = true
}

// 复制用例
const handleCopy = (row: any) => {
  isCreating.value = true
  editingCaseId.value = row.case_id
  editForm.name = row.name + ' (副本)'
  editForm.description = row.description || ''
  editForm.category = row.category || 'normal'
  editForm.priority = row.priority || 'medium'
  editForm.method = row.method || 'GET'
  editForm.url = row.url || ''
  editForm.expected_status_code = row.expected_status_code || 200
  editForm.max_response_time_ms = row.max_response_time_ms || 3000
  editForm.headersStr = JSON.stringify(row.headers || {}, null, 2)
  editForm.bodyStr = JSON.stringify(row.body || {}, null, 2)
  editForm.queryParamsStr = JSON.stringify(row.query_params || {}, null, 2)
  editDialogVisible.value = true
}

// 确认编辑/复制
const confirmEdit = async () => {
  if (!editForm.name.trim()) {
    MessagePlugin.warning('请输入用例名称')
    return
  }
  
  saving.value = true
  try {
    // 解析 JSON 字符串
    let headers, body, queryParams
    try {
      headers = JSON.parse(editForm.headersStr || '{}')
    } catch { headers = {} }
    try {
      body = JSON.parse(editForm.bodyStr || '{}')
    } catch { body = null }
    try {
      queryParams = JSON.parse(editForm.queryParamsStr || '{}')
    } catch { queryParams = {} }

    const data = {
      name: editForm.name,
      description: editForm.description,
      category: editForm.category,
      priority: editForm.priority,
      method: editForm.method,
      url: editForm.url,
      expected_status_code: editForm.expected_status_code,
      max_response_time_ms: editForm.max_response_time_ms,
      headers,
      body,
      query_params: queryParams
    }

    if (isCreating.value) {
      await developmentApi.copyTest(editingCaseId.value, data)
      MessagePlugin.success('复制成功')
    } else {
      await developmentApi.updateTest(editingCaseId.value, data)
      MessagePlugin.success('保存成功')
    }
    
    editDialogVisible.value = false
    loadTestCases()
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 执行单个
const handleExecute = (row: any) => {
  executeTargetIds.value = [row.case_id]
  executeDialogVisible.value = true
}

// 批量执行
const handleBatchExecute = () => {
  executeTargetIds.value = [...selectedIds.value]
  executeDialogVisible.value = true
}

// 确认执行
const confirmExecute = async () => {
  executing.value = true
  try {
    const res = await developmentApi.executeTests({
      test_case_ids: executeTargetIds.value,
      base_url: executeForm.base_url,
      environment: executeForm.environment
    })
    MessagePlugin.success(`执行完成，通过: ${res.passed}/${res.total}，通过率: ${res.pass_rate}%`)
    executeDialogVisible.value = false
  } catch (error) {
    console.error('执行测试失败:', error)
  } finally {
    executing.value = false
  }
}

// 删除
const handleDelete = async (row: any) => {
  try {
    await developmentApi.deleteTest(row.case_id)
    MessagePlugin.success('删除成功')
    loadTestCases()
  } catch (error) {
    console.error('删除失败:', error)
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

const getCategoryTheme = (category: string) => {
  const map: Record<string, string> = {
    'normal': 'success', 'boundary': 'warning', 
    'exception': 'danger', 'security': 'primary'
  }
  return map[category] || 'default'
}

const getCategoryLabel = (category: string) => {
  const map: Record<string, string> = {
    'normal': '正常', 'boundary': '边界', 
    'exception': '异常', 'security': '安全'
  }
  return map[category] || category
}

const getPriorityTheme = (priority: string) => {
  const map: Record<string, string> = {
    'P0': 'danger', 'P1': 'warning', 'P2': 'primary', 'P3': 'default'
  }
  return map[priority] || 'default'
}
</script>

<style scoped>
.tests-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.endpoint-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.endpoint-path {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
}

.code-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
}
</style>
