<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="tests-page">
    <!-- 工具栏 -->
    <PageToolbar
      v-model:search="filters.search"
      search-placeholder="搜索测试用例"
      @search="search"
    >
      <template #filters>
        <t-select
          v-model="filters.category"
          placeholder="用例类别"
          clearable
          style="width: 120px;"
          @change="search"
        >
          <t-option value="normal">正常场景</t-option>
          <t-option value="boundary">边界测试</t-option>
          <t-option value="exception">异常测试</t-option>
          <t-option value="security">安全测试</t-option>
        </t-select>
        <t-select
          v-model="filters.priority"
          placeholder="优先级"
          clearable
          style="width: 100px;"
          @change="search"
        >
          <t-option value="P0">P0</t-option>
          <t-option value="P1">P1</t-option>
          <t-option value="P2">P2</t-option>
          <t-option value="P3">P3</t-option>
        </t-select>
      </template>
      <template #actions>
        <t-button 
          theme="primary" 
          @click="handleBatchExecute" 
          :disabled="!hasSelection"
        >
          <template #icon><PlayIcon /></template>
          执行选中 ({{ selectionCount }})
        </t-button>
      </template>
    </PageToolbar>

    <!-- 测试用例列表 -->
    <DataTable
      :data="items"
      :columns="columns"
      :loading="loading"
      :pagination="pagination"
      :selected-keys="selectedIds"
      row-key="case_id"
      @page-change="handlePageChange"
      @select-change="handleSelectChange"
    >
      <template #endpoint="{ row }">
        <div class="endpoint-cell">
          <StatusTag type="method" :value="row.endpoint_method" size="small" />
          <span class="endpoint-path">{{ row.endpoint_path }}</span>
        </div>
      </template>
      <template #category="{ row }">
        <StatusTag type="category" :value="row.category" size="small" />
      </template>
      <template #priority="{ row }">
        <StatusTag type="priority" :value="row.priority" variant="outline" size="small" />
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
          <t-link theme="primary" @click="detailDialog.open(row)">详情</t-link>
          <t-link theme="primary" @click="openEdit(row)">编辑</t-link>
          <t-link theme="primary" @click="openCopy(row)">复制</t-link>
          <t-link theme="primary" @click="executeDialog.open([row.case_id])">执行</t-link>
          <t-popconfirm content="确定删除该测试用例？" @confirm="handleDelete(row)">
            <t-link theme="danger">删除</t-link>
          </t-popconfirm>
        </t-space>
      </template>
    </DataTable>

    <!-- 执行对话框 -->
    <t-dialog
      v-model:visible="executeDialog.visible.value"
      header="执行测试"
      :confirm-btn="{ content: '执行', loading: executeDialog.loading.value }"
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
      v-model:visible="detailDialog.visible.value"
      header="测试用例详情"
      size="600px"
    >
      <template #footer>
        <t-space>
          <t-button @click="detailDialog.close()">关闭</t-button>
          <t-button theme="primary" @click="openEdit(detailDialog.data.value)">编辑</t-button>
        </t-space>
      </template>
      <template v-if="detailDialog.data.value">
        <t-descriptions :column="1" bordered>
          <t-descriptions-item label="用例名称">{{ detailDialog.data.value.name }}</t-descriptions-item>
          <t-descriptions-item label="描述">{{ detailDialog.data.value.description || '-' }}</t-descriptions-item>
          <t-descriptions-item label="类别">
            <StatusTag type="category" :value="detailDialog.data.value.category" />
          </t-descriptions-item>
          <t-descriptions-item label="优先级">
            <StatusTag type="priority" :value="detailDialog.data.value.priority" variant="outline" />
          </t-descriptions-item>
          <t-descriptions-item label="请求方法">{{ detailDialog.data.value.method }}</t-descriptions-item>
          <t-descriptions-item label="请求URL">{{ detailDialog.data.value.url }}</t-descriptions-item>
          <t-descriptions-item label="期望状态码">{{ detailDialog.data.value.expected_status_code }}</t-descriptions-item>
        </t-descriptions>
        
        <t-divider>请求头</t-divider>
        <pre class="code-block">{{ safeStringifyJSON(detailDialog.data.value.headers) }}</pre>
        
        <t-divider>请求体</t-divider>
        <pre class="code-block">{{ safeStringifyJSON(detailDialog.data.value.body) }}</pre>
      </template>
    </t-drawer>

    <!-- 编辑对话框 -->
    <t-dialog
      v-model:visible="editDialog.visible.value"
      :header="isCreating ? '复制测试用例' : '编辑测试用例'"
      width="700px"
      :confirm-btn="{ content: '保存', loading: editDialog.loading.value }"
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
                <t-option v-for="m in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']" :key="m" :value="m">{{ m }}</t-option>
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
          <t-textarea v-model="editForm.headersStr" placeholder='{"Content-Type": "application/json"}' :rows="3" style="font-family: monospace;" />
        </t-form-item>
        <t-form-item label="查询参数 (JSON)">
          <t-textarea v-model="editForm.queryParamsStr" placeholder='{"page": 1, "size": 10}' :rows="2" style="font-family: monospace;" />
        </t-form-item>
        <t-form-item label="请求体 (JSON)">
          <t-textarea v-model="editForm.bodyStr" placeholder='{"key": "value"}' :rows="5" style="font-family: monospace;" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { PlayIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'
import { PageToolbar, DataTable, StatusTag } from '../../components'
import { useList, useTableSelection, useDialog } from '../../composables'
import { safeParseJSON, safeStringifyJSON } from '../../utils'

// =====================================================
// 列表数据
// =====================================================
const { items, loading, pagination, filters, handlePageChange, search, refresh } = useList({
  fetchFn: (params) => developmentApi.listTests(params),
  defaultParams: { search: '', category: '', priority: '' }
})

// 表格选择
const { selectedIds, handleSelectChange, hasSelection, selectionCount } = useTableSelection({ rowKey: 'case_id' })

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

// =====================================================
// 对话框
// =====================================================
const executeDialog = useDialog<string[]>()
const detailDialog = useDialog<any>()
const editDialog = useDialog<any>()
const isCreating = ref(false)

// 表单数据
const executeForm = reactive({
  base_url: 'http://localhost:8080',
  environment: 'local'
})

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

// =====================================================
// 事件处理
// =====================================================

// 切换启用状态
const handleToggle = async (row: any, enabled: boolean) => {
  try {
    await developmentApi.updateTest(row.case_id, { is_enabled: enabled })
    row.is_enabled = enabled ? 1 : 0
    MessagePlugin.success(enabled ? '已启用' : '已禁用')
  } catch (error) {
    console.error('切换状态失败:', error)
  }
}

// 打开编辑
const openEdit = (row: any) => {
  if (!row) return
  isCreating.value = false
  fillEditForm(row)
  detailDialog.close()
  editDialog.open(row)
}

// 打开复制
const openCopy = (row: any) => {
  isCreating.value = true
  fillEditForm(row, true)
  editDialog.open(row)
}

// 填充编辑表单
const fillEditForm = (row: any, isCopy = false) => {
  editForm.name = isCopy ? `${row.name} (副本)` : row.name || ''
  editForm.description = row.description || ''
  editForm.category = row.category || 'normal'
  editForm.priority = row.priority || 'medium'
  editForm.method = row.method || 'GET'
  editForm.url = row.url || ''
  editForm.expected_status_code = row.expected_status_code || 200
  editForm.max_response_time_ms = row.max_response_time_ms || 3000
  editForm.headersStr = safeStringifyJSON(row.headers)
  editForm.bodyStr = safeStringifyJSON(row.body)
  editForm.queryParamsStr = safeStringifyJSON(row.query_params)
}

// 确认编辑
const confirmEdit = async () => {
  if (!editForm.name.trim()) {
    MessagePlugin.warning('请输入用例名称')
    return
  }

  await editDialog.confirm(async () => {
    const data = {
      name: editForm.name,
      description: editForm.description,
      category: editForm.category,
      priority: editForm.priority,
      method: editForm.method,
      url: editForm.url,
      expected_status_code: editForm.expected_status_code,
      max_response_time_ms: editForm.max_response_time_ms,
      headers: safeParseJSON(editForm.headersStr, {}),
      body: safeParseJSON(editForm.bodyStr, null),
      query_params: safeParseJSON(editForm.queryParamsStr, {})
    }

    if (isCreating.value) {
      await developmentApi.copyTest(editDialog.data.value.case_id, data)
      MessagePlugin.success('复制成功')
    } else {
      await developmentApi.updateTest(editDialog.data.value.case_id, data)
      MessagePlugin.success('保存成功')
    }
    refresh()
  })
}

// 批量执行
const handleBatchExecute = () => {
  executeDialog.open([...selectedIds.value])
}

// 确认执行
const confirmExecute = async () => {
  await executeDialog.confirm(async () => {
    const res = await developmentApi.executeTests({
      test_case_ids: executeDialog.data.value!,
      base_url: executeForm.base_url,
      environment: executeForm.environment
    })
    MessagePlugin.success(`执行完成，通过: ${res.passed}/${res.total}，通过率: ${res.pass_rate}%`)
  })
}

// 删除
const handleDelete = async (row: any) => {
  try {
    await developmentApi.deleteTest(row.case_id)
    MessagePlugin.success('删除成功')
    refresh()
  } catch (error) {
    console.error('删除失败:', error)
  }
}
</script>

<style scoped>
.tests-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
