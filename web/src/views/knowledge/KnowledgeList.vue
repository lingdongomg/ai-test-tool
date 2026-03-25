<!-- 知识库管理页面 -->
<template>
  <div class="knowledge-list">
    <div class="page-header">
      <h2>知识库管理</h2>
      <div class="header-actions">
        <t-button theme="primary" @click="showCreateDialog = true">
          <template #icon><add-icon /></template>
          添加知识
        </t-button>
        <t-button @click="showLearnDialog = true">
          <template #icon><add-icon /></template>
          从文本学习
        </t-button>
        <t-button @click="showLogLearnDialog = true">
          <template #icon><cloud-upload-icon /></template>
          从日志学习
        </t-button>
        <t-button @click="handleRebuildIndex" :loading="rebuildingIndex">
          重建索引
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
          <div class="stat-value active">{{ statistics.by_status?.active || 0 }}</div>
          <div class="stat-label">活跃知识</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card hover class="stat-card">
          <div class="stat-value pending">{{ statistics.by_status?.pending || 0 }}</div>
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
      <t-row :gutter="16" align="middle">
        <t-col :flex="1">
          <t-select v-model="filters.type" placeholder="知识类型" clearable style="width: 150px" @change="handleSearch">
            <t-option label="认证配置" value="auth_config" />
            <t-option label="错误模式" value="error_pattern" />
            <t-option label="性能基线" value="performance_baseline" />
            <t-option label="业务规则" value="business_rule" />
            <t-option label="API依赖" value="api_dependency" />
            <t-option label="安全规则" value="security_rule" />
            <t-option label="环境配置" value="env_config" />
            <t-option label="测试经验" value="test_experience" />
            <t-option label="项目配置(旧)" value="project_config" />
            <t-option label="模块知识(旧)" value="module_context" />
          </t-select>
        </t-col>
        <t-col :flex="1">
          <t-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
            <t-option label="活跃" value="active" />
            <t-option label="待审核" value="pending" />
            <t-option label="已归档" value="archived" />
          </t-select>
        </t-col>
        <t-col :flex="1">
          <t-input v-model="filters.tags" placeholder="标签(逗号分隔)" clearable style="width: 180px" @enter="handleSearch" />
        </t-col>
        <t-col :flex="1">
          <t-input v-model="filters.keyword" placeholder="搜索标题或内容" clearable style="width: 200px" @enter="handleSearch" />
        </t-col>
        <t-col>
          <t-space>
            <t-button theme="primary" @click="handleSearch">搜索</t-button>
            <t-button @click="resetFilters">重置</t-button>
          </t-space>
        </t-col>
      </t-row>
    </t-card>

    <!-- 知识列表 -->
    <t-card class="list-card">
      <t-table
        :data="knowledgeList"
        :columns="columns"
        :loading="loading"
        :pagination="tablePagination"
        row-key="knowledge_id"
        hover
        stripe
        @page-change="handlePageChange"
      >
        <template #empty>
          <div style="padding: 48px 0; text-align: center; color: var(--td-text-color-placeholder);">
            <p style="font-size: 14px; margin-bottom: 8px;">暂无知识条目</p>
            <p style="font-size: 12px;">点击"添加知识"手动录入，或使用"从日志学习"自动提取知识</p>
          </div>
        </template>
        <template #title="{ row }">
          <t-link theme="primary" @click="showDetail(row)">{{ row.title }}</t-link>
        </template>
        <template #type="{ row }">
          <t-tag :theme="getTypeTagType(row.type)" variant="light" size="small">
            {{ getTypeName(row.type) }}
          </t-tag>
        </template>
        <template #scope="{ row }">
          <code v-if="row.scope" style="font-size: 12px;">{{ row.scope }}</code>
          <span v-else class="text-muted">-</span>
        </template>
        <template #tags="{ row }">
          <t-space size="small" v-if="row.tags?.length">
            <t-tag v-for="tag in row.tags.slice(0, 3)" :key="tag" size="small" variant="light">
              {{ tag }}
            </t-tag>
            <span v-if="row.tags.length > 3" class="text-muted">+{{ row.tags.length - 3 }}</span>
          </t-space>
          <span v-else class="text-muted">-</span>
        </template>
        <template #priority="{ row }">
          <t-tag v-if="row.priority > 0" theme="warning" size="small">{{ row.priority }}</t-tag>
          <span v-else>-</span>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="editKnowledge(row)">编辑</t-link>
            <t-popconfirm content="确定删除该知识？" @confirm="deleteKnowledge(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
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
            <t-option label="认证配置" value="auth_config" />
            <t-option label="错误模式" value="error_pattern" />
            <t-option label="性能基线" value="performance_baseline" />
            <t-option label="业务规则" value="business_rule" />
            <t-option label="API依赖" value="api_dependency" />
            <t-option label="安全规则" value="security_rule" />
            <t-option label="环境配置" value="env_config" />
            <t-option label="测试经验" value="test_experience" />
          </t-select>
        </t-form-item>
        <t-form-item label="子分类">
          <t-input v-model="formData.category" placeholder="可选，如 bearer_token, client_error_4xx 等" />
        </t-form-item>
        <t-form-item label="适用范围">
          <t-input v-model="formData.scope" placeholder="如 /api/user/* 或模块名" />
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
        <t-button @click="cancelCreateDialog">取消</t-button>
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
          <t-tag :theme="getTypeTagType(detailKnowledge.type)" variant="light" size="small">
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
          <t-space size="small">
            <t-tag v-for="tag in detailKnowledge.tags" :key="tag" size="small" variant="light">{{ tag }}</t-tag>
          </t-space>
        </div>
      </div>
    </t-dialog>

    <!-- 从文本学习对话框 -->
    <t-dialog
      v-model:visible="showLearnDialog"
      header="从文本学习知识"
      width="600px"
    >
      <t-form :data="learnForm" label-width="100px">
        <t-form-item label="文本内容" required>
          <t-textarea
            v-model="learnForm.content"
            :rows="8"
            placeholder="粘贴日志片段、API文档、错误信息等文本，系统将自动提取知识"
          />
        </t-form-item>
        <t-form-item label="来源说明">
          <t-input v-model="learnForm.source_ref" placeholder="可选，如：生产日志 2026-03" />
        </t-form-item>
        <t-form-item label="自动审核">
          <t-switch v-model="learnForm.auto_approve" />
          <span style="margin-left: 8px; color: var(--td-text-color-placeholder);">高置信度知识自动通过审核</span>
        </t-form-item>
      </t-form>
      <template #footer>
        <t-button @click="showLearnDialog = false">取消</t-button>
        <t-button theme="primary" @click="handleLearn" :loading="learning">开始学习</t-button>
      </template>
    </t-dialog>

    <!-- 从日志学习对话框 -->
    <t-dialog
      v-model:visible="showLogLearnDialog"
      header="从日志学习知识"
      width="700px"
    >
      <t-tabs v-model="logLearnTab">
        <t-tab-panel value="task" label="从分析任务学习">
          <div style="padding: 16px 0;">
            <t-form label-width="100px">
              <t-form-item label="选择任务" required>
                <t-select
                  v-model="logLearnForm.task_id"
                  placeholder="选择已完成的分析任务"
                  style="width: 100%"
                  :loading="loadingTasks"
                  filterable
                >
                  <t-option
                    v-for="task in completedTasks"
                    :key="task.task_id"
                    :value="task.task_id"
                    :label="`${task.name} (${task.total_requests || 0}个请求)`"
                  />
                </t-select>
                <div v-if="completedTasks.length === 0 && !loadingTasks" style="margin-top: 8px; color: var(--td-text-color-placeholder); font-size: 12px;">
                  暂无已完成的分析任务，请先到「日志洞察」页面上传日志
                </div>
              </t-form-item>
              <t-form-item label="自动审核">
                <t-switch v-model="logLearnForm.auto_approve" />
                <span style="margin-left: 8px; color: var(--td-text-color-placeholder);">高置信度知识自动通过审核</span>
              </t-form-item>
            </t-form>
          </div>
        </t-tab-panel>
        <t-tab-panel value="file" label="上传日志文件">
          <div style="padding: 16px 0;">
            <t-form label-width="100px">
              <t-form-item label="日志文件" required>
                <t-upload
                  v-model="logLearnFiles"
                  theme="custom"
                  accept=".log,.txt,.json"
                  :auto-upload="false"
                  :max="1"
                  @change="handleFileChange"
                >
                  <template #default>
                    <div class="upload-area" :class="{ 'has-file': logLearnFiles.length }">
                      <template v-if="!logLearnFiles.length">
                        <cloud-upload-icon style="font-size: 48px; color: var(--td-brand-color); margin-bottom: 8px;" />
                        <div style="font-size: 14px; font-weight: 500;">点击或拖拽上传日志文件</div>
                        <div style="font-size: 12px; color: var(--td-text-color-placeholder); margin-top: 4px;">
                          支持 .log .txt .json 格式，最大 100MB
                        </div>
                      </template>
                      <template v-else>
                        <div style="display: flex; align-items: center; gap: 8px;">
                          <t-icon name="file" />
                          <span>{{ logLearnFiles[0]?.name || '已选择文件' }}</span>
                          <t-tag size="small" theme="success">已选择</t-tag>
                        </div>
                      </template>
                    </div>
                  </template>
                </t-upload>
              </t-form-item>
              <t-form-item label="来源说明">
                <t-input v-model="logLearnForm.source_ref" placeholder="可选，如：生产日志 2026-03" />
              </t-form-item>
              <t-form-item label="最大行数">
                <t-input-number v-model="logLearnForm.max_lines" :min="100" placeholder="不限制" style="width: 200px" />
              </t-form-item>
              <t-form-item label="自动审核">
                <t-switch v-model="logLearnForm.auto_approve" />
                <span style="margin-left: 8px; color: var(--td-text-color-placeholder);">高置信度知识自动通过审核</span>
              </t-form-item>
            </t-form>
          </div>
        </t-tab-panel>
      </t-tabs>
      <template #footer>
        <t-button @click="showLogLearnDialog = false">取消</t-button>
        <t-button theme="primary" @click="handleLogLearn" :loading="logLearning">开始学习</t-button>
      </template>
    </t-dialog>

    <!-- 学习结果对话框 -->
    <t-dialog
      v-model:visible="showLearnResultDialog"
      header="学习结果"
      width="700px"
    >
      <div v-if="learnResult">
        <t-alert theme="success" :message="learnResult.message" style="margin-bottom: 16px;" />
        <t-table
          :data="learnResult.items || []"
          :columns="resultColumns"
          row-key="knowledge_id"
          stripe
          hover
          v-if="learnResult.items?.length"
        >
          <template #type="{ row }">
            <t-tag :theme="getTypeTagType(row.type)" variant="light" size="small">{{ getTypeName(row.type) }}</t-tag>
          </template>
          <template #confidence="{ row }">
            <t-tag :theme="row.confidence >= 0.8 ? 'success' : row.confidence >= 0.5 ? 'warning' : 'default'" size="small">
              {{ (row.confidence * 100).toFixed(0) }}%
            </t-tag>
          </template>
          <template #status="{ row }">
            <t-tag v-if="row.status === 'active'" theme="success" size="small">已通过</t-tag>
            <t-tag v-else theme="warning" size="small">待审核</t-tag>
          </template>
        </t-table>
        <div v-else style="padding: 24px; text-align: center; color: var(--td-text-color-placeholder);">
          未提取到知识条目
        </div>
      </div>
      <template #footer>
        <t-button theme="primary" @click="closeLearnResult">关闭</t-button>
      </template>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon, RefreshIcon, CloudUploadIcon } from 'tdesign-icons-vue-next'
