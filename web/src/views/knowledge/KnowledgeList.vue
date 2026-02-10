<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="knowledge-list">
    <div class="page-header">
      <h2>知识库管理</h2>
      <div class="header-actions">
        <t-button theme="primary" @click="showCreateDialog = true">
          <template #icon><add-icon /></template>
          添加知识
        </t-button>
        <t-button @click="refreshList">
          <template #icon><refresh-icon /></template>
          刷新
        </t-button>
      </div>
    </div>

    <!-- 统计信息 -->
    <t-row :gutter="20" class="stats-row">
      <t-col :span="6">
        <t-card hover class="stat-card">
          <div class="stat-value">{{ statistics.total || 0 }}</div>
          <div class="stat-label">知识总数</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card hover class="stat-card">
          <div class="stat-value">{{ statistics.by_status?.active || 0 }}</div>
          <div class="stat-label">活跃知识</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card hover class="stat-card pending">
          <div class="stat-value">{{ statistics.by_status?.pending || 0 }}</div>
          <div class="stat-label">待审核</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card hover class="stat-card">
          <div class="stat-value">{{ statistics.by_status?.archived || 0 }}</div>
          <div class="stat-label">已归档</div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 筛选区域 -->
    <t-card class="filter-card">
      <t-form :inline="true" class="filter-form">
        <t-form-item label="知识类型">
          <t-select v-model="filters.type" placeholder="全部" clearable style="width: 150px">
            <t-option label="项目配置" value="project_config" />
            <t-option label="业务规则" value="business_rule" />
            <t-option label="模块知识" value="module_context" />
            <t-option label="测试经验" value="test_experience" />
          </t-select>
        </t-form-item>
        <t-form-item label="状态">
          <t-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <t-option label="活跃" value="active" />
            <t-option label="待审核" value="pending" />
            <t-option label="已归档" value="archived" />
          </t-select>
        </t-form-item>
        <t-form-item label="标签">
          <t-input v-model="filters.tags" placeholder="多个用逗号分隔" style="width: 200px" />
        </t-form-item>
        <t-form-item label="关键词">
          <t-input v-model="filters.keyword" placeholder="搜索标题或内容" style="width: 200px" />
        </t-form-item>
        <t-form-item>
          <t-button theme="primary" @click="handleSearch">搜索</t-button>
          <t-button @click="resetFilters">重置</t-button>
        </t-form-item>
      </t-form>
    </t-card>

    <!-- 知识列表 -->
    <t-card class="list-card">
      <t-table :data="knowledgeList" :loading="loading" stripe>
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
        <t-table-column prop="scope" label="适用范围" width="150">
          <template #cell="{ row }">
            <code v-if="row.scope">{{ row.scope }}</code>
            <span v-else class="text-muted">-</span>
          </template>
        </t-table-column>
        <t-table-column prop="tags" label="标签" width="200">
          <template #cell="{ row }">
            <t-tag v-for="tag in row.tags?.slice(0, 3)" :key="tag" size="small" class="tag-item">
              {{ tag }}
            </t-tag>
            <span v-if="row.tags?.length > 3" class="text-muted">+{{ row.tags.length - 3 }}</span>
          </template>
        </t-table-column>
        <t-table-column prop="priority" label="优先级" width="80" align="center">
          <template #cell="{ row }">
            <t-tag v-if="row.priority > 0" theme="warning" size="small">{{ row.priority }}</t-tag>
            <span v-else>-</span>
          </template>
        </t-table-column>
        <t-table-column label="操作" width="150" fixed="right">
          <template #cell="{ row }">
            <t-button variant="text" size="small" @click="editKnowledge(row)">编辑</t-button>
            <t-button variant="text" theme="danger" size="small" @click="deleteKnowledge(row)">删除</t-button>
          </template>
        </t-table-column>
      </t-table>

      <t-pagination
        v-model:current="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-size-options="[10, 20, 50, 100]"
        show-jumper
        class="pagination"
        @change="handlePageChange"
        @page-size-change="handleSizeChange"
      />
    </t-card>

    <!-- 创建/编辑对话框 -->
    <t-dialog
      v-model:visible="showCreateDialog"
      :header="editingKnowledge ? '编辑知识' : '添加知识'"
      width="700px"
    >
      <t-form :data="formData" label-width="100px">
        <t-form-item label="标题" required>
          <t-input v-model="formData.title" placeholder="简洁描述知识内容" />
        </t-form-item>
        <t-form-item label="内容" required>
          <t-textarea
            v-model="formData.content"
            :rows="6"
            placeholder="详细描述知识内容，包含具体的配置值、规则等"
          />
        </t-form-item>
        <t-form-item label="类型">
          <t-select v-model="formData.type" style="width: 200px">
            <t-option label="项目配置" value="project_config" />
            <t-option label="业务规则" value="business_rule" />
            <t-option label="模块知识" value="module_context" />
            <t-option label="测试经验" value="test_experience" />
          </t-select>
        </t-form-item>
        <t-form-item label="子分类">
          <t-input v-model="formData.category" placeholder="可选，如 auth, header 等" />
        </t-form-item>
        <t-form-item label="适用范围">
          <t-input v-model="formData.scope" placeholder="如 /api/live/* 或模块名" />
        </t-form-item>
        <t-form-item label="优先级">
          <t-input-number v-model="formData.priority" :min="0" :max="10" />
        </t-form-item>
        <t-form-item label="标签">
          <t-select
            v-model="formData.tags"
            multiple
            filterable
            creatable
            placeholder="输入并回车添加"
            style="width: 100%"
          />
        </t-form-item>
      </t-form>
      <template #footer>
        <t-button @click="showCreateDialog = false">取消</t-button>
        <t-button theme="primary" @click="saveKnowledge" :loading="saving">保存</t-button>
      </template>
    </t-dialog>

    <!-- 详情对话框 -->
    <t-dialog v-model:visible="showDetailDialog" header="知识详情" width="600px">
      <div v-if="detailKnowledge" class="knowledge-detail">
        <div class="detail-item">
          <label>标题：</label>
          <span>{{ detailKnowledge.title }}</span>
        </div>
        <div class="detail-item">
          <label>类型：</label>
          <t-tag :theme="getTypeTagType(detailKnowledge.type)" size="small">
            {{ getTypeName(detailKnowledge.type) }}
          </t-tag>
        </div>
        <div class="detail-item">
          <label>内容：</label>
          <div class="content-box">{{ detailKnowledge.content }}</div>
        </div>
        <div class="detail-item" v-if="detailKnowledge.scope">
          <label>适用范围：</label>
          <code>{{ detailKnowledge.scope }}</code>
        </div>
        <div class="detail-item" v-if="detailKnowledge.tags?.length">
          <label>标签：</label>
          <t-tag v-for="tag in detailKnowledge.tags" :key="tag" size="small" class="tag-item">
            {{ tag }}
          </t-tag>
        </div>
      </div>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'
