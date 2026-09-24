<template>
  <div class="agent-shell">
    <button
      v-if="!expanded"
      class="agent-launcher"
      type="button"
      :aria-label="launcherLabel"
      :aria-expanded="expanded"
      @click="openPanel"
    >
      <span class="launcher-icon"><el-icon><MagicStick /></el-icon></span>
      <span v-if="!isMobile" class="launcher-text">智能助手</span>
      <span v-if="hasUnread" class="unread-dot" aria-label="有新回复"></span>
    </button>

    <transition name="fade">
      <div v-if="expanded && isMobile" class="agent-backdrop" @click="closePanel"></div>
    </transition>

    <transition name="slide">
      <aside ref="panelRef" v-if="expanded" class="agent-panel" aria-label="实验室运营智能助手">
        <header class="panel-header">
          <div class="agent-title">
            <span class="agent-logo"><el-icon><MagicStick /></el-icon></span>
            <span>
              <strong>实验室运营智能助手</strong>
              <small>查询与安全预填 · 提交前由你确认</small>
            </span>
          </div>
          <div class="header-actions">
            <el-tooltip content="清空对话" placement="bottom">
              <el-button
                circle
                plain
                size="small"
                :icon="Delete"
                :disabled="loading"
                aria-label="清空对话"
                @click="clearConversation"
              />
            </el-tooltip>
            <el-button
              circle
              text
              size="small"
              :icon="Close"
              aria-label="收起智能助手"
              @click="closePanel"
            />
          </div>
        </header>

        <div ref="chatPanel" class="chat-panel" aria-live="polite">
          <section v-if="showQuickQuestions" class="quick-section">
            <span class="quick-heading">快捷提问</span>
            <button
              v-for="item in quickQuestions"
              :key="item.question"
              class="quick-card"
              type="button"
              :disabled="loading"
              @click="submitQuestion(item.question)"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </button>
          </section>

          <article
            v-for="message in messages"
            :key="message.id"
            class="message-row"
            :class="message.role"
          >
            <span class="avatar">
              <el-icon v-if="message.role === 'assistant'"><MagicStick /></el-icon>
              <el-icon v-else><User /></el-icon>
            </span>
            <div class="message-content">
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
              <div v-if="message.role === 'assistant' && message.tools?.length" class="tool-list">
                <span>已查询</span>
                <el-tag
                  v-for="tool in message.tools"
                  :key="`${message.id}-${tool.name}`"
                  :type="tool.status === 'success' ? 'success' : 'danger'"
                  effect="plain"
                  size="small"
                >
                  {{ toolLabels[tool.name] || tool.name }}
                </el-tag>
              </div>
              <LabOpsEvidenceList
                v-if="message.role === 'assistant'"
                :evidence="message.evidence || []"
                :retrieval="message.retrieval || {}"
              />
              <small class="message-meta">
                {{ message.time }}
                <span v-if="message.domain"> · {{ domainLabels[message.domain] || message.domain }}</span>
              </small>
            </div>
          </article>

          <article v-if="loading" class="message-row assistant">
            <span class="avatar"><el-icon><MagicStick /></el-icon></span>
            <div class="message-bubble loading-bubble">
              <span>正在查询</span><i></i><i></i><i></i>
            </div>
          </article>
        </div>

        <form class="composer" @submit.prevent="submitQuestion()">
          <el-input
            ref="inputRef"
            v-model="question"
            type="textarea"
            :rows="2"
            resize="none"
            maxlength="1000"
            :disabled="loading"
            placeholder="询问采购进度或仪器预约……"
            @keydown.enter.exact.prevent="submitQuestion()"
          />
          <div class="composer-footer">
            <span>Enter 发送 · 可预填，提交仍由你确认</span>
            <el-button
              type="primary"
              :icon="Promotion"
              :loading="loading"
              :disabled="!question.trim()"
              native-type="submit"
            >
              发送
            </el-button>
          </div>
        </form>
      </aside>
    </transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  Calendar,
  Close,
  Delete,
  MagicStick,
  Promotion,
  ShoppingCart,
  User,
} from '@element-plus/icons-vue'
import LabOpsActionCard from '@/components/LabOpsActionCard.vue'
import LabOpsEquipmentActionCard from '@/components/LabOpsEquipmentActionCard.vue'
import LabOpsEvidenceList from '@/components/LabOpsEvidenceList.vue'
import { queryLabOpsAgent } from '@/api/labopsAgent'
import {
  buildLabOpsHistoryContent,
  useLabOpsActionNavigation,
} from '@/composables/useLabOpsActionNavigation'

