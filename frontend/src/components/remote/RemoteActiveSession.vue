<template>
  <Teleport to="body">
    <div class="remote-console" v-if="sessionInfo">
      <div class="console-bar">
        <div class="left-info">
          <span class="status-dot"></span>
          <span>正在连接: {{ sessionInfo.machineName }}</span>
          <el-divider direction="vertical" />
          <span>
            剩余时间:
            <strong :class="{ 'text-danger': remainingSeconds < 300 }">{{ formattedTime }}</strong>
          </span>
        </div>

        <div class="center-actions">
          <span v-if="isLocalMode" style="color: #67c23a; font-size: 14px; font-weight: bold;">
            <el-icon style="vertical-align: middle; margin-right: 4px"><Monitor /></el-icon>
            [本机模式] 请点击屏幕顶部红色按钮结束会话
          </span>
          <el-tooltip v-else content="发送本机剪贴板 (Ctrl+V)" placement="bottom">
            <el-button type="primary" link @click="syncLocalClipboardToRemote">
              <el-icon style="margin-right: 5px"><CopyDocument /></el-icon> 发送本机剪贴板
            </el-button>
          </el-tooltip>
        </div>

        <div class="right-actions">
          <el-tooltip v-if="!isLocalMode" content="Win键/Alt+Tab需全屏" placement="bottom">
            <el-button type="info" size="small" @click="toggleFullscreen" plain>
              <el-icon><FullScreen /></el-icon> {{ isFullscreen ? '退出全屏' : '全屏模式' }}
            </el-button>
          </el-tooltip>

          <el-button type="danger" size="small" @click="handleDisconnect(false)">
            <el-icon><SwitchButton /></el-icon> 主动登出
          </el-button>
        </div>
      </div>

      <div v-if="takeoverRequest" class="takeover-alert" role="alert">
        <div class="takeover-icon">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="takeover-copy">
          <div class="takeover-title">紧急使用申请</div>
          <div class="takeover-message">
            用户 <strong>{{ takeoverRequest.applicant_name }}</strong> 请求接管当前主机
          </div>
        </div>
        <div class="takeover-countdown">
          <span>{{ takeoverCountdown }}</span>
          <small>秒</small>
        </div>
        <div class="takeover-actions">
          <el-button size="large" type="primary" @click="handleApproveTakeover">
            同意
          </el-button>
          <el-button size="large" plain @click="handleRejectTakeover">拒绝</el-button>
        </div>
      </div>

      <div
        class="iframe-container"
        @pointerdown="!isLocalMode && scheduleGuacamoleFocus('remote_pointer', [0, 80, 180])"
        @click="!isLocalMode && syncLocalClipboardToRemote()"
      >
        <iframe
          v-if="!isLocalMode"
          :src="guacamoleUrl"
          frameborder="0"
          class="guacamole-frame"
          ref="guacFrame"
          tabindex="0"
          @load="scheduleGuacamoleFocus('iframe_load', [120, 400, 900])"
        ></iframe>

        <div v-else class="local-placeholder">
          <div class="local-content">
            <el-icon class="local-icon"><Monitor /></el-icon>
            <h2>正在使用本机桌面...</h2>
            <p>浏览器已最小化，请直接操作本机。</p>
            <p style="color: #e6a23c; margin-top: 20px;">使用完毕后，请点击屏幕顶部的红色按钮“结束会话”</p>

            <div style="margin-top: 30px;">
              <el-button type="info" plain size="small" @click="sendAhkSignal('LIMS_UNLOCK_LOCAL_SESSION_KEY_888')">
                如果浏览器误弹出，点此再次最小化
              </el-button>
            </div>

            <!-- 兜底：如果误进本机模式（例如你在别的电脑打开了 kiosk 链接），一键切回远程连接 -->
            <div style="margin-top: 12px;">
              <el-button type="warning" plain size="small" @click="forceSwitchToRemote">
                我在其他电脑上，切换为远程连接
              </el-button>
            </div>

          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import {
  connectRdpBooking,
  disconnectRdpBooking,
  checkBookingStatus,
  approveTakeover,
  rejectTakeover,
  deviceLogin
} from '@/api/remote_access';
import { useAuthStore } from '@/stores/auth';
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus';
import { Warning, FullScreen, Monitor, CopyDocument, SwitchButton } from '@element-plus/icons-vue';

