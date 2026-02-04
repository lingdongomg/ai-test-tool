/**
 * API 模块入口
 * 统一导出 v2 API
 */

import api, {
  dashboardApi,
  developmentApi,
  monitoringApi,
  insightsApi,
  aiApi,
  importApi
} from './v2'

// 重新导出所有 API
export {
  dashboardApi,
  developmentApi,
  monitoringApi,
  insightsApi,
  aiApi,
  importApi
}

export default api