const STORAGE_KEY = 'labopsAgentSidebarExpanded'
const expanded = ref(sessionStorage.getItem(STORAGE_KEY) === 'true')
const isMobile = ref(window.innerWidth < 768)
const hasUnread = ref(false)
const chatPanel = ref(null)
const inputRef = ref(null)
const panelRef = ref(null)
const question = ref('')
const loading = ref(false)
const conversationId = ref(null)
let messageSequence = 0
const { openEquipmentReservation, openProcurementRequest } = useLabOpsActionNavigation(closePanel)

const toolLabels = {
  list_procurement_requests: '采购申请列表',
  get_procurement_request: '采购申请详情',
  prepare_procurement_request: '采购信息校验',
  search_equipment: '仪器搜索',
  prepare_equipment_reservation: '预约信息校验',
  get_my_reservations: '我的仪器预约',
  get_available_slots: '可预约时段',
  check_reservation_conflict: '预约冲突检查',
}

const domainLabels = {
  procurement: '采购查询',
  equipment: '仪器预约查询',
  mixed: '综合查询',
  general: '使用说明',
}

const quickQuestions = [
  { title: '我的采购申请到哪一步了？', question: '我最近有哪些采购申请，分别进行到哪一步了？', icon: ShoppingCart },
  { title: '查看被驳回的申请', question: '我最近被驳回的采购申请有哪些，下一步应该怎么处理？', icon: ShoppingCart },
  { title: '查看我的仪器预约', question: '我接下来有哪些仪器预约？', icon: Calendar },
  { title: '搜索可预约仪器', question: '帮我搜索名称或介绍中包含XRD的可预约仪器。', icon: Calendar },
]

function formatTime() {
  return new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function welcomeMessage() {
  return {
    id: `message-${++messageSequence}`,
    role: 'assistant',
    content: '你好，我可以查询采购申请和仪器预约，也能生成采购草稿或预填仪器预约。所有最终提交都需要你亲自确认。',
    time: formatTime(),
  }
}

const messages = ref([welcomeMessage()])
const showQuickQuestions = computed(() => messages.value.length === 1)
const launcherLabel = computed(() => hasUnread.value ? '打开智能助手，有新回复' : '打开智能助手')

watch(expanded, (value) => {
  sessionStorage.setItem(STORAGE_KEY, String(value))
  if (value) hasUnread.value = false
})

function handleResize() {
  isMobile.value = window.innerWidth < 768
}

function handleEscape(event) {
  if (event.key === 'Escape' && expanded.value) closePanel()
}

function handleOutsidePointer(event) {
  if (!expanded.value || isMobile.value) return
  if (!panelRef.value?.contains(event.target)) closePanel()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  window.addEventListener('keydown', handleEscape)
  document.addEventListener('pointerdown', handleOutsidePointer)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleEscape)
  document.removeEventListener('pointerdown', handleOutsidePointer)
})

async function openPanel() {
  expanded.value = true
  await nextTick()
  inputRef.value?.focus()
  await scrollToBottom()
}

function closePanel() {
  expanded.value = false
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
  if (chatPanel.value) chatPanel.value.scrollTop = chatPanel.value.scrollHeight
}

