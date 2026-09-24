<template>
  <el-card class="box-card" shadow="never">
    <template #header><div class="card-header"><span>🖥️ 远程主机连接</span></div></template>
    
    <el-form :model="bookingForm" label-width="100px" v-loading="isLoadingMachines">
      <el-row><el-col :span="24"><el-form-item label="选择主机">
        <el-select v-model="bookingForm.machineId" placeholder="请选择要连接的主机" style="width: 100%;" filterable @change="handleMachineChange">
          <el-option v-for="machine in machines" :key="machine.id" :label="machine.name" :value="machine.id">
            <span style="float: left">{{ machine.name }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px">{{ machine.ip_address }}</span>
          </el-option>
        </el-select>
      </el-form-item></el-col></el-row>

      <div class="status-area">
        <div v-if="machineStatus.status === 'occupied' && !machineStatus.is_self_booking" class="alert-box occupied">
          <el-alert type="warning" show-icon :closable="false"><template #title><span class="alert-title">该主机正在被其他用户使用</span></template>
            <div class="alert-content">
              <p>当前用户: <strong>{{ machineStatus.user }}</strong></p>
              <p>预计结束: {{ formatToBeijingTime(machineStatus.end_time) }}</p>
              <p v-if="showTakeoverCountdown" class="takeover-countdown">
                插队倒计时: <strong>{{ formattedTakeoverCountdown }}</strong>，归零后将自动接管。
              </p>
              <p v-if="showTakeoverRejectedCooldown" class="takeover-cooldown">
                对方已拒绝，<strong>{{ formattedTakeoverRejectedCooldown }}</strong> 后可再次申请。
              </p>
              <p class="hint">如果您急需使用，可以申请紧急插队。</p>
            </div>
          </el-alert>
          <div class="action-btn">
            <el-button v-if="showTakeoverRejectedCooldown" type="danger" disabled plain>
              对方已拒绝 {{ formattedTakeoverRejectedCooldown }}
            </el-button>
            <el-button v-else-if="showTakeoverCountdown" type="warning" loading>
              等待响应 {{ formattedTakeoverCountdown }}
            </el-button>
            <el-button v-else type="danger" @click="handleRequestTakeover">申请紧急插队</el-button>
          </div>
        </div>

        <div v-else-if="machineStatus.status === 'occupied' && machineStatus.is_self_booking" class="alert-box self">
          <el-alert type="success" show-icon :closable="false"><template #title><span class="alert-title">您正在使用该主机</span></template><div class="alert-content"><p>您已有一个正在进行的会话。</p></div></el-alert>
          <div class="action-btn">
            <el-button type="success" size="large" @click="emitConnect(machineStatus.booking_id, getCurrentMachineObj())"><el-icon><Connection /></el-icon> 回到连接</el-button>
          </div>
        </div>

        <div v-else-if="machineStatus.status === 'free' && bookingForm.machineId" class="alert-box free">
          <div class="free-content"><el-icon class="free-icon"><Monitor /></el-icon><p>当前主机空闲，您可以直接连接</p></div>
          <div class="action-btn">
            <el-button type="primary" size="large" @click="handleInstantConnect" :loading="isSubmitting"><el-icon><Connection /></el-icon> 立即连接</el-button>
          </div>
        </div>
      </div>
    </el-form>
  </el-card>

  <div style="height: 20px;"></div>

  <el-card class="box-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span>📋 我的连接记录</span>
          <el-date-picker
            v-model="selectedDate"
            type="date"
            placeholder="选择日期查询"
            size="small"
            style="margin-left: 20px; width: 160px;"
            :clearable="false"
            @change="handleFetchMyBookings"
          />
        </div>
        <el-button class="button" type="primary" plain @click="handleFetchMyBookings" :loading="isLoadingBookings">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </template>
    
    <el-table :data="myBookings" stripe v-loading="isLoadingBookings">
      <el-table-column prop="machine.name" label="主机" min-width="120" />
      <el-table-column prop="start_time" label="开始时间" width="180">
        <template #default="s">{{ formatToBeijingTime(s.row.start_time) }}</template>
      </el-table-column>
      <el-table-column prop="end_time" label="结束时间" width="180">
        <template #default="s">{{ formatToBeijingTime(s.row.end_time) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="s"><el-tag :type="getBookingStatusTag(s.row.status)">{{ getBookingStatusText(s.row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" min-width="150">
        <template #default="s">
          <el-button v-if="['confirmed','active'].includes(s.row.status)" type="success" size="small" @click="emitConnect(s.row.id, s.row.machine)">连接</el-button>
          <el-button v-if="s.row.status === 'confirmed' && isBeforeStartTime(s.row.start_time)" type="danger" plain size="small" @click="handleCancelBooking(s.row.id)">取消</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, reactive, watch } from 'vue';
