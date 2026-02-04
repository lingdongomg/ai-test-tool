<template>
  <div class="ai-assistant-page">
    <t-row :gutter="[16, 16]">
      <!-- 左侧：对话区域 -->
      <t-col :xs="24" :lg="14">
        <t-card title="AI 助手" class="chat-card">
          <template #actions>
            <t-button variant="text" size="small" @click="handleClearChat">清空对话</t-button>
          </template>
          
          <div class="chat-messages" ref="messagesRef">
            <div 
              v-for="(msg, index) in messages" 
              :key="index" 
              class="message"
              :class="msg.role"
            >
              <div class="message-avatar">
                <UserIcon v-if="msg.role === 'user'" />
                <ChatIcon v-else />
              </div>
              <div class="message-content">
                <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
                <div class="message-time">{{ msg.time }}</div>
              </div>
            </div>
            <div v-if="thinking" class="message assistant">
              <div class="message-avatar"><ChatIcon /></div>
              <div class="message-content">
                <div class="thinking-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="chat-input">
            <t-textarea
              v-model="inputText"
              placeholder="输入问题，例如：如何提高测试覆盖率？"
              :rows="2"
              @keydown.enter.ctrl="handleSend"
            />
            <t-button theme="primary" :loading="thinking" @click="handleSend">
              发送
            </t-button>
          </div>
        </t-card>
      </t-col>

      <!-- 右侧：功能面板 -->
      <t-col :xs="24" :lg="10">
        <!-- 快捷功能 -->
        <t-card title="快捷功能">
          <div class="quick-functions">
            <div class="function-item" @click="handleFunction('coverage')">
              <ChartPieIcon class="function-icon" />
              <div class="function-info">
                <div class="function-title">覆盖率分析</div>
                <div class="function-desc">分析测试覆盖率缺口</div>
              </div>
            </div>
            <div class="function-item" @click="handleFunction('risk')">
              <ErrorCircleIcon class="function-icon" />
              <div class="function-info">
                <div class="function-title">风险分析</div>
                <div class="function-desc">识别高风险接口</div>
              </div>
            </div>
            <div class="function-item" @click="handleFunction('performance')">
              <ChartLineIcon class="function-icon" />
              <div class="function-info">
                <div class="function-title">性能分析</div>
                <div class="function-desc">分析性能趋势</div>
              </div>
            </div>
          </div>
        </t-card>

        <!-- AI 洞察 -->
        <t-card title="AI 洞察" style="margin-top: 16px;">
          <template #actions>
            <t-button variant="text" size="small" @click="loadInsights">刷新</t-button>
          </template>
          <div class="insights-list" v-if="insights.length">
            <div 
              v-for="insight in insights" 
              :key="insight.id" 
              class="insight-item"
              @click="handleInsightClick(insight)"
            >
              <t-tag 
                :theme="getSeverityTheme(insight.severity)" 
                size="small"
              >
                {{ getSeverityLabel(insight.severity) }}
              </t-tag>
              <span class="insight-title">{{ insight.title }}</span>
              <t-button 
                v-if="!insight.is_resolved"
                variant="text" 
                size="small"
                @click.stop="handleResolve(insight)"
              >
                处理
              </t-button>
            </div>
          </div>
          <t-empty v-else description="暂无洞察" />
        </t-card>

        <!-- 智能建议 -->
        <t-card title="智能建议" style="margin-top: 16px;">
          <div class="recommendations-list" v-if="recommendations.length">
            <div 
              v-for="rec in recommendations" 
              :key="rec.id" 
              class="recommendation-item"
            >
              <div class="rec-title">{{ rec.title }}</div>
              <div class="rec-desc">{{ rec.description }}</div>
            </div>
          </div>
          <t-empty v-else description="暂无建议" />
        </t-card>
      </t-col>
    </t-row>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { MessagePlugin } from 'tdesign-vue-next'
import { 
  UserIcon, 
  ChatIcon, 
  ChartPieIcon, 
  ErrorCircleIcon, 
  ChartLineIcon 
} from 'tdesign-icons-vue-next'
import { aiApi } from '../../api/v2'
import { marked } from 'marked'

// 对话
const messages = ref<any[]>([
  {
    role: 'assistant',
    content: '你好！我是 AI 助手，可以帮助你：\n\n- 分析测试覆盖率\n- 识别高风险接口\n- 生成测试用例\n- 解答测试相关问题\n\n有什么可以帮助你的？',
    time: formatTime(new Date())
  }
])
const inputText = ref('')
const thinking = ref(false)
const messagesRef = ref<HTMLElement | null>(null)

// 洞察和建议
const insights = ref<any[]>([])
const recommendations = ref<any[]>([])

