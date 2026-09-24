<template>
  <div class="agent-page">
    <section class="agent-header">
      <div class="agent-identity">
        <div class="agent-logo">
          <el-icon><MagicStick /></el-icon>
        </div>
        <div>
          <div class="title-row">
            <h1>实验室运营智能助手</h1>
            <el-tag type="success" effect="light" round>查询与安全预填</el-tag>
          </div>
          <p>查询采购申请进度、仪器信息、可预约时段和我的预约记录</p>
        </div>
      </div>
      <el-button :icon="Delete" plain :disabled="loading" @click="clearConversation">
        清空对话
      </el-button>
    </section>

    <section v-if="showQuickQuestions" class="quick-section">
      <div class="section-heading">
        <span>你可以这样问</span>
        <small>回答来自当前账号有权访问的实时业务数据</small>
      </div>
      <div class="quick-grid">
        <button
          v-for="item in quickQuestions"
          :key="item.question"
          class="quick-card"
          type="button"
          :disabled="loading"
          @click="submitQuestion(item.question)"
        >
          <span class="quick-icon" :class="item.domain">
            <el-icon><component :is="item.icon" /></el-icon>
          </span>
          <span>
            <strong>{{ item.title }}</strong>
            <small>{{ item.question }}</small>
          </span>
        </button>
      </div>
    </section>

    <section ref="chatPanel" class="chat-panel" aria-live="polite">
      <article
        v-for="message in messages"
        :key="message.id"
        class="message-row"
        :class="message.role"
      >
        <div class="avatar">
          <el-icon v-if="message.role === 'assistant'"><MagicStick /></el-icon>
          <el-icon v-else><User /></el-icon>
        </div>
        <div class="message-body">
          <div class="message-bubble">{{ message.content }}</div>
          <template v-for="action in message.actions || []" :key="action.id">
            <LabOpsActionCard
              v-if="action.type === 'procurement_form_prefill'"
              :action="action"
              @open="openProcurementRequest(action)"
            />
            <LabOpsEquipmentActionCard
              v-else-if="action.type === 'equipment_reservation_prefill'"
              :action="action"
              @open="openEquipmentReservation(action)"
            />
          </template>
          <div v-if="message.role === 'assistant' && message.tools?.length" class="tool-trace">
            <span class="trace-title">已查询</span>
            <el-tag
              v-for="tool in message.tools"
              :key="`${message.id}-${tool.name}`"
              :type="tool.status === 'success' ? 'success' : 'danger'"
              size="small"
              effect="plain"
            >
              {{ toolLabels[tool.name] || tool.name }}
            </el-tag>
          </div>
          <LabOpsEvidenceList
            v-if="message.role === 'assistant'"
            :evidence="message.evidence || []"
            :retrieval="message.retrieval || {}"
          />
          <div class="message-meta">
            <span>{{ message.time }}</span>
            <span v-if="message.domain">{{ domainLabels[message.domain] || message.domain }}</span>
            <span v-if="message.requestId">请求编号 {{ message.requestId }}</span>
          </div>
        </div>
      </article>

      <article v-if="loading" class="message-row assistant">
        <div class="avatar"><el-icon><MagicStick /></el-icon></div>
        <div class="message-body">
          <div class="message-bubble loading-bubble">
            <span>正在查询业务数据</span>
            <i></i><i></i><i></i>
          </div>
        </div>
      </article>
    </section>

    <section class="composer">
      <el-input
        v-model="question"
        type="textarea"
        :rows="3"
        resize="none"
        maxlength="1000"
        show-word-limit
        :disabled="loading"
        placeholder="例如：我最近的采购申请到哪一步了？"
        @keydown.enter.exact.prevent="submitQuestion()"
      />
      <div class="composer-footer">
        <span>Enter 发送，Shift + Enter 换行。助手可预填，最终提交仍由你确认。</span>
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="loading"
          :disabled="!question.trim()"
          @click="submitQuestion()"
        >
          发送
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { Calendar, Delete, MagicStick, Promotion, ShoppingCart, User } from '@element-plus/icons-vue'
import LabOpsActionCard from '@/components/LabOpsActionCard.vue'
import LabOpsEquipmentActionCard from '@/components/LabOpsEquipmentActionCard.vue'
import LabOpsEvidenceList from '@/components/LabOpsEvidenceList.vue'
import { queryLabOpsAgent } from '@/api/labopsAgent'
import {
  buildLabOpsHistoryContent,
  useLabOpsActionNavigation,
} from '@/composables/useLabOpsActionNavigation'