import { knowledgeApi, insightsApi } from '../../api/v2'
import type { PrimaryTableCol } from 'tdesign-vue-next'

// 状态
const loading = ref(false)
const saving = ref(false)
const learning = ref(false)
const rebuildingIndex = ref(false)
const knowledgeList = ref<any[]>([])
const statistics = ref<any>({})
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showLearnDialog = ref(false)
const editingKnowledge = ref<any>(null)
const detailKnowledge = ref<any>(null)

// 从日志学习
const showLogLearnDialog = ref(false)
const logLearning = ref(false)
const logLearnTab = ref('task')
const loadingTasks = ref(false)
const completedTasks = ref<any[]>([])
const logLearnFiles = ref<any[]>([])
const logLearnForm = reactive({
  task_id: '',
  auto_approve: true,
  source_ref: '',
  max_lines: null as number | null,
})

// 学习结果
const showLearnResultDialog = ref(false)
const learnResult = ref<any>(null)

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
  type: 'business_rule',
  category: '',
  scope: '',
  priority: 0,
  tags: [] as string[]
})

// 类型映射（V2 扩展 8 种 + 旧类型兼容）
const typeNames: Record<string, string> = {
  auth_config: '认证配置',
  error_pattern: '错误模式',
  performance_baseline: '性能基线',
  business_rule: '业务规则',
  api_dependency: 'API依赖',
  security_rule: '安全规则',
  env_config: '环境配置',
  test_experience: '测试经验',
  // 旧类型兼容
  project_config: '项目配置',
  module_context: '模块知识',
}

