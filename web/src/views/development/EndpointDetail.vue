<template>
  <div class="endpoint-detail" v-loading="loading">
    <!-- 基本信息 -->
    <t-card class="info-card">
      <div class="endpoint-header">
        <div class="endpoint-title">
          <t-tag :theme="getMethodTheme(endpoint.method)" size="large">
            {{ endpoint.method }}
          </t-tag>
          <span class="endpoint-path">{{ endpoint.path }}</span>
        </div>
        <div class="endpoint-actions">
          <t-button theme="primary" @click="handleGenerateTests">
            <template #icon><AddIcon /></template>
            生成测试用例
          </t-button>
          <t-button @click="handleExecuteTests" :disabled="!testCases.length">
            <template #icon><PlayIcon /></template>
            执行测试
          </t-button>
        </div>
      </div>
      <t-descriptions :column="3" style="margin-top: 16px;">
        <t-descriptions-item label="接口ID">{{ endpoint.endpoint_id }}</t-descriptions-item>
        <t-descriptions-item label="描述">{{ endpoint.description || '-' }}</t-descriptions-item>
        <t-descriptions-item label="标签">
          <t-space v-if="tags.length">
            <t-tag v-for="tag in tags" :key="tag.id" variant="light">{{ tag.name }}</t-tag>
          </t-space>
          <span v-else>-</span>
        </t-descriptions-item>
        <t-descriptions-item label="测试用例数">{{ statistics.total_cases || 0 }}</t-descriptions-item>
        <t-descriptions-item label="近期通过率">{{ statistics.recent_pass_rate || 0 }}%</t-descriptions-item>
        <t-descriptions-item label="创建时间">{{ endpoint.created_at }}</t-descriptions-item>
      </t-descriptions>
    </t-card>

    <!-- 测试用例列表 -->
    <t-card title="测试用例" style="margin-top: 16px;">
      <template #actions>
        <t-button theme="primary" variant="text" size="small" @click="handleGenerateTests">
          <template #icon><AddIcon /></template>
          生成用例
        </t-button>
      </template>
      <t-table
        :data="testCases"
        :columns="caseColumns"
        :loading="casesLoading"
        row-key="test_case_id"
        hover
      >
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
            @change="(val: boolean) => handleToggleCase(row, val)"
          />
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleViewCase(row)">详情</t-link>
            <t-link theme="primary" @click="handleEditCase(row)">编辑</t-link>
            <t-link theme="primary" @click="handleCopyCase(row)">复制</t-link>
            <t-link theme="primary" @click="handleExecuteCase(row)">执行</t-link>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- 最近执行记录 -->
    <t-card title="最近执行记录" style="margin-top: 16px;">
      <t-table
        :data="recentExecutions"
        :columns="executionColumns"
        row-key="id"
        hover
        size="small"
      >
        <template #status="{ row }">
          <t-tag :theme="getStatusTheme(row.status)" size="small">
            {{ getStatusLabel(row.status) }}
          </t-tag>
        </template>
        <template #response_time_ms="{ row }">
          {{ row.response_time_ms ? `${row.response_time_ms}ms` : '-' }}
        </template>
      </t-table>
      <t-empty v-if="!recentExecutions.length" description="暂无执行记录" />
    </t-card>

    <!-- 执行测试对话框 -->
    <t-dialog
      v-model:visible="executeDialogVisible"
      header="执行测试"
      :confirm-btn="{ content: '执行', loading: executing }"
      @confirm="confirmExecute"
    >
      <t-form :data="executeForm" label-width="100px">
        <t-form-item label="目标环境">
          <t-select v-model="executeForm.environment" style="width: 100%;">
            <t-option value="local">本地环境</t-option>
            <t-option value="test">测试环境</t-option>
            <t-option value="staging">预发环境</t-option>
            <t-option value="production">生产环境</t-option>
          </t-select>
        </t-form-item>
        <t-form-item label="服务器地址">
          <t-input v-model="executeForm.base_url" placeholder="http://localhost:8080" />
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 测试用例详情抽屉 -->
    <t-drawer
      v-model:visible="detailDrawerVisible"
      header="测试用例详情"
      size="600px"
    >
      <template #footer>
        <t-space>
          <t-button @click="detailDrawerVisible = false">关闭</t-button>
          <t-button theme="primary" @click="handleEditCase(currentCase)">编辑</t-button>
        </t-space>
      </template>
      <template v-if="currentCase">
        <t-descriptions :column="1" bordered>
          <t-descriptions-item label="用例ID">{{ currentCase.case_id }}</t-descriptions-item>
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
          <t-descriptions-item label="最大响应时间">{{ currentCase.max_response_time_ms }}ms</t-descriptions-item>
        </t-descriptions>
        
        <t-divider>请求头</t-divider>
        <pre class="code-block">{{ formatJson(currentCase.headers) }}</pre>
        
        <t-divider>查询参数</t-divider>
        <pre class="code-block">{{ formatJson(currentCase.query_params) }}</pre>
        
        <t-divider>请求体</t-divider>
        <pre class="code-block">{{ formatJson(currentCase.body) }}</pre>
      </template>
    </t-drawer>

    <!-- 编辑测试用例对话框 -->
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
import { useRoute } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon, PlayIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'

const route = useRoute()
const endpointId = route.params.id as string

// 数据
const loading = ref(false)
const endpoint = ref<any>({})
const testCases = ref<any[]>([])
const tags = ref<any[]>([])
const recentExecutions = ref<any[]>([])
const statistics = ref<any>({})
const casesLoading = ref(false)

