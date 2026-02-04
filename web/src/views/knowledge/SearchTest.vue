<!-- 该文件内容使用AI生成，注意识别准确性 -->
<template>
  <div class="knowledge-search">
    <div class="page-header">
      <h2>知识检索测试</h2>
    </div>

    <el-card class="search-card">
      <el-form :model="searchForm" label-width="100px">
        <el-form-item label="查询文本">
          <el-input
            v-model="searchForm.query"
            type="textarea"
            :rows="3"
            placeholder="输入要查询的内容，例如：直播电商模块需要传入什么参数？"
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="知识类型">
              <el-select v-model="searchForm.types" multiple placeholder="不限" style="width: 100%">
                <el-option label="项目配置" value="project_config" />
                <el-option label="业务规则" value="business_rule" />
                <el-option label="模块知识" value="module_context" />
                <el-option label="测试经验" value="test_experience" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="标签过滤">
              <el-select
                v-model="searchForm.tags"
                multiple
                filterable
                allow-create
                placeholder="可选"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="范围">
              <el-input v-model="searchForm.scope" placeholder="如 /api/live/*" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="返回数量">
              <el-input-number v-model="searchForm.top_k" :min="1" :max="20" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最低相似度">
              <el-slider v-model="searchForm.min_score" :min="0" :max="1" :step="0.1" show-input />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="doSearch" :loading="searching">
            <el-icon><Search /></el-icon>
            检索
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 检索结果 -->
    <el-card v-if="searchResult" class="result-card">
      <template #header>
        <div class="result-header">
          <span>检索结果</span>
          <el-tag type="info">{{ searchResult.total }} 条匹配</el-tag>
          <el-tag>Token估算: {{ searchResult.token_count }}</el-tag>
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
            <el-tag :type="getTypeTagType(item.type)" size="small">{{ getTypeName(item.type) }}</el-tag>
            <el-tag type="success" size="small">相似度: {{ (item.score * 100).toFixed(1) }}%</el-tag>
            <el-tag v-if="item.source" type="info" size="small">{{ item.source }}</el-tag>
          </div>
          <div class="item-content">{{ item.content }}</div>
          <div class="item-meta">
            <span v-if="item.scope"><code>{{ item.scope }}</code></span>
            <span v-if="item.tags?.length">
              <el-tag v-for="tag in item.tags" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
            </span>
          </div>
        </div>
      </div>

      <!-- RAG上下文预览 -->
      <div class="rag-preview" v-if="searchResult.rag_context_preview">
        <h4>RAG上下文预览</h4>
        <pre>{{ searchResult.rag_context_preview }}</pre>
      </div>
    </el-card>

    <el-empty v-if="searched && !searchResult?.items?.length" description="未找到相关知识" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const API_BASE = '/api/v2/knowledge'

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
    ElMessage.warning('请输入查询文本')
    return
  }

  searching.value = true
  searched.value = true
  
  try {
    const response = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(searchForm)
    })

    if (!response.ok) throw new Error('检索失败')

    searchResult.value = await response.json()
  } catch (error) {
    ElMessage.error('检索失败')
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