function buildErrorMessage(error) {
  const status = error.response?.status
  const code = error.response?.data?.code
  const detail = error.response?.data?.detail
  if (status === 503 && code === 'agent_disabled') return '智能助手尚未启用，请检查后端配置。'
  if (status === 503) return '模型服务暂时不可用，请稍后重试。'
  if (status === 502) return '模型返回异常，本次没有执行任何写操作，请重新提问。'
  if (status === 403) return '当前账号没有智能助手使用权限。'
  if (status === 401) return '登录状态已失效，请重新登录。'
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
    if (!expanded.value) hasUnread.value = true
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
.agent-launcher {
  position: fixed;
  z-index: 1800;
  top: 50%;
  right: 0;
  width: 48px;
  min-height: 126px;
  padding: 12px 9px;
  transform: translateY(-50%);
  border: 1px solid #79bbff;
  border-right: 0;
  border-radius: 16px 0 0 16px;
  color: #fff;
  background: linear-gradient(160deg, #337ecc, #409eff);
  box-shadow: 0 8px 24px rgba(51, 126, 204, .25);
  cursor: pointer;
}
.launcher-icon { display: grid; place-items: center; font-size: 21px; }
.launcher-text { display: block; margin: 8px auto 0; line-height: 1.35; writing-mode: vertical-rl; letter-spacing: 2px; }
.unread-dot { position: absolute; top: 7px; left: 7px; width: 9px; height: 9px; border-radius: 50%; background: #f56c6c; box-shadow: 0 0 0 2px #fff; }

.agent-panel {
  position: fixed;
  z-index: 1900;
  top: 60px;
  right: 0;
  bottom: 0;
  width: min(380px, calc(100vw - 24px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-left: 1px solid #dcdfe6;
  background: #f6f8fb;
  box-shadow: -12px 0 32px rgba(31, 45, 61, .16);
}
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 14px 12px 14px 16px; border-bottom: 1px solid #e4e7ed; background: #fff; }
.agent-title { display: flex; align-items: center; gap: 10px; min-width: 0; }
.agent-title > span:last-child { min-width: 0; }
.agent-title strong, .agent-title small { display: block; }
.agent-title strong { overflow: hidden; color: #303133; font-size: 15px; text-overflow: ellipsis; white-space: nowrap; }
.agent-title small { margin-top: 4px; color: #909399; font-size: 11px; }
.agent-logo, .avatar { display: grid; place-items: center; flex: 0 0 auto; color: #337ecc; background: #ecf5ff; }
.agent-logo { width: 36px; height: 36px; border-radius: 11px; font-size: 19px; }
.header-actions { display: flex; align-items: center; gap: 2px; }

.chat-panel { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 14px; scroll-behavior: smooth; }
.quick-section { margin-bottom: 16px; padding: 12px; border: 1px solid #e4e7ed; border-radius: 12px; background: #fff; }
.quick-heading { display: block; margin-bottom: 9px; color: #606266; font-size: 12px; font-weight: 600; }
.quick-card { width: 100%; display: flex; align-items: center; gap: 8px; margin-top: 7px; padding: 9px 10px; border: 1px solid #e4e7ed; border-radius: 9px; color: #606266; background: #fafcff; cursor: pointer; text-align: left; }
.quick-card:hover:not(:disabled) { border-color: #79bbff; color: #337ecc; background: #ecf5ff; }
.quick-card:disabled { cursor: not-allowed; opacity: .6; }
.message-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 15px; }
.message-row.user { flex-direction: row-reverse; }
.avatar { width: 30px; height: 30px; border-radius: 9px; }
.user .avatar { color: #606266; background: #ebeef5; }
.message-content { min-width: 0; max-width: 84%; }
.message-bubble { padding: 10px 12px; border-radius: 4px 12px 12px; color: #303133; background: #fff; box-shadow: 0 2px 8px rgba(31, 45, 61, .06); line-height: 1.62; white-space: pre-wrap; word-break: break-word; }
.user .message-bubble { color: #fff; background: #409eff; border-radius: 12px 4px 12px 12px; }
.tool-list { display: flex; align-items: center; flex-wrap: wrap; gap: 5px; margin-top: 7px; color: #909399; font-size: 11px; }
.message-meta { display: block; margin-top: 5px; color: #a8abb2; font-size: 10px; }
.user .message-meta { text-align: right; }
.loading-bubble { display: flex; align-items: center; gap: 4px; }
.loading-bubble i { width: 4px; height: 4px; border-radius: 50%; background: #409eff; animation: pulse 1.2s infinite; }
.loading-bubble i:nth-child(3) { animation-delay: .15s; }
.loading-bubble i:nth-child(4) { animation-delay: .3s; }
@keyframes pulse { 0%, 70%, 100% { opacity: .25; } 35% { opacity: 1; } }

.composer { flex: 0 0 auto; padding: 12px; border-top: 1px solid #e4e7ed; background: #fff; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 8px; }
.composer-footer > span { color: #a8abb2; font-size: 10px; }
.agent-backdrop { position: fixed; z-index: 1850; inset: 0; background: rgba(0, 0, 0, .32); }

.slide-enter-active, .slide-leave-active { transition: transform .22s ease, opacity .22s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); opacity: .5; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 767px) {
  .agent-launcher { top: auto; right: 18px; bottom: 22px; width: 52px; min-height: 52px; padding: 0; transform: none; border: 0; border-radius: 50%; }
  .agent-panel { top: 0; width: min(420px, 100vw); height: 100dvh; }
  .panel-header { padding-top: max(14px, env(safe-area-inset-top)); }
  .composer { padding-bottom: max(12px, env(safe-area-inset-bottom)); }
}
</style>
