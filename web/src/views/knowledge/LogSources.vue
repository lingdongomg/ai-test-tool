<template>
  <div class="log-sources">
    <div class="page-header">
      <h2>日志源管理</h2>
      <div class="header-actions">
        <t-button theme="primary" @click="showCreateDialog = true">
          <template #icon><add-icon /></template>
          新增日志源
        </t-button>
        <t-button @click="loadSources">
          <template #icon><refresh-icon /></template>
          刷新
        </t-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <t-row :gutter="20" class="stats-row">
      <t-col :span="6">
        <t-card hover class="stat-card">
          <div class="stat-value">{{ sources.length }}</div>
          <div class="stat-label">总日志源</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card hover class="stat-card connected">
          <div class="stat-value">{{ connectedCount }}</div>
          <div class="stat-label">已连接</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card hover class="stat-card">
          <div class="stat-value">{{ totalLinesReceived.toLocaleString() }}</div>
          <div class="stat-label">接收行数</div>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card hover class="stat-card">
          <div class="stat-value">{{ totalAnalyses }}</div>
          <div class="stat-label">触发分析</div>
        </t-card>
      </t-col>
    </t-row>

    <!-- 日志源列表 -->
    <t-card class="list-card">
      <t-table :data="sources" :loading="loading" stripe>
        <template #empty>
          <div style="padding: 48px 0; text-align: center; color: var(--td-text-color-placeholder);">
            <p style="font-size: 14px; margin-bottom: 8px;">暂无日志源</p>
            <p style="font-size: 12px;">点击「新增日志源」创建实时日志接入通道</p>
          </div>
        </template>
        <t-table-column prop="name" label="名称" min-width="150">
          <template #cell="{ row }">
            <span style="font-weight: 500;">{{ row.name }}</span>
            <div v-if="row.description" style="font-size: 12px; color: rgba(0,0,0,0.4); margin-top: 2px;">{{ row.description }}</div>
          </template>
        </t-table-column>
        <t-table-column prop="status" label="状态" width="100">
          <template #cell="{ row }">
            <t-tag v-if="row.status === 'connected'" theme="success" size="small">
              <span style="margin-right: 4px;">&#x1F7E2;</span>已连接
            </t-tag>
            <t-tag v-else theme="default" size="small">
              <span style="margin-right: 4px;">&#x1F534;</span>已断开
            </t-tag>
          </template>
        </t-table-column>
        <t-table-column prop="total_lines_received" label="接收行数" width="110" align="right">
          <template #cell="{ row }">{{ (row.total_lines_received || 0).toLocaleString() }}</template>
        </t-table-column>
        <t-table-column prop="total_analyses_triggered" label="分析次数" width="100" align="right" />
        <t-table-column prop="auto_learn" label="自动学习" width="90" align="center">
          <template #cell="{ row }">
            <t-tag v-if="row.auto_learn" theme="success" size="small">开启</t-tag>
            <t-tag v-else theme="default" size="small">关闭</t-tag>
          </template>
        </t-table-column>
        <t-table-column prop="last_active_at" label="最后活跃" width="140">
          <template #cell="{ row }">
            <span v-if="row.last_active_at">{{ formatTime(row.last_active_at) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </t-table-column>
        <t-table-column label="操作" width="150" fixed="right">
          <template #cell="{ row }">
            <t-button variant="text" size="small" @click="editSource(row)">编辑</t-button>
            <t-button variant="text" theme="danger" size="small" @click="deleteSource(row)">删除</t-button>
          </template>
        </t-table-column>
      </t-table>
    </t-card>

    <!-- 新增/编辑对话框 -->
    <t-dialog
      v-model:visible="showCreateDialog"
      :header="editingSource ? '编辑日志源' : '新增日志源'"
      width="600px"
    >
      <t-form :data="formData" label-width="120px">
        <t-form-item label="名称" required>
          <t-input v-model="formData.name" placeholder="日志源名称" />
        </t-form-item>
        <t-form-item label="描述">
          <t-input v-model="formData.description" placeholder="描述信息" />
        </t-form-item>
        <t-form-item label="标签">
          <t-select
            v-model="formData.tags"
            multiple
            filterable
            creatable
            placeholder="输入并回车添加标签"
            style="width: 100%"
          />
        </t-form-item>
        <t-divider>缓冲设置</t-divider>
        <t-form-item label="缓冲行数阈值">
          <t-input-number v-model="formData.buffer_size" :min="10" :max="1000" :step="10" style="width: 200px" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">行</span>
        </t-form-item>
        <t-form-item label="缓冲超时">
          <t-input-number v-model="formData.buffer_timeout_sec" :min="5" :max="300" style="width: 200px" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">秒</span>
        </t-form-item>
        <t-divider>自动学习</t-divider>
        <t-form-item label="自动学习">
          <t-switch v-model="formData.auto_learn" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">分析完成后自动提取知识</span>
        </t-form-item>
        <t-form-item label="自动审核阈值">
          <t-input-number v-model="formData.auto_approve_threshold" :min="0" :max="1" :step="0.1" :decimal-places="1" style="width: 200px" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">置信度达到此值自动通过</span>
        </t-form-item>
        <t-divider>告警配置</t-divider>
        <t-form-item label="实时告警">
          <t-switch v-model="formData.alert_enabled" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">ERROR/CRITICAL 日志立即告警</span>
        </t-form-item>
        <t-form-item label="Webhook URL">
          <t-input v-model="formData.webhook_url" placeholder="告警通知地址（如企微机器人 Webhook）" />
          <div style="margin-top: 4px; font-size: 12px; color: rgba(0,0,0,0.4);">留空则不发送外部通知，告警仍会记录在系统中</div>
        </t-form-item>
        <div v-if="editingSource" style="margin-top: 16px; padding: 12px; background: #f5f7fa; border-radius: 4px;">
          <div style="font-size: 12px; color: rgba(0,0,0,0.4);">WebSocket 连接地址</div>
          <code style="font-size: 13px;">ws://{{ window.location.host }}/ws/logs?source_id={{ editingSource.source_id }}</code>
        </div>
      </t-form>
      <template #footer>
        <t-button @click="cancelDialog">取消</t-button>
        <t-button theme="primary" @click="saveSource" :loading="saving">保存</t-button>
      </template>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'
import { AddIcon, RefreshIcon } from 'tdesign-icons-vue-next'
import { logStreamApi } from '../../api/v2'

const loading = ref(false)
const saving = ref(false)
const sources = ref<any[]>([])
const showCreateDialog = ref(false)
const editingSource = ref<any>(null)

const formData = reactive({
  name: '',
  description: '',
  tags: [] as string[],
  buffer_size: 100,
  buffer_timeout_sec: 30,
  auto_learn: true,
  auto_approve_threshold: 0.8,
  alert_enabled: true,
  webhook_url: '',
})

// 统计
const connectedCount = computed(() => sources.value.filter(s => s.status === 'connected').length)
const totalLinesReceived = computed(() => sources.value.reduce((sum, s) => sum + (s.total_lines_received || 0), 0))
const totalAnalyses = computed(() => sources.value.reduce((sum, s) => sum + (s.total_analyses_triggered || 0), 0))

// 加载列表
const loadSources = async () => {
  loading.value = true
  try {
    const data: any = await logStreamApi.listSources()
    sources.value = data.items || []
  } catch (error) {
    console.error('加载日志源失败:', error)
    MessagePlugin.error('加载日志源失败')
  } finally {
    loading.value = false
  }
}

// 编辑
const editSource = (row: any) => {
  editingSource.value = row
  formData.name = row.name
  formData.description = row.description || ''
  formData.tags = row.tags || []
  formData.buffer_size = row.buffer_size || 100
  formData.buffer_timeout_sec = row.buffer_timeout_sec || 30
  formData.auto_learn = row.auto_learn !== false
  formData.auto_approve_threshold = row.auto_approve_threshold || 0.8
  formData.alert_enabled = row.alert_enabled !== false
  formData.webhook_url = row.webhook_url || ''
  showCreateDialog.value = true
}

// 保存
const saveSource = async () => {
  if (!formData.name) {
    MessagePlugin.warning('请填写名称')
    return
  }
  saving.value = true
  try {
    if (editingSource.value) {
      await logStreamApi.updateSource(editingSource.value.source_id, formData)
      MessagePlugin.success('更新成功')
    } else {
      const res: any = await logStreamApi.createSource(formData)
      MessagePlugin.success(`创建成功，WebSocket URL: ${res.ws_url}`)
    }
    showCreateDialog.value = false
    resetForm()
    loadSources()
  } catch (error) {
    MessagePlugin.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 删除
const deleteSource = (row: any) => {
  const confirmDialog = DialogPlugin.confirm({
    header: '确认删除',
    body: `确定要删除日志源「${row.name}」吗？活跃连接将被断开。`,
    onConfirm: async () => {
      try {
        await logStreamApi.deleteSource(row.source_id)
        MessagePlugin.success('删除成功')
        loadSources()
      } catch (error) {
        MessagePlugin.error('删除失败')
      }
    },
    onClose: () => {
      confirmDialog.destroy()
    }
  })
}

// 取消
const cancelDialog = () => {
  showCreateDialog.value = false
  resetForm()
}

// 重置
const resetForm = () => {
  editingSource.value = null
  formData.name = ''
  formData.description = ''
  formData.tags = []
  formData.buffer_size = 100
  formData.buffer_timeout_sec = 30
  formData.auto_learn = true
  formData.auto_approve_threshold = 0.8
}

// 时间格式化
const formatTime = (time: string) => {
  if (!time) return '-'
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
}

onMounted(() => {
  loadSources()
})
</script>

<style scoped>
.log-sources {
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

.stat-card.connected .stat-value {
  color: #52c41a;
}

.list-card {
  margin-bottom: 20px;
}

.text-muted {
  color: #909399;
}
</style>
