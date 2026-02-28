<!-- 该文件内容使用AI生成，注意识别准确性 -->
<!-- 递归文件夹树节点组件 -->
<template>
  <div
    class="folder-node"
    :class="{ active: selectedFolderId === node.folder_id }"
    :style="{ paddingLeft: depth * 16 + 'px' }"
    @click="$emit('select', node.folder_id)"
    @contextmenu.prevent="$emit('context-menu', $event, node)"
    @dragover.prevent="$emit('drag-over', $event, node.folder_id)"
    @dragleave="$emit('drag-leave', $event)"
    @drop="$emit('drop', $event, node.folder_id)"
  >
    <span
      class="folder-expand"
      :class="{ invisible: !node.children?.length }"
      @click.stop="toggleExpand"
    >
      <ChevronRightIcon v-if="!expanded" size="14px" />
      <ChevronDownIcon v-else size="14px" />
    </span>
    <span class="folder-icon">
      {{ node.children?.length ? (expanded ? '📂' : '📁') : '📁' }}
    </span>
    <span class="folder-name">{{ node.name }}</span>
    <span v-if="node.case_count" class="folder-badge">{{ node.case_count }}</span>
  </div>
  <!-- 递归渲染子节点 -->
  <template v-if="expanded && node.children?.length">
    <FolderTreeNode
      v-for="child in node.children"
      :key="child.folder_id"
      :node="child"
      :depth="depth + 1"
      :selected-folder-id="selectedFolderId"
      @select="$emit('select', $event)"
      @context-menu="(e: MouseEvent, f: any) => $emit('context-menu', e, f)"
      @drag-over="(e: DragEvent, id: string) => $emit('drag-over', e, id)"
      @drag-leave="(e: DragEvent) => $emit('drag-leave', e)"
      @drop="(e: DragEvent, id: string) => $emit('drop', e, id)"
    />
  </template>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ChevronRightIcon, ChevronDownIcon } from 'tdesign-icons-vue-next'

interface FolderNode {
  folder_id: string
  name: string
  parent_id: string | null
  sort_order: number
  case_count: number
  children?: FolderNode[]
}

defineProps<{
  node: FolderNode
  depth: number
  selectedFolderId: string | null
}>()

defineEmits<{
  select: [folderId: string]
  'context-menu': [event: MouseEvent, folder: FolderNode]
  'drag-over': [event: DragEvent, folderId: string]
  'drag-leave': [event: DragEvent]
  drop: [event: DragEvent, folderId: string]
}>()

const expanded = ref(true)

const toggleExpand = () => {
  expanded.value = !expanded.value
}
</script>

<script lang="ts">
export default {
  name: 'FolderTreeNode',
}
</script>

<style scoped>
.folder-expand {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--td-text-color-placeholder);
  cursor: pointer;
  border-radius: 3px;
  transition: color 0.15s;
}

.folder-expand:hover {
  color: var(--td-text-color-primary);
}

.folder-expand.invisible {
  visibility: hidden;
}

.folder-badge {
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
</style>