// 加载数据
const loadInsights = async () => {
  try {
    const res = await aiApi.listInsights({ is_resolved: false, page_size: 5 })
    insights.value = res.items || []
  } catch (error) {
    console.error('加载洞察失败:', error)
  }
}

const loadRecommendations = async () => {
  try {
    const res = await aiApi.getRecommendations({ limit: 5 })
    recommendations.value = res.recommendations || []
  } catch (error) {
    console.error('加载建议失败:', error)
  }
}

onMounted(() => {
  loadInsights()
  loadRecommendations()
})

// 发送消息
const handleSend = async () => {
  if (!inputText.value.trim() || thinking.value) return
  
  const userMessage = inputText.value.trim()
  messages.value.push({
    role: 'user',
    content: userMessage,
    time: formatTime(new Date())
  })
  inputText.value = ''
  
  scrollToBottom()
  thinking.value = true
  
  try {
    const res = await aiApi.chat({ message: userMessage })
    messages.value.push({
      role: 'assistant',
      content: res.answer,
      time: formatTime(new Date())
    })
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，我遇到了一些问题，请稍后再试。',
      time: formatTime(new Date())
    })
  } finally {
    thinking.value = false
    scrollToBottom()
  }
}

// 清空对话
const handleClearChat = () => {
  messages.value = [messages.value[0]]
}

// 快捷功能
const handleFunction = async (type: string) => {
  thinking.value = true
  messages.value.push({
    role: 'user',
    content: type === 'coverage' ? '分析测试覆盖率' : 
             type === 'risk' ? '识别高风险接口' : '分析性能趋势',
    time: formatTime(new Date())
  })
  scrollToBottom()
  
  try {
    let res: any
    if (type === 'coverage') {
      res = await aiApi.analyzeCoverage()
    } else if (type === 'risk') {
      res = await aiApi.analyzeRisk()
    } else {
      res = await aiApi.analyzePerformance({ type: 'performance', days: 7 })
    }
    
    const insightsList = res.insights || []
    let content = insightsList.length 
      ? insightsList.map((i: any) => `### ${i.title}\n${i.description}\n\n**建议：**\n${(i.recommendations || []).map((r: string) => `- ${r}`).join('\n')}`).join('\n\n---\n\n')
      : '暂无发现需要关注的问题。'
    
    messages.value.push({
      role: 'assistant',
      content,
      time: formatTime(new Date())
    })
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: '分析失败，请稍后再试。',
      time: formatTime(new Date())
    })
  } finally {
    thinking.value = false
    scrollToBottom()
  }
}

// 处理洞察
const handleInsightClick = (insight: any) => {
  inputText.value = `请详细解释这个问题：${insight.title}`
}

const handleResolve = async (insight: any) => {
  try {
    await aiApi.resolveInsight(insight.id)
    insight.is_resolved = true
    MessagePlugin.success('已标记为处理')
  } catch (error) {
    console.error('处理失败:', error)
  }
}

// 辅助函数
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const renderMarkdown = (content: string) => {
  return marked(content)
}

function formatTime(date: Date) {
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

const getSeverityTheme = (severity: string) => {
  const map: Record<string, string> = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'default'
  }
  return map[severity] || 'default'
}

const getSeverityLabel = (severity: string) => {
  const map: Record<string, string> = {
    'high': '高',
    'medium': '中',
    'low': '低'
  }
  return map[severity] || severity
}
</script>

<style scoped>
.ai-assistant-page {
  height: calc(100vh - 120px);
}

.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  min-height: 400px;
  max-height: 500px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #0052d9;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #667eea;
}

.message-content {
  max-width: 70%;
}

.message-text {
  background: #fff;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.message.user .message-text {
  background: #0052d9;
  color: #fff;
}

.message-text :deep(p) {
  margin: 0 0 8px;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(pre) {
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
}

.message.user .message-text :deep(pre) {
  background: rgba(255, 255, 255, 0.1);
}

.message-time {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.3);
  margin-top: 4px;
}

.message.user .message-time {
  text-align: right;
}

.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.thinking-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #0052d9;
  animation: thinking 1.4s infinite ease-in-out both;
}

.thinking-dots span:nth-child(1) { animation-delay: -0.32s; }
.thinking-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes thinking {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.chat-input {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  align-items: flex-end;
}

.chat-input .t-textarea {
  flex: 1;
}

.quick-functions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.function-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #f5f7fa;
}

.function-item:hover {
  background: #e8f4ff;
}

.function-icon {
  font-size: 24px;
  color: #0052d9;
}

.function-title {
  font-weight: 500;
}

.function-desc {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
}

.insights-list,
.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.insight-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
}

.insight-item:hover {
  background: #f5f7fa;
}

.insight-title {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommendation-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.rec-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.rec-desc {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.6);
}
</style>