const props = defineProps(['bookingTarget']);
const emit = defineEmits(['session-end']);
const authStore = useAuthStore();
const route = useRoute();

// --- 状态定义 ---
const sessionInfo = ref(null);
const isLocalMode = ref(false);
const guacamoleUrl = ref('');
const remainingSeconds = ref(0);
const heartbeatTimer = ref(null);
const localCountdownTimer = ref(null);
const takeoverRequest = ref(null);
const takeoverCountdown = ref(60);
const isFullscreen = ref(false);
const guacFrame = ref(null);
const pendingClipboardText = ref('');
const hasPendingClipboardSync = ref(false);
const isComponentMounted = ref(true);
const isEndingSession = ref(false);
const localWasHidden = ref(false);
const localAutoLogoutArmed = ref(false);
const localExitRequested = ref(false);
let reauthPromise = null;
const localUnlockTimers = [];
const guacFocusTimers = [];

const clearLocalUnlockTimers = () => {
  while (localUnlockTimers.length) {
    clearTimeout(localUnlockTimers.pop());
  }
};

const clearGuacamoleFocusTimers = () => {
  while (guacFocusTimers.length) {
    clearTimeout(guacFocusTimers.pop());
  }
};

const scheduleLocalUnlockSignal = (delay) => {
  const timer = setTimeout(() => {
    const idx = localUnlockTimers.indexOf(timer);
    if (idx >= 0) localUnlockTimers.splice(idx, 1);
    if (!isLocalMode.value || localExitRequested.value || isEndingSession.value) return;
    sendAhkSignal('LIMS_UNLOCK_LOCAL_SESSION_KEY_888');
  }, delay);
  localUnlockTimers.push(timer);
};

// 防重复唤醒
const hasAlertedTakeover = ref(false);

// 仅用于“误判修复按钮”：如果你之前用 kiosk_mode 做区分，点按钮可清理
const KIOSK_MODE_SESSION_KEY = 'LIMS_KIOSK_MODE_SESSION_V1';
const DEVICE_LOGIN_PAYLOAD_KEY = 'LIMS_DEVICE_LOGIN_PAYLOAD_V1';
const TAKEOVER_WAKE_TITLE = '🛑LIMS_WAKE_UP_REQ🛑';
const AHK_MAGIC_SIGNALS = new Set([
  'LIMS_UNLOCK_LOCAL_SESSION_KEY_888',
  'LIMS_FORCE_LOCK_NOW',
  'LIMS_ALERT_TAKEOVER_PENDING',
  'LIMS_REMOTE_SESSION_ACTIVE',
  'LIMS_REMOTE_SESSION_ENDED',
  TAKEOVER_WAKE_TITLE
]);
const getSafeDocumentTitle = () => {
  const title = document.title || '实验室管理系统';
  return AHK_MAGIC_SIGNALS.has(title) ? '实验室管理系统' : title;
};

const syncKioskModeFromUrl = () => {
  try {
    const params = new URLSearchParams(window.location.search || "");
    const v = params.get('kiosk_mode');
    if (v === 'true') {
      sessionStorage.setItem(KIOSK_MODE_SESSION_KEY, 'true');
    }
  } catch {}
};

const normalizeUser = (u) => {
  const s = (u || '').trim().toLowerCase();
  if (!s) return '';
  if (s.includes('\\')) return s.split('\\').pop();
  if (s.includes('@')) return s.split('@')[0];
  return s;
};

