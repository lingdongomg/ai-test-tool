import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { title: '概览' }
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('../views/Tasks.vue'),
      meta: { title: '分析任务' }
    },
    {
      path: '/tasks/:id',
      name: 'TaskDetail',
      component: () => import('../views/TaskDetail.vue'),
      meta: { title: '任务详情' }
    },
    {
      path: '/endpoints',
      name: 'Endpoints',
      component: () => import('../views/Endpoints.vue'),
      meta: { title: '接口管理' }
    },
    {
      path: '/tags',
      name: 'Tags',
      component: () => import('../views/Tags.vue'),
      meta: { title: '标签管理' }
    },
    {
      path: '/import',
      name: 'Import',
      component: () => import('../views/Import.vue'),
      meta: { title: '文档导入' }
    },
    {
      path: '/scenarios',
      name: 'Scenarios',
      component: () => import('../views/Scenarios.vue'),
      meta: { title: '测试场景' }
    },
    {
      path: '/scenarios/:id',
      name: 'ScenarioDetail',
      component: () => import('../views/ScenarioDetail.vue'),
      meta: { title: '场景详情' }
    },
    {
      path: '/executions',
      name: 'Executions',
      component: () => import('../views/Executions.vue'),
      meta: { title: '执行记录' }
    },
    {
      path: '/analysis',
      name: 'Analysis',
      component: () => import('../views/Analysis.vue'),
      meta: { title: '智能分析' }
    },
    {
      path: '/test-cases',
      name: 'TestCases',
      component: () => import('../views/TestCases.vue'),
      meta: { title: '测试用例' }
    }
  ]
})

export default router
