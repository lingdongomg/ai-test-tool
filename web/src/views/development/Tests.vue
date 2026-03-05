<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="tests-page">
    <!-- 工具栏 -->
    <PageToolbar
      v-model:search="filters.search"
      search-placeholder="搜索测试用例"
      @search="search"
    >
      <template #filters>
        <t-select
          v-model="filters.category"
          placeholder="用例类别"
          clearable
          style="width: 120px;"
          @change="search"
        >
          <t-option value="normal">正常场景</t-option>
          <t-option value="boundary">边界测试</t-option>
          <t-option value="exception">异常测试</t-option>
          <t-option value="security">安全测试</t-option>
        </t-select>
        <t-select
          v-model="filters.priority"
          placeholder="优先级"
          clearable
          style="width: 100px;"
          @change="search"
        >
          <t-option value="P0">P0</t-option>
          <t-option value="P1">P1</t-option>
          <t-option value="P2">P2</t-option>
          <t-option value="P3">P3</t-option>
        </t-select>
      </template>
      <template #actions>
        <t-button theme="default" variant="outline" @click="folderDialogRef?.openOrganize()">
          <template #icon><ViewModuleIcon /></template>
          智能分组
        </t-button>
        <t-button theme="default" variant="outline" @click="folderDialogRef?.openCreate(null)">
          <template #icon><FolderAddIcon /></template>
          新建文件夹
        </t-button>
        <t-button
          theme="primary"
          @click="handleBatchExecute"
          :disabled="!hasSelection"
        >
          <template #icon><PlayIcon /></template>
          执行选中 ({{ selectionCount }})
        </t-button>
      </template>
    </PageToolbar>

    <!-- 双栏布局 -->
    <div class="tests-layout">
      <!-- 左侧文件夹树 -->
      <div class="folder-panel">
        <div class="folder-header">
          <span class="folder-title">文件夹</span>
        </div>
        <div class="folder-tree">
          <div
            class="folder-node"
            :class="{ active: !selectedFolderId }"
            @click="selectFolder(null)"
          >
            <span class="folder-icon">📋</span>
            <span class="folder-name">全部</span>
            <span v-if="totalCount" class="folder-badge">{{ totalCount }}</span>
          </div>
          <FolderTreeNode
            v-for="folder in folderTree"
            :key="folder.folder_id"
            :node="folder"
            :depth="1"
            :selected-folder-id="selectedFolderId"
            @select="selectFolder"
            @context-menu="showFolderMenu"
            @drag-over="onDragOver"
            @drag-leave="onDragLeave"
            @drop="onDrop"
          />
          <div
            class="folder-node uncategorized"
            :class="{ active: selectedFolderId === 'uncategorized' }"
            @click="selectFolder('uncategorized')"
            @dragover.prevent="onDragOver($event, null)"
            @dragleave="onDragLeave($event)"
            @drop="onDrop($event, null)"
          >
            <span class="folder-icon">📄</span>
            <span class="folder-name">未分类</span>
            <span v-if="uncategorizedCount" class="folder-badge">{{ uncategorizedCount }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧用例列表 -->
      <div class="cases-panel">
        <DataTable
          :data="items"
          :columns="columns"
          :loading="loading"
          :pagination="pagination"
          :selected-keys="selectedIds"
          row-key="case_id"
          @page-change="handlePageChange"
          @select-change="handleSelectChange"
        >
          <template #name="{ row }">
            <span class="case-name" draggable="true" @dragstart="onDragStart($event, row)">
              {{ row.name }}
            </span>
          </template>
          <template #endpoint="{ row }">
            <div class="endpoint-cell">
              <StatusTag type="method" :value="row.endpoint_method" size="small" />
              <span class="endpoint-path">{{ row.endpoint_path }}</span>
            </div>
          </template>
          <template #category="{ row }">
            <StatusTag type="category" :value="row.category" size="small" />
          </template>
          <template #priority="{ row }">
            <StatusTag type="priority" :value="row.priority" variant="outline" size="small" />
          </template>
          <template #is_enabled="{ row }">
            <t-switch :value="!!row.is_enabled" size="small" @change="(val: boolean) => handleToggle(row, val)" />
          </template>
          <template #op="{ row }">
            <t-space>
              <t-link theme="primary" @click="openDetail(row)">详情</t-link>
              <t-link theme="primary" @click="openEdit(row)">编辑</t-link>
              <t-link theme="primary" @click="openCopy(row)">复制</t-link>
              <t-dropdown :options="moveMenuOptions" @click="(item: any) => handleMoveMenu(item, row)">
                <t-link theme="primary">移动</t-link>
              </t-dropdown>
              <t-link theme="primary" @click="openExecute([row.case_id])">执行</t-link>
              <t-popconfirm content="确定删除该测试用例？" @confirm="handleDelete(row)">
                <t-link theme="danger">删除</t-link>
              </t-popconfirm>
            </t-space>
          </template>
        </DataTable>

        <!-- 批量操作栏 -->
        <div v-if="hasSelection" class="batch-bar">
          <span>已选 {{ selectionCount }} 个用例</span>
          <t-dropdown :options="batchMoveOptions" @click="handleBatchMoveMenu">
            <t-button size="small" variant="outline">批量移动</t-button>
          </t-dropdown>
        </div>
      </div>
    </div>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <div class="context-menu-item" @click="handleCtxCreate">新建子文件夹</div>
      <div class="context-menu-item" @click="handleCtxRename">重命名</div>
      <div class="context-menu-item danger" @click="confirmDeleteFolder(contextMenu.folder)">删除文件夹</div>
    </div>

    <!-- 子组件对话框 -->
    <CaseDetailDrawer
      v-model:visible="detailVisible"
      :data="detailData"
      @edit="openEditFromDetail"
    />
    <CaseEditDialog
      v-model:visible="editVisible"
      :data="editData"
      :is-copy="editIsCopy"
      @saved="refresh"
    />
    <ExecuteDialog
      v-model:visible="executeVisible"
      :case-ids="executeCaseIds"
    />
    <FolderDialog
      ref="folderDialogRef"
      :flat-folders="flatFolders"
      @folders-changed="loadFolders"
      @data-changed="refreshAll"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'
import { PlayIcon, ViewModuleIcon, FolderAddIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'
import { PageToolbar, DataTable, StatusTag } from '../../components'
import { useList, useTableSelection } from '../../composables'
import FolderTreeNode from './FolderTreeNode.vue'
import CaseDetailDrawer from './components/CaseDetailDrawer.vue'
import CaseEditDialog from './components/CaseEditDialog.vue'
import ExecuteDialog from './components/ExecuteDialog.vue'
import FolderDialog from './components/FolderDialog.vue'

// =====================================================
// 文件夹状态
// =====================================================
interface FolderNode {
  folder_id: string
  name: string
  parent_id: string | null
  sort_order: number
  case_count: number
  children?: FolderNode[]
}

const folders = ref<any[]>([])
const uncategorizedCount = ref(0)
const selectedFolderId = ref<string | null>(null)
const totalCount = ref(0)
const folderDialogRef = ref<InstanceType<typeof FolderDialog> | null>(null)

const folderTree = computed<FolderNode[]>(() => {
  const map = new Map<string, FolderNode>()
  const roots: FolderNode[] = []
  for (const f of folders.value) {
    map.set(f.folder_id, { ...f, children: [] })
  }
  for (const f of folders.value) {
    const node = map.get(f.folder_id)!
    if (f.parent_id && map.has(f.parent_id)) {
      map.get(f.parent_id)!.children!.push(node)
    } else {
      roots.push(node)
    }
  }
  const sumCount = (node: FolderNode): number => {
    let total = node.case_count || 0
    for (const child of node.children || []) { total += sumCount(child) }
    node.case_count = total
    return total
  }
  roots.forEach(sumCount)
  return roots
})

const flatFolders = computed(() => {
  const result: Array<{ folder_id: string; name: string; level: number }> = []
  const walk = (nodes: FolderNode[], level: number) => {
    for (const n of nodes) {
      result.push({ folder_id: n.folder_id, name: n.name, level })
      if (n.children?.length) walk(n.children, level + 1)
    }
  }
  walk(folderTree.value, 1)
  return result
})

const loadFolders = async () => {
  try {
    const res = await developmentApi.listFolders() as any
    folders.value = res.folders || []
    uncategorizedCount.value = res.uncategorized_count || 0
  } catch (error) {
    console.error('加载文件夹失败:', error)
    MessagePlugin.error('加载文件夹失败')
  }
}

const selectFolder = (folderId: string | null) => {
  selectedFolderId.value = folderId
  search()
}

// =====================================================
// 列表数据
// =====================================================
const { items, loading, pagination, filters, handlePageChange, search, refresh } = useList({
  fetchFn: (params) => {
    const extra: any = {}
    if (selectedFolderId.value) { extra.folder_id = selectedFolderId.value }
    return developmentApi.listTests({ ...params, ...extra })
  },
  defaultParams: { search: '', category: '', priority: '' }
})

const updateTotalCount = async () => {
  try {
    const res = await developmentApi.listTests({ page: 1, page_size: 1 }) as any
    totalCount.value = res.total || 0
  } catch { /* ignore */ }
}

const refreshAll = () => {
  refresh()
  updateTotalCount()
}

const { selectedIds, handleSelectChange, hasSelection, selectionCount } = useTableSelection({ rowKey: 'case_id' })

const columns = [
  { colKey: 'row-select', type: 'multiple', width: 50 },
  { colKey: 'name', title: '用例名称', ellipsis: true },
  { colKey: 'endpoint', title: '关联接口', width: 250 },
  { colKey: 'category', title: '类别', width: 100 },
  { colKey: 'priority', title: '优先级', width: 80 },
  { colKey: 'is_enabled', title: '启用', width: 80 },
  { colKey: 'op', title: '操作', width: 280, fixed: 'right' }
]

// =====================================================
// 详情/编辑/执行 对话框状态
// =====================================================
const detailVisible = ref(false)
const detailData = ref<any>(null)
const editVisible = ref(false)
const editData = ref<any>(null)
const editIsCopy = ref(false)
const executeVisible = ref(false)
const executeCaseIds = ref<string[]>([])

const openDetail = (row: any) => {
  detailData.value = row
  detailVisible.value = true
}
const openEdit = (row: any) => {
  if (!row) return
  editIsCopy.value = false
  editData.value = row
  editVisible.value = true
}
const openCopy = (row: any) => {
  editIsCopy.value = true
  editData.value = row
  editVisible.value = true
}
const openEditFromDetail = (row: any) => {
  detailVisible.value = false
  openEdit(row)
}
const openExecute = (caseIds: string[]) => {
  executeCaseIds.value = caseIds
  executeVisible.value = true
}
const handleBatchExecute = () => {
  openExecute([...selectedIds.value])
}

// =====================================================
// 用例操作
// =====================================================
const handleToggle = async (row: any, enabled: boolean) => {
  try {
    await developmentApi.updateTest(row.case_id, { is_enabled: enabled })
    row.is_enabled = enabled
    MessagePlugin.success(enabled ? '已启用' : '已禁用')
  } catch (error) {
    console.error('切换状态失败:', error)
  }
}

const handleDelete = async (row: any) => {
  try {
    await developmentApi.deleteTest(row.case_id)
    MessagePlugin.success('删除成功')
    refresh()
    await loadFolders()
    updateTotalCount()
  } catch (error) {
    console.error('删除失败:', error)
    MessagePlugin.error('删除失败')
  }
}

// =====================================================
// 右键菜单
// =====================================================
const contextMenu = reactive({ visible: false, x: 0, y: 0, folder: null as FolderNode | null })

const showFolderMenu = (event: MouseEvent, folder: FolderNode) => {
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.folder = folder
  contextMenu.visible = true
}
const hideContextMenu = () => { contextMenu.visible = false }

const handleCtxCreate = () => {
  folderDialogRef.value?.openCreate(contextMenu.folder?.folder_id ?? null)
  contextMenu.visible = false
}
const handleCtxRename = () => {
  if (contextMenu.folder) folderDialogRef.value?.openRename(contextMenu.folder)
  contextMenu.visible = false
}

const confirmDeleteFolder = async (folder: FolderNode | null) => {
  if (!folder) return
  contextMenu.visible = false
  const dialog = DialogPlugin.confirm({
    header: '删除文件夹',
    body: `确定删除文件夹「${folder.name}」吗？删除后文件夹下的用例将移至未分类。`,
    confirmBtn: { content: '删除', theme: 'danger' },
    onConfirm: async () => {
      try {
        await developmentApi.deleteFolder(folder.folder_id)
        MessagePlugin.success('文件夹已删除')
        if (selectedFolderId.value === folder.folder_id) selectedFolderId.value = null
        await loadFolders()
        refresh()
      } catch (error) {
        console.error('删除文件夹失败:', error)
      } finally {
        dialog.destroy()
      }
    },
  })
}

// =====================================================
// 拖拽移动
// =====================================================
let dragCaseIds: string[] = []

const onDragStart = (event: DragEvent, row: any) => {
  dragCaseIds = hasSelection.value ? [...selectedIds.value] : [row.case_id]
  event.dataTransfer?.setData('text/plain', JSON.stringify(dragCaseIds))
}
const onDragOver = (event: DragEvent, _folderId: string | null) => {
  (event.currentTarget as HTMLElement)?.classList.add('drag-over')
}
const onDragLeave = (event: DragEvent) => {
  (event.currentTarget as HTMLElement)?.classList.remove('drag-over')
}
const onDrop = async (event: DragEvent, folderId: string | null) => {
  (event.currentTarget as HTMLElement)?.classList.remove('drag-over')
  if (!dragCaseIds.length) return
  try {
    await developmentApi.moveCases({ case_ids: dragCaseIds, folder_id: folderId })
    MessagePlugin.success(`已移动 ${dragCaseIds.length} 个用例`)
    dragCaseIds = []
    await loadFolders()
    refresh()
    updateTotalCount()
  } catch (error) {
    console.error('移动失败:', error)
    MessagePlugin.error('移动失败')
  }
}

// =====================================================
// 移动菜单
// =====================================================
const moveMenuOptions = [
  { content: '移出文件夹', value: '__uncategorized__' },
  { content: '移动到...', value: '__dialog__' },
]
const batchMoveOptions = computed(() => [
  { content: '移出文件夹', value: '__uncategorized__' },
  { content: '移动到...', value: '__dialog__' },
])

const handleMoveMenu = async (item: any, row: any) => {
  if (item.value === '__uncategorized__') {
    await developmentApi.moveCases({ case_ids: [row.case_id], folder_id: null })
    MessagePlugin.success('已移出文件夹')
    await loadFolders()
    refresh()
  } else if (item.value === '__dialog__') {
    folderDialogRef.value?.openMove([row.case_id])
  }
}
const handleBatchMoveMenu = async (item: any) => {
  if (item.value === '__uncategorized__') {
    await developmentApi.moveCases({ case_ids: [...selectedIds.value], folder_id: null })
    MessagePlugin.success('已移出文件夹')
    await loadFolders()
    refresh()
  } else if (item.value === '__dialog__') {
    folderDialogRef.value?.openMove([...selectedIds.value])
  }
}

// =====================================================
// 生命周期
// =====================================================
onMounted(() => {
  loadFolders()
  updateTotalCount()
  document.addEventListener('click', hideContextMenu)
})
onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu)
})
</script>

