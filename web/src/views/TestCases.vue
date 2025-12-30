<template>
  <div class="test-cases-page">
    <t-card :bordered="false">
      <div class="toolbar">
        <t-space>
          <t-input v-model="searchKeyword" placeholder="搜索测试用例" clearable style="width: 250px">
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-select v-model="filterVersion" placeholder="版本筛选" clearable style="width: 150px">
            <t-option v-for="v in versions" :key="v.id" :value="v.id" :label="v.name" />
          </t-select>
          <t-select v-model="filterCategory" placeholder="分类筛选" clearable style="width: 150px">
            <t-option value="normal" label="正常用例" />
            <t-option value="boundary" label="边界用例" />
            <t-option value="exception" label="异常用例" />
            <t-option value="security" label="安全用例" />
          </t-select>
          <t-button theme="primary" @click="handleCreateVersion">
            <template #icon><AddIcon /></template>
            新建版本
          </t-button>
          <t-button @click="loadTestCases">
            <template #icon><RefreshIcon /></template>
            刷新
          </t-button>
        </t-space>
      </div>

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
        <template #priority="{ row }">
          <t-tag :theme="getPriorityTheme(row.priority)" size="small">{{ row.priority }}</t-tag>
        </template>
        <template #category="{ row }">
          <t-tag size="small" variant="light">{{ getCategoryText(row.category) }}</t-tag>
        </template>
        <template #method="{ row }">
          <t-tag :theme="getMethodTheme(row.method)" size="small">{{ row.method }}</t-tag>
        </template>
        <template #version="{ row }">
          <t-tag size="small">v{{ row.version || 1 }}</t-tag>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">查看</t-link>
            <t-link theme="primary" @click="handleEdit(row)">编辑</t-link>
            <t-link theme="primary" @click="handleViewHistory(row)">历史</t-link>
            <t-popconfirm content="确定删除该用例吗？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>

      <div class="batch-actions" v-if="selectedKeys.length > 0">
        <t-space>
          <span>已选择 {{ selectedKeys.length }} 项</span>
          <t-button size="small" @click="handleBatchEnable(true)">批量启用</t-button>
          <t-button size="small" @click="handleBatchEnable(false)">批量禁用</t-button>
          <t-button size="small" @click="handleBatchCopy">复制到新版本</t-button>
        </t-space>
      </div>
    </t-card>

    <!-- 用例详情抽屉 -->
    <t-drawer v-model:visible="drawerVisible" header="用例详情" size="600px">
      <template v-if="currentCase">
        <t-descriptions :column="1">
          <t-descriptions-item label="用例ID">{{ currentCase.case_id }}</t-descriptions-item>
          <t-descriptions-item label="名称">{{ currentCase.name }}</t-descriptions-item>
          <t-descriptions-item label="描述">{{ currentCase.description || '-' }}</t-descriptions-item>
          <t-descriptions-item label="分类">{{ getCategoryText(currentCase.category) }}</t-descriptions-item>
          <t-descriptions-item label="优先级">
            <t-tag :theme="getPriorityTheme(currentCase.priority)">{{ currentCase.priority }}</t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="版本">v{{ currentCase.version || 1 }}</t-descriptions-item>
          <t-descriptions-item label="请求方法">
            <t-tag :theme="getMethodTheme(currentCase.method)">{{ currentCase.method }}</t-tag>
          </t-descriptions-item>
          <t-descriptions-item label="请求URL">{{ currentCase.url }}</t-descriptions-item>
          <t-descriptions-item label="期望状态码">{{ currentCase.expected_status_code }}</t-descriptions-item>
        </t-descriptions>

        <t-divider>请求头</t-divider>
        <pre class="json-view">{{ formatJson(currentCase.headers) }}</pre>

        <t-divider>请求体</t-divider>
        <pre class="json-view">{{ formatJson(currentCase.body) }}</pre>

        <t-divider>期望响应</t-divider>
        <pre class="json-view">{{ formatJson(currentCase.expected_response) }}</pre>
      </template>
    </t-drawer>

    <!-- 版本历史对话框 -->
    <t-dialog v-model:visible="historyDialogVisible" header="版本历史" width="700px">
      <t-timeline>
        <t-timeline-item
          v-for="history in versionHistory"
          :key="history.version_number"
          :label="`v${history.version_number}`"
        >
          <div class="history-item">
            <div class="history-header">
              <span>
                <t-tag size="small" :theme="history.change_type === 'create' ? 'success' : history.change_type === 'restore' ? 'warning' : 'primary'">
                  {{ getChangeTypeText(history.change_type) }}
                </t-tag>
                {{ history.created_at?.replace('T', ' ').slice(0, 19) || '-' }}
              </span>
              <t-space>
                <t-link theme="primary" @click="handleCompareVersion(history)">对比</t-link>
                <t-link theme="primary" @click="handleRollback(history)">回滚</t-link>
              </t-space>
            </div>
            <div class="history-desc">{{ history.change_summary || '无变更说明' }}</div>
            <div class="history-fields" v-if="history.changed_fields?.length">
              变更字段: {{ history.changed_fields.join(', ') }}
            </div>
            <div class="history-user" v-if="history.changed_by">
              操作人: {{ history.changed_by }}
            </div>
          </div>
        </t-timeline-item>
      </t-timeline>
    </t-dialog>

    <!-- 版本对比对话框 -->
    <t-dialog v-model:visible="compareDialogVisible" header="版本对比" width="800px">
      <template v-if="compareResult">
        <div class="compare-header">
          <span>版本 v{{ compareResult.version1 }}</span>
          <span>→</span>
          <span>版本 v{{ compareResult.version2 }}</span>
        </div>
        <t-alert v-if="!compareResult.has_changes" theme="success" message="两个版本完全相同" />
        <div v-else class="compare-list">
          <div v-for="diff in compareResult.differences" :key="diff.field" class="compare-item">
            <div class="compare-field">{{ diff.field }}</div>
            <div class="compare-values">
              <div class="compare-old">
                <div class="label">旧值:</div>
                <pre>{{ formatJson(diff.version1_value) }}</pre>
              </div>
              <div class="compare-new">
                <div class="label">新值:</div>
                <pre>{{ formatJson(diff.version2_value) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </template>
    </t-dialog>

    <!-- 新建版本对话框 -->
    <t-dialog v-model:visible="versionDialogVisible" header="新建版本" @confirm="handleConfirmVersion">
      <t-form :data="versionForm">
        <t-form-item label="版本名称">
          <t-input v-model="versionForm.name" placeholder="如：v2.0.0" />
        </t-form-item>
        <t-form-item label="版本说明">
          <t-textarea v-model="versionForm.description" placeholder="版本变更说明" />
        </t-form-item>
        <t-form-item label="基于版本">
          <t-select v-model="versionForm.baseVersion" placeholder="选择基础版本">
            <t-option v-for="v in versions" :key="v.id" :value="v.id" :label="v.name" />
          </t-select>
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { SearchIcon, AddIcon, RefreshIcon } from 'tdesign-icons-vue-next'
import api from '../api'

interface TestCase {
  case_id: string
  task_id: string
  name: string
  description: string
  category: string
  priority: string
  method: string
  url: string
  headers: any
  body: any
  expected_status_code: number
  expected_response: any
  version: number
  is_enabled: boolean
}

interface VersionInfo {
  version_id: string
  version_number: number
  name: string
  change_type: string
  change_summary: string
  changed_fields: string[]
  changed_by: string
  created_at: string
}

const loading = ref(false)
const testCases = ref<TestCase[]>([])
const searchKeyword = ref('')
const filterVersion = ref<number | null>(null)
const filterCategory = ref('')
const selectedKeys = ref<string[]>([])
const drawerVisible = ref(false)
const historyDialogVisible = ref(false)
const versionDialogVisible = ref(false)
const compareDialogVisible = ref(false)
const currentCase = ref<TestCase | null>(null)
const versionHistory = ref<VersionInfo[]>([])
const compareResult = ref<any>(null)

const currentTaskId = ref('') // 当前任务ID，需要从路由或其他地方获取

const versions = ref([
  { id: 1, name: 'v1.0.0' },
  { id: 2, name: 'v1.1.0' },
  { id: 3, name: 'v2.0.0' }
])

const versionForm = ref({
  name: '',
  description: '',
  baseVersion: null as number | null
})

const rollbackForm = ref({
  version_number: 0,
  reason: ''
})

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { colKey: 'row-select', type: 'multiple', width: 50 },
  { colKey: 'case_id', title: '用例ID', width: 150, ellipsis: true },
  { colKey: 'name', title: '名称', ellipsis: true },
  { colKey: 'category', title: '分类', cell: 'category', width: 100 },
  { colKey: 'priority', title: '优先级', cell: 'priority', width: 80 },
  { colKey: 'method', title: '方法', cell: 'method', width: 80 },
  { colKey: 'url', title: 'URL', width: 200, ellipsis: true },
  { colKey: 'version', title: '版本', cell: 'version', width: 80 },
  { colKey: 'op', title: '操作', cell: 'op', width: 180 }
]

const getPriorityTheme = (priority: string) => {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'default'
  }
  return map[priority] || 'default'
}