// 执行测试
const executeDialogVisible = ref(false)
const executing = ref(false)
const executeForm = reactive({
  environment: 'local',
  base_url: 'http://localhost:8080'
})

// 详情抽屉
const detailDrawerVisible = ref(false)
const currentCase = ref<any>(null)

// 编辑对话框
const editDialogVisible = ref(false)
const saving = ref(false)
const isCreating = ref(false)  // 是否为复制创建新用例
const editingCaseId = ref('')
const editForm = reactive({
  name: '',
  description: '',
  category: 'normal',
  priority: 'medium',
  method: 'GET',
  url: '',
  expected_status_code: 200,
  max_response_time_ms: 3000,
  headersStr: '{}',
  bodyStr: '{}',
  queryParamsStr: '{}'
})

// 表格列
const caseColumns = [
  { colKey: 'name', title: '用例名称', ellipsis: true },
  { colKey: 'category', title: '类别', width: 100 },
  { colKey: 'priority', title: '优先级', width: 80 },
  { colKey: 'is_enabled', title: '启用', width: 80 },
  { colKey: 'op', title: '操作', width: 200 }
]

const executionColumns = [
  { colKey: 'executed_at', title: '执行时间', width: 180 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'response_time_ms', title: '响应时间', width: 100 },
  { colKey: 'status_code', title: '状态码', width: 80 }
]

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const res = await developmentApi.getEndpoint(endpointId)
    endpoint.value = res.endpoint || {}
    testCases.value = res.test_cases || []
    tags.value = res.tags || []
    recentExecutions.value = res.recent_executions || []
    statistics.value = res.statistics || {}
  } catch (error) {
    console.error('加载接口详情失败:', error)
    MessagePlugin.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// 生成测试用例
const handleGenerateTests = async () => {
  try {
    const res = await developmentApi.generateTestsForEndpoint(endpointId)
    MessagePlugin.success(res.message || `生成了 ${res.total_cases} 个测试用例`)
    loadData()
  } catch (error) {
    console.error('生成测试用例失败:', error)
  }
}

// 执行测试
const handleExecuteTests = () => {
  executeDialogVisible.value = true
}

const handleExecuteCase = (_row: any) => {
  // 可以根据 _row 设置单个用例执行
  executeDialogVisible.value = true
}

const confirmExecute = async () => {
  executing.value = true
  try {
    const res = await developmentApi.executeTests({
      endpoint_id: endpointId,
      base_url: executeForm.base_url,
      environment: executeForm.environment
    })
    MessagePlugin.success(`执行完成，通过率: ${res.pass_rate}%`)
    executeDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('执行测试失败:', error)
  } finally {
    executing.value = false
  }
}

// 切换用例启用状态
const handleToggleCase = async (row: any, enabled: boolean) => {
  try {
    await developmentApi.updateTest(row.case_id, { is_enabled: enabled })
    row.is_enabled = enabled ? 1 : 0
    MessagePlugin.success(enabled ? '已启用' : '已禁用')
  } catch (error) {
    console.error('切换状态失败:', error)
  }
}

// 查看用例详情
const handleViewCase = (row: any) => {
  currentCase.value = row
  detailDrawerVisible.value = true
}

// 编辑用例
const handleEditCase = (row: any) => {
  if (!row) return
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
  editForm.headersStr = formatJson(row.headers)
  editForm.bodyStr = formatJson(row.body)
  editForm.queryParamsStr = formatJson(row.query_params)
  detailDrawerVisible.value = false
  editDialogVisible.value = true
}

// 复制用例
const handleCopyCase = (row: any) => {
  isCreating.value = true
  editingCaseId.value = row.case_id  // 原始用例ID，用于复制
  editForm.name = row.name + ' (副本)'
  editForm.description = row.description || ''
  editForm.category = row.category || 'normal'
  editForm.priority = row.priority || 'medium'
  editForm.method = row.method || 'GET'
  editForm.url = row.url || ''
  editForm.expected_status_code = row.expected_status_code || 200
  editForm.max_response_time_ms = row.max_response_time_ms || 3000
  editForm.headersStr = formatJson(row.headers)
  editForm.bodyStr = formatJson(row.body)
  editForm.queryParamsStr = formatJson(row.query_params)
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
      // 复制创建新用例
      await developmentApi.copyTest(editingCaseId.value, data)
      MessagePlugin.success('复制成功')
    } else {
      // 更新现有用例
      await developmentApi.updateTest(editingCaseId.value, data)
      MessagePlugin.success('保存成功')
    }
    
    editDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

// 格式化 JSON
const formatJson = (obj: any): string => {
  if (!obj) return '{}'
  if (typeof obj === 'string') {
    try {
      return JSON.stringify(JSON.parse(obj), null, 2)
    } catch {
      return obj
    }
  }
  return JSON.stringify(obj, null, 2)
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

const getStatusTheme = (status: string) => {
  const map: Record<string, string> = {
    'passed': 'success', 'failed': 'danger', 'skipped': 'default'
  }
  return map[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    'passed': '通过', 'failed': '失败', 'skipped': '跳过'
  }
  return map[status] || status
}
</script>

<style scoped>
.endpoint-detail {
  max-width: 1200px;
}

.endpoint-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.endpoint-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.endpoint-path {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 18px;
  font-weight: 500;
}

.endpoint-actions {
  display: flex;
  gap: 8px;
}

.code-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