const getCurrentUsername = () => {
  const direct = authStore.user?.username || authStore.user?.user_name || authStore.user?.account;
  if (direct) return normalizeUser(direct);

  // 兜底：从 localStorage / sessionStorage 中读取当前用户。
  const keys = ['user', 'auth_user', 'currentUser', 'userInfo', 'profile', 'auth'];
  const stores = [localStorage, sessionStorage];
  for (const store of stores) {
    for (const k of keys) {
      try {
        const v = store.getItem(k);
        if (!v) continue;
        if (v.startsWith('{')) {
          const obj = JSON.parse(v);
          const cand = obj.username || obj.user_name || obj.account;
          if (cand) return normalizeUser(cand);
        } else if (v.length < 64) {
          return normalizeUser(v);
        }
      } catch {}
    }
  }
  return '';
};

const formattedTime = computed(() => {
  const s = Math.max(0, Number(remainingSeconds.value || 0));
  const hh = Math.floor(s / 3600).toString().padStart(2,'0');
  const mm = Math.floor((s % 3600) / 60).toString().padStart(2,'0');
  const ss = Math.floor(s % 60).toString().padStart(2,'0');
  return `${hh}:${mm}:${ss}`;
});

const getTakeoverRemainingSeconds = (payload) => {
  const raw = payload?.remaining_seconds;
  if (Number.isFinite(Number(raw))) return Math.max(0, Math.ceil(Number(raw)));
  const fallback = payload?.timeout_seconds;
  if (Number.isFinite(Number(fallback))) return Math.max(0, Math.ceil(Number(fallback)));
  return 60;
};

const focusGuacamoleFrame = (reason = 'focus') => {
  if (!isComponentMounted.value || isLocalMode.value || !guacFrame.value) return false;

  try {
    guacFrame.value.setAttribute('tabindex', '0');
    guacFrame.value.focus({ preventScroll: true });
  } catch {
    try { guacFrame.value.focus(); } catch {}
  }

  try {
    guacFrame.value.contentWindow?.postMessage({
      type: 'LIMS_GUAC_FOCUS_KEYBOARD',
      reason,
      ts: Date.now()
    }, '*');
  } catch {}

  return document.activeElement === guacFrame.value;
};

const scheduleGuacamoleFocus = (reason = 'focus', delays = [0, 80, 180, 350]) => {
  if (isLocalMode.value) return;
  for (const delay of delays) {
    const timer = setTimeout(() => {
      const idx = guacFocusTimers.indexOf(timer);
      if (idx >= 0) guacFocusTimers.splice(idx, 1);
      focusGuacamoleFrame(reason);
    }, delay);
    guacFocusTimers.push(timer);
  }
};

const onFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement;
  scheduleGuacamoleFocus(isFullscreen.value ? 'fullscreen_enter' : 'fullscreen_exit', [60, 160, 320, 650]);
};
const onVisibilityChange = () => {
  if (!isLocalMode.value) return;
  if (document.hidden) {
    localWasHidden.value = true;
    return;
  }
  if (localAutoLogoutArmed.value && localWasHidden.value && localExitRequested.value) {
    localAutoLogoutArmed.value = false;
    handleDisconnect(true);
  }
};
const isAhkEndSessionHotkey = (e) => (
  e.ctrlKey && (e.key === 'F9' || e.code === 'F9' || e.keyCode === 120 || e.which === 120)
);

const onGlobalKeydown = (e) => {
  handleUserGestureForClipboardSync(e);
  // Ctrl+F9：接收 AHK 发送的“结束会话”信号。捕获阶段处理，避免焦点在页面控件上时丢信号。
  if (isAhkEndSessionHotkey(e) && isLocalMode.value) {
    e.preventDefault?.();
    e.stopPropagation?.();
    console.log("收到 AHK 登出信号");
    localExitRequested.value = true;
    handleDisconnect(true);
  }
};

onMounted(() => {
  isComponentMounted.value = true;

  syncKioskModeFromUrl();
  initializeSession();

  document.addEventListener('fullscreenchange', onFullscreenChange);
  document.addEventListener('visibilitychange', onVisibilityChange);
  window.addEventListener('message', handleIframeMessage);
  document.addEventListener('keydown', onGlobalKeydown, true);
});

