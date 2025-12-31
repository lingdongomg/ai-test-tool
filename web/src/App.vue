<template>
  <t-layout>
    <t-aside width="220px" class="sidebar">
      <div class="logo">
        <ApiIcon class="logo-icon" />
        <span class="logo-text">AI Test Tool</span>
      </div>
      <t-menu
        :value="activeMenu"
        theme="dark"
        @change="handleMenuChange"
      >
        <t-menu-item value="dashboard">
          <template #icon><DashboardIcon /></template>
          概览
        </t-menu-item>
        <t-menu-item value="tasks">
          <template #icon><RocketIcon /></template>
          分析任务
        </t-menu-item>
        <t-menu-item value="endpoints">
          <template #icon><ApiIcon /></template>
          接口管理
        </t-menu-item>
        <t-menu-item value="tags">
          <template #icon><TagIcon /></template>
          标签管理
        </t-menu-item>
        <t-menu-item value="import">
          <template #icon><FileImportIcon /></template>
          文档导入
        </t-menu-item>
        <t-submenu value="testing" title="测试中心">
          <template #icon><TaskIcon /></template>
          <t-menu-item value="scenarios">测试场景</t-menu-item>
          <t-menu-item value="test-cases">测试用例</t-menu-item>
          <t-menu-item value="executions">执行记录</t-menu-item>
        </t-submenu>
        <t-menu-item value="analysis">
          <template #icon><ChartAnalyticsIcon /></template>
          智能分析
        </t-menu-item>
      </t-menu>
    </t-aside>
    <t-layout>
      <t-header class="header">
        <div class="header-title">{{ currentTitle }}</div>
      </t-header>
      <t-content class="content">
        <router-view />
      </t-content>
    </t-layout>
  </t-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  DashboardIcon, 
  ApiIcon, 
  TagIcon, 
  FileImportIcon, 
  TaskIcon,
  ChartAnalyticsIcon,
  RocketIcon
} from 'tdesign-icons-vue-next'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => {
  const name = route.name as string
  if (name === 'ScenarioDetail') return 'scenarios'
  if (name === 'TaskDetail') return 'tasks'
  return name?.toLowerCase() || 'dashboard'
})

const currentTitle = computed(() => {
  return (route.meta?.title as string) || 'AI Test Tool'
})

const handleMenuChange = (value: string) => {
  router.push({ name: value.charAt(0).toUpperCase() + value.slice(1) })
}
</script>

<style scoped>
.sidebar {
  background: linear-gradient(180deg, #001529 0%, #002140 100%);
  min-height: 100vh;
}

.logo {
  display: flex;
  align-items: center;
  padding: 16px 24px;
  color: #fff;
}

.logo-icon {
  font-size: 28px;
  color: #0052d9;
}

.logo-text {
  margin-left: 12px;
  font-size: 18px;
  font-weight: 600;
}

.header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  height: 64px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
}

.content {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}
</style>
