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
        <t-button theme="default" variant="outline" @click="openAutoOrganize">
          <template #icon><ViewModuleIcon /></template>
          智能分组
        </t-button>
        <t-button theme="default" variant="outline" @click="openCreateFolder(null)">
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
          <!-- 全部 -->
          <div
            class="folder-node"
            :class="{ active: !selectedFolderId }"
            @click="selectFolder(null)"
          >
            <span class="folder-icon">📋</span>
            <span class="folder-name">全部</span>
            <span v-if="totalCount" class="folder-badge">{{ totalCount }}</span>
          </div>
          <!-- 文件夹列表（递归渲染，支持多级嵌套） -->
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
          <!-- 未分类 -->
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
            <span
              class="case-name"
              draggable="true"
              @dragstart="onDragStart($event, row)"
            >
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
            <t-switch
              :value="!!row.is_enabled"
              size="small"
              @change="(val: boolean) => handleToggle(row, val)"
            />
          </template>
          <template #op="{ row }">
            <t-space>
              <t-link theme="primary" @click="detailDialog.open(row)">详情</t-link>
              <t-link theme="primary" @click="openEdit(row)">编辑</t-link>
              <t-link theme="primary" @click="openCopy(row)">复制</t-link>
              <t-dropdown :options="getMoveMenuOptions(row)" @click="(item: any) => handleMoveMenu(item, row)">
                <t-link theme="primary">移动</t-link>
              </t-dropdown>
              <t-link theme="primary" @click="executeDialog.open([row.case_id])">执行</t-link>
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
      <div class="context-menu-item" @click="openCreateFolder(contextMenu.folder?.folder_id)">
        新建子文件夹
      </div>
      <div class="context-menu-item" @click="openRenameFolder(contextMenu.folder)">
        重命名
      </div>
      <div class="context-menu-item danger" @click="confirmDeleteFolder(contextMenu.folder)">
        删除文件夹
      </div>
    </div>

    <!-- 执行对话框 -->
    <t-dialog
      v-model:visible="executeDialog.visible.value"
      header="执行测试"
      :confirm-btn="{ content: '执行', loading: executeDialog.loading.value }"
      @confirm="confirmExecute"
    >
      <t-form :data="executeForm" label-width="100px">
        <t-form-item label="服务器地址">
          <t-input v-model="executeForm.base_url" placeholder="http://localhost:8080" />
        </t-form-item>
        <t-form-item label="目标环境">
          <t-select v-model="executeForm.environment" style="width: 100%;">
            <t-option value="local">本地环境</t-option>
            <t-option value="test">测试环境</t-option>
            <t-option value="staging">预发环境</t-option>
          </t-select>
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 详情抽屉 -->
    <t-drawer
      v-model:visible="detailDialog.visible.value"
      header="测试用例详情"
      size="600px"
    >
      <template #footer>
        <t-space>
          <t-button @click="detailDialog.close()">关闭</t-button>
          <t-button theme="primary" @click="openEdit(detailDialog.data.value)">编辑</t-button>
        </t-space>
      </template>
      <template v-if="detailDialog.data.value">
        <t-descriptions :column="1" bordered>
          <t-descriptions-item label="用例名称">{{ detailDialog.data.value.name }}</t-descriptions-item>
          <t-descriptions-item label="描述">{{ detailDialog.data.value.description || '-' }}</t-descriptions-item>
          <t-descriptions-item label="类别">
            <StatusTag type="category" :value="detailDialog.data.value.category" />
          </t-descriptions-item>
          <t-descriptions-item label="优先级">
            <StatusTag type="priority" :value="detailDialog.data.value.priority" variant="outline" />
          </t-descriptions-item>
          <t-descriptions-item label="请求方法">{{ detailDialog.data.value.method }}</t-descriptions-item>
          <t-descriptions-item label="请求URL">{{ detailDialog.data.value.url }}</t-descriptions-item>
          <t-descriptions-item label="期望状态码">{{ detailDialog.data.value.expected_status_code }}</t-descriptions-item>
        </t-descriptions>

        <t-divider>请求头</t-divider>
        <pre class="code-block">{{ safeStringifyJSON(detailDialog.data.value.headers) }}</pre>

        <t-divider>请求体</t-divider>
        <pre class="code-block">{{ safeStringifyJSON(detailDialog.data.value.body) }}</pre>
      </template>
    </t-drawer>

    <!-- 编辑对话框 -->
    <t-dialog
      v-model:visible="editDialog.visible.value"
      :header="isCreating ? '复制测试用例' : '编辑测试用例'"
      width="700px"
      :confirm-btn="{ content: '保存', loading: editDialog.loading.value }"
      @confirm="confirmEdit"
    >
      <t-form :data="editForm" label-width="100px" label-align="top">
        <t-row :gutter="16">
          <t-col :span="12">
            <t-form-item label="用例名称" required>
              <t-input v-model="editForm.name" placeholder="请输入用例名称" />
            </t-form-item>
          </t-col>
          <t-col :span="6">
            <t-form-item label="类别">
              <t-select v-model="editForm.category" style="width: 100%;">
                <t-option value="normal">正常场景</t-option>
                <t-option value="boundary">边界测试</t-option>
                <t-option value="exception">异常测试</t-option>
                <t-option value="security">安全测试</t-option>
              </t-select>
            </t-form-item>
          </t-col>
          <t-col :span="6">
            <t-form-item label="优先级">
              <t-select v-model="editForm.priority" style="width: 100%;">
                <t-option value="high">高</t-option>
                <t-option value="medium">中</t-option>
                <t-option value="low">低</t-option>
              </t-select>
            </t-form-item>
          </t-col>
        </t-row>
        <t-form-item label="描述">
          <t-textarea v-model="editForm.description" placeholder="请输入用例描述" :rows="2" />
        </t-form-item>
        <t-row :gutter="16">
          <t-col :span="6">
            <t-form-item label="请求方法">
              <t-select v-model="editForm.method" style="width: 100%;">
                <t-option v-for="m in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']" :key="m" :value="m">{{ m }}</t-option>
              </t-select>
            </t-form-item>
          </t-col>
          <t-col :span="18">
            <t-form-item label="请求URL">
              <t-input v-model="editForm.url" placeholder="/api/v1/xxx" />
            </t-form-item>
          </t-col>
        </t-row>
        <t-row :gutter="16">
          <t-col :span="12">
            <t-form-item label="期望状态码">
              <t-input-number v-model="editForm.expected_status_code" :min="100" :max="599" style="width: 100%;" />
            </t-form-item>
          </t-col>
          <t-col :span="12">
            <t-form-item label="最大响应时间(ms)">
              <t-input-number v-model="editForm.max_response_time_ms" :min="100" :max="60000" style="width: 100%;" />
            </t-form-item>
          </t-col>
        </t-row>
        <t-form-item label="请求头 (JSON)">
          <t-textarea v-model="editForm.headersStr" placeholder='{"Content-Type": "application/json"}' :rows="3" style="font-family: monospace;" />
        </t-form-item>
        <t-form-item label="查询参数 (JSON)">
          <t-textarea v-model="editForm.queryParamsStr" placeholder='{"page": 1, "size": 10}' :rows="2" style="font-family: monospace;" />
        </t-form-item>
        <t-form-item label="请求体 (JSON)">
          <t-textarea v-model="editForm.bodyStr" placeholder='{"key": "value"}' :rows="5" style="font-family: monospace;" />
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 新建/重命名文件夹对话框 -->
    <t-dialog
      v-model:visible="folderDialog.visible"
      :header="folderDialog.isRename ? '重命名文件夹' : '新建文件夹'"
      :confirm-btn="{ content: '确定', loading: folderDialog.loading }"
      @confirm="confirmFolderDialog"
    >
      <t-form label-width="80px">
        <t-form-item label="名称" required>
          <t-input v-model="folderDialog.name" placeholder="请输入文件夹名称" />
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- 智能分组预览对话框 -->
    <t-dialog
      v-model:visible="organizeDialog.visible"
      header="智能分组预览"
      width="500px"
      :confirm-btn="{ content: '执行分组', loading: organizeDialog.loading }"
      @confirm="confirmAutoOrganize"
    >
      <div v-if="organizeDialog.preview">
        <t-alert v-if="organizeDialog.preview.total_cases === 0" theme="warning" message="当前没有未分类的用例" />
        <template v-else>
          <t-alert theme="info" :message="`将对 ${organizeDialog.preview.total_cases} 个未分类用例进行自动分组，共 ${organizeDialog.preview.total_groups} 个分组`" style="margin-bottom: 12px;" />
          <t-table
            :data="organizeDialog.preview.groups"
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
      v-model:visible="moveDialog.visible"
      header="移动到文件夹"
      :confirm-btn="{ content: '确定', loading: moveDialog.loading }"
      @confirm="confirmMoveDialog"
    >
      <t-radio-group v-model="moveDialog.targetFolderId" style="display: flex; flex-direction: column; gap: 8px;">
        <t-radio value="">未分类</t-radio>
        <template v-for="folder in flatFolders" :key="folder.folder_id">
          <t-radio :value="folder.folder_id">
            <span :style="{ paddingLeft: (folder.level - 1) * 16 + 'px' }">{{ folder.name }}</span>
          </t-radio>
        </template>
      </t-radio-group>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next'