import { useRoute } from 'vue-router';
import { fetchMyRdpBookings, createInstantRdpBooking, cancelRdpBooking, fetchMachineCurrentStatus, requestTakeover } from '@/api/remote_access';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh, Connection, Monitor } from '@element-plus/icons-vue';

const props = defineProps(['machines', 'loading']);
const emit = defineEmits(['start-session']);
const route = useRoute();

const bookingForm = reactive({ machineId: null });
const machineStatus = ref({ status: 'free' });
const myBookings = ref([]);
const isLoadingBookings = ref(false);
const isSubmitting = ref(false);
const isWaitingTakeover = ref(false);
const takeoverRemainingSeconds = ref(null);
const takeoverRejectedRemainingSeconds = ref(0);
const takeoverRejectedUntil = ref(0);
const takeoverRejectedBookingId = ref(null);
const takeoverPollTimer = ref(null);
const takeoverRejectedTimer = ref(null);
const machineStatusPollTimer = ref(null);
const kioskStatusPollTimer = ref(null);
const TAKEOVER_TIMEOUT_SECONDS = 60;
const TAKEOVER_REJECTED_COOLDOWN_SECONDS = 5 * 60;
const MACHINE_STATUS_POLL_MS = 3000;
const KIOSK_REMOTE_SIGNAL_STATE_KEY = 'LIMS_KIOSK_REMOTE_SIGNAL_STATE_V1';
const AHK_MAGIC_SIGNALS = new Set([
  'LIMS_UNLOCK_LOCAL_SESSION_KEY_888',
  'LIMS_FORCE_LOCK_NOW',
  'LIMS_ALERT_TAKEOVER_PENDING',
  'LIMS_REMOTE_SESSION_ACTIVE',
  'LIMS_REMOTE_SESSION_ENDED'
]);
const getStoredKioskSignalState = () => {
  try { return sessionStorage.getItem(KIOSK_REMOTE_SIGNAL_STATE_KEY) || 'unknown'; } catch { return 'unknown'; }
};
const kioskRemoteSignalState = ref(getStoredKioskSignalState());
const lastActiveClipboardSignalAt = ref(0);
const lastEndedClipboardSignalAt = ref(0);
const lastEndedTitleSignalAt = ref(0);
let ahkTitleSignalSeq = 0;

// 初始化：默认显示“北京时间的今天”
const selectedDate = ref(new Date());

const showTakeoverCountdown = computed(() =>
  machineStatus.value?.is_takeover_pending &&
  machineStatus.value?.takeover_status === 'pending' &&
  takeoverRemainingSeconds.value !== null
);