const typeTagTypes: Record<string, string> = {
  auth_config: 'primary',
  error_pattern: 'danger',
  performance_baseline: 'warning',
  business_rule: 'success',
  api_dependency: 'primary',
  security_rule: 'danger',
  env_config: 'default',
  test_experience: 'warning',
  project_config: 'primary',
  module_context: 'default',
}

const getTypeName = (type: string) => typeNames[type] || type
const getTypeTagType = (type: string) => (typeTagTypes[type] || 'default') as any

// TDesign 表格列定义
const columns: PrimaryTableCol[] = [
  { colKey: 'title', title: '标题', ellipsis: true, minWidth: 200 },
  { colKey: 'type', title: '类型', width: 120 },
  { colKey: 'scope', title: '适用范围', width: 180, ellipsis: true },
  { colKey: 'tags', title: '标签', width: 200 },
  { colKey: 'priority', title: '优先级', width: 80, align: 'center' },
  { colKey: 'op', title: '操作', width: 130, fixed: 'right' },
]

// 学习结果列定义
const resultColumns: PrimaryTableCol[] = [
  { colKey: 'title', title: '标题', ellipsis: true },
  { colKey: 'type', title: '类型', width: 100 },
  { colKey: 'confidence', title: '置信度', width: 80, align: 'center' },
  { colKey: 'status', title: '状态', width: 80 },
]

