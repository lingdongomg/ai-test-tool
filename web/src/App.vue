<template>
  <t-layout>
    <t-aside width="240px" class="sidebar">
      <div class="logo">
        <ApiIcon class="logo-icon" />
        <span class="logo-text">AI Test Tool</span>
      </div>
      <t-menu
        :value="activeMenu"
        :expanded="expandedMenus"
        theme="dark"
        @change="handleMenuChange"
        @expand="handleMenuExpand"
        class="menu-transparent"
      >
        <!-- 首页 -->
        <t-menu-item value="dashboard">
          <template #icon><DashboardIcon /></template>
          首页
        </t-menu-item>
        
        <!-- 开发自测 -->
        <t-submenu value="development" title="开发自测">
          <template #icon><CodeIcon /></template>
          <t-menu-item value="dev-endpoints">接口管理</t-menu-item>
          <t-menu-item value="dev-tests">测试用例</t-menu-item>
          <t-menu-item value="dev-executions">执行记录</t-menu-item>
        </t-submenu>
        
        <!-- 线上监控 -->
        <t-submenu value="monitoring" title="线上监控">
          <template #icon><ChartLineIcon /></template>
          <t-menu-item value="monitor-requests">监控用例库</t-menu-item>
          <t-menu-item value="monitor-health">健康检查</t-menu-item>
          <t-menu-item value="monitor-history">检查历史</t-menu-item>
          <t-menu-item value="monitor-alerts">告警管理</t-menu-item>
        </t-submenu>
        
        <!-- 日志洞察 -->
        <t-submenu value="insights" title="日志洞察">
          <template #icon><FileSearchIcon /></template>
          <t-menu-item value="insight-upload">日志上传</t-menu-item>
          <t-menu-item value="insight-tasks">分析任务</t-menu-item>
          <t-menu-item value="insight-reports">分析报告</t-menu-item>
        </t-submenu>
        
        <!-- AI 助手 -->
        <t-menu-item value="ai">
          <template #icon><ChatIcon /></template>
          AI 助手
        </t-menu-item>
        
        <t-divider style="margin: 8px 16px; background: rgba(255,255,255,0.1);" />
        
        <!-- 系统设置 -->
        <t-menu-item value="import">
          <template #icon><SettingIcon /></template>
          文档导入
        </t-menu-item>
      </t-menu>
    </t-aside>
    <t-layout>
      <t-header class="header">
        <div class="header-left">
          <t-breadcrumb v-if="breadcrumbs.length > 1">
            <t-breadcrumb-item v-for="(item, index) in breadcrumbs" :key="index">
              <router-link v-if="item.path && index < breadcrumbs.length - 1" :to="item.path">
                {{ item.title }}
              </router-link>
              <span v-else>{{ item.title }}</span>
            </t-breadcrumb-item>
          </t-breadcrumb>
          <div v-else class="header-title">{{ currentTitle }}</div>
        </div>
        <div class="header-right">
          <t-button theme="primary" variant="text" @click="handleQuickAction('import')">
            <template #icon><FileImportIcon /></template>
            导入文档
          </t-button>
        </div>
      </t-header>
      <t-content class="content">
        <router-view v-slot="{ Component }">
          <keep-alive :include="cachedViews">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </t-content>
    </t-layout>
  </t-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  DashboardIcon, 
  ApiIcon, 
  CodeIcon,
  ChartLineIcon,
  FileSearchIcon,
  ChatIcon,
  SettingIcon,
  FileImportIcon
} from 'tdesign-icons-vue-next'

const route = useRoute()
const router = useRouter()

// 缓存的视图
const cachedViews = ['Dashboard']

// 展开的菜单
const expandedMenus = ref<string[]>(['development'])

// 当前激活的菜单
const activeMenu = computed(() => {
  const path = route.path
  const name = route.name as string
  
  // 开发自测模块
  if (path.startsWith('/development')) {
    if (path.includes('/endpoints')) return 'dev-endpoints'
    if (path.includes('/tests')) return 'dev-tests'
    if (path.includes('/executions')) return 'dev-executions'
  }
  
  // 线上监控模块
  if (path.startsWith('/monitoring')) {
    if (path.includes('/requests')) return 'monitor-requests'
    if (path.includes('/health-check')) return 'monitor-health'
    if (path.includes('/history')) return 'monitor-history'
    if (path.includes('/alerts')) return 'monitor-alerts'
  }
  
  // 日志洞察模块
  if (path.startsWith('/insights')) {
    if (path.includes('/upload')) return 'insight-upload'
    if (path.includes('/tasks')) return 'insight-tasks'
    if (path.includes('/reports')) return 'insight-reports'
  }
  
  // 其他页面
  if (path === '/ai') return 'ai'
  if (path === '/import') return 'import'
  if (path === '/dashboard') return 'dashboard'
  
  return 'dashboard'
})