<style scoped>
.tests-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tests-layout {
  display: flex;
  gap: 16px;
  min-height: 500px;
}

.folder-panel {
  width: 240px;
  min-width: 240px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.folder-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--td-border-level-1-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.folder-title {
  font-weight: 600;
  font-size: 14px;
}

.folder-tree {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

:deep(.folder-node) {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.15s;
  font-size: 13px;
}

:deep(.folder-node):hover {
  background: var(--td-bg-color-container-hover);
}

:deep(.folder-node).active {
  background: var(--td-brand-color-light);
  color: var(--td-brand-color);
  font-weight: 500;
}

:deep(.folder-node).drag-over {
  background: var(--td-brand-color-light-hover);
  outline: 2px dashed var(--td-brand-color);
  outline-offset: -2px;
}

:deep(.folder-node).uncategorized {
  border-top: 1px solid var(--td-border-level-1-color);
  margin-top: 4px;
}

:deep(.folder-icon) { font-size: 14px; flex-shrink: 0; }
:deep(.folder-name) { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:deep(.folder-badge) { margin-left: 6px; font-size: 10px; line-height: 16px; min-width: 18px; height: 16px; padding: 0 5px; border-radius: 8px; text-align: center; flex-shrink: 0; background: var(--td-brand-color-light); color: var(--td-brand-color); font-weight: 500; }

.cases-panel { flex: 1; min-width: 0; position: relative; }
.endpoint-cell { display: flex; align-items: center; gap: 8px; }
.endpoint-path { font-family: 'Monaco', 'Menlo', monospace; font-size: 12px; color: var(--td-text-color-secondary); }
.case-name { cursor: grab; }
.case-name:active { cursor: grabbing; }

.batch-bar {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: var(--td-shadow-2);
  z-index: 10;
  font-size: 13px;
}

.context-menu {
  position: fixed;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  box-shadow: var(--td-shadow-3);
  padding: 4px 0;
  z-index: 1000;
  min-width: 140px;
}

.context-menu-item { padding: 8px 16px; font-size: 13px; cursor: pointer; transition: background 0.15s; }
.context-menu-item:hover { background: var(--td-bg-color-container-hover); }
.context-menu-item.danger { color: var(--td-error-color); }
.context-menu-item.danger:hover { background: var(--td-error-color-1); }
</style>