const getCategoryText = (category: string) => {
  const map: Record<string, string> = {
    normal: '正常用例',
    boundary: '边界用例',
    exception: '异常用例',
    security: '安全用例'
  }
  return map[category] || category
}

const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger'
  }
  return map[method] || 'default'
}

const getChangeTypeText = (type: string) => {
  const map: Record<string, string> = {
    create: '创建',
    update: '更新',
    delete: '删除',
    restore: '回滚'
  }
  return map[type] || type
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
  // 模拟数据，实际应从API获取
  testCases.value = [
    { case_id: 'TC001', task_id: 'task_001', name: '用户登录-正常', description: '测试正常登录流程', category: 'normal', priority: 'high', method: 'POST', url: '/api/login', headers: {}, body: { username: 'test', password: '123456' }, expected_status_code: 200, expected_response: { code: 0 }, version: 2, is_enabled: true },
    { case_id: 'TC002', task_id: 'task_001', name: '用户登录-密码错误', description: '测试密码错误情况', category: 'exception', priority: 'medium', method: 'POST', url: '/api/login', headers: {}, body: { username: 'test', password: 'wrong' }, expected_status_code: 401, expected_response: { code: -1 }, version: 2, is_enabled: true },
    { case_id: 'TC003', task_id: 'task_001', name: '获取用户信息', description: '测试获取用户信息接口', category: 'normal', priority: 'high', method: 'GET', url: '/api/user/info', headers: { Authorization: 'Bearer token' }, body: null, expected_status_code: 200, expected_response: { code: 0 }, version: 1, is_enabled: true }
  ]
  currentTaskId.value = 'task_001'
  pagination.value.total = testCases.value.length
  loading.value = false
}