const getLocalMachineId = () => {
  const qid = route.query?.local_machine_id;
  if (qid) {
    const n = Number(qid);
    if (!Number.isNaN(n)) return n;
  }
  try {
    const raw = sessionStorage.getItem(DEVICE_LOGIN_PAYLOAD_KEY);
    if (!raw) return null;
    const payload = JSON.parse(raw);
    const pid = payload?.machine_id;
    const n = Number(pid);
    if (!Number.isNaN(n)) return n;
  } catch {}
  return null;
};

const getLocalMachineName = () => {
  const qname = route.query?.local_machine_name;
  if (qname && String(qname).trim()) return String(qname).trim().toLowerCase();
  try {
    const raw = sessionStorage.getItem(DEVICE_LOGIN_PAYLOAD_KEY);
    if (!raw) return '';
    const payload = JSON.parse(raw);
    const name = payload?.machine_name;
    return name ? String(name).trim().toLowerCase() : '';
  } catch {
    return '';
  }
};

const isAuthError = (e) => {
  const status = e?.response?.status;
  return status === 401 || status === 403;
};

const loadDeviceLoginPayload = () => {
  try {
    const raw = sessionStorage.getItem(DEVICE_LOGIN_PAYLOAD_KEY);
    if (!raw) return null;
    const payload = JSON.parse(raw);
    if (!payload || !(payload.device_secret || payload.local_user || payload.machine_id || payload.machine_name)) return null;
    return payload;
  } catch {
    return null;
  }
};

const reAuthWithDeviceLogin = async () => {
  const payload = loadDeviceLoginPayload();
  if (!payload) return false;
  if (reauthPromise) return reauthPromise;
  reauthPromise = (async () => {
    try {
      const res = await deviceLogin(payload);
      authStore.setTokens(res.data.access, res.data.refresh);
      await authStore.fetchUser();
      return true;
    } catch {
      return false;
    } finally {
      reauthPromise = null;
    }
  })();
  return reauthPromise;
};

onUnmounted(() => {
  isComponentMounted.value = false;
  stopHeartbeat();
  clearLocalUnlockTimers();
  clearGuacamoleFocusTimers();

  document.removeEventListener('fullscreenchange', onFullscreenChange);
  document.removeEventListener('visibilitychange', onVisibilityChange);
  window.removeEventListener('message', handleIframeMessage);
  document.removeEventListener('keydown', onGlobalKeydown, true);

  requestAnimationFrame(() => {
    document.body.style.cssText = "";
    document.body.classList.remove('el-popup-parent--hidden');
    document.querySelectorAll('.v-modal').forEach(el => el.remove());
  });

  if (document.fullscreenElement) {
    document.exitFullscreen().catch(()=>{});
  }
});

// ------------------------------------------------------------
// ✅ 新增：用 AHK 的真实动作来确认“本机模式”
// 做法：发解锁暗号 -> 监听 visibilitychange (页面被最小化会变 hidden)
// - 700ms 内变 hidden -> 说明 AHK 生效 -> 本机模式
// - 否则 -> 远程模式
// ------------------------------------------------------------
const tryConfirmLocalByAhk = async () => {
  const TIMEOUT_MS = 700;

  return new Promise((resolve) => {
    let done = false;

    const finish = (ok) => {
      if (done) return;
      done = true;
      try { document.removeEventListener('visibilitychange', onVis); } catch {}
      resolve(ok);
    };

    const onVis = () => {
      // AHK 最小化 Edge 后，页面会 hidden，这是最可靠的“本机确认”
      if (document.hidden) finish(true);
    };

    // 监听
    document.addEventListener('visibilitychange', onVis);

    // 触发解锁（即使 copy 失败也不立刻判失败，还是等 timeout）
    try { sendAhkCommand('LIMS_UNLOCK_LOCAL_SESSION_KEY_888'); } catch {}

    // 如果已经是 hidden（极少情况），直接确认
    if (document.hidden) {
      finish(true);
      return;
    }

    // 超时判失败
    setTimeout(() => finish(false), TIMEOUT_MS);
  });
};

