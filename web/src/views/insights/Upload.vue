<template>
  <div class="upload-page">
    <t-row :gutter="[16, 16]">
      <!-- 上传区域 -->
      <t-col :xs="24" :lg="12">
        <t-card title="上传日志文件">
          <t-upload
            v-model="fileList"
            theme="custom"
            accept=".log,.txt,.json"
            :auto-upload="false"
            :max="1"
            @change="handleFileChange"
          >
            <template #default>
              <div class="upload-area" :class="{ 'has-file': fileList.length }">
                <template v-if="!fileList.length">
                  <UploadIcon class="upload-icon" />
                  <div class="upload-text">点击或拖拽文件到此处</div>
                  <div class="upload-hint">支持 .log, .txt, .json 格式</div>
                </template>
                <template v-else>
                  <FileIcon class="file-icon" />
                  <div class="file-name">{{ fileList[0].name }}</div>
                  <div class="file-size">{{ formatFileSize(fileList[0].size) }}</div>
                </template>
              </div>
            </template>
          </t-upload>
          
          <t-divider />
          
          <t-form :data="uploadForm" label-width="100px">
            <t-form-item label="检测类型">
              <t-checkbox-group v-model="uploadForm.detect_types">
                <t-checkbox value="error">错误日志</t-checkbox>
                <t-checkbox value="warning">警告日志</t-checkbox>
                <t-checkbox value="exception">异常堆栈</t-checkbox>
                <t-checkbox value="performance">性能异常</t-checkbox>
                <t-checkbox value="security">安全风险</t-checkbox>
              </t-checkbox-group>
            </t-form-item>
            <t-form-item label="AI 分析">
              <t-switch v-model="uploadForm.include_ai_analysis" />
              <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">使用 AI 分析异常原因</span>
            </t-form-item>
            <t-form-item>
              <t-button 
                theme="primary" 
                :loading="uploading" 
                :disabled="!fileList.length"
                @click="handleUpload"
              >
                <template #icon><UploadIcon /></template>
                开始分析
              </t-button>
            </t-form-item>
          </t-form>
        </t-card>
      </t-col>

      <!-- 粘贴日志 -->
      <t-col :xs="24" :lg="12">
        <t-card title="粘贴日志内容">
          <t-textarea 
            v-model="pasteContent" 
            placeholder="直接粘贴日志内容进行分析..."
            :rows="12"
          />
          
          <t-divider />
          
          <t-button 
            theme="primary" 
            :loading="analyzing" 
            :disabled="!pasteContent.trim()"
            @click="handleAnalyze"
          >
            <template #icon><SearchIcon /></template>
            分析日志
          </t-button>
        </t-card>
      </t-col>
    </t-row>

    <!-- 分析结果 -->
    <t-card title="分析结果" style="margin-top: 16px;" v-if="result">
      <div class="result-header">
        <div class="result-summary">
          <t-tag theme="danger" size="large" v-if="result.critical_count">
            {{ result.critical_count }} 个严重
          </t-tag>
          <t-tag theme="warning" size="large" v-if="result.error_count">
            {{ result.error_count }} 个错误
          </t-tag>
          <t-tag theme="default" size="large" v-if="result.warning_count">
            {{ result.warning_count }} 个警告
          </t-tag>
        </div>
        <t-button variant="outline" @click="handleViewReport">
          查看完整报告
        </t-button>
      </div>

      <t-divider />

      <t-collapse>
        <t-collapse-panel 
          v-for="(anomaly, index) in (result.anomalies || []).slice(0, 10)" 
          :key="index"
          :header="anomaly.message"
        >
          <template #headerRightContent>
            <t-tag :theme="getSeverityTheme(anomaly.severity)" size="small">
              {{ anomaly.severity }}
            </t-tag>
          </template>
          <div class="anomaly-detail">
            <p><strong>类型:</strong> {{ anomaly.type }}</p>
            <p><strong>行号:</strong> {{ anomaly.line_number || '-' }}</p>
            <p v-if="anomaly.context"><strong>上下文:</strong></p>
            <pre v-if="anomaly.context" class="context-block">{{ anomaly.context }}</pre>
            <p v-if="anomaly.ai_analysis"><strong>AI 分析:</strong> {{ anomaly.ai_analysis }}</p>
          </div>
        </t-collapse-panel>
      </t-collapse>

      <div v-if="result.anomalies?.length > 10" style="text-align: center; margin-top: 16px;">
        <t-button variant="text" @click="handleViewReport">
          查看全部 {{ result.total_anomalies }} 个异常
        </t-button>
      </div>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { MessagePlugin } from 'tdesign-vue-next'