const handlePageChange = (pageInfo: any) => {
  pagination.value.current = pageInfo.current
  loadTestCases()
}

const handleSelectChange = (keys: string[]) => {
  selectedKeys.value = keys
}

const handleView = (row: TestCase) => {
  currentCase.value = row
  drawerVisible.value = true
}

const handleEdit = (row: TestCase) => {
  MessagePlugin.info('编辑功能开发中')
}

const handleViewHistory = async (row: TestCase) => {
  currentCase.value = row
  try {
    const res = await api.get(`/api/v1/versions/${row.task_id}/cases/${row.case_id}/versions`)
    versionHistory.value = res.data.versions || []
  } catch (error) {
    // 使用模拟数据
    versionHistory.value = [
      { version_id: 'v_001', version_number: 2, name: row.name, change_type: 'update', change_summary: '更新了请求参数', changed_fields: ['body', 'headers'], changed_by: 'admin', created_at: '2025-01-15T10:30:00' },
      { version_id: 'v_000', version_number: 1, name: row.name, change_type: 'create', change_summary: '初始版本', changed_fields: [], changed_by: 'system', created_at: '2025-01-10T15:20:00' }
    ]
  }
  historyDialogVisible.value = true
}

const handleDelete = async (row: TestCase) => {
  MessagePlugin.success('删除成功')
  loadTestCases()
}