const chatPanel = ref(null)
const question = ref('')
const loading = ref(false)
const conversationId = ref(null)
let messageSequence = 0
const { openEquipmentReservation, openProcurementRequest } = useLabOpsActionNavigation()

const toolLabels = {
  list_procurement_requests: '采购申请列表',
  get_procurement_request: '采购申请详情',
  prepare_procurement_request: '采购信息校验',
  search_equipment: '仪器搜索',
  prepare_equipment_reservation: '预约信息校验',
  get_my_reservations: '我的仪器预约',
  get_available_slots: '仪器可预约时段',
  check_reservation_conflict: '预约冲突检查',
}

const domainLabels = {
  procurement: '采购查询',
  equipment: '仪器预约查询',
  mixed: '综合查询',
  general: '使用说明',
}

const quickQuestions = [
  {
    title: '采购申请进度',
    question: '我最近有哪些采购申请，分别进行到哪一步了？',
    domain: 'procurement',
    icon: ShoppingCart,
  },
  {
    title: '被驳回的申请',
    question: '我最近被驳回的采购申请有哪些，下一步应该怎么处理？',
    domain: 'procurement',
    icon: ShoppingCart,
  },
  {
    title: '我的仪器预约',
    question: '我接下来有哪些仪器预约？',
    domain: 'equipment',
    icon: Calendar,
  },
  {
    title: '查找可用仪器',
    question: '帮我搜索名称或介绍中包含XRD的可预约仪器。',
    domain: 'equipment',
    icon: Calendar,
  },
]

const welcomeMessage = () => ({
  id: `message-${++messageSequence}`,
  role: 'assistant',
  content: '你好，我可以查询采购和仪器预约，也能安全预填申请页面。所有最终提交都需要你亲自确认。',
  time: formatTime(),
})

const messages = ref([welcomeMessage()])
const showQuickQuestions = computed(() => messages.value.length === 1)