import { UploadIcon, FileIcon, SearchIcon } from 'tdesign-icons-vue-next'
import { insightsApi } from '../../api/v2'

const router = useRouter()

// 文件上传
const fileList = ref<any[]>([])
const uploading = ref(false)
const uploadForm = reactive({
  detect_types: ['error', 'warning', 'exception'],
  include_ai_analysis: true
})

// 粘贴分析
const pasteContent = ref('')
const analyzing = ref(false)

// 结果
const result = ref<any>(null)

// 文件变化
const handleFileChange = (files: any[]) => {
  fileList.value = files
}

// 上传分析
const handleUpload = async () => {
  if (!fileList.value.length) return
  
  uploading.value = true
  result.value = null
  
  try {
    const file = fileList.value[0].raw
    const res = await insightsApi.uploadLog(file, {
      detect_types: uploadForm.detect_types.join(','),
      include_ai_analysis: uploadForm.include_ai_analysis
    })
    
    MessagePlugin.success('上传成功，正在后台分析')
    
    // 跳转到任务列表
    router.push('/insights/tasks')
  } catch (error) {
    console.error('上传失败:', error)
  } finally {
    uploading.value = false
  }
}

// 粘贴分析
const handleAnalyze = async () => {
  if (!pasteContent.value.trim()) return
  
  analyzing.value = true
  result.value = null
  
  try {
    const res = await insightsApi.detectAnomalies({
      log_content: pasteContent.value,
      include_ai_analysis: uploadForm.include_ai_analysis,
      detect_types: uploadForm.detect_types
    })
    
    result.value = res
    MessagePlugin.success(`分析完成，发现 ${res.total_anomalies} 个异常`)
  } catch (error) {
    console.error('分析失败:', error)
  } finally {
    analyzing.value = false
  }
}

// 查看报告
const handleViewReport = () => {
  if (result.value?.report_id) {
    router.push(`/insights/reports/${result.value.report_id}`)
  } else {
    router.push('/insights/reports')
  }
}

// 辅助函数
const formatFileSize = (size: number) => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

const getSeverityTheme = (severity: string) => {
  const map: Record<string, string> = {
    'critical': 'danger',
    'error': 'warning',
    'warning': 'default'
  }
  return map[severity] || 'default'
}
</script>

<style scoped>
.upload-page {
  max-width: 1200px;
}

.upload-area {
  border: 2px dashed #dcdcdc;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover {
  border-color: #0052d9;
  background: #f0f5ff;
}

.upload-area.has-file {
  border-color: #0052d9;
  background: #f0f5ff;
}

.upload-icon {
  font-size: 48px;
  color: #0052d9;
}

.upload-text {
  font-size: 16px;
  color: rgba(0, 0, 0, 0.7);
  margin-top: 12px;
}

.upload-hint {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 4px;
}

.file-icon {
  font-size: 48px;
  color: #0052d9;
}

.file-name {
  font-size: 16px;
  font-weight: 500;
  margin-top: 12px;
}

.file-size {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 4px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-summary {
  display: flex;
  gap: 12px;
}

.anomaly-detail {
  font-size: 14px;
}

.context-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
}
</style>