// --- 初始化连接 ---
const initializeSession = async () => {
  const booking = props.bookingTarget;
  if (!booking) return;

  try {
    const currentUser = getCurrentUsername();
    const machineUser = normalizeUser(booking.machine?.username || booking.machine?.user_name || booking.machine?.user || '');
    const machineNameUser = normalizeUser(booking.machine?.name || '');
    const userLooksLocal = !!(currentUser && ((machineUser && currentUser === machineUser) || (machineNameUser && currentUser === machineNameUser)));

    const localMachineId = getLocalMachineId();
    const localMachineName = getLocalMachineName();
    const bookingMachineId = Number(booking.machine?.id);
    const bookingMachineName = String(booking.machine?.name || '').trim().toLowerCase();

    const idMatch = Number.isFinite(localMachineId) && Number.isFinite(bookingMachineId) && localMachineId === bookingMachineId;
    const nameMatch = localMachineName && bookingMachineName && localMachineName === bookingMachineName;
    const isTargetLocal = idMatch || nameMatch || userLooksLocal;
    const forceRemote = booking.forceRemote === true ? true : false;

    // 本机判定：URL 绑定主机匹配，或系统登录用户名等于目标主机 Windows 用户名/主机名。
    // 命中时绝不退化到 Guacamole，否则自连会触发 RDP 连接冲突。
    let isLocal = false;
    if (!forceRemote && isTargetLocal && userLooksLocal) {
      isLocal = await tryConfirmLocalByAhk();
      if (!isComponentMounted.value) return;

      // 本机账号连本机时，绝不能退化成 Guacamole 远程画面。
      // 即使短时间内 visibility 事件没回来，也进入本机占位并继续发 AHK 最小化信号。
      if (!isLocal && isTargetLocal && userLooksLocal) {
        sendAhkSignal('LIMS_UNLOCK_LOCAL_SESSION_KEY_888');
        isLocal = true;
      }
    }

    isLocalMode.value = isLocal;
    sessionInfo.value = { machineName: booking.machine.name + (isLocal ? " (本机)" : "") };

    if (isLocal) {
      // 本机模式：不调用 connectRdpBooking，避免真的 RDP 把自己挤到锁屏
      ElMessage.success({ message: '已进入本机模式：浏览器将最小化，请直接操作桌面。', duration: 3000 });
      // 页面切到本机占位状态后再补发最小化信号，避免渲染/全屏状态变化把浏览器重新顶出来。
      clearLocalUnlockTimers();
      scheduleLocalUnlockSignal(300);
      scheduleLocalUnlockSignal(1200);
      localAutoLogoutArmed.value = true;
      localWasHidden.value = document.hidden;
      localExitRequested.value = false;
      startHeartbeat(booking.id);
      return;
    }

    // 远程模式：正常连接 Guacamole
    document.documentElement.requestFullscreen?.().catch(()=>{});
    const res = await connectRdpBooking(booking.id);
    if (!isComponentMounted.value) return;
    guacamoleUrl.value = res.data.connection_url;
    scheduleGuacamoleFocus('connect_ready', [300, 900, 1600]);
    startHeartbeat(booking.id);
  } catch (err) {
    if (err !== 'cancel' && isComponentMounted.value) {
      console.error(err);
      const detail = err?.response?.data?.detail || err?.message || '连接初始化失败';
      ElMessage.error(detail);
      emit('session-end');
    }
  }
};

// 兜底：强制切到远程
const forceSwitchToRemote = async () => {
  const booking = props.bookingTarget;
  if (!booking) return;

  try { sessionStorage.removeItem(KIOSK_MODE_SESSION_KEY); } catch {}

  stopHeartbeat();
  clearLocalUnlockTimers();
  isLocalMode.value = false;
  localAutoLogoutArmed.value = false;
  localWasHidden.value = false;
  localExitRequested.value = false;
  sessionInfo.value = { machineName: booking.machine.name };

  try {
    document.documentElement.requestFullscreen?.().catch(()=>{});
    const res = await connectRdpBooking(booking.id);
    if (!isComponentMounted.value) return;
    guacamoleUrl.value = res.data.connection_url;
    scheduleGuacamoleFocus('force_remote_ready', [300, 900, 1600]);
    startHeartbeat(booking.id);
    ElMessage.success('已切换为远程连接模式');
  } catch (e) {
    console.error(e);
    ElMessage.error('切换失败：请返回上一页重新进入');
  }
};

