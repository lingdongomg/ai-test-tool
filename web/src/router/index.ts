import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    // ==================== 首页 ====================
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { title: '首页', icon: 'dashboard' }
    },
    
    // ==================== 开发自测模块 ====================
    {
      path: '/development',
      name: 'Development',
      redirect: '/development/endpoints',
      meta: { title: '开发自测' },
      children: [
        {
          path: 'endpoints',
          name: 'DevEndpoints',
          component: () => import('../views/development/Endpoints.vue'),
          meta: { title: '接口管理', parent: 'Development' }
        },
        {
          path: 'endpoints/:id',
          name: 'DevEndpointDetail',
          component: () => import('../views/development/EndpointDetail.vue'),
          meta: { title: '接口详情', parent: 'Development' }
        },
        {
          path: 'tests',
          name: 'DevTests',
          component: () => import('../views/development/Tests.vue'),
          meta: { title: '测试用例', parent: 'Development' }
        },
        {
          path: 'executions',
          name: 'DevExecutions',
          component: () => import('../views/development/Executions.vue'),
          meta: { title: '执行记录', parent: 'Development' }
        }
      ]
    },
    
    // ==================== 线上监控模块 ====================
    {
      path: '/monitoring',
      name: 'Monitoring',
      redirect: '/monitoring/requests',
      meta: { title: '线上监控' },
      children: [
        {
          path: 'requests',
          name: 'MonitorRequests',
          component: () => import('../views/monitoring/Requests.vue'),
          meta: { title: '监控用例库', parent: 'Monitoring' }
        },
        {
          path: 'health-check',
          name: 'HealthCheck',
          component: () => import('../views/monitoring/HealthCheck.vue'),
          meta: { title: '健康检查', parent: 'Monitoring' }
        },
        {
          path: 'history',
          name: 'MonitorHistory',
          component: () => import('../views/monitoring/History.vue'),
          meta: { title: '检查历史', parent: 'Monitoring' }
        },
        {
          path: 'alerts',
          name: 'MonitorAlerts',
          component: () => import('../views/monitoring/Alerts.vue'),
          meta: { title: '告警管理', parent: 'Monitoring' }
        }
      ]
    },
    
    // ==================== 日志洞察模块 ====================
    {
      path: '/insights',
      name: 'Insights',
      redirect: '/insights/upload',
      meta: { title: '日志洞察' },
      children: [
        {
          path: 'upload',
          name: 'LogUpload',
          component: () => import('../views/insights/Upload.vue'),
          meta: { title: '日志上传', parent: 'Insights' }
        },
        {
          path: 'tasks',
          name: 'InsightTasks',
          component: () => import('../views/insights/Tasks.vue'),
          meta: { title: '分析任务', parent: 'Insights' }
        },
        {
          path: 'tasks/:id',
          name: 'InsightTaskDetail',
          component: () => import('../views/insights/TaskDetail.vue'),
          meta: { title: '任务详情', parent: 'Insights' }
        },
        {
          path: 'reports',
          name: 'InsightReports',
          component: () => import('../views/insights/Reports.vue'),
          meta: { title: '分析报告', parent: 'Insights' }
        },
        {
          path: 'reports/:id',
          name: 'InsightReportDetail',
          component: () => import('../views/insights/ReportDetail.vue'),
          meta: { title: '报告详情', parent: 'Insights' }
        }
      ]
    },
    
    // ==================== AI 助手 ====================
    {
      path: '/ai',
      name: 'AI',
      component: () => import('../views/ai/Assistant.vue'),
      meta: { title: 'AI 助手' }
    },
    
    // ==================== 系统设置 ====================
    {
      path: '/import',
      name: 'Import',
      component: () => import('../views/settings/Import.vue'),
      meta: { title: '文档导入' }
    }
  ]
})

export default router
