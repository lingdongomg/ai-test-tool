<template>
  <div class="reports-page">
    <t-card>
      <t-table
        :data="reports"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        hover
        @page-change="handlePageChange"
      >
        <template #statistics="{ row }">
          <t-space size="small" v-if="row.statistics">
            <t-tag theme="danger" variant="light" size="small" v-if="row.statistics.critical_count">
              严重 {{ row.statistics.critical_count }}
            </t-tag>
            <t-tag theme="warning" variant="light" size="small" v-if="row.statistics.error_count">
              错误 {{ row.statistics.error_count }}
            </t-tag>
            <t-tag theme="default" variant="light" size="small" v-if="row.statistics.warning_count">
              警告 {{ row.statistics.warning_count }}
            </t-tag>
          </t-space>
          <span v-else>-</span>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">查看</t-link>
            <t-link theme="primary" @click="handleDownload(row)">下载</t-link>
          </t-space>
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { insightsApi } from '../../api/v2'

const router = useRouter()

// 数据
const reports = ref<any[]>([])
const loading = ref(false)

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 表格列
const columns = [
  { colKey: 'id', title: 'ID', width: 80 },
  { colKey: 'title', title: '报告标题', ellipsis: true },
  { colKey: 'statistics', title: '异常统计', width: 250 },
  { colKey: 'created_at', title: '创建时间', width: 180 },
  { colKey: 'op', title: '操作', width: 120 }
]

// 加载数据
const loadReports = async () => {
  loading.value = true
  try {
    const res = await insightsApi.listReports({
      page: pagination.current,
      page_size: pagination.pageSize
    })
    reports.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载报告列表失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadReports)

// 分页
const handlePageChange = (pageInfo: any) => {
  pagination.current = pageInfo.current
  pagination.pageSize = pageInfo.pageSize
  loadReports()
}

// 查看
const handleView = (row: any) => {
  router.push(`/insights/reports/${row.id}`)
}

// 下载
const handleDownload = async (row: any) => {
  try {
    const blob = await insightsApi.downloadReport(row.id)
    const url = window.URL.createObjectURL(blob as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${row.id}.md`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载失败:', error)
  }
}
</script>

<style scoped>
.reports-page {
  max-width: 1200px;
}
</style>