// --- 工具函数：向剪贴板写入 AHK 暗号 ---
const sendAhkCommand = (cmd) => {
  try {
    const ta = document.createElement("textarea");
    ta.value = cmd;
    ta.style.position = "fixed"; ta.style.left = "-9999px"; ta.style.top = "0";
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    const successful = document.execCommand('copy');
    document.body.removeChild(ta);
    return successful;
  } catch {
    return false;
  }
};

const sendAhkTitleSignal = (cmd, holdMs = 3000) => {
  const originalTitle = getSafeDocumentTitle();
  try {
    document.title = cmd;
    setTimeout(() => {
      if (document.title === cmd) {
        document.title = originalTitle;
      }
    }, holdMs);
    return true;
  } catch {
    return false;
  }
};

const sendAhkSignal = (cmd) => {
  const ok = sendAhkCommand(cmd);

  // 页面 hidden/minimized 时剪贴板写入可能失败，用标题做 AHK 兜底通道。
  sendAhkTitleSignal(cmd, 3000);

  return ok;
};

const sendTakeoverWakeSignal = () => {
  const ok = sendAhkCommand('LIMS_ALERT_TAKEOVER_PENDING');
  // 保持旧版标题唤醒暗号，兼容 land1/land3 旧脚本；新版 a 脚本也会识别。
  sendAhkTitleSignal(TAKEOVER_WAKE_TITLE, 2500);
  return ok;
};

// --- 心跳检测 ---
const startHeartbeat = (id) => {
  stopHeartbeat();
  hasAlertedTakeover.value = false;
  checkStatus(id);
  heartbeatTimer.value = setInterval(() => checkStatus(id), 2000);
  localCountdownTimer.value = setInterval(() => {
    if (remainingSeconds.value > 0) {
      remainingSeconds.value = Math.max(0, remainingSeconds.value - 1);
    }
    if (takeoverRequest.value && takeoverCountdown.value > 0) {
      takeoverCountdown.value = Math.max(0, takeoverCountdown.value - 1);
    }
    if ((remainingSeconds.value === 0 || (takeoverRequest.value && takeoverCountdown.value === 0)) && !isEndingSession.value) {
      checkStatus(id);
    }
  }, 1000);
};

const stopHeartbeat = () => {
  if (heartbeatTimer.value) {
    clearInterval(heartbeatTimer.value);
    heartbeatTimer.value = null;
  }
  if (localCountdownTimer.value) {
    clearInterval(localCountdownTimer.value);
    localCountdownTimer.value = null;
  }
};

