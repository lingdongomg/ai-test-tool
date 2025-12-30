<template>
  <div class="tags-page">
    <t-card :bordered="false">
      <div class="toolbar">
        <t-button theme="primary" @click="showCreateDialog">
          <template #icon><AddIcon /></template>
          新建标签
        </t-button>
      </div>

      <t-table
        :data="tags"
        :columns="columns"
        row-key="id"
        :loading="loading"
        :tree="{ childrenKey: 'children', treeNodeColumnIndex: 0 }"
      >
        <template #color="{ row }">
          <div class="color-tag" :style="{ backgroundColor: row.color }">
            {{ row.color }}
          </div>
        </template>
        <template #is_system="{ row }">
          <t-tag :theme="row.is_system ? 'warning' : 'default'" size="small">
            {{ row.is_system ? '系统' : '自定义' }}
          </t-tag>
        </template>
        <template #op="{ row }">
          <t-space>
            <t-link theme="primary" @click="handleEdit(row)">编辑</t-link>
            <t-link theme="primary" @click="handleAddChild(row)">添加子标签</t-link>
            <t-popconfirm content="确定删除该标签吗？" @confirm="handleDelete(row)">
              <t-link theme="danger" :disabled="row.is_system">删除</t-link>
            </t-popconfirm>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <t-dialog
      v-model:visible="dialogVisible"
      :header="isEdit ? '编辑标签' : '新建标签'"
      @confirm="handleSubmit"
    >
      <t-form :data="formData" :rules="rules" ref="formRef">
        <t-form-item label="标签名称" name="name">
          <t-input v-model="formData.name" placeholder="请输入标签名称" />
        </t-form-item>
        <t-form-item label="描述" name="description">
          <t-textarea v-model="formData.description" placeholder="请输入描述" />
        </t-form-item>
        <t-form-item label="颜色" name="color">
          <t-color-picker v-model="formData.color" />
        </t-form-item>
        <t-form-item label="父标签" name="parent_id" v-if="!isEdit">
          <t-select v-model="formData.parent_id" clearable placeholder="选择父标签（可选）">
            <t-option v-for="tag in flatTags" :key="tag.id" :value="tag.id" :label="tag.name" />
          </t-select>
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { AddIcon } from 'tdesign-icons-vue-next'
import { tagApi } from '../api'

interface Tag {
  id: number
  name: string
  description: string
  color: string
  parent_id: number | null
  is_system: boolean
  children?: Tag[]
}

const loading = ref(false)
const tags = ref<Tag[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)

const formData = ref({
  name: '',
  description: '',
  color: '#1890ff',
  parent_id: null as number | null
})

const rules = {
  name: [{ required: true, message: '请输入标签名称' }]
}

const formRef = ref()

const columns = [
  { colKey: 'name', title: '标签名称', width: 200 },
  { colKey: 'description', title: '描述', ellipsis: true },
  { colKey: 'color', title: '颜色', cell: 'color', width: 120 },
  { colKey: 'is_system', title: '类型', cell: 'is_system', width: 100 },
  { colKey: 'op', title: '操作', cell: 'op', width: 200 }
]

const flatTags = computed(() => {
  const result: Tag[] = []
  const flatten = (items: Tag[]) => {
    items.forEach(item => {
      result.push(item)
      if (item.children) flatten(item.children)
    })
  }
  flatten(tags.value)
  return result
})

const loadTags = async () => {
  loading.value = true
  const data = await tagApi.tree()
  tags.value = data as Tag[]
  loading.value = false
}

const showCreateDialog = () => {
  isEdit.value = false
  editingId.value = null
  formData.value = { name: '', description: '', color: '#1890ff', parent_id: null }
  dialogVisible.value = true
}

const handleEdit = (row: Tag) => {
  isEdit.value = true
  editingId.value = row.id
  formData.value = {
    name: row.name,
    description: row.description,
    color: row.color,
    parent_id: row.parent_id
  }
  dialogVisible.value = true
}

const handleAddChild = (row: Tag) => {
  isEdit.value = false
  editingId.value = null
  formData.value = { name: '', description: '', color: '#1890ff', parent_id: row.id }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate()
  if (valid !== true) return

  if (isEdit.value && editingId.value) {
    await tagApi.update(editingId.value, formData.value)
    MessagePlugin.success('更新成功')
  } else {
    await tagApi.create(formData.value)
    MessagePlugin.success('创建成功')
  }
  
  dialogVisible.value = false
  loadTags()
}

const handleDelete = async (row: Tag) => {
  await tagApi.delete(row.id)
  MessagePlugin.success('删除成功')
  loadTags()
}

onMounted(loadTags)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}

.color-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
}
</style>
