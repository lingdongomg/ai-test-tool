<template>
  <div class="report-detail" v-loading="loading">
    <t-card>
      <template #title>
        {{ report.title || '分析报告' }}
      </template>
      <template #actions>
        <t-button variant="outline" @click="handleDownload">
          <template #icon><DownloadIcon /></template>
          下载报告
        </t-button>
      </template>
      
      <div class="report-meta" v-if="report.statistics">
        <t-tag theme="danger" size="large" v-if="report.statistics.critical_count">
          {{ report.statistics.critical_count }} 个严重
        </t-tag>
        <t-tag theme="warning" size="large" v-if="report.statistics.error_count">
          {{ report.statistics.error_count }} 个错误
        </t-tag>
        <t-tag theme="default" size="large" v-if="report.statistics.warning_count">
          {{ report.statistics.warning_count }} 个警告
        </t-tag>
        <span class="report-time">创建于 {{ report.created_at }}</span>
      </div>
      
      <t-divider />
      
      <div class="report-content" v-html="renderedContent"></div>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { DownloadIcon } from 'tdesign-icons-vue-next'
import { insightsApi } from '../../api/v2'
import { marked } from 'marked'

const route = useRoute()
const reportId = parseInt(route.params.id as string)

// 数据
const loading = ref(false)
const report = ref<any>({})

// 渲染 Markdown
const renderedContent = computed(() => {
  if (!report.value.content) return ''
  return marked(report.value.content)
})

// 加载数据
const loadReport = async () => {
  loading.value = true
  try {
    report.value = await insightsApi.getReport(reportId)
  } catch (error) {
    console.error('加载报告失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadReport)

// 下载
const handleDownload = async () => {
  try {
    const blob = await insightsApi.downloadReport(reportId)
    const url = window.URL.createObjectURL(blob as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${reportId}.md`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载失败:', error)
  }
}
</script>

<style scoped>
.report-detail {
  max-width: 1000px;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.report-time {
  color: rgba(0, 0, 0, 0.4);
  font-size: 14px;
  margin-left: auto;
}

.report-content {
  line-height: 1.8;
}

.report-content :deep(h1),
.report-content :deep(h2),
.report-content :deep(h3) {
  margin-top: 24px;
  margin-bottom: 12px;
}

.report-content :deep(pre) {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
}

.report-content :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}

.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.report-content :deep(th),
.report-content :deep(td) {
  border: 1px solid #e5e5e5;
  padding: 8px 12px;
  text-align: left;
}

.report-content :deep(th) {
  background: #f5f7fa;
}
</style>