import { AddIcon, RefreshIcon } from 'tdesign-icons-vue-next'
import { knowledgeApi } from '../../api/v2'

// 状态
const loading = ref(false)
const saving = ref(false)
const knowledgeList = ref<any[]>([])
const statistics = ref<any>({})
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const editingKnowledge = ref<any>(null)
const detailKnowledge = ref<any>(null)

// 筛选
const filters = reactive({
  type: '',
  status: '',
  tags: '',
  keyword: ''
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 表单数据
const formData = reactive({
  title: '',
  content: '',
  type: 'project_config',
  category: '',
  scope: '',
  priority: 0,
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
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filters.type) params.type = filters.type
    if (filters.status) params.status = filters.status
    if (filters.tags) params.tags = filters.tags
    if (filters.keyword) params.keyword = filters.keyword

    const data: any = await knowledgeApi.list(params)

    knowledgeList.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    // axios 拦截器已处理错误提示
  } finally {
    loading.value = false
  }
}

// 加载统计
const loadStatistics = async () => {
  try {
    statistics.value = await knowledgeApi.getStatistics()
  } catch (error) {
    console.error('Failed to load statistics', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadList()
}

// 重置筛选
const resetFilters = () => {
  filters.type = ''
  filters.status = ''
  filters.tags = ''
  filters.keyword = ''
  handleSearch()
}

// 刷新
const refreshList = () => {
  loadList()
  loadStatistics()
}

// 分页
const handleSizeChange = () => {
  pagination.page = 1
  loadList()
}

const handlePageChange = () => {
  loadList()
}

// 显示详情
const showDetail = (row: any) => {
  detailKnowledge.value = row
  showDetailDialog.value = true
}

// 编辑
const editKnowledge = (row: any) => {
  editingKnowledge.value = row
  formData.title = row.title
  formData.content = row.content
  formData.type = row.type
  formData.category = row.category || ''
  formData.scope = row.scope || ''
  formData.priority = row.priority || 0
  formData.tags = row.tags || []
  showCreateDialog.value = true
}

// 保存
const saveKnowledge = async () => {
  if (!formData.title || !formData.content) {
    MessagePlugin.warning('请填写标题和内容')
    return
  }

  saving.value = true
  try {
    if (editingKnowledge.value) {
      await knowledgeApi.update(editingKnowledge.value.knowledge_id, formData)
      MessagePlugin.success('更新成功')
    } else {
      await knowledgeApi.create(formData)
      MessagePlugin.success('创建成功')
    }
    showCreateDialog.value = false
    resetForm()
    refreshList()
  } catch (error) {
    // axios 拦截器已处理错误提示
  } finally {
    saving.value = false
  }
}

// 删除
const deleteKnowledge = async (row: any) => {
  const confirmDialog = DialogPlugin.confirm({
    header: '确认删除',
    body: '确定要删除这条知识吗？',
    onConfirm: async () => {
      try {
        await knowledgeApi.delete(row.knowledge_id)
        MessagePlugin.success('删除成功')
        refreshList()
      } catch (error) {
        // axios 拦截器已处理错误提示
      }
    },
    onClose: () => {
      confirmDialog.destroy()
    }
  })
}

// 重置表单
const resetForm = () => {
  editingKnowledge.value = null
  formData.title = ''
  formData.content = ''
  formData.type = 'project_config'
  formData.category = ''
  formData.scope = ''
  formData.priority = 0
  formData.tags = []
}

// 初始化
onMounted(() => {
  loadList()
  loadStatistics()
})
</script>

<style scoped>
.knowledge-list {
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

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  color: #909399;
  margin-top: 8px;
}

.stat-card.pending .stat-value {
  color: #e6a23c;
}

.filter-card {
  margin-bottom: 20px;
}

.list-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

.tag-item {
  margin-right: 4px;
}

.text-muted {
  color: #909399;
}

.knowledge-detail .detail-item {
  margin-bottom: 16px;
}

.knowledge-detail .detail-item label {
  font-weight: bold;
  margin-right: 8px;
}

.content-box {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  margin-top: 8px;
}
</style>