// TDesign 分页配置
const tablePagination = computed(() => ({
  current: pagination.page,
  pageSize: pagination.pageSize,
  total: pagination.total,
  pageSizeOptions: [10, 20, 50, 100],
  showJumper: true,
}))

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
    console.error('加载知识列表失败:', error)
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

// 分页变化
const handlePageChange = (pageInfo: any) => {
  pagination.page = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
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
    console.error('保存知识失败:', error)
  } finally {
    saving.value = false
  }
}

// 删除
const deleteKnowledge = async (row: any) => {
  try {
    await knowledgeApi.delete(row.knowledge_id)
    MessagePlugin.success('删除成功')
    refreshList()
  } catch (error) {
    console.error('删除知识失败:', error)
  }
}

// 重置表单
const resetForm = () => {
  editingKnowledge.value = null
  formData.title = ''
  formData.content = ''
  formData.type = 'business_rule'
  formData.category = ''
  formData.scope = ''
  formData.priority = 0
  formData.tags = []
}

const cancelCreateDialog = () => {
  showCreateDialog.value = false
  resetForm()
}

// 从文本学习
const learnForm = reactive({
  content: '',
  source_ref: '',
  auto_approve: true
})

const handleLearn = async () => {
  if (!learnForm.content.trim()) {
    MessagePlugin.warning('请输入文本内容')
    return
  }
  learning.value = true
  try {
    const result: any = await knowledgeApi.learn({
      content: learnForm.content,
      source_ref: learnForm.source_ref || undefined,
      auto_approve: learnForm.auto_approve
    })
    showLearnDialog.value = false
    learnResult.value = result
    showLearnResultDialog.value = true
    learnForm.content = ''
    learnForm.source_ref = ''
    refreshList()
  } catch (error) {
    // error handled by interceptor
  } finally {
    learning.value = false
  }
}

// 重建索引
const handleRebuildIndex = async () => {
  rebuildingIndex.value = true
  try {
    const res: any = await knowledgeApi.rebuildIndex()
    MessagePlugin.success(res.message || '索引重建完成')
  } catch (error) {
    // error handled by interceptor
  } finally {
    rebuildingIndex.value = false
  }
}

