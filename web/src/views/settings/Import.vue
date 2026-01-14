<template>
  <div class="import-page">
    <t-card title="导入接口文档" :bordered="false">
      <template #actions>
        <t-button theme="default" @click="showHelp = true">
          <template #icon><HelpCircleIcon /></template>
          帮助
        </t-button>
      </template>
      
      <!-- 上传区域 -->
      <t-upload
        ref="uploadRef"
        v-model="fileList"
        :action="uploadAction"
        :auto-upload="false"
        :multiple="false"
        accept=".json"
        theme="custom"
        draggable
        @change="handleFileChange"
      >
        <div class="upload-area">
          <CloudUploadIcon class="upload-icon" />
          <div class="upload-text">
            <p class="main">点击或拖拽文件到此处上传</p>
            <p class="sub">支持 Swagger/OpenAPI、Postman Collection 格式的 JSON 文件</p>
          </div>
        </div>
      </t-upload>
      
      <!-- 文件信息 -->
      <div v-if="selectedFile" class="file-info">
        <div class="file-item">
          <FileIcon class="file-icon" />
          <div class="file-detail">
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
          </div>
          <t-button theme="default" variant="text" @click="clearFile">
            <CloseIcon />
          </t-button>
        </div>
      </div>
      
      <!-- 导入选项 -->
      <div v-if="selectedFile" class="import-options">
        <t-form :data="importOptions" layout="inline">
          <t-form-item label="文档类型">
            <t-select v-model="importOptions.docType" style="width: 180px">
              <t-option value="auto" label="自动检测" />
              <t-option value="swagger" label="Swagger/OpenAPI" />
              <t-option value="postman" label="Postman Collection" />
            </t-select>
          </t-form-item>
          <t-form-item label="更新策略">
            <t-select v-model="importOptions.updateStrategy" style="width: 180px">
              <t-option value="merge" label="合并更新" />
              <t-option value="replace" label="完全替换" />
              <t-option value="skip" label="跳过已有" />
            </t-select>
          </t-form-item>
        </t-form>
        
        <div class="strategy-desc">
          <InfoCircleIcon />
          <span v-if="importOptions.updateStrategy === 'merge'">
            合并更新：更新已有接口，新增缺失接口，保留其他接口
          </span>
          <span v-else-if="importOptions.updateStrategy === 'replace'">
            完全替换：删除不在新文档中的接口
          </span>
          <span v-else>
            跳过已有：仅新增缺失接口，不更新已有接口
          </span>
        </div>
      </div>
      
      <!-- 预览/导入按钮 -->
      <div v-if="selectedFile" class="action-buttons">
        <t-button variant="outline" @click="previewImport" :loading="previewing">
          预览
        </t-button>
        <t-button variant="outline" @click="diffImport" :loading="diffing">
          对比差异
        </t-button>
        <t-button theme="primary" @click="doImport" :loading="importing">
          开始导入
        </t-button>
      </div>
    </t-card>
    
    <!-- 预览结果 -->
    <t-card v-if="previewResult" title="预览结果" :bordered="false" class="preview-card">
      <div class="preview-stats">
        <t-statistic title="文档类型" :value="previewResult.doc_type" />
        <t-statistic title="接口数量" :value="previewResult.endpoint_count" />
        <t-statistic title="标签数量" :value="previewResult.tag_count" />
      </div>
      
      <t-divider />
      
      <div class="preview-tags">
        <span class="label">标签：</span>
        <t-tag v-for="tag in previewResult.tags" :key="tag" variant="light">{{ tag }}</t-tag>
      </div>
      
      <t-table
        :data="previewResult.endpoints"
        :columns="previewColumns"
        row-key="endpoint_id"
        :max-height="400"
        size="small"
      />
    </t-card>
    
    <!-- 差异对比结果 -->
    <t-card v-if="diffResult" title="差异对比" :bordered="false" class="diff-card">
      <div class="diff-stats">
        <t-statistic title="新增" :value="diffResult.total_new" value-style="color: #00a870" />
        <t-statistic title="更新" :value="diffResult.total_updated" value-style="color: #0052d9" />
        <t-statistic title="未变" :value="diffResult.total_unchanged" />
        <t-statistic title="删除" :value="diffResult.total_deleted" value-style="color: #e34d59" />
      </div>
      
      <t-table
        :data="diffResult.diffs"
        :columns="diffColumns"
        row-key="endpoint_id"
        :max-height="400"
        size="small"
      />
    </t-card>
    
    <!-- 导入结果 -->
    <t-card v-if="importResult" title="导入结果" :bordered="false" class="result-card">
      <t-alert
        :theme="importResult.success ? 'success' : 'error'"
        :message="importResult.message"
      />
      
      <div v-if="importResult.success" class="result-stats">
        <t-statistic title="新增" :value="importResult.created_count" />
        <t-statistic title="更新" :value="importResult.updated_count" />
        <t-statistic title="跳过" :value="importResult.skipped_count" />
        <t-statistic title="删除" :value="importResult.deleted_count" />
      </div>
    </t-card>
    
    <!-- 帮助弹窗 -->
    <t-dialog v-model:visible="showHelp" header="导入帮助" :footer="false" width="600px">
      <div class="help-content">
        <h4>支持的文档格式</h4>
        <ul>
          <li><strong>Swagger/OpenAPI</strong>：支持 2.0、3.0、3.1 版本</li>
          <li><strong>Postman Collection</strong>：支持 2.0、2.1 版本</li>
        </ul>
        
        <h4>更新策略说明</h4>
        <ul>
          <li><strong>合并更新</strong>：推荐使用。更新已有接口的信息，新增文档中新的接口，保留数据库中其他接口</li>
          <li><strong>完全替换</strong>：谨慎使用。会删除数据库中不在新文档中的接口</li>
          <li><strong>跳过已有</strong>：仅新增接口，不会修改已有接口的任何信息</li>
        </ul>
        
        <h4>导出 Swagger 文档</h4>
        <p>如果你的项目使用了 Swagger 注解，可以访问 <code>/v2/api-docs</code> 或 <code>/v3/api-docs</code> 获取 JSON 文档</p>
      </div>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { 
  CloudUploadIcon, 
  FileIcon, 
  CloseIcon, 
  HelpCircleIcon,
  InfoCircleIcon 
} from 'tdesign-icons-vue-next'
import { importApi } from '../../api'