import { PlayIcon, ViewModuleIcon, FolderAddIcon } from 'tdesign-icons-vue-next'
import { developmentApi } from '../../api/v2'
import { PageToolbar, DataTable, StatusTag } from '../../components'
import { useList, useTableSelection, useDialog } from '../../composables'
import { safeParseJSON, safeStringifyJSON } from '../../utils'
import FolderTreeNode from './FolderTreeNode.vue'

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

  // 递归汇总：父文件夹 case_count = 自身直接用例数 + 所有子孙用例数
  const sumCount = (node: FolderNode): number => {
    let total = node.case_count || 0
    for (const child of node.children || []) {
      total += sumCount(child)
    }
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
    if (selectedFolderId.value) {
      extra.folder_id = selectedFolderId.value
    }
    return developmentApi.listTests({ ...params, ...extra })
  },
  defaultParams: { search: '', category: '', priority: '' }
})

// 监听总数变化
const updateTotalCount = async () => {
  try {
    const res = await developmentApi.listTests({ page: 1, page_size: 1 }) as any
    totalCount.value = res.total || 0
  } catch { /* ignore */ }
}

// 表格选择
const { selectedIds, handleSelectChange, hasSelection, selectionCount } = useTableSelection({ rowKey: 'case_id' })

// 表格列
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
// 对话框
// =====================================================
const executeDialog = useDialog<string[]>()
const detailDialog = useDialog<any>()
const editDialog = useDialog<any>()
const isCreating = ref(false)

