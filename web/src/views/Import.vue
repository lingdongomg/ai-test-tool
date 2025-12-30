<template>
  <div class="import-page">
    <t-row :gutter="16">
      <t-col :span="12">
        <t-card title="导入接口文档" :bordered="false">
          <t-form :data="formData" @submit="handleSubmit">
            <t-form-item label="文档类型">
              <t-radio-group v-model="formData.docType">
                <t-radio value="auto">自动检测</t-radio>
                <t-radio value="swagger">Swagger/OpenAPI</t-radio>
                <t-radio value="postman">Postman Collection</t-radio>
              </t-radio-group>
            </t-form-item>
            
            <t-form-item label="导入方式">
              <t-radio-group v-model="importMode">
                <t-radio value="file">上传文件</t-radio>
                <t-radio value="json">粘贴JSON</t-radio>
              </t-radio-group>
            </t-form-item>

            <t-form-item label="选择文件" v-if="importMode === 'file'">
              <t-upload
                v-model="fileList"
                :auto-upload="false"
                accept=".json,.yaml,.yml"
                :max="1"
                theme="file"
              />
            </t-form-item>

            <t-form-item label="JSON内容" v-if="importMode === 'json'">
              <t-textarea
                v-model="formData.jsonContent"
                placeholder="粘贴Swagger或Postman JSON内容"
                :autosize="{ minRows: 10, maxRows: 20 }"
              />
            </t-form-item>

            <t-form-item label="更新策略">
              <t-radio-group v-model="formData.updateStrategy">
                <t-radio value="merge">合并更新（更新已有，新增缺失）</t-radio>
                <t-radio value="replace">完全替换（删除旧数据）</t-radio>
                <t-radio value="skip">跳过已有（仅新增）</t-radio>
              </t-radio-group>
            </t-form-item>

            <t-form-item>
              <t-space>
                <t-button theme="default" @click="handlePreview" :loading="previewLoading">
                  预览
                </t-button>
                <t-button theme="primary" type="submit" :loading="submitLoading">
                  导入
                </t-button>
              </t-space>
            </t-form-item>
          </t-form>
        </t-card>
      </t-col>

      <t-col :span="12">
        <t-card title="预览结果" :bordered="false">
          <t-alert v-if="previewResult" theme="info" :message="`将导入 ${previewResult.endpoint_count} 个接口，${previewResult.tag_count} 个标签`" />
          
          <div v-if="previewResult" class="preview-content">
            <t-divider>标签列表</t-divider>
            <t-space wrap>
              <t-tag v-for="tag in previewResult.tags" :key="tag.name" size="small">
                {{ tag.name }}
              </t-tag>
            </t-space>

            <t-divider>接口列表（前20个）</t-divider>
            <t-table
              :data="previewResult.endpoints?.slice(0, 20)"
              :columns="previewColumns"
              size="small"
              :pagination="false"
            >
              <template #method="{ row }">
                <t-tag :theme="getMethodTheme(row.method)" size="small">{{ row.method }}</t-tag>
              </template>
            </t-table>
          </div>

          <t-empty v-else description="请先预览或导入文档" />
        </t-card>
      </t-col>
    </t-row>

    <t-card title="导入历史" :bordered="false" class="mt-4">
      <t-table :data="importHistory" :columns="historyColumns" size="small">
        <template #status="{ row }">
          <t-tag :theme="row.status === 'success' ? 'success' : 'danger'">
            {{ row.status === 'success' ? '成功' : '失败' }}
          </t-tag>
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { importApi } from '../api'

const formData = ref({
  docType: 'auto',
  jsonContent: '',
  updateStrategy: 'merge'
})

const importMode = ref('file')
const fileList = ref<any[]>([])
const previewLoading = ref(false)
const submitLoading = ref(false)
const previewResult = ref<any>(null)

const importHistory = ref([
  { id: 1, filename: 'swagger.json', type: 'swagger', endpoints: 45, tags: 8, status: 'success', time: '2025-01-15 10:30:00' },
  { id: 2, filename: 'postman_collection.json', type: 'postman', endpoints: 23, tags: 5, status: 'success', time: '2025-01-14 15:20:00' }
])

const previewColumns = [
  { colKey: 'method', title: '方法', cell: 'method', width: 80 },
  { colKey: 'path', title: '路径', ellipsis: true },
  { colKey: 'name', title: '名称', width: 200, ellipsis: true }
]

const historyColumns = [
  { colKey: 'filename', title: '文件名' },
  { colKey: 'type', title: '类型', width: 100 },
  { colKey: 'endpoints', title: '接口数', width: 80 },
  { colKey: 'tags', title: '标签数', width: 80 },
  { colKey: 'status', title: '状态', cell: 'status', width: 80 },
  { colKey: 'time', title: '导入时间', width: 180 }
]

const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'default'
  }
  return map[method] || 'default'
}

const getContent = async () => {
  if (importMode.value === 'file') {
    if (fileList.value.length === 0) {
      MessagePlugin.warning('请选择文件')
      return null
    }
    const file = fileList.value[0].raw
    const text = await file.text()
    return JSON.parse(text)
  } else {
    if (!formData.value.jsonContent) {
      MessagePlugin.warning('请输入JSON内容')
      return null
    }
    return JSON.parse(formData.value.jsonContent)
  }
}

const handlePreview = async () => {
  const content = await getContent()
  if (!content) return

  previewLoading.value = true
  const result = await importApi.preview({
    content,
    doc_type: formData.value.docType
  })
  previewResult.value = result
  previewLoading.value = false
}

const handleSubmit = async () => {
  const content = await getContent()
  if (!content) return

  submitLoading.value = true
  
  const result = await importApi.importJson({
    content,
    doc_type: formData.value.docType,
    source_name: fileList.value[0]?.name || 'manual_import'
  })
  
  MessagePlugin.success(`导入成功：${(result as any).endpoint_count} 个接口，${(result as any).tag_count} 个标签`)
  previewResult.value = result
  submitLoading.value = false
}
</script>

<style scoped>
.preview-content {
  margin-top: 16px;
}

.mt-4 {
  margin-top: 16px;
}
</style>
