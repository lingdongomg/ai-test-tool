<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="pending-review">
    <div class="page-header">
      <h2>待审核知识</h2>
      <div class="header-actions">
        <t-button @click="loadList">
          <template #icon><refresh-icon /></template>
          刷新
        </t-button>
      </div>
    </div>

    <t-alert
      v-if="pendingList.length > 0"
      theme="warning"
      :closable="false"
      class="alert-box"
    >
      有 {{ pendingList.length }} 条知识等待审核。这些知识来自AI自动学习，请确认其准确性后再批准。
    </t-alert>

    <t-card class="list-card">
      <div class="batch-actions" v-if="selectedIds.length > 0">
        <span>已选择 {{ selectedIds.length }} 项</span>
        <t-button theme="success" size="small" @click="batchApprove">批量通过</t-button>
        <t-button theme="danger" size="small" @click="batchReject">批量拒绝</t-button>
      </div>

      <t-table
        :data="pendingList"
        :loading="loading"
        :selected-row-keys="selectedIds"
        @select-change="handleSelectionChange"
        row-key="knowledge_id"
        stripe
      >
        <t-table-column type="selection" width="55" />
        <t-table-column prop="title" label="标题" min-width="200">
          <template #cell="{ row }">
            <t-link theme="primary" @click="showDetail(row)">{{ row.title }}</t-link>
          </template>
        </t-table-column>
        <t-table-column prop="type" label="类型" width="120">
          <template #cell="{ row }">
            <t-tag :theme="getTypeTagType(row.type)" size="small">
              {{ getTypeName(row.type) }}
            </t-tag>
          </template>
        </t-table-column>
        <t-table-column prop="content" label="内容预览" min-width="300">
          <template #cell="{ row }">
            <div class="content-preview">{{ row.content?.slice(0, 100) }}...</div>
          </template>
        </t-table-column>
        <t-table-column prop="scope" label="适用范围" width="150">
          <template #cell="{ row }">
            <code v-if="row.scope">{{ row.scope }}</code>
            <span v-else class="text-muted">-</span>
          </template>
        </t-table-column>
        <t-table-column label="操作" width="180" fixed="right">
          <template #cell="{ row }">
            <t-button variant="text" theme="success" size="small" @click="approveOne(row)">通过</t-button>
            <t-button variant="text" theme="warning" size="small" @click="editAndApprove(row)">编辑</t-button>
            <t-button variant="text" theme="danger" size="small" @click="rejectOne(row)">拒绝</t-button>
          </template>
        </t-table-column>
      </t-table>

      <t-empty v-if="!loading && pendingList.length === 0" description="暂无待审核知识" />
    </t-card>

    <!-- 详情/编辑对话框 -->
    <t-dialog
      v-model:visible="showEditDialog"
      :header="isEditing ? '编辑并审核' : '知识详情'"
      width="700px"
    >
      <t-form v-if="currentKnowledge" :data="editForm" label-width="100px">
        <t-form-item label="标题">
          <t-input v-model="editForm.title" :disabled="!isEditing" />
        </t-form-item>
        <t-form-item label="类型">
          <t-select v-model="editForm.type" :disabled="!isEditing" style="width: 200px">
            <t-option label="项目配置" value="project_config" />
            <t-option label="业务规则" value="business_rule" />
            <t-option label="模块知识" value="module_context" />
            <t-option label="测试经验" value="test_experience" />
          </t-select>
        </t-form-item>
        <t-form-item label="内容">
          <t-textarea
            v-model="editForm.content"
            :rows="8"
            :disabled="!isEditing"
          />
        </t-form-item>
        <t-form-item label="适用范围">
          <t-input v-model="editForm.scope" :disabled="!isEditing" />
        </t-form-item>
        <t-form-item label="标签">
          <t-select
            v-model="editForm.tags"
            multiple
            filterable
            creatable
            :disabled="!isEditing"
            style="width: 100%"
          />
        </t-form-item>
      </t-form>
      <template #footer>
        <t-button @click="showEditDialog = false">取消</t-button>
        <template v-if="isEditing">
          <t-button theme="primary" @click="saveAndApprove" :loading="saving">保存并通过</t-button>
        </template>
        <template v-else>
          <t-button theme="success" @click="approveOne(currentKnowledge!)">通过</t-button>
          <t-button theme="warning" @click="startEdit">编辑</t-button>
          <t-button theme="danger" @click="rejectOne(currentKnowledge!)">拒绝</t-button>
        </template>
      </template>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'
import { RefreshIcon } from 'tdesign-icons-vue-next'

const API_BASE = '/api/v2/knowledge'

// 状态
const loading = ref(false)
const saving = ref(false)
const pendingList = ref<any[]>([])
const selectedIds = ref<string[]>([])
const showEditDialog = ref(false)
const isEditing = ref(false)
const currentKnowledge = ref<any>(null)