function formatTime() {
  return new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function addMessage(payload) {
  messages.value.push({
    id: `message-${++messageSequence}`,
    time: formatTime(),
    ...payload,
  })
}

async function scrollToBottom() {
  await nextTick()
  if (chatPanel.value) {
    chatPanel.value.scrollTop = chatPanel.value.scrollHeight
  }
}

function buildErrorMessage(error) {
  const status = error.response?.status
  const code = error.response?.data?.code
  const detail = error.response?.data?.detail
  if (status === 503 && code === 'agent_disabled') {
    return '智能助手尚未启用，请联系管理员检查后端配置。'
  }
  if (status === 503) return '模型服务暂时不可用，请稍后重试。'
  if (status === 502) return '模型返回了异常结果，本次没有执行任何写操作，请重新提问。'
  if (status === 401) return '登录状态已失效，请重新登录后再试。'
  if (status === 400) return detail || '问题格式不正确，请修改后重试。'
  return detail || '查询失败，请检查网络后重试。'
}

async function submitQuestion(presetQuestion) {
  if (loading.value) return
  const content = String(presetQuestion ?? question.value).trim()
  if (!content) return

  const history = messages.value
    .filter(message => ['user', 'assistant'].includes(message.role))
    .slice(-8)
    .map(message => ({ role: message.role, content: buildLabOpsHistoryContent(message) }))
  question.value = ''
  addMessage({ role: 'user', content })
  loading.value = true
  await scrollToBottom()

  try {
    const response = await queryLabOpsAgent(content, history, conversationId.value)
    conversationId.value = response.data.conversation_id || conversationId.value
    addMessage({
      role: 'assistant',
      content: response.data.answer,
      domain: response.data.domain,
      tools: response.data.tools || [],
      requestId: response.data.request_id,
      actions: response.data.actions || [],
      evidence: response.data.evidence || [],
      retrieval: response.data.retrieval || {},
    })
  } catch (error) {
    addMessage({
      role: 'assistant',
      content: buildErrorMessage(error),
      domain: 'general',
      tools: [],
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function clearConversation() {
  if (loading.value) return
  question.value = ''
  conversationId.value = null
  messages.value = [welcomeMessage()]
}
</script>

<style scoped>
.agent-page {
  width: min(1080px, 100%);
  min-height: calc(100vh - 108px);
  margin: 0 auto;
  display: grid;
  grid-template-rows: auto auto minmax(320px, 1fr) auto;
  gap: 16px;
}

.agent-header,
.quick-section,
.chat-panel,
.composer {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 16px;
  box-shadow: 0 8px 28px rgba(31, 45, 61, 0.06);
}

.agent-header {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.agent-identity,
.title-row,
.section-heading,
.composer-footer,
.tool-trace,
.message-meta {
  display: flex;
  align-items: center;
}

.agent-identity { gap: 14px; }
.agent-logo,
.avatar,
.quick-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
}
.agent-logo {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  color: #fff;
  font-size: 25px;
  background: linear-gradient(135deg, #337ecc, #79bbff);
}
.title-row { gap: 10px; flex-wrap: wrap; }
h1 { margin: 0; font-size: 23px; color: #303133; }
.agent-header p { margin: 7px 0 0; color: #606266; }

.quick-section { padding: 18px 20px; }
.section-heading { justify-content: space-between; margin-bottom: 14px; }
.section-heading span { font-weight: 600; color: #303133; }
.section-heading small { color: #909399; }
.quick-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.quick-card {
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: #fafcff;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  cursor: pointer;
  transition: border-color .2s, transform .2s, box-shadow .2s;
}
.quick-card:hover:not(:disabled) {
  border-color: #79bbff;
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(64, 158, 255, .12);
}
.quick-card:disabled { cursor: not-allowed; opacity: .65; }
.quick-card strong,
.quick-card small { display: block; }
.quick-card strong { color: #303133; margin-bottom: 4px; }
.quick-card small { color: #909399; line-height: 1.45; }
.quick-icon { width: 38px; height: 38px; border-radius: 10px; font-size: 19px; }
.quick-icon.procurement { color: #b88230; background: #fdf6ec; }
.quick-icon.equipment { color: #337ecc; background: #ecf5ff; }

.chat-panel {
  min-height: 320px;
  max-height: calc(100vh - 360px);
  overflow-y: auto;
  padding: 24px;
  scroll-behavior: smooth;
}
.message-row { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 20px; }
.message-row.user { flex-direction: row-reverse; }
.avatar { width: 34px; height: 34px; border-radius: 10px; background: #ecf5ff; color: #337ecc; }
.user .avatar { background: #f0f2f5; color: #606266; }
.message-body { max-width: min(76%, 760px); }
.message-bubble {
  padding: 12px 15px;
  border-radius: 4px 14px 14px 14px;
  background: #f4f7fb;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.user .message-bubble { color: #fff; background: #409eff; border-radius: 14px 4px 14px 14px; }
.tool-trace { gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.trace-title { color: #909399; font-size: 12px; }
.message-meta { gap: 10px; flex-wrap: wrap; margin-top: 6px; color: #a8abb2; font-size: 11px; }
.user .message-meta { justify-content: flex-end; }
.loading-bubble { display: flex; align-items: center; gap: 5px; }
.loading-bubble i { width: 5px; height: 5px; border-radius: 50%; background: #409eff; animation: pulse 1.2s infinite; }
.loading-bubble i:nth-child(3) { animation-delay: .15s; }
.loading-bubble i:nth-child(4) { animation-delay: .3s; }
@keyframes pulse { 0%, 70%, 100% { opacity: .25; } 35% { opacity: 1; } }

.composer { padding: 16px; }
.composer-footer { justify-content: space-between; gap: 16px; margin-top: 10px; }
.composer-footer span { color: #909399; font-size: 12px; }

@media (max-width: 767px) {
  .agent-page { min-height: calc(100vh - 86px); gap: 12px; }
  .agent-header { align-items: flex-start; padding: 16px; }
  .agent-header > .el-button { padding: 8px; }
  .agent-header > .el-button :deep(span) { display: none; }
  h1 { font-size: 19px; }
  .agent-header p { font-size: 13px; }
  .quick-grid { grid-template-columns: 1fr; }
  .section-heading { align-items: flex-start; flex-direction: column; gap: 5px; }
  .chat-panel { padding: 16px 12px; max-height: calc(100vh - 330px); }
  .message-body { max-width: 86%; }
  .composer-footer span { display: none; }
  .composer-footer { justify-content: flex-end; }
}
</style>