const checkStatus = async (id) => {
  if (!isComponentMounted.value) return;
  try {
    const res = await checkBookingStatus(id);
    if (!isComponentMounted.value) return;
    const data = res.data;

    if (data.status === 'force_disconnected') {
      stopHeartbeat();
      if (isLocalMode.value) sendAhkSignal("LIMS_FORCE_LOCK_NOW");
      else if (document.fullscreenElement) document.exitFullscreen();
      try { emit('session-end'); } catch(e){}
      ElMessageBox.alert(data.message || '会话已结束', '连接断开');
      return;
    }

    // 插队：标题信号唤醒
    if (data.takeover_request?.has_request) {
      takeoverRequest.value = data.takeover_request;
      takeoverCountdown.value = getTakeoverRemainingSeconds(data.takeover_request);

      if (isLocalMode.value && !hasAlertedTakeover.value) {
        hasAlertedTakeover.value = true;
        // 用 AHK 真实监听的暗号唤醒本机浏览器，显示插队处理条。
        sendTakeoverWakeSignal();
      }
    } else {
      takeoverRequest.value = null;
      hasAlertedTakeover.value = false;
    }

    remainingSeconds.value = Math.max(0, Math.floor(Number(data.remaining_seconds || 0)));
  } catch (e) {
    if (isAuthError(e)) {
      const ok = await reAuthWithDeviceLogin();
      if (ok) {
        // 重新认证后再试一次
        try {
          const retryRes = await checkBookingStatus(id);
          if (!isComponentMounted.value) return;
          const data = retryRes.data;
          if (data.status === 'force_disconnected') {
            stopHeartbeat();
            if (isLocalMode.value) sendAhkSignal("LIMS_FORCE_LOCK_NOW");
            else if (document.fullscreenElement) document.exitFullscreen();
            try { emit('session-end'); } catch(e){}
            ElMessageBox.alert(data.message || '会话已结束', '连接断开');
            return;
          }
          if (data.takeover_request?.has_request) {
            takeoverRequest.value = data.takeover_request;
            takeoverCountdown.value = getTakeoverRemainingSeconds(data.takeover_request);
            if (isLocalMode.value && !hasAlertedTakeover.value) {
              hasAlertedTakeover.value = true;
              sendTakeoverWakeSignal();
            }
          } else {
            takeoverRequest.value = null;
            hasAlertedTakeover.value = false;
          }
          remainingSeconds.value = Math.max(0, Math.floor(Number(data.remaining_seconds || 0)));
        } catch {
          // 仍失败则忽略，避免抖动时结束会话
        }
      }
    }
    // 心跳失败不立刻结束，避免网络抖动
  }
};

// --- 退出 ---
const handleDisconnect = async (skipConfirm) => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const safeDisconnect = async () => {
    if (!props.bookingTarget) return;
    let lastError = null;

    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        await disconnectRdpBooking(props.bookingTarget.id);
        return true;
      } catch (e) {
        lastError = e;
        if (isAuthError(e)) {
          const ok = await reAuthWithDeviceLogin();
          if (ok) {
            await disconnectRdpBooking(props.bookingTarget.id);
            return true;
          }
        }
        if (attempt < 3) await sleep(700);
      }
    }
    throw lastError;
  };

  const performLogout = async () => {
    if (isEndingSession.value) return;
    isEndingSession.value = true;
    let disconnectConfirmed = false;
    try {
      if (isLocalMode.value) {
        localExitRequested.value = true;
        clearLocalUnlockTimers();
        sendAhkCommand("LIMS_FORCE_LOCK_NOW");
      }
      if (document.fullscreenElement) await document.exitFullscreen().catch(()=>{});
      if (props.bookingTarget) {
        try {
          disconnectConfirmed = await safeDisconnect();
        } catch {
          ElMessage.warning('登出请求未确认，稍后会自动结束');
        }
      }
    } finally {
      emit('session-end');
      if (disconnectConfirmed || !props.bookingTarget) ElMessage.success('已登出');
      localExitRequested.value = false;
      isEndingSession.value = false;
    }
  };

  if (skipConfirm) {
    performLogout();
  } else {
    try {
      await ElMessageBox.confirm('确定结束会话？', '提示', { type: 'warning' });
      performLogout();
    } catch (err) {
      if (err !== 'cancel' && window.confirm("确定结束会话？")) performLogout();
    }
  }
};

const handleApproveTakeover = async () => {
  if (isLocalMode.value) sendAhkSignal("LIMS_FORCE_LOCK_NOW");
  await approveTakeover(props.bookingTarget.id);
  emit('session-end');
};

const handleRejectTakeover = async () => {
  await rejectTakeover(props.bookingTarget.id);
  takeoverRequest.value = null;
  hasAlertedTakeover.value = false;
};

const toggleFullscreen = async () => {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await document.documentElement.requestFullscreen?.();
    }
  } finally {
    scheduleGuacamoleFocus('toolbar_fullscreen_toggle', [80, 180, 350, 700]);
  }
};

