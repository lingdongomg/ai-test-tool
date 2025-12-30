<template>
  <div class="analysis-page">
    <t-row :gutter="16">
      <t-col :span="8">
        <t-card title="知识库统计" :bordered="false">
          <t-descriptions :column="1" v-if="kbStats">
            <t-descriptions-item label="接口总数">{{ kbStats.total_endpoints }}</t-descriptions-item>
            <t-descriptions-item label="标签数量">{{ kbStats.tags?.length || 0 }}</t-descriptions-item>
            <t-descriptions-item label="状态">
              <t-tag :theme="kbStats.is_empty ? 'warning' : 'success'">
                {{ kbStats.is_empty ? '空' : '正常' }}
              </t-tag>
            </t-descriptions-item>
          </t-descriptions>
          <t-button block class="mt-4" @click="loadKbStats">刷新统计</t-button>
        </t-card>
      </t-col>
      <t-col :span="16">
        <t-card title="标签分布" :bordered="false">
          <v-chart class="chart" :option="tagChartOption" autoresize />
        </t-card>
      </t-col>
    </t-row>

    <t-card title="覆盖率分析" :bordered="false" class="mt-4">
      <t-form layout="inline">
        <t-form-item label="URL列表">
          <t-textarea
            v-model="analysisForm.urls"
            placeholder="输入URL列表，每行一个"
            :autosize="{ minRows: 3, maxRows: 6 }"
            style="width: 400px"
          />
        </t-form-item>
        <t-form-item>
          <t-space>
            <t-button theme="primary" @click="handleAnalyzeCoverage" :loading="analyzing">
              分析覆盖率
            </t-button>
            <t-button @click="handleDocComparison" :loading="comparing">
              文档对比分析
            </t-button>
          </t-space>
        </t-form-item>
      </t-form>

      <t-divider v-if="coverageResult" />
      
      <div v-if="coverageResult" class="coverage-result">
        <t-row :gutter="16">
          <t-col :span="6">
            <t-statistic title="日志URL数" :value="coverageResult.total_log_urls" />
          </t-col>
          <t-col :span="6">
            <t-statistic title="匹配数" :value="coverageResult.matched_count" />
          </t-col>
          <t-col :span="6">
            <t-statistic title="匹配率" :value="coverageResult.match_rate" />
          </t-col>
          <t-col :span="6">
            <t-statistic title="文档覆盖率" :value="coverageResult.doc_coverage" />
          </t-col>
        </t-row>

        <t-divider>未匹配URL（可能是第三方接口）</t-divider>
        <t-table
          :data="coverageResult.unmatched_urls?.map((url: string) => ({ url }))"
          :columns="[{ colKey: 'url', title: 'URL' }]"
          size="small"
          :pagination="false"
          max-height="200"
        />

        <t-divider>未调用的文档接口</t-divider>
        <t-table
          :data="coverageResult.uncalled_endpoints_list"
          :columns="uncalledColumns"
          size="small"
          :pagination="false"
          max-height="200"
        >
          <template #method="{ row }">
            <t-tag :theme="getMethodTheme(row.method)" size="small">{{ row.method }}</t-tag>
          </template>
        </t-table>
      </div>
    </t-card>

    <t-card title="AI分析结果" :bordered="false" class="mt-4" v-if="aiAnalysis">
      <t-alert theme="info" title="AI分析完成" :message="`发现 ${aiAnalysis.summary?.total_issues || 0} 个问题`" />
      
      <t-divider>文档完整性</t-divider>
      <t-descriptions :column="2">
        <t-descriptions-item label="文档遗漏接口">
          {{ aiAnalysis.doc_completeness?.missing_in_doc?.length || 0 }} 个
        </t-descriptions-item>
        <t-descriptions-item label="未使用接口">
          {{ aiAnalysis.doc_completeness?.unused_in_doc?.length || 0 }} 个
        </t-descriptions-item>
      </t-descriptions>

      <t-divider>改进建议</t-divider>
      <t-list :split="true">
        <t-list-item v-for="(rec, index) in aiAnalysis.recommendations" :key="index">
          {{ rec }}
        </t-list-item>
      </t-list>
    </t-card>

    <t-card title="批量分类" :bordered="false" class="mt-4">
      <t-form layout="inline">
        <t-form-item label="URL列表">
          <t-textarea
            v-model="categorizeForm.urls"
            placeholder="输入URL列表，每行一个"
            :autosize="{ minRows: 3, maxRows: 6 }"
            style="width: 400px"
          />
        </t-form-item>
        <t-form-item>
          <t-button theme="primary" @click="handleBatchCategorize" :loading="categorizing">
            批量分类
          </t-button>
        </t-form-item>
      </t-form>

      <t-table
        v-if="categorizeResult?.categorized"
        :data="categorizeResult.categorized"
        :columns="categorizeColumns"
        size="small"
        class="mt-4"
      >
        <template #source="{ row }">
          <t-tag :theme="row.source === 'doc' ? 'success' : 'warning'" size="small">
            {{ row.source === 'doc' ? '文档' : '推断' }}
          </t-tag>
        </template>
      </t-table>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { analysisApi } from '../api'

const kbStats = ref<any>(null)
const analyzing = ref(false)
const comparing = ref(false)
const categorizing = ref(false)
const coverageResult = ref<any>(null)
const aiAnalysis = ref<any>(null)
const categorizeResult = ref<any>(null)

const analysisForm = ref({
  urls: ''
})

const categorizeForm = ref({
  urls: ''
})

const uncalledColumns = [
  { colKey: 'method', title: '方法', cell: 'method', width: 80 },
  { colKey: 'path', title: '路径' },
  { colKey: 'name', title: '名称', width: 200 }
]

const categorizeColumns = [
  { colKey: 'url', title: 'URL', ellipsis: true },
  { colKey: 'suggested_category', title: '分类', width: 150 },
  { colKey: 'source', title: '来源', cell: 'source', width: 80 }
]

const getMethodTheme = (method: string) => {
  const map: Record<string, string> = {
    GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger'
  }
  return map[method] || 'default'
}

const tagChartOption = computed(() => {
  const stats = kbStats.value?.tag_statistics || {}
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: Object.entries(stats).map(([name, value]) => ({ name, value }))
    }]
  }
})

const loadKbStats = async () => {
  kbStats.value = await analysisApi.knowledgeBaseStats()
}

const parseUrls = (text: string) => {
  return text.split('\n').map(s => s.trim()).filter(s => s)
}

const handleAnalyzeCoverage = async () => {
  const urls = parseUrls(analysisForm.value.urls)
  if (urls.length === 0) return

  analyzing.value = true
  coverageResult.value = await analysisApi.coverage({ urls })
  analyzing.value = false
}

const handleDocComparison = async () => {
  const urls = parseUrls(analysisForm.value.urls)
  if (urls.length === 0) return

  comparing.value = true
  const result = await analysisApi.docComparison({ urls, include_ai_analysis: true }) as any
  coverageResult.value = result.coverage
  aiAnalysis.value = result.ai_analysis
  comparing.value = false
}

const handleBatchCategorize = async () => {
  const urls = parseUrls(categorizeForm.value.urls)
  if (urls.length === 0) return

  categorizing.value = true
  categorizeResult.value = await analysisApi.batchCategorize({ urls })
  categorizing.value = false
}

onMounted(loadKbStats)
</script>

<style scoped>
.chart {
  height: 250px;
}

.mt-4 {
  margin-top: 16px;
}

.coverage-result {
  margin-top: 16px;
}
</style>