const formatCountdown = (value, fallback = 0) => {
  const rawSeconds = Number(value ?? fallback);
  const seconds = Math.max(0, Number.isFinite(rawSeconds) ? rawSeconds : Number(fallback) || 0);
  const mm = Math.floor(seconds / 60).toString().padStart(2, '0');
  const ss = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${mm}:${ss}`;
};

const formattedTakeoverCountdown = computed(() =>
  formatCountdown(takeoverRemainingSeconds.value, TAKEOVER_TIMEOUT_SECONDS)
);

const showTakeoverRejectedCooldown = computed(() =>
  machineStatus.value?.status === 'occupied' &&
  machineStatus.value?.booking_id === takeoverRejectedBookingId.value &&
  takeoverRejectedRemainingSeconds.value > 0
);

const formattedTakeoverRejectedCooldown = computed(() =>
  formatCountdown(takeoverRejectedRemainingSeconds.value, TAKEOVER_REJECTED_COOLDOWN_SECONDS)
);

const stopTakeoverRejectedCooldown = () => {
  if (takeoverRejectedTimer.value) {
    clearInterval(takeoverRejectedTimer.value);
    takeoverRejectedTimer.value = null;
  }
  takeoverRejectedUntil.value = 0;
  takeoverRejectedRemainingSeconds.value = 0;
  takeoverRejectedBookingId.value = null;
};

const updateTakeoverRejectedCountdown = () => {
  const remaining = Math.max(0, Math.ceil((takeoverRejectedUntil.value - Date.now()) / 1000));
  takeoverRejectedRemainingSeconds.value = remaining;
  if (remaining <= 0) stopTakeoverRejectedCooldown();
};

const startTakeoverRejectedCooldown = (seconds = TAKEOVER_REJECTED_COOLDOWN_SECONDS, bookingId = machineStatus.value?.booking_id) => {
  const numericSeconds = Number(seconds);
  const normalized = Math.max(
    0,
    Math.ceil(Number.isFinite(numericSeconds) ? numericSeconds : TAKEOVER_REJECTED_COOLDOWN_SECONDS)
  );
  if (!bookingId || normalized <= 0) {
    stopTakeoverRejectedCooldown();
    return;
  }

  takeoverRejectedBookingId.value = bookingId;
  takeoverRejectedUntil.value = Date.now() + normalized * 1000;
  updateTakeoverRejectedCountdown();
  if (!takeoverRejectedTimer.value) {
    takeoverRejectedTimer.value = setInterval(updateTakeoverRejectedCountdown, 1000);
  }
};

const syncTakeoverStateFromStatus = (status) => {
  const waitingForMe = (
    status?.status === 'occupied' &&
    status?.is_takeover_pending &&
    status?.takeover_status === 'pending'
  );

  if (!waitingForMe) {
    if (!isWaitingTakeover.value) takeoverRemainingSeconds.value = null;
    return false;
  }

  isWaitingTakeover.value = true;
  const raw = status.takeover_remaining_seconds;
  const seconds = Number.isFinite(Number(raw)) ? Number(raw) : TAKEOVER_TIMEOUT_SECONDS;
  takeoverRemainingSeconds.value = Math.max(0, Math.ceil(seconds));
  return true;
};

const syncTakeoverRejectedCooldownFromStatus = (status) => {
  if (!status || status.status !== 'occupied') {
    stopTakeoverRejectedCooldown();
    return;
  }

  if (takeoverRejectedBookingId.value && takeoverRejectedBookingId.value !== status.booking_id) {
    stopTakeoverRejectedCooldown();
  }

  const raw = status.takeover_rejected_cooldown_remaining_seconds;
  const seconds = Number.isFinite(Number(raw)) ? Number(raw) : 0;
  if (seconds > 0) {
    startTakeoverRejectedCooldown(seconds, status.booking_id);
  } else if (status.takeover_status !== 'rejected' && takeoverRejectedBookingId.value === status.booking_id) {
    stopTakeoverRejectedCooldown();
  }
};

const applyMachineStatus = (machineId, status) => {
  const previousStatus = machineStatus.value?.status;
  machineStatus.value = status;
  const waitingForMe = syncTakeoverStateFromStatus(status);
  syncTakeoverRejectedCooldownFromStatus(status);
  handleKioskStatusSignal(machineId, status);

  if (previousStatus === 'occupied' && status?.status === 'free') {
    handleFetchMyBookings();
  }

  return waitingForMe;
};

/**
 * [新增] 强制将服务器返回的 ISO 时间字符串格式化为北京时间显示
 * 解决即便在海外访问，显示的也是北京实验室时间的问题
 */
const formatToBeijingTime = (isoString) => {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'Asia/Shanghai' // 强制指定北京时区
    }).format(date).replace(/\//g, '-');
  } catch (e) {
    return isoString;
  }
};

// 辅助：获取 YYYY-MM-DD 格式日期
const getLocalDateString = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

onMounted(() => {
  handleFetchMyBookings();
  startMachineStatusPoll();
  startKioskStatusPoll();
});
onUnmounted(() => {
  stopTakeoverPoll();
  stopTakeoverRejectedCooldown();
  stopMachineStatusPoll();
  stopKioskStatusPoll();
});

const handleMachineChange = async (id) => {
  if (!id) return;
  stopTakeoverPoll();
  isWaitingTakeover.value = false;
  takeoverRemainingSeconds.value = null;
  stopTakeoverRejectedCooldown();
  try {
    const res = await fetchMachineCurrentStatus(id);
    if (applyMachineStatus(id, res.data)) startTakeoverPoll();
  } catch (e) { console.error(e); }
};

watch(() => props.machines, (newVal) => {
  if (newVal?.length > 0 && !bookingForm.machineId) {
    bookingForm.machineId = newVal[0].id;
    handleMachineChange(newVal[0].id);
  }
}, { immediate: true });

const handleInstantConnect = async () => {
  if (!bookingForm.machineId) return;
  isSubmitting.value = true;
  try {
    const res = await createInstantRdpBooking(bookingForm.machineId);
    ElMessage.success('连接准备就绪...');
    handleFetchMyBookings();
    handleMachineChange(bookingForm.machineId);
    emitConnect(res.data.id, getCurrentMachineObj());
  } catch (error) { ElMessage.error(error.response?.data?.detail || '连接请求失败'); } 
  finally { isSubmitting.value = false; }
};

const emitConnect = (id, machineObj) => {
  emit('start-session', { id, machine: machineObj });
};

const normalizeMachineName = (v) => String(v || '').trim().toLowerCase();
const normalizeUser = (v) => {
  const s = normalizeMachineName(v);
  if (!s) return '';
  if (s.includes('\\')) return s.split('\\').pop();
  if (s.includes('@')) return s.split('@')[0];
  return s;
};

const isKioskLocalMachine = (machineId) => {
  if (route.query?.kiosk_mode !== 'true') return false;

  const localId = Number(route.query?.local_machine_id);
  const targetId = Number(machineId);
  if (Number.isFinite(localId) && Number.isFinite(targetId) && localId === targetId) return true;

  const machine = props.machines.find(m => Number(m.id) === targetId);
  if (!machine) return false;

  const localUser = normalizeUser(route.query?.local_user);
  if (localUser) {
    const machineUser = normalizeUser(machine.username || machine.user_name || machine.user);
    const machineNameUser = normalizeUser(machine.name);
    if ((machineUser && localUser === machineUser) || (machineNameUser && localUser === machineNameUser)) return true;
  }

  const localName = normalizeMachineName(route.query?.local_machine_name);
  return !!(localName && normalizeMachineName(machine.name) === localName);
};

const sendAhkCommand = (cmd) => {
  try {
    const ta = document.createElement('textarea');
    ta.value = cmd;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
};

const getSafeDocumentTitle = () => {
  const title = document.title || '实验室管理系统';
  return AHK_MAGIC_SIGNALS.has(title) ? '实验室管理系统' : title;
};

const sendAhkTitleSignal = (cmd, holdMs = 1800) => {
  const originalTitle = getSafeDocumentTitle();
  const seq = ++ahkTitleSignalSeq;
  try {
    document.title = cmd;
    setTimeout(() => {
      if (seq === ahkTitleSignalSeq && document.title === cmd) document.title = originalTitle;
    }, holdMs);
    return true;
  } catch {
    return false;
  }
};

const sendAhkSignal = (cmd) => {
  const ok = sendAhkCommand(cmd);
  sendAhkTitleSignal(cmd, 3000);
  return ok;
};

const setKioskRemoteSignalState = (state) => {
  kioskRemoteSignalState.value = state;
  try { sessionStorage.setItem(KIOSK_REMOTE_SIGNAL_STATE_KEY, state); } catch {}
};

const sendClipboardSignalIfDue = (cmd, lastSentAtRef, throttleMs, now = Date.now()) => {
  if ((now - lastSentAtRef.value) < throttleMs) return false;
  const ok = sendAhkCommand(cmd);
  lastSentAtRef.value = now;
  return ok;
};

const handleKioskStatusSignal = (machineId, status) => {
  if (!isKioskLocalMachine(machineId)) return;

  const now = Date.now();
  const remoteOccupied = status?.status === 'occupied' && status?.is_self_booking === false;

  if (remoteOccupied) {
    // 高频标题心跳保证看门狗能在 1 秒内最小化浏览器；剪贴板只在切换时/低频补发，避免影响远控用户复制粘贴。
    sendAhkTitleSignal('LIMS_REMOTE_SESSION_ACTIVE', 1600);
    if (kioskRemoteSignalState.value !== 'remote_active') {
      sendAhkSignal('LIMS_REMOTE_SESSION_ACTIVE');
      lastActiveClipboardSignalAt.value = now;
    } else {
      sendClipboardSignalIfDue('LIMS_REMOTE_SESSION_ACTIVE', lastActiveClipboardSignalAt, 30000, now);
    }
    setKioskRemoteSignalState('remote_active');
    return;
  }

  if (status?.status === 'free' || status?.is_self_booking === true) {
    const wasRemoteActive = kioskRemoteSignalState.value === 'remote_active';
    if (wasRemoteActive) {
      sendAhkSignal('LIMS_REMOTE_SESSION_ENDED');
      lastEndedClipboardSignalAt.value = now;
    } else if (status?.status === 'free') {
      // 页面刷新后前端状态会丢；空闲页低频补发 ended，可把仍停在 remote-suppressed 的看门狗拉回全屏。
      if ((now - lastEndedTitleSignalAt.value) > 2500) {
        sendAhkTitleSignal('LIMS_REMOTE_SESSION_ENDED', 1400);
        lastEndedTitleSignalAt.value = now;
      }
      sendClipboardSignalIfDue('LIMS_REMOTE_SESSION_ENDED', lastEndedClipboardSignalAt, 20000, now);
    }
    setKioskRemoteSignalState('local_available');
  }
};

const pollKioskCurrentStatus = async () => {
  if (!bookingForm.machineId || !isKioskLocalMachine(bookingForm.machineId)) return;
  try {
    const res = await fetchMachineCurrentStatus(bookingForm.machineId);
    applyMachineStatus(bookingForm.machineId, res.data);
  } catch (e) {
    console.warn('kiosk status poll failed', e);
  }
};

const pollSelectedMachineStatus = async () => {
  if (!bookingForm.machineId || isWaitingTakeover.value || isKioskLocalMachine(bookingForm.machineId)) return;
  try {
    const res = await fetchMachineCurrentStatus(bookingForm.machineId);
    applyMachineStatus(bookingForm.machineId, res.data);
  } catch (e) {
    console.warn('machine status poll failed', e);
  }
};

const startMachineStatusPoll = () => {
  stopMachineStatusPoll();
  pollSelectedMachineStatus();
  machineStatusPollTimer.value = setInterval(pollSelectedMachineStatus, MACHINE_STATUS_POLL_MS);
};

const stopMachineStatusPoll = () => {
  if (machineStatusPollTimer.value) {
    clearInterval(machineStatusPollTimer.value);
    machineStatusPollTimer.value = null;
  }
};

const startKioskStatusPoll = () => {
  stopKioskStatusPoll();
  pollKioskCurrentStatus();
  kioskStatusPollTimer.value = setInterval(pollKioskCurrentStatus, 500);
};

const stopKioskStatusPoll = () => {
  if (kioskStatusPollTimer.value) {
    clearInterval(kioskStatusPollTimer.value);
    kioskStatusPollTimer.value = null;
  }
};

const handleFetchMyBookings = async () => {
  isLoadingBookings.value = true;
  try {
    const params = {
      date: getLocalDateString(selectedDate.value)
    };
    const res = await fetchMyRdpBookings(params);
    myBookings.value = res.data.results || res.data;
  } finally {
    isLoadingBookings.value = false;
  }
};

const handleRequestTakeover = async () => {
  if (showTakeoverRejectedCooldown.value) {
    ElMessage.warning(`请等待 ${formattedTakeoverRejectedCooldown.value} 后再次申请`);
    return;
  }

  try {
    await ElMessageBox.confirm('申请插队？', '紧急插队', { type: 'warning' });
    const tid = machineStatus.value.booking_id;
    if (!tid) return;
    const res = await requestTakeover(tid);
    ElMessage.success('申请已发送');
    isWaitingTakeover.value = true;
    stopTakeoverRejectedCooldown();
    machineStatus.value = {
      ...machineStatus.value,
      ...res.data,
      is_takeover_pending: true,
      takeover_status: 'pending'
    };
    syncTakeoverStateFromStatus(machineStatus.value);
    startTakeoverPoll();
  } catch (e) {
    const seconds = Number(e?.response?.data?.takeover_rejected_cooldown_remaining_seconds);
    if (seconds > 0) {
      startTakeoverRejectedCooldown(seconds, machineStatus.value?.booking_id);
      ElMessage.warning(`对方已拒绝，请 ${formattedTakeoverRejectedCooldown.value} 后再次申请`);
    }
  }
};

const pollTakeoverStatus = async () => {
  if (!bookingForm.machineId) return;
  try {
    const res = await fetchMachineCurrentStatus(bookingForm.machineId);
    applyMachineStatus(bookingForm.machineId, res.data);

    if (res.data.status === 'free') {
      stopTakeoverPoll();
      isWaitingTakeover.value = false;
      takeoverRemainingSeconds.value = null;
      ElMessage.success('对方已下线');
      handleInstantConnect();
    } else if (res.data.takeover_status === 'rejected') {
      stopTakeoverPoll();
      isWaitingTakeover.value = false;
      takeoverRemainingSeconds.value = null;
      const rejectedCooldownSeconds = Number(res.data.takeover_rejected_cooldown_remaining_seconds);
      startTakeoverRejectedCooldown(
        Number.isFinite(rejectedCooldownSeconds) ? rejectedCooldownSeconds : TAKEOVER_REJECTED_COOLDOWN_SECONDS,
        res.data.booking_id
      );
      ElMessage.error('对方拒绝');
    }
  } catch (e) {
    console.warn('takeover poll failed', e);
  }
};

const startTakeoverPoll = () => {
  stopTakeoverPoll();
  pollTakeoverStatus();
  takeoverPollTimer.value = setInterval(pollTakeoverStatus, 1000);
};

const stopTakeoverPoll = () => {
  if (takeoverPollTimer.value) {
    clearInterval(takeoverPollTimer.value);
    takeoverPollTimer.value = null;
  }
};
const handleCancelBooking = async (id) => { try { await ElMessageBox.confirm('确定取消？','提示'); await cancelRdpBooking(id); ElMessage.success('已取消'); handleFetchMyBookings(); handleMachineChange(bookingForm.machineId); } catch(e){} };
const getCurrentMachineObj = () => props.machines.find(m => m.id === bookingForm.machineId) || { name: 'Host', ip_address: '' };
const isBeforeStartTime = (t) => new Date(t) > new Date();
const getBookingStatusTag = (s) => ({ confirmed:'primary', active:'success', completed:'info', canceled:'warning' }[s] || 'info');
const getBookingStatusText = (s) => ({ confirmed:'已确认', active:'使用中', completed:'已完成', canceled:'已取消' }[s] || s);
</script>

<style scoped>
.status-area { margin-top: 20px; }
.alert-box { padding: 15px; border-radius: 6px; border: 1px solid #ebeef5; }
.alert-box.occupied { background-color: #fdf6ec; border-color: #faecd8; }
.alert-box.self { background-color: #f0f9eb; border-color: #e1f3d8; }
.alert-box.free { background-color: #f4f4f5; border-color: #e9e9eb; text-align: center; padding: 30px; }
.alert-title { font-size: 16px; font-weight: bold; }
.alert-content { margin-top: 10px; line-height: 1.6; color: #606266; }
.takeover-countdown { color: #e6a23c; font-weight: 600; }
.takeover-cooldown { color: #f56c6c; font-weight: 600; }
.action-btn { margin-top: 15px; text-align: right; }
.free .action-btn { text-align: center; margin-top: 20px; }
.free-content { color: #909399; }
.free-icon { font-size: 40px; margin-bottom: 10px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; }
</style>
