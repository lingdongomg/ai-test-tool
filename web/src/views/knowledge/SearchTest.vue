<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="knowledge-search">
    <div class="page-header">
      <h2>知识检索测试</h2>
    </div>

    <t-card class="search-card">
      <t-form :data="searchForm" label-align="left" label-width="100px">
        <t-form-item label="查询文本">
          <t-textarea
            v-model="searchForm.query"
            :rows="3"
            placeholder="输入要查询的内容，例如：直播电商模块需要传入什么参数？"
          />
        </t-form-item>
        <t-row :gutter="20">
          <t-col :span="8">
            <t-form-item label="知识类型">
              <t-select v-model="searchForm.types" multiple placeholder="不限" style="width: 100%">
                <t-option label="项目配置" value="project_config" />
                <t-option label="业务规则" value="business_rule" />
                <t-option label="模块知识" value="module_context" />
                <t-option label="测试经验" value="test_experience" />
              </t-select>
            </t-form-item>
          </t-col>
          <t-col :span="8">
            <t-form-item label="标签过滤">
              <t-select
                v-model="searchForm.tags"
                multiple
                filterable
                creatable
                placeholder="可选"
                style="width: 100%"
              />
            </t-form-item>
          </t-col>
          <t-col :span="8">
            <t-form-item label="范围">
              <t-input v-model="searchForm.scope" placeholder="如 /api/live/*" />
            </t-form-item>
          </t-col>
        </t-row>
        <t-row :gutter="20">
          <t-col :span="8">
            <t-form-item label="返回数量">
              <t-input-number v-model="searchForm.top_k" :min="1" :max="20" />
            </t-form-item>
          </t-col>
          <t-col :span="8">
            <t-form-item label="最低相似度">
              <t-slider v-model="searchForm.min_score" :min="0" :max="1" :step="0.1" show-input />
            </t-form-item>
          </t-col>
        </t-row>
        <t-form-item>
          <t-button theme="primary" @click="doSearch" :loading="searching">
            <template #icon><search-icon /></template>
            检索
          </t-button>
        </t-form-item>
      </t-form>
    </t-card>

    <!-- 检索结果 -->
    <t-card v-if="searchResult" class="result-card">
      <template #header>
        <div class="result-header">
          <span>检索结果</span>
          <t-tag theme="default">{{ searchResult.total }} 条匹配</t-tag>
          <t-tag>Token估算: {{ searchResult.token_count }}</t-tag>
        </div>
      </template>

      <div class="result-list">
        <div
          v-for="(item, index) in searchResult.items"
          :key="item.knowledge_id"
          class="result-item"
        >
          <div class="item-header">
            <span class="item-rank">#{{ index + 1 }}</span>
            <span class="item-title">{{ item.title }}</span>
            <t-tag :theme="getTypeTagType(item.type)" size="small">{{ getTypeName(item.type) }}</t-tag>
            <t-tag theme="success" size="small">相似度: {{ (item.score * 100).toFixed(1) }}%</t-tag>
            <t-tag v-if="item.source" theme="default" size="small">{{ item.source }}</t-tag>
          </div>
          <div class="item-content">{{ item.content }}</div>
          <div class="item-meta">
            <span v-if="item.scope"><code>{{ item.scope }}</code></span>
            <span v-if="item.tags?.length">
              <t-tag v-for="tag in item.tags" :key="tag" size="small" class="tag-item">{{ tag }}</t-tag>
            </span>
          </div>
        </div>
      </div>

      <!-- RAG上下文预览 -->
      <div class="rag-preview" v-if="searchResult.rag_context_preview">
        <h4>RAG上下文预览</h4>
        <pre>{{ searchResult.rag_context_preview }}</pre>
      </div>
    </t-card>

    <t-empty v-if="searched && !searchResult?.items?.length" description="未找到相关知识" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { SearchIcon } from 'tdesign-icons-vue-next'
import { knowledgeApi } from '../../api/v2'

// 状态
const searching = ref(false)
const searched = ref(false)
const searchResult = ref<any>(null)

// 搜索表单
const searchForm = reactive({
  query: '',
  types: [] as string[],
  tags: [] as string[],
  scope: '',
  top_k: 5,
  min_score: 0.3
})

// 类型映射
const typeNames: Record<string, string> = {
  project_config: '项目配置',
  business_rule: '业务规则',
  module_context: '模块知识',
  test_experience: '测试经验'
}

const typeTagTypes: Record<string, string> = {
  project_config: 'primary',
  business_rule: 'success',
  module_context: 'warning',
  test_experience: 'info'
}

const getTypeName = (type: string) => typeNames[type] || type
const getTypeTagType = (type: string) => typeTagTypes[type] || ''

// 执行检索
const doSearch = async () => {
  if (!searchForm.query.trim()) {
    MessagePlugin.warning('请输入查询文本')
    return
  }

  searching.value = true
  searched.value = true

  try {
    searchResult.value = await knowledgeApi.search(searchForm)
  } catch (error) {
    searchResult.value = null
  } finally {
    searching.value = false
  }
}
</script>

<style scoped>
.knowledge-search {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}

.search-card {
  margin-bottom: 20px;
}

.result-card {
  margin-bottom: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-list {
  margin-bottom: 20px;
}

.result-item {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 12px;
}

.result-item:hover {
  border-color: #409eff;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.item-rank {
  font-weight: bold;
  color: #409eff;
}

.item-title {
  font-weight: 500;
  font-size: 15px;
}

.item-content {
  color: #606266;
  line-height: 1.6;
  margin-bottom: 8px;
  white-space: pre-wrap;
}

.item-meta {
  display: flex;
  gap: 12px;
  color: #909399;
  font-size: 13px;
}

.tag-item {
  margin-right: 4px;
}

.rag-preview {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.rag-preview h4 {
  margin: 0 0 12px;
}

.rag-preview pre {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}
</style>