const executeForm = reactive({
  base_url: 'http://localhost:8080',
  environment: 'local'
})

const editForm = reactive({
  name: '',
  description: '',
  category: 'normal',
  priority: 'medium',
  method: 'GET',
  url: '',
  expected_status_code: 200,
  max_response_time_ms: 3000,
  headersStr: '{}',
  bodyStr: '{}',
  queryParamsStr: '{}'
})

// 文件夹对话框
const folderDialog = reactive({
  visible: false,
  loading: false,
  isRename: false,
  name: '',
  parentId: null as string | null,
  editingFolderId: null as string | null,
})

// 智能分组对话框
const organizeDialog = reactive({
  visible: false,
  loading: false,
  preview: null as any,
})

// 移动对话框
const moveDialog = reactive({
  visible: false,
  loading: false,
  caseIds: [] as string[],
  targetFolderId: '',
})

// 右键菜单
const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  folder: null as FolderNode | null,
})

// =====================================================
// 文件夹操作
// =====================================================
const openCreateFolder = (parentId: string | null) => {
  folderDialog.isRename = false
  folderDialog.name = ''
  folderDialog.parentId = parentId
  folderDialog.editingFolderId = null
  folderDialog.visible = true
  contextMenu.visible = false
}

const openRenameFolder = (folder: FolderNode | null) => {
  if (!folder) return
  folderDialog.isRename = true
  folderDialog.name = folder.name
  folderDialog.editingFolderId = folder.folder_id
  folderDialog.visible = true
  contextMenu.visible = false
}