// --- 剪贴板同步 ---
const syncLocalClipboardToRemote = async () => {
  if (!guacFrame.value) return;
  try {
    const text = await navigator.clipboard.readText();
    if (text) guacFrame.value.contentWindow.postMessage({ type: 'SEND_TO_REMOTE_CLIPBOARD', text }, '*');
  } catch {
    console.warn("Clipboard failed");
  } finally {
    scheduleGuacamoleFocus('clipboard_sync', [0, 120, 260]);
  }
};

const handleIframeMessage = (e) => {
  if (!isComponentMounted.value) return;
  if (e.data?.type === 'REMOTE_CLIPBOARD') {
    pendingClipboardText.value = e.data.text;
    hasPendingClipboardSync.value = true;
  }
  if (e.data?.type === 'REMOTE_FILE_START') {
    ElNotification({ title:'文件传输', message: e.data.filename, type:'success' });
  }
};

const handleUserGestureForClipboardSync = async () => {
  if(!hasPendingClipboardSync.value) return;
  try {
    await navigator.clipboard.writeText(pendingClipboardText.value);
    ElMessage.success('剪贴板已同步');
  } catch {}
  hasPendingClipboardSync.value = false;
};
</script>

<style scoped>
.remote-console {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: #000;
  z-index: 1200;
  display: flex;
  flex-direction: column;
  pointer-events: auto;
}
.console-bar {
  height: 40px;
  flex-shrink: 0;
  background: #2c3e50;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.iframe-container {
  flex: 1;
  width: 100%;
  height: calc(100vh - 40px);
  overflow: hidden;
  background: #000;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
}
.guacamole-frame {
  width: 100%;
  height: 100%;
  border: none;
  object-fit: contain;
  outline: none;
}
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  background: #67c23a;
  border-radius: 50%;
  margin-right: 8px;
}
.takeover-alert {
  position: absolute;
  top: 56px;
  left: 50%;
  z-index: 6;
  width: min(760px, calc(100vw - 48px));
  min-height: 78px;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.97);
  color: #1f2d3d;
  padding: 14px 16px;
  border: 1px solid rgba(230, 162, 60, 0.72);
  border-left: 6px solid #e6a23c;
  border-radius: 8px;
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.32);
  display: flex;
  align-items: center;
  gap: 14px;
  animation: takeoverIn 180ms ease-out;
}
.takeover-icon {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  border-radius: 50%;
  color: #fff;
  background: #e6a23c;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}
.takeover-copy {
  min-width: 0;
  flex: 1;
}
.takeover-title {
  font-size: 16px;
  line-height: 22px;
  font-weight: 700;
  color: #1f2d3d;
}
.takeover-message {
  margin-top: 2px;
  font-size: 14px;
  line-height: 20px;
  color: #52616f;
  overflow-wrap: anywhere;
}
.takeover-message strong {
  color: #1f2d3d;
}
.takeover-countdown {
  width: 76px;
  min-height: 50px;
  flex: 0 0 76px;
  border-radius: 6px;
  background: #fff7e8;
  border: 1px solid #f3d19e;
  color: #b88230;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
}
.takeover-countdown span {
  font-size: 26px;
  line-height: 48px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.takeover-countdown small {
  font-size: 12px;
  font-weight: 600;
}
.takeover-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
@keyframes takeoverIn {
  from { transform: translate(-50%, -10px); opacity: 0; }
  to { transform: translate(-50%, 0); opacity: 1; }
}
.text-danger { color: #f56c6c; font-weight: bold; }
.center-actions { display: flex; gap: 10px; }
.local-placeholder {
  color: #fff;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
.local-content { text-align: center; animation: fadeIn 1s; }
.local-icon { font-size: 80px; color: #409EFF; margin-bottom: 20px; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 720px) {
  .takeover-alert {
    top: 48px;
    width: calc(100vw - 24px);
    align-items: stretch;
    flex-wrap: wrap;
    gap: 10px;
  }
  .takeover-copy {
    flex: 1 1 calc(100% - 58px);
  }
  .takeover-countdown {
    flex: 0 0 72px;
  }
  .takeover-actions {
    flex: 1 1 auto;
    justify-content: flex-end;
  }
}
</style>
