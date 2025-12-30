<template>
  <div class="endpoints-page">
    <t-card :bordered="false">
      <div class="toolbar">
        <t-space>
          <t-input v-model="searchKeyword" placeholder="搜索接口" clearable style="width: 300px">
            <template #prefix-icon><SearchIcon /></template>
          </t-input>
          <t-select v-model="filterMethod" placeholder="HTTP方法" clearable style="width: 120px">
            <t-option value="GET" label="GET" />
            <t-option value="POST" label="POST" />
            <t-option value="PUT" label="PUT" />
            <t-option value="DELETE" label="DELETE" />
            <t-option value="PATCH" label="PATCH" />
          </t-select>
          <t-select v-model="filterTag" placeholder="标签筛选" clearable style="width: 150px">
            <t-option v-for="tag in allTags" :key="tag.id" :value="tag.id" :label="tag.name" />
          </t-select>
          <t-button @click="loadEndpoints">
            <template #icon><RefreshIcon /></template>
            刷新
          </t-button>
        </t-space>
      </div>

      <t-table
        :data="endpoints"
        :columns="columns"
        row-key="endpoint_id"
        :loading="loading"
        :pagination="pagination"
        @page-change="handlePageChange"
      >
        <template #method="{ row }">
          <t-tag :theme="getMethodTheme(row.method)" size="small">{{ row.method }}</t-tag>
        </template>
        <template #tags="{ row }">
          <t-space size="small">
            <t-tag v-for="tag in row.tags" :key="tag" size="small" variant="light">{{ tag }}</t-tag>
          </t-space>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleView(row)">查看</t-link>
            <t-link theme="primary" @click="handleEdit(row)">编辑</t-link>
            <t-popconfirm content="确定删除该接口吗？" @confirm="handleDelete(row)">
              <t-link theme="danger">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <t-drawer v-model:visible="drawerVisible" :header="drawerTitle" size="600px">
      <t-descriptions :column="1" v-if="currentEndpoint">
        <t-descriptions-item label="接口名称">{{ currentEndpoint.name }}</t-descriptions-item>
        <t-descriptions-item label="请求方法">
          <t-tag :theme="getMethodTheme(currentEndpoint.method)">{{ currentEndpoint.method }}</t-tag>
        </t-descriptions-item>
        <t-descriptions-item label="接口路径">{{ currentEndpoint.path }}</t-descriptions-item>
        <t-descriptions-item label="描述">{{ currentEndpoint.description || '-' }}</t-descriptions-item>
        <t-descriptions-item label="摘要">{{ currentEndpoint.summary || '-' }}</t-descriptions-item>
        <t-descriptions-item label="标签">
          <t-space size="small">
            <t-tag v-for="tag in currentEndpoint.tags" :key="tag" size="small">{{ tag }}</t-tag>
          </t-space>
        </t-descriptions-item>
        <t-descriptions-item label="来源">{{ currentEndpoint.source_type }}</t-descriptions-item>
      </t-descriptions>
      
      <t-divider>参数定义</t-divider>
      <pre v-if="currentEndpoint?.parameters" class="json-view">{{ JSON.stringify(currentEndpoint.parameters, null, 2) }}</pre>
      
      <t-divider>请求体</t-divider>
      <pre v-if="currentEndpoint?.request_body" class="json-view">{{ JSON.stringify(currentEndpoint.request_body, null, 2) }}</pre>
    </t-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { SearchIcon, RefreshIcon } from 'tdesign-icons-vue-next'
import { endpointApi, tagApi } from '../api'

interface Endpoint {
  endpoint_id: string
  name: string
  method: string
  path: string
  description: string
  summary: string
  tags: string[]
  source_type: string
  parameters?: any[]
  request_body?: any
}

const loading = ref(false)
const endpoints = ref<Endpoint[]>([])
const allTags = ref<any[]>([])
const searchKeyword = ref('')
const filterMethod = ref('')
const filterTag = ref<number | null>(null)
const drawerVisible = ref(false)
const drawerTitle = ref('接口详情')
const currentEndpoint = ref<Endpoint | null>(null)

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { colKey: 'method', title: '方法', cell: 'method', width: 80 },
  { colKey: 'path', title: '路径', ellipsis: true },
  { colKey: 'name', title: '名称', width: 200, ellipsis: true },
  { colKey: 'tags', title: '标签', cell: 'tags', width: 200 },
  { colKey: 'source_type', title: '来源', width: 100 },
  { colKey: 'op', title: '操作', cell: 'op', width: 150 }
]

const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    DELETE: 'danger',
    PATCH: 'default'
  }
  return map[method] || 'default'
}

const loadEndpoints = async () => {
  loading.value = true
  const data = await endpointApi.list({
    search: searchKeyword.value || undefined,
    method: filterMethod.value || undefined,
    tag_id: filterTag.value || undefined,
    page: pagination.value.current,
    size: pagination.value.pageSize
  }) as any
  
  endpoints.value = data.items || []
  pagination.value.total = data.total || 0
  loading.value = false
}

const loadTags = async () => {
  const data = await tagApi.list()
  allTags.value = data as any[]
}

const handlePageChange = (pageInfo: any) => {
  pagination.value.current = pageInfo.current
  pagination.value.pageSize = pageInfo.pageSize
  loadEndpoints()
}

const handleView = async (row: Endpoint) => {
  const data = await endpointApi.get(row.endpoint_id)
  currentEndpoint.value = data as Endpoint
  drawerTitle.value = `接口详情 - ${row.name}`
  drawerVisible.value = true
}

const handleEdit = (row: Endpoint) => {
  MessagePlugin.info('编辑功能开发中')
}

const handleDelete = async (row: Endpoint) => {
  await endpointApi.delete(row.endpoint_id)
  MessagePlugin.success('删除成功')
  loadEndpoints()
}

watch([searchKeyword, filterMethod, filterTag], () => {
  pagination.value.current = 1
  loadEndpoints()
}, { debounce: 300 } as any)

onMounted(() => {
  loadEndpoints()
  loadTags()
})
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}

.json-view {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow: auto;
  max-height: 300px;
}
</style>