const confirmFolderDialog = async () => {
  if (!folderDialog.name.trim()) {
    MessagePlugin.warning('请输入文件夹名称')
    return
  }
  folderDialog.loading = true
  try {
    if (folderDialog.isRename && folderDialog.editingFolderId) {
      await developmentApi.updateFolder(folderDialog.editingFolderId, { name: folderDialog.name })
      MessagePlugin.success('重命名成功')
    } else {
      await developmentApi.createFolder({
        name: folderDialog.name,
        parent_id: folderDialog.parentId,
      })
      MessagePlugin.success('文件夹创建成功')
    }
    folderDialog.visible = false
    await loadFolders()
  } catch (error) {
    console.error('文件夹操作失败:', error)
  } finally {
    folderDialog.loading = false
  }
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
        if (selectedFolderId.value === folder.folder_id) {
          selectedFolderId.value = null
        }
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

const showFolderMenu = (event: MouseEvent, folder: FolderNode) => {
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.folder = folder
  contextMenu.visible = true
}

const hideContextMenu = () => {
  contextMenu.visible = false
}

// =====================================================
// 智能分组
// =====================================================
const openAutoOrganize = async () => {
  organizeDialog.visible = true
  organizeDialog.preview = null
  organizeDialog.loading = false
  try {
    const res = await developmentApi.autoOrganize(true) as any
    organizeDialog.preview = res
  } catch (error) {
    organizeDialog.visible = false
    console.error('预览分组失败:', error)
  }
}

const confirmAutoOrganize = async () => {
  organizeDialog.loading = true
  try {
    const res = await developmentApi.autoOrganize(false) as any
    MessagePlugin.success(`分组完成：创建 ${res.created_folders} 个文件夹，移动 ${res.moved_cases} 个用例`)
    organizeDialog.visible = false
    await loadFolders()
    refresh()
    updateTotalCount()
  } catch (error) {
    console.error('执行分组失败:', error)
  } finally {
    organizeDialog.loading = false
  }
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
  const target = event.currentTarget as HTMLElement
  target?.classList.add('drag-over')
}

const onDragLeave = (event: DragEvent) => {
  const target = event.currentTarget as HTMLElement
  target?.classList.remove('drag-over')
}

const onDrop = async (event: DragEvent, folderId: string | null) => {
  const target = event.currentTarget as HTMLElement
  target?.classList.remove('drag-over')
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
  }
}

// =====================================================
// 移动菜单
// =====================================================
const getMoveMenuOptions = (_row: any) => {
  const options: any[] = [
    { content: '移出文件夹', value: '__uncategorized__' },
    { content: '移动到...', value: '__dialog__' },
  ]
  return options
}

const handleMoveMenu = async (item: any, row: any) => {
  if (item.value === '__uncategorized__') {
    await developmentApi.moveCases({ case_ids: [row.case_id], folder_id: null })
    MessagePlugin.success('已移出文件夹')
    await loadFolders()
    refresh()
  } else if (item.value === '__dialog__') {
    moveDialog.caseIds = [row.case_id]
    moveDialog.targetFolderId = ''
    moveDialog.visible = true
  }
}

const batchMoveOptions = computed(() => [
  { content: '移出文件夹', value: '__uncategorized__' },
  { content: '移动到...', value: '__dialog__' },
])

const handleBatchMoveMenu = async (item: any) => {
  if (item.value === '__uncategorized__') {
    await developmentApi.moveCases({ case_ids: [...selectedIds.value], folder_id: null })
    MessagePlugin.success('已移出文件夹')
    await loadFolders()
    refresh()
  } else if (item.value === '__dialog__') {
    moveDialog.caseIds = [...selectedIds.value]
    moveDialog.targetFolderId = ''
    moveDialog.visible = true
  }
}