// 加载已完成的分析任务
const loadCompletedTasks = async () => {
  loadingTasks.value = true
  try {
    const data: any = await insightsApi.listTasks({ status: 'completed', page_size: 100 })
    completedTasks.value = data.items || []
  } catch (error) {
    console.error('加载任务列表失败:', error)
    completedTasks.value = []
  } finally {
    loadingTasks.value = false
  }
}

// 文件选择回调
const handleFileChange = (value: any) => {
  logLearnFiles.value = value || []
}

// 从日志学习
const handleLogLearn = async () => {
  logLearning.value = true
  try {
    let result: any

    if (logLearnTab.value === 'task') {
      if (!logLearnForm.task_id) {
        MessagePlugin.warning('请选择分析任务')
        logLearning.value = false
        return
      }
      result = await knowledgeApi.learnFromTask({
        task_id: logLearnForm.task_id,
        auto_approve: logLearnForm.auto_approve,
      })
      // 从任务学习是同步的，显示结果
      showLogLearnDialog.value = false
      learnResult.value = result
      showLearnResultDialog.value = true
      MessagePlugin.success(result.message || '知识学习完成')
    } else {
      // 从文件学习 — 异步模式
      if (!logLearnFiles.value.length) {
        MessagePlugin.warning('请选择日志文件')
        logLearning.value = false
        return
      }
      const fileObj = logLearnFiles.value[0]
      const file = fileObj?.raw || fileObj
      if (!file) {
        MessagePlugin.warning('文件读取失败，请重新选择')
        logLearning.value = false
        return
      }
      result = await knowledgeApi.learnFromFile(file, {
        auto_approve: logLearnForm.auto_approve,
        source_ref: logLearnForm.source_ref || undefined,
        max_lines: logLearnForm.max_lines || undefined,
      })
      // 文件学习是异步的，立即关闭弹窗
      showLogLearnDialog.value = false
      const taskId = result.task_id || ''
      MessagePlugin.success({
        content: `文件已上传，正在后台学习知识${taskId ? `（任务 ${taskId}）` : ''}，完成后可在列表中查看`,
        duration: 5000,
      })
      // 重置表单
      logLearnForm.task_id = ''
      logLearnForm.source_ref = ''
      logLearnForm.max_lines = null
      logLearnFiles.value = []
    }
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '知识学习失败'
    MessagePlugin.error(msg)
  } finally {
    logLearning.value = false
  }
}

// 关闭学习结果
const closeLearnResult = () => {
  showLearnResultDialog.value = false
  learnResult.value = null
  logLearnForm.task_id = ''
  logLearnForm.source_ref = ''
  logLearnForm.max_lines = null
  logLearnFiles.value = []
  refreshList()
}

// 初始化
onMounted(() => {
  loadList()
  loadStatistics()
})

// 打开日志学习对话框时加载任务
watch(showLogLearnDialog, (visible) => {
  if (visible) {
    loadCompletedTasks()
  }
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

.header-actions {
  display: flex;
  gap: 8px;
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
  color: var(--td-brand-color, #0052d9);
}

.stat-value.active {
  color: var(--td-success-color, #2ba471);
}

.stat-value.pending {
  color: var(--td-warning-color, #e37318);
}

.stat-label {
  color: var(--td-text-color-secondary);
  margin-top: 8px;
}

.filter-card {
  margin-bottom: 20px;
}

.list-card {
  margin-bottom: 20px;
}

.text-muted {
  color: var(--td-text-color-placeholder);
}

.knowledge-detail .detail-item {
  margin-bottom: 16px;
}

.knowledge-detail .detail-item label {
  font-weight: bold;
  margin-right: 8px;
  display: inline-block;
  min-width: 80px;
}

.content-box {
  background: var(--td-bg-color-secondarycontainer);
  padding: 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  margin-top: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.upload-area {
  padding: 32px 20px;
  text-align: center;
  border: 1px dashed var(--td-component-stroke);
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s;
  width: 100%;
}

.upload-area:hover {
  border-color: var(--td-brand-color);
}

.upload-area.has-file {
  border-style: solid;
  border-color: var(--td-success-color);
  background: var(--td-success-color-1);
}
</style>