// 面包屑
const breadcrumbs = computed(() => {
  const crumbs: { title: string; path?: string }[] = []
  const path = route.path
  
  if (path.startsWith('/development')) {
    crumbs.push({ title: '开发自测', path: '/development/endpoints' })
    if (path.includes('/endpoints')) {
      if (route.params.id) {
        crumbs.push({ title: '接口管理', path: '/development/endpoints' })
        crumbs.push({ title: '接口详情' })
      } else {
        crumbs.push({ title: '接口管理' })
      }
    } else if (path.includes('/tests')) {
      crumbs.push({ title: '测试用例' })
    } else if (path.includes('/executions')) {
      crumbs.push({ title: '执行记录' })
    }
  } else if (path.startsWith('/monitoring')) {
    crumbs.push({ title: '线上监控', path: '/monitoring/requests' })
    if (path.includes('/requests')) crumbs.push({ title: '监控用例库' })
    else if (path.includes('/health-check')) crumbs.push({ title: '健康检查' })
    else if (path.includes('/history')) crumbs.push({ title: '检查历史' })
    else if (path.includes('/alerts')) crumbs.push({ title: '告警管理' })
  } else if (path.startsWith('/insights')) {
    crumbs.push({ title: '日志洞察', path: '/insights/upload' })
    if (path.includes('/upload')) crumbs.push({ title: '日志上传' })
    else if (path.includes('/tasks')) {
      if (route.params.id) {
        crumbs.push({ title: '分析任务', path: '/insights/tasks' })
        crumbs.push({ title: '任务详情' })
      } else {
        crumbs.push({ title: '分析任务' })
      }
    } else if (path.includes('/reports')) {
      if (route.params.id) {
        crumbs.push({ title: '分析报告', path: '/insights/reports' })
        crumbs.push({ title: '报告详情' })
      } else {
        crumbs.push({ title: '分析报告' })
      }
    }
  } else {
    crumbs.push({ title: route.meta?.title as string || '首页' })
  }
  
  return crumbs
})

// 当前页面标题
const currentTitle = computed(() => {
  return (route.meta?.title as string) || 'AI Test Tool'
})

// 根据路由自动展开对应菜单
watch(() => route.path, (path) => {
  if (path.startsWith('/development') && !expandedMenus.value.includes('development')) {
    expandedMenus.value.push('development')
  }
  if (path.startsWith('/monitoring') && !expandedMenus.value.includes('monitoring')) {
    expandedMenus.value.push('monitoring')
  }
  if (path.startsWith('/insights') && !expandedMenus.value.includes('insights')) {
    expandedMenus.value.push('insights')
  }
}, { immediate: true })

// 菜单点击处理
const handleMenuChange = (value: string) => {
  const routeMap: Record<string, string> = {
    'dashboard': '/dashboard',
    'dev-endpoints': '/development/endpoints',
    'dev-tests': '/development/tests',
    'dev-executions': '/development/executions',
    'monitor-requests': '/monitoring/requests',
    'monitor-health': '/monitoring/health-check',
    'monitor-history': '/monitoring/history',
    'monitor-alerts': '/monitoring/alerts',
    'insight-upload': '/insights/upload',
    'insight-tasks': '/insights/tasks',
    'insight-reports': '/insights/reports',
    'ai': '/ai',
    'import': '/import'
  }
  
  const targetPath = routeMap[value]
  if (targetPath) {
    router.push(targetPath)
  }
}

// 菜单展开处理
const handleMenuExpand = (value: string[]) => {
  expandedMenus.value = value
}

// 快捷操作
const handleQuickAction = (action: string) => {
  if (action === 'import') {
    router.push('/import')
  }
}
</script>

<style scoped>
.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  min-height: 100vh;
}

.menu-transparent {
  background: transparent !important;
}

.logo {
  display: flex;
  align-items: center;
  padding: 20px 24px;
  color: #fff;
  height: 64px;
  box-sizing: border-box;
}

.logo-icon {
  font-size: 28px;
  color: #4080ff;
}

.logo-text {
  margin-left: 12px;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
  background: linear-gradient(90deg, #4080ff, #36d1dc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
  overflow-y: auto;
}

:deep(.t-menu__item) {
  border-radius: 8px;
  margin: 2px 8px;
}

:deep(.t-menu__item.t-is-active) {
  background: rgba(64, 128, 255, 0.15) !important;
}

:deep(.t-submenu__title) {
  border-radius: 8px;
  margin: 2px 8px;
}

:deep(.t-breadcrumb) {
  font-size: 14px;
}
</style>
