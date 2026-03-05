<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <!-- 新建/重命名文件夹对话框 -->
  <t-dialog
    v-model:visible="dialogVisible"
    :header="isRename ? '重命名文件夹' : '新建文件夹'"
    :confirm-btn="{ content: '确定', loading: confirmLoading }"
    @confirm="handleConfirm"
  >
    <t-form label-width="80px">
      <t-form-item label="名称" required>
        <t-input v-model="folderName" placeholder="请输入文件夹名称" />
      </t-form-item>
    </t-form>
  </t-dialog>

  <!-- 智能分组预览对话框 -->
  <t-dialog
    v-model:visible="organizeVisible"
    header="智能分组预览"
    width="500px"
    :confirm-btn="{ content: '执行分组', loading: organizeLoading }"
    @confirm="handleOrganize"
  >
    <div v-if="organizePreview">
      <t-alert v-if="organizePreview.total_cases === 0" theme="warning" message="当前没有未分类的用例" />
      <template v-else>
        <t-alert theme="info" :message="`将对 ${organizePreview.total_cases} 个未分类用例进行自动分组，共 ${organizePreview.total_groups} 个分组`" style="margin-bottom: 12px;" />
        <t-table
          :data="organizePreview.groups"
          :columns="[
            { colKey: 'path', title: '文件夹路径' },
            { colKey: 'case_count', title: '用例数', width: 80 }
          ]"
          size="small"
          :max-height="300"
          row-key="path"
        />
      </template>
    </div>
    <t-loading v-else />
  </t-dialog>

  <!-- 移动到文件夹对话框 -->
  <t-dialog
    v-model:visible="moveVisible"
    header="移动到文件夹"
    :confirm-btn="{ content: '确定', loading: moveLoading }"
    @confirm="handleMove"
  >
    <t-radio-group v-model="moveTargetFolderId" style="display: flex; flex-direction: column; gap: 8px;">
      <t-radio value="">未分类</t-radio>
      <template v-for="folder in flatFolders" :key="folder.folder_id">
        <t-radio :value="folder.folder_id">
          <span :style="{ paddingLeft: (folder.level - 1) * 16 + 'px' }">{{ folder.name }}</span>
        </t-radio>
      </template>
    </t-radio-group>
  </t-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { developmentApi } from '../../../api/v2'

interface FlatFolder {
  folder_id: string
  name: string
  level: number
}

const props = defineProps<{
  flatFolders: FlatFolder[]
}>()

const emit = defineEmits<{
  'folders-changed': []
  'data-changed': []
}>()

// ===== 文件夹创建/重命名 =====
const dialogVisible = ref(false)
const confirmLoading = ref(false)
const isRename = ref(false)
const folderName = ref('')
const parentId = ref<string | null>(null)
const editingFolderId = ref<string | null>(null)

const openCreate = (parentFolderId: string | null) => {
  isRename.value = false
  folderName.value = ''
  parentId.value = parentFolderId
  editingFolderId.value = null
  dialogVisible.value = true
}

const openRename = (folder: { folder_id: string; name: string }) => {
  isRename.value = true
  folderName.value = folder.name
  editingFolderId.value = folder.folder_id
  dialogVisible.value = true
}

const handleConfirm = async () => {
  if (!folderName.value.trim()) {
    MessagePlugin.warning('请输入文件夹名称')
    return
  }
  confirmLoading.value = true
  try {
    if (isRename.value && editingFolderId.value) {
      await developmentApi.updateFolder(editingFolderId.value, { name: folderName.value })
      MessagePlugin.success('重命名成功')
    } else {
      await developmentApi.createFolder({ name: folderName.value, parent_id: parentId.value })
      MessagePlugin.success('文件夹创建成功')
    }
    dialogVisible.value = false
    emit('folders-changed')
  } catch (error) {
    console.error('文件夹操作失败:', error)
  } finally {
    confirmLoading.value = false
  }
}

// ===== 智能分组 =====
const organizeVisible = ref(false)
const organizeLoading = ref(false)
const organizePreview = ref<any>(null)

const openOrganize = async () => {
  organizeVisible.value = true
  organizePreview.value = null
  organizeLoading.value = false
  try {
    organizePreview.value = await developmentApi.autoOrganize(true) as any
  } catch (error) {
    organizeVisible.value = false
    console.error('预览分组失败:', error)
  }
}

const handleOrganize = async () => {
  organizeLoading.value = true
  try {
    const res = await developmentApi.autoOrganize(false) as any
    MessagePlugin.success(`分组完成：创建 ${res.created_folders} 个文件夹，移动 ${res.moved_cases} 个用例`)
    organizeVisible.value = false
    emit('folders-changed')
    emit('data-changed')
  } catch (error) {
    console.error('执行分组失败:', error)
  } finally {
    organizeLoading.value = false
  }
}

// ===== 移动到文件夹 =====
const moveVisible = ref(false)
const moveLoading = ref(false)
const moveCaseIds = ref<string[]>([])
const moveTargetFolderId = ref('')

const openMove = (caseIds: string[]) => {
  moveCaseIds.value = caseIds
  moveTargetFolderId.value = ''
  moveVisible.value = true
}

const handleMove = async () => {
  moveLoading.value = true
  try {
    await developmentApi.moveCases({
      case_ids: moveCaseIds.value,
      folder_id: moveTargetFolderId.value || null
    })
    MessagePlugin.success(`已移动 ${moveCaseIds.value.length} 个用例`)
    moveVisible.value = false
    emit('folders-changed')
    emit('data-changed')
  } catch (error) {
    console.error('移动失败:', error)
  } finally {
    moveLoading.value = false
  }
}

defineExpose({
  openCreate,
  openRename,
  openOrganize,
  openMove
})
</script>
