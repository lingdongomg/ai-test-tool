<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="knowledge-list">
    <div class="page-header">
      <h2>知识库管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          添加知识
        </el-button>
        <el-button @click="refreshList">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 统计信息 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ statistics.total || 0 }}</div>
          <div class="stat-label">知识总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ statistics.by_status?.active || 0 }}</div>
          <div class="stat-label">活跃知识</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card pending">
          <div class="stat-value">{{ statistics.by_status?.pending || 0 }}</div>
          <div class="stat-label">待审核</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ statistics.by_status?.archived || 0 }}</div>
          <div class="stat-label">已归档</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="知识类型">
          <el-select v-model="filters.type" placeholder="全部" clearable style="width: 150px">
            <el-option label="项目配置" value="project_config" />
            <el-option label="业务规则" value="business_rule" />
            <el-option label="模块知识" value="module_context" />
            <el-option label="测试经验" value="test_experience" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="活跃" value="active" />
            <el-option label="待审核" value="pending" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="filters.tags" placeholder="多个用逗号分隔" style="width: 200px" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索标题或内容" style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 知识列表 -->
    <el-card class="list-card">
      <el-table :data="knowledgeList" v-loading="loading" stripe>
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="showDetail(row)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)" size="small">
              {{ getTypeName(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scope" label="适用范围" width="150">
          <template #default="{ row }">
            <code v-if="row.scope">{{ row.scope }}</code>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" width="200">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags?.slice(0, 3)" :key="tag" size="small" class="tag-item">
              {{ tag }}
            </el-tag>
            <span v-if="row.tags?.length > 3" class="text-muted">+{{ row.tags.length - 3 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.priority > 0" type="warning" size="small">{{ row.priority }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="editKnowledge(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="deleteKnowledge(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingKnowledge ? '编辑知识' : '添加知识'"
      width="700px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="formData.title" placeholder="简洁描述知识内容" />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="formData.content"
            type="textarea"
            :rows="6"
            placeholder="详细描述知识内容，包含具体的配置值、规则等"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="formData.type" style="width: 200px">
            <el-option label="项目配置" value="project_config" />
            <el-option label="业务规则" value="business_rule" />
            <el-option label="模块知识" value="module_context" />
            <el-option label="测试经验" value="test_experience" />
          </el-select>
        </el-form-item>
        <el-form-item label="子分类">
          <el-input v-model="formData.category" placeholder="可选，如 auth, header 等" />
        </el-form-item>
        <el-form-item label="适用范围">
          <el-input v-model="formData.scope" placeholder="如 /api/live/* 或模块名" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="formData.priority" :min="0" :max="10" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="formData.tags"
            multiple
            filterable
            allow-create
            placeholder="输入并回车添加"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveKnowledge" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="知识详情" width="600px">
      <div v-if="detailKnowledge" class="knowledge-detail">
        <div class="detail-item">
          <label>标题：</label>
          <span>{{ detailKnowledge.title }}</span>
        </div>
        <div class="detail-item">
          <label>类型：</label>
          <el-tag :type="getTypeTagType(detailKnowledge.type)" size="small">
            {{ getTypeName(detailKnowledge.type) }}
          </el-tag>
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
          <el-tag v-for="tag in detailKnowledge.tags" :key="tag" size="small" class="tag-item">
            {{ tag }}
          </el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

const API_BASE = '/api/v2/knowledge'

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
    const params = new URLSearchParams()
    if (filters.type) params.append('type', filters.type)
    if (filters.status) params.append('status', filters.status)
    if (filters.tags) params.append('tags', filters.tags)
    if (filters.keyword) params.append('keyword', filters.keyword)
    params.append('page', String(pagination.page))
    params.append('page_size', String(pagination.pageSize))

    const response = await fetch(`${API_BASE}?${params}`)
    const data = await response.json()
    
    knowledgeList.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 加载统计
const loadStatistics = async () => {
  try {
    const response = await fetch(`${API_BASE}/statistics`)
    statistics.value = await response.json()
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
    ElMessage.warning('请填写标题和内容')
    return
  }

  saving.value = true
  try {
    const url = editingKnowledge.value
      ? `${API_BASE}/${editingKnowledge.value.knowledge_id}`
      : API_BASE
    const method = editingKnowledge.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })

    if (response.ok) {
      ElMessage.success(editingKnowledge.value ? '更新成功' : '创建成功')
      showCreateDialog.value = false
      resetForm()
      refreshList()
    } else {
      throw new Error('保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 删除
const deleteKnowledge = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除这条知识吗？', '确认删除', {
      type: 'warning'
    })

    const response = await fetch(`${API_BASE}/${row.knowledge_id}`, {
      method: 'DELETE'
    })

    if (response.ok) {
      ElMessage.success('删除成功')
      refreshList()
    }
  } catch (error) {
    // 用户取消
  }
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