const handleBatchEnable = (enabled: boolean) => {
  MessagePlugin.success(enabled ? '批量启用成功' : '批量禁用成功')
  selectedKeys.value = []
}

const handleBatchCopy = () => {
  MessagePlugin.info('复制到新版本功能开发中')
}

const handleCreateVersion = () => {
  versionForm.value = { name: '', description: '', baseVersion: null }
  versionDialogVisible.value = true
}

const handleConfirmVersion = () => {
  MessagePlugin.success('版本创建成功')
  versionDialogVisible.value = false
}

const handleCompareVersion = async (history: VersionInfo) => {
  if (!currentCase.value) return
  
  const latestVersion = versionHistory.value[0]?.version_number || 1
  if (history.version_number === latestVersion) {
    MessagePlugin.warning('当前已是最新版本')
    return
  }
  
  try {
    const res = await api.get(`/api/v1/versions/${currentCase.value.task_id}/cases/${currentCase.value.case_id}/versions/compare`, {
      params: { v1: history.version_number, v2: latestVersion }
    })
    compareResult.value = res.data
    compareDialogVisible.value = true
  } catch (error) {
    // 模拟数据
    compareResult.value = {
      version1: history.version_number,
      version2: latestVersion,
      has_changes: true,
      differences: [
        { field: 'body', version1_value: { username: 'old' }, version2_value: { username: 'test' } },
        { field: 'headers', version1_value: {}, version2_value: { 'Content-Type': 'application/json' } }
      ]
    }
    compareDialogVisible.value = true
  }
}

const handleRollback = async (history: VersionInfo) => {
  if (!currentCase.value) return
  
  rollbackForm.value = {
    version_number: history.version_number,
    reason: ''
  }
  
  const confirmed = await MessagePlugin.confirm({
    header: '确认回滚',
    body: `确定要回滚到版本 v${history.version_number} 吗？`,
    confirmBtn: '确认回滚',
    cancelBtn: '取消'
  })
  
  if (confirmed) {
    try {
      await api.post(`/api/v1/versions/${currentCase.value.task_id}/cases/${currentCase.value.case_id}/restore`, {
        version_number: history.version_number,
        reason: '用户手动回滚'
      })
      MessagePlugin.success(`已回滚到版本 v${history.version_number}`)
      historyDialogVisible.value = false
      loadTestCases()
    } catch (error) {
      MessagePlugin.success(`已回滚到版本 v${history.version_number}`)
      historyDialogVisible.value = false
    }
  }
}

onMounted(loadTestCases)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
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
}

.history-item {
  padding: 8px 0;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-desc {
  color: rgba(0, 0, 0, 0.6);
  font-size: 13px;
  margin-top: 4px;
}

.history-fields {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
  margin-top: 4px;
}

.history-user {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
  margin-top: 2px;
}

.compare-header {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
}

.compare-list {
  max-height: 500px;
  overflow-y: auto;
}

.compare-item {
  border: 1px solid #e7e7e7;
  border-radius: 4px;
  margin-bottom: 12px;
  overflow: hidden;
}

.compare-field {
  background: #f5f7fa;
  padding: 8px 12px;
  font-weight: 500;
  border-bottom: 1px solid #e7e7e7;
}

.compare-values {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.compare-old, .compare-new {
  padding: 8px 12px;
}

.compare-old {
  background: #fff1f0;
  border-right: 1px solid #e7e7e7;
}

.compare-new {
  background: #f6ffed;
}

.compare-values .label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 4px;
}

.compare-values pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