// 编辑表单
const editForm = reactive({
  title: '',
  content: '',
  type: 'project_config',
  scope: '',
  tags: [] as string[]
})

// 类型映射
const typeNames: Record<string, string> = {
  project_config: '项目配置',
  business_rule: '业务规则',
  module_context: '模块知识',
  test_experience: '测试经验'
}

const typeTagTypes: Record<string, string> = {
  project_config: 'primary',
  business_rule: 'success',
  module_context: 'warning',
  test_experience: 'info'
}

const getTypeName = (type: string) => typeNames[type] || type
const getTypeTagType = (type: string) => typeTagTypes[type] || ''

// 加载列表
const loadList = async () => {
  loading.value = true
  try {
    const response = await fetch(`${API_BASE}/pending?limit=100`)
    const data = await response.json()
    pendingList.value = data.items || []
  } catch (error) {
    MessagePlugin.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedIds.value = selection.map(item => item.knowledge_id)
}

// 显示详情
const showDetail = (row: any) => {
  currentKnowledge.value = row
  editForm.title = row.title
  editForm.content = row.content
  editForm.type = row.type
  editForm.scope = row.scope || ''
  editForm.tags = row.tags || []
  isEditing.value = false
  showEditDialog.value = true
}

// 开始编辑
const startEdit = () => {
  isEditing.value = true
}

// 编辑并审核
const editAndApprove = (row: any) => {
  showDetail(row)
  isEditing.value = true
}

// 保存并通过
const saveAndApprove = async () => {
  if (!currentKnowledge.value) return

  saving.value = true
  try {
    // 先更新
    const updateResponse = await fetch(`${API_BASE}/${currentKnowledge.value.knowledge_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editForm)
    })

    if (!updateResponse.ok) throw new Error('更新失败')

    // 再审核通过
    await doReview([currentKnowledge.value.knowledge_id], 'approve')

    showEditDialog.value = false
    loadList()
  } catch (error) {
    MessagePlugin.error('操作失败')
  } finally {
    saving.value = false
  }
}

// 审核操作
const doReview = async (ids: string[], action: 'approve' | 'reject') => {
  const response = await fetch(`${API_BASE}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ knowledge_ids: ids, action })
  })

  if (!response.ok) throw new Error('审核失败')

  const result = await response.json()
  MessagePlugin.success(result.message)
}

// 通过单个
const approveOne = async (row: any) => {
  try {
    await doReview([row.knowledge_id], 'approve')
    showEditDialog.value = false
    loadList()
  } catch (error) {
    MessagePlugin.error('操作失败')
  }
}

// 拒绝单个
const rejectOne = async (row: any) => {
  const confirmDialog = DialogPlugin.confirm({
    header: '确认拒绝',
    body: '确定要拒绝这条知识吗？',
    onConfirm: async () => {
      try {
        await doReview([row.knowledge_id], 'reject')
        showEditDialog.value = false
        loadList()
      } catch (error) {
        MessagePlugin.error('拒绝失败')
      }
    },
    onClose: () => {
      confirmDialog.destroy()
    }
  })
}

// 批量通过
const batchApprove = async () => {
  if (selectedIds.value.length === 0) return

  const confirmDialog = DialogPlugin.confirm({
    header: '批量通过',
    body: `确定要通过选中的 ${selectedIds.value.length} 条知识吗？`,
    onConfirm: async () => {
      try {
        await doReview(selectedIds.value, 'approve')
        MessagePlugin.success(`已通过 ${selectedIds.value.length} 条知识`)
        selectedIds.value = []
        loadList()
      } catch (error) {
        MessagePlugin.error('批量通过失败')
      }
    },
    onClose: () => {
      confirmDialog.destroy()
    }
  })
}

// 批量拒绝
const batchReject = async () => {
  if (selectedIds.value.length === 0) return

  const confirmDialog = DialogPlugin.confirm({
    header: '批量拒绝',
    body: `确定要拒绝选中的 ${selectedIds.value.length} 条知识吗？`,
    onConfirm: async () => {
      try {
        await doReview(selectedIds.value, 'reject')
        MessagePlugin.success(`已拒绝 ${selectedIds.value.length} 条知识`)
        selectedIds.value = []
        loadList()
      } catch (error) {
        MessagePlugin.error('批量拒绝失败')
      }
    },
    onClose: () => {
      confirmDialog.destroy()
    }
  })
}

// 初始化
onMounted(() => {
  loadList()
})
</script>

<style scoped>
.pending-review {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}

.alert-box {
  margin-bottom: 20px;
}

.list-card {
  margin-bottom: 20px;
}

.batch-actions {
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.content-preview {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.text-muted {
  color: #909399;
}
</style>