const confirmMoveDialog = async () => {
  moveDialog.loading = true
  try {
    await developmentApi.moveCases({
      case_ids: moveDialog.caseIds,
      folder_id: moveDialog.targetFolderId || null
    })
    MessagePlugin.success(`已移动 ${moveDialog.caseIds.length} 个用例`)
    moveDialog.visible = false
    await loadFolders()
    refresh()
    updateTotalCount()
  } catch (error) {
    console.error('移动失败:', error)
  } finally {
    moveDialog.loading = false
  }
}

// =====================================================
// 用例操作（与原有逻辑一致）
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

const openEdit = (row: any) => {
  if (!row) return
  isCreating.value = false
  fillEditForm(row)
  detailDialog.close()
  editDialog.open(row)
}

const openCopy = (row: any) => {
  isCreating.value = true
  fillEditForm(row, true)
  editDialog.open(row)
}

const fillEditForm = (row: any, isCopy = false) => {
  editForm.name = isCopy ? `${row.name} (副本)` : row.name || ''
  editForm.description = row.description || ''
  editForm.category = row.category || 'normal'
  editForm.priority = row.priority || 'medium'
  editForm.method = row.method || 'GET'
  editForm.url = row.url || ''
  editForm.expected_status_code = row.expected_status_code || 200
  editForm.max_response_time_ms = row.max_response_time_ms || 3000
  editForm.headersStr = safeStringifyJSON(row.headers)
  editForm.bodyStr = safeStringifyJSON(row.body)
  editForm.queryParamsStr = safeStringifyJSON(row.query_params)
}

const confirmEdit = async () => {
  if (!editForm.name.trim()) {
    MessagePlugin.warning('请输入用例名称')
    return
  }

  await editDialog.confirm(async () => {
    const data = {
      name: editForm.name,
      description: editForm.description,
      category: editForm.category,
      priority: editForm.priority,
      method: editForm.method,
      url: editForm.url,
      expected_status_code: editForm.expected_status_code,
      max_response_time_ms: editForm.max_response_time_ms,
      headers: safeParseJSON(editForm.headersStr, {}),
      body: safeParseJSON(editForm.bodyStr, null),
      query_params: safeParseJSON(editForm.queryParamsStr, {})
    }

    if (isCreating.value) {
      await developmentApi.copyTest(editDialog.data.value.case_id, data)
      MessagePlugin.success('复制成功')
    } else {
      await developmentApi.updateTest(editDialog.data.value.case_id, data)
      MessagePlugin.success('保存成功')
    }
    refresh()
  })
}

const handleBatchExecute = () => {
  executeDialog.open([...selectedIds.value])
}

const confirmExecute = async () => {
  await executeDialog.confirm(async () => {
    const res = await developmentApi.executeTests({
      test_case_ids: executeDialog.data.value!,
      base_url: executeForm.base_url,
      environment: executeForm.environment
    }) as any
    MessagePlugin.success(`执行完成，通过: ${res.passed}/${res.total}，通过率: ${res.pass_rate}%`)
  })
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

/* 左侧文件夹面板 */
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

:deep(.folder-icon) {
  font-size: 14px;
  flex-shrink: 0;
}

:deep(.folder-name) {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.folder-badge) {
  margin-left: 6px;
  font-size: 10px;
  line-height: 16px;
  min-width: 18px;
  height: 16px;
  padding: 0 5px;
  border-radius: 8px;
  text-align: center;
  flex-shrink: 0;
  background: var(--td-brand-color-light);
  color: var(--td-brand-color);
  font-weight: 500;
}

/* 右侧用例面板 */
.cases-panel {
  flex: 1;
  min-width: 0;
  position: relative;
}

.endpoint-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.endpoint-path {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
}

.case-name {
  cursor: grab;
}

.case-name:active {
  cursor: grabbing;
}

.code-block {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
}

/* 批量操作栏 */
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
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  font-size: 13px;
}

/* 右键菜单 */
.context-menu {
  position: fixed;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  padding: 4px 0;
  z-index: 1000;
  min-width: 140px;
}

.context-menu-item {
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.context-menu-item:hover {
  background: var(--td-bg-color-container-hover);
}

.context-menu-item.danger {
  color: var(--td-error-color);
}

.context-menu-item.danger:hover {
  background: var(--td-error-color-1);
}
</style>