const uploadRef = ref()
const fileList = ref([])
const selectedFile = ref<File | null>(null)
const showHelp = ref(false)

const previewing = ref(false)
const diffing = ref(false)
const importing = ref(false)

const previewResult = ref<any>(null)
const diffResult = ref<any>(null)
const importResult = ref<any>(null)

const importOptions = ref({
  docType: 'auto',
  updateStrategy: 'merge'
})

const uploadAction = ''

const previewColumns = [
  { colKey: 'method', title: '方法', width: 80 },
  { colKey: 'path', title: '路径', ellipsis: true },
  { colKey: 'name', title: '名称', ellipsis: true },
  { colKey: 'summary', title: '描述', ellipsis: true }
]

const diffColumns = [
  { colKey: 'method', title: '方法', width: 80 },
  { colKey: 'path', title: '路径', ellipsis: true },
  { colKey: 'name', title: '名称', ellipsis: true },
  { 
    colKey: 'status', 
    title: '状态', 
    width: 100,
    cell: (h: any, { row }: any) => {
      const statusMap: Record<string, { theme: string; text: string }> = {
        new: { theme: 'success', text: '新增' },
        updated: { theme: 'primary', text: '更新' },
        unchanged: { theme: 'default', text: '未变' },
        deleted: { theme: 'danger', text: '删除' }
      }
      const status = statusMap[row.status] || { theme: 'default', text: row.status }
      return h('t-tag', { theme: status.theme, variant: 'light' }, status.text)
    }
  }
]

const handleFileChange = (files: any[]) => {
  if (files.length > 0) {
    selectedFile.value = files[0].raw
    previewResult.value = null
    diffResult.value = null
    importResult.value = null
  }
}

const clearFile = () => {
  fileList.value = []
  selectedFile.value = null
  previewResult.value = null
  diffResult.value = null
  importResult.value = null
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const previewImport = async () => {
  if (!selectedFile.value) return
  
  previewing.value = true
  try {
    const result = await importApi.preview(selectedFile.value, importOptions.value.docType)
    previewResult.value = result
    diffResult.value = null
  } catch (error) {
    console.error('预览失败:', error)
  } finally {
    previewing.value = false
  }
}

const diffImport = async () => {
  if (!selectedFile.value) return
  
  diffing.value = true
  try {
    const result = await importApi.diff(selectedFile.value, importOptions.value.docType)
    diffResult.value = result
    previewResult.value = null
  } catch (error) {
    console.error('对比失败:', error)
  } finally {
    diffing.value = false
  }
}

const doImport = async () => {
  if (!selectedFile.value) return
  
  importing.value = true
  try {
    const result = await importApi.uploadFile(
      selectedFile.value, 
      importOptions.value.docType,
      importOptions.value.updateStrategy
    )
    importResult.value = result
    if (result.success) {
      MessagePlugin.success('导入成功')
    }
  } catch (error) {
    console.error('导入失败:', error)
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.import-page {
  padding: 16px;
}

.import-page .t-card + .t-card {
  margin-top: 16px;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  border: 2px dashed var(--td-border-level-2-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: var(--td-brand-color);
  background: var(--td-brand-color-light);
}

.upload-icon {
  font-size: 48px;
  color: var(--td-brand-color);
  margin-bottom: 16px;
}

.upload-text {
  text-align: center;
}

.upload-text .main {
  font-size: 16px;
  color: var(--td-text-color-primary);
  margin-bottom: 8px;
}

.upload-text .sub {
  font-size: 14px;
  color: var(--td-text-color-secondary);
}

.file-info {
  margin-top: 16px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: var(--td-bg-color-container);
  border-radius: 6px;
}

.file-icon {
  font-size: 24px;
  color: var(--td-brand-color);
  margin-right: 12px;
}

.file-detail {
  flex: 1;
}

.file-name {
  font-weight: 500;
  margin-right: 12px;
}

.file-size {
  color: var(--td-text-color-secondary);
  font-size: 12px;
}

.import-options {
  margin-top: 24px;
  padding: 16px;
  background: var(--td-bg-color-container);
  border-radius: 6px;
}

.strategy-desc {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--td-brand-color-light);
  border-radius: 4px;
  font-size: 13px;
  color: var(--td-text-color-secondary);
}

.action-buttons {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.preview-stats,
.diff-stats,
.result-stats {
  display: flex;
  gap: 48px;
  margin-bottom: 16px;
}

.preview-tags {
  margin-bottom: 16px;
}

.preview-tags .label {
  margin-right: 8px;
  color: var(--td-text-color-secondary);
}

.preview-tags .t-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.help-content h4 {
  margin: 16px 0 8px;
}

.help-content h4:first-child {
  margin-top: 0;
}

.help-content ul {
  padding-left: 20px;
}

.help-content li {
  margin-bottom: 8px;
}

.help-content code {
  padding: 2px 6px;
  background: var(--td-bg-color-container);
  border-radius: 4px;
  font-family: monospace;
}
</style>
