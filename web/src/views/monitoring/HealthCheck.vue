<template>
  <div class="health-check-page">
    <t-card title="执行健康检查">
      <t-form :data="checkForm" label-width="120px">
        <t-form-item label="目标服务器" required>
          <t-input v-model="checkForm.base_url" placeholder="https://api.example.com" style="width: 400px;" />
        </t-form-item>
        <t-form-item label="检查范围">
          <t-radio-group v-model="checkForm.scope">
            <t-radio value="all">全部启用的监控</t-radio>
            <t-radio value="tag">按标签筛选</t-radio>
          </t-radio-group>
        </t-form-item>
        <t-form-item label="标签筛选" v-if="checkForm.scope === 'tag'">
          <t-input v-model="checkForm.tag_filter" placeholder="输入标签名" style="width: 200px;" />
        </t-form-item>
        <t-form-item label="AI 验证">
          <t-switch v-model="checkForm.use_ai_validation" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.4);">使用 AI 判断返回结果是否正常</span>
        </t-form-item>
        <t-form-item label="超时时间">
          <t-input-number v-model="checkForm.timeout_seconds" :min="5" :max="120" suffix="秒" />
        </t-form-item>
        <t-form-item label="并发数">
          <t-input-number v-model="checkForm.parallel" :min="1" :max="20" />
        </t-form-item>
        <t-form-item>
          <t-button theme="primary" :loading="checking" @click="handleCheck">
            <template #icon><PlayIcon /></template>
            开始检查
          </t-button>
        </t-form-item>
      </t-form>
    </t-card>

    <!-- 检查结果 -->
    <t-card title="检查结果" style="margin-top: 16px;" v-if="result">
      <div class="result-summary">
        <div class="result-stat">
          <div class="result-value">{{ result.total }}</div>
          <div class="result-label">总数</div>
        </div>
        <div class="result-stat success">
          <div class="result-value">{{ result.healthy }}</div>
          <div class="result-label">健康</div>
        </div>
        <div class="result-stat danger">
          <div class="result-value">{{ result.unhealthy }}</div>
          <div class="result-label">异常</div>
        </div>
        <div class="result-stat">
          <div class="result-value">{{ result.health_rate }}%</div>
          <div class="result-label">健康率</div>
        </div>
        <div class="result-stat">
          <div class="result-value">{{ result.duration_ms }}ms</div>
          <div class="result-label">耗时</div>
        </div>
      </div>

      <t-divider />

      <t-table
        :data="result.results || []"
        :columns="resultColumns"
        row-key="request_id"
        size="small"
      >
        <template #success="{ row }">
          <t-tag :theme="row.success ? 'success' : 'danger'" size="small">
            {{ row.success ? '健康' : '异常' }}
          </t-tag>
        </template>
        <template #response_time_ms="{ row }">
          {{ row.response_time_ms ? `${row.response_time_ms}ms` : '-' }}
        </template>
        <template #ai_analysis="{ row }">
          <t-tooltip v-if="row.ai_analysis" :content="row.ai_analysis.summary">
            <t-tag size="small" variant="light">
              {{ row.ai_analysis.is_normal ? '正常' : '异常' }}
            </t-tag>
          </t-tooltip>
          <span v-else>-</span>
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { PlayIcon } from 'tdesign-icons-vue-next'
import { monitoringApi } from '../../api/v2'

// 表单
const checkForm = reactive({
  base_url: '',
  scope: 'all',
  tag_filter: '',
  use_ai_validation: true,
  timeout_seconds: 30,
  parallel: 5
})

// 状态
const checking = ref(false)
const result = ref<any>(null)

// 结果列
const resultColumns = [
  { colKey: 'method', title: '方法', width: 80 },
  { colKey: 'url', title: 'URL', ellipsis: true },
  { colKey: 'success', title: '状态', width: 80 },
  { colKey: 'status_code', title: '状态码', width: 80 },
  { colKey: 'response_time_ms', title: '响应时间', width: 100 },
  { colKey: 'ai_analysis', title: 'AI分析', width: 100 },
  { colKey: 'error_message', title: '错误信息', ellipsis: true }
]

// 执行检查
const handleCheck = async () => {
  if (!checkForm.base_url) {
    MessagePlugin.warning('请输入目标服务器地址')
    return
  }
  
  checking.value = true
  result.value = null
  
  try {
    const res = await monitoringApi.runHealthCheck({
      base_url: checkForm.base_url,
      tag_filter: checkForm.scope === 'tag' ? checkForm.tag_filter : undefined,
      use_ai_validation: checkForm.use_ai_validation,
      timeout_seconds: checkForm.timeout_seconds,
      parallel: checkForm.parallel
    })
    
    result.value = res
    MessagePlugin.success(`检查完成，健康率: ${res.health_rate}%`)
  } catch (error) {
    console.error('健康检查失败:', error)
  } finally {
    checking.value = false
  }
}
</script>

<style scoped>
.health-check-page {
  max-width: 1000px;
}

.result-summary {
  display: flex;
  gap: 32px;
  justify-content: center;
  padding: 16px 0;
}

.result-stat {
  text-align: center;
}

.result-stat.success .result-value {
  color: #38ef7d;
}

.result-stat.danger .result-value {
  color: #f5576c;
}

.result-value {
  font-size: 32px;
  font-weight: 600;
}

.result-label {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.4);
  margin-top: 4px;
}
</style>
