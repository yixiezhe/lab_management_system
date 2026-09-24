<template>
  <div style="padding: 20px;">
    <RemoteActiveSession 
      v-if="activeSession" 
      :key="'session-' + componentKey"
      :bookingTarget="activeSession" 
      @session-end="handleSessionEnd" 
    />

    <el-card v-else-if="kioskLoginRequired && !kioskLoginReady" shadow="never">
      <div style="padding: 20px; text-align: center; color: #606266;">
        <p>正在进行设备自动登录，请稍候...</p>
        <p style="font-size: 12px; margin-top: 8px; color: #909399;">若网络抖动，会自动重试。</p>
      </div>
    </el-card>

    <RemoteBookingDashboard 
      v-else 
      :key="'dashboard-' + componentKey"
      :machines="machines"
      :loading="isLoading" 
      @start-session="handleStartSession" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { fetchRdpMachines, deviceLogin } from '@/api/remote_access';
import RemoteBookingDashboard from '../components/remote/RemoteBookingDashboard.vue';
import RemoteActiveSession from '../components/remote/RemoteActiveSession.vue';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const machines = ref([]);
const isLoading = ref(false);
const activeSession = ref(null); 
const pendingHandoffSession = ref(null);
const componentKey = ref(0);

// --- [核心修改] 全自动身份识别 ---
// 兼容端口映射环境的识别逻辑：
// 1. 检查 URL 是否包含 ?kiosk_mode=true (推荐，需要在 AHK 脚本中配置)
// 2. 检查 域名 是否为 localhost/127.0.0.1 (兜底，防止通过内网IP访问时失效)
const isKioskHost = computed(() => {
  // 方式一：URL 参数标记 (最稳妥)
  if (route.query.kiosk_mode === 'true') {
    return true;
  }
  // 方式二：本地环回地址检测
  const hostname = window.location.hostname;
  return hostname === 'localhost' || hostname === '127.0.0.1';
});

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

const isLocalUserMatch = (bookingData) => {
  const currentUser = getCurrentUsername();
  const machineUser = normalizeUser(bookingData?.machine?.username || bookingData?.machine?.user_name || bookingData?.machine?.user || '');
  const machineNameUser = normalizeUser(bookingData?.machine?.name || '');
  return !!(currentUser && ((machineUser && currentUser === machineUser) || (machineNameUser && currentUser === machineNameUser)));
};

const isBoundLocalSession = computed(() =>
  activeSession.value ? isLocalUserMatch(activeSession.value) : false
);

onMounted(() => {
  pendingHandoffSession.value = consumeSessionHandoffFromRoute();
  initDeviceLoginThenLoad();
  startKioskSessionGuard();
  forceCleanDom();
  
  // 调试日志，方便在控制台确认当前被识别为什么身份
  console.log(`[LIMS Identity Check] Is Kiosk Host? ${isKioskHost.value}`);
});

onUnmounted(() => {
  stopKioskSessionGuard();
  if (deviceLoginRetryTimer) {
    clearTimeout(deviceLoginRetryTimer);
    deviceLoginRetryTimer = null;
  }
});

const DEVICE_LOGIN_FLAG = 'LIMS_DEVICE_LOGIN_ATTEMPTED_V1';
const DEVICE_LOGIN_PAYLOAD_KEY = 'LIMS_DEVICE_LOGIN_PAYLOAD_V1';
const REMOTE_SESSION_HANDOFF_PREFIX = 'LIMS_REMOTE_SESSION_HANDOFF_V1:';
const REMOTE_SESSION_HANDOFF_QUERY = 'remote_session_token';
const DEVICE_LOGIN_RETRY_DELAY_MS = 2000;
const DEVICE_LOGIN_MAX_RETRY = 3;
const KIOSK_SESSION_CHECK_INTERVAL_MS = 60 * 1000;
const KIOSK_SESSION_RENEW_AFTER_MS = 6 * 60 * 60 * 1000;
let deviceLoginInProgress = false;
let deviceLoginRetryTimer = null;
let kioskSessionGuardTimer = null;
const kioskLoginReady = ref(true);

const debugKioskLogin = (message, type = 'info', silent = false) => {
  const full = `[设备登录] ${message}`;
  if (type === 'error') {
    console.error(full);
    if (!silent) {
      try {
        ElMessage({ message: full, type, duration: 5000, showClose: true });
      } catch {}
    }
    return;
  }
  console.info(full);
};

const restorePreviousKioskSession = (previousSession) => {
  if (!previousSession?.accessToken && !previousSession?.refreshToken) return;
  authStore.accessToken = previousSession.accessToken || null;
  authStore.refreshToken = previousSession.refreshToken || null;
  authStore.user = previousSession.user || null;
  authStore.loginTimestamp = previousSession.loginTimestamp || 0;

  if (previousSession.accessToken) localStorage.setItem('accessToken', previousSession.accessToken);
  else localStorage.removeItem('accessToken');
  if (previousSession.refreshToken) localStorage.setItem('refreshToken', previousSession.refreshToken);
  else localStorage.removeItem('refreshToken');
  if (previousSession.user) localStorage.setItem('user', JSON.stringify(previousSession.user));
  else localStorage.removeItem('user');
  if (previousSession.loginTimestamp) localStorage.setItem('loginTimestamp', String(previousSession.loginTimestamp));
  else localStorage.removeItem('loginTimestamp');
};

const kioskLoginRequired = computed(() => {
  if (route.query.kiosk_mode !== 'true') return false;
  if (route.query.device_secret || route.query.local_user || route.query.local_machine_id || route.query.local_machine_name) return true;
  try {
    return !!sessionStorage.getItem(DEVICE_LOGIN_PAYLOAD_KEY);
  } catch {
    return false;
  }
});

const initDeviceLoginThenLoad = async () => {
  if (kioskLoginRequired.value) {
    kioskLoginReady.value = false;
  }
  const ok = await tryDeviceLogin();
  // kiosk 设备登录失败时不再继续拉数据，避免 401 触发“会话已过期”
  if (ok === false) return;
  kioskLoginReady.value = true;
  loadMachines();
  ensureKioskDeviceSession();
  startPendingHandoffSession();
};

const tryDeviceLogin = async (options = {}) => {
  const { force = false, silent = false } = options;
  const log = (message, type = 'info') => debugKioskLogin(message, type, silent);
  const kiosk = route.query.kiosk_mode === 'true';
  const machineId = route.query.local_machine_id;
  const machineName = route.query.local_machine_name;
  const localUser = route.query.local_user;
  const secret = route.query.device_secret;
  let storedPayload = null;
  try {
    const raw = sessionStorage.getItem(DEVICE_LOGIN_PAYLOAD_KEY);
    storedPayload = raw ? JSON.parse(raw) : null;
  } catch {}

  if (storedPayload?.device_secret && !secret) {
    log('发现旧缓存 device_secret，当前 URL 未携带密钥，已清理旧缓存');
    storedPayload = { ...storedPayload };
    delete storedPayload.device_secret;
    try { sessionStorage.removeItem(DEVICE_LOGIN_FLAG); } catch {}
  }

  const finalSecret = secret || storedPayload?.device_secret;
  const hasKioskIdentity = !!(localUser || machineId || machineName || storedPayload?.local_user || storedPayload?.machine_id || storedPayload?.machine_name || finalSecret);
  log(`STEP 1 读取 URL: kiosk=${kiosk}, local_user=${localUser || ''}, machine_id=${machineId || ''}, machine_name=${machineName || ''}, has_secret=${!!finalSecret}`);
  if (!kiosk || !hasKioskIdentity) {
    log('非 kiosk 登录场景，跳过设备登录');
    return true;
  }

  if (deviceLoginInProgress) {
    log('已有设备登录请求进行中，跳过重复请求');
    return true;
  }
  if (!force && sessionStorage.getItem(DEVICE_LOGIN_FLAG) === '1' && authStore.accessToken) {
    log('已有设备登录成功标记和 token，直接加载页面');
    return true;
  }
  try { sessionStorage.removeItem(DEVICE_LOGIN_FLAG); } catch {}
  deviceLoginInProgress = true;

  const machinePayload = {};
  if (finalSecret) machinePayload.device_secret = String(finalSecret);
  if (machineId) machinePayload.machine_id = Number(machineId);
  if (machineName) machinePayload.machine_name = String(machineName);
  if (localUser) machinePayload.local_user = String(localUser);
  if (!machinePayload.local_user && storedPayload?.local_user) machinePayload.local_user = storedPayload.local_user;
  if (!machinePayload.machine_id && storedPayload?.machine_id) machinePayload.machine_id = storedPayload.machine_id;
  if (!machinePayload.machine_name && storedPayload?.machine_name) machinePayload.machine_name = storedPayload.machine_name;
  log(`STEP 2 准备请求后端: local_user=${machinePayload.local_user || ''}, machine_id=${machinePayload.machine_id || ''}, machine_name=${machinePayload.machine_name || ''}, has_secret=${!!machinePayload.device_secret}`);

  // 先保存设备登录参数，便于会话中断后自动续登
  try { sessionStorage.setItem(DEVICE_LOGIN_PAYLOAD_KEY, JSON.stringify(machinePayload)); } catch {}

  const previousSession = {
    accessToken: authStore.accessToken,
    refreshToken: authStore.refreshToken,
    user: authStore.user ? JSON.parse(JSON.stringify(authStore.user)) : null,
    loginTimestamp: authStore.loginTimestamp
  };

  // kiosk 模式强制清掉旧 token，避免“会话过期”卡死
  authStore.clearTokensSilently();

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let lastError = null;

  for (let attempt = 1; attempt <= DEVICE_LOGIN_MAX_RETRY; attempt += 1) {
    try {
      log(`STEP 3 正在请求后端设备登录，第 ${attempt} 次`);
      const res = await deviceLogin(machinePayload);
      log('STEP 4 后端设备登录成功，正在保存 token');
      authStore.setTokens(res.data.access, res.data.refresh);
      try {
        await authStore.fetchUser({ silent: true });
        log(`STEP 5 用户信息获取成功: ${authStore.user?.username || ''}`);
      } catch {
        log('STEP 5 用户信息请求失败，但 token 已保存', 'warning');
        // 设备登录成功但用户信息请求失败时，保留 token，避免被误清理
      }
      const now = Date.now();
      authStore.loginTimestamp = now;
      localStorage.setItem('loginTimestamp', String(now));

      sessionStorage.setItem(DEVICE_LOGIN_FLAG, '1');
      if (deviceLoginRetryTimer) {
        clearTimeout(deviceLoginRetryTimer);
        deviceLoginRetryTimer = null;
      }

      // 登录成功后移除敏感参数，避免泄露
      const newQuery = { ...route.query };
      delete newQuery.device_secret;
      router.replace({ query: newQuery }).catch(() => {});
      kioskLoginReady.value = true;
      log('STEP 6 设备自动登录流程完成');
      deviceLoginInProgress = false;
      return true;
    } catch (e) {
      lastError = e;
      const debugStep = e?.response?.data?.debug_step || '';
      const detail = e?.response?.data?.detail || e?.message || '未知错误';
      log(`ERROR 后端设备登录失败: ${detail}${debugStep ? ` (${debugStep})` : ''}`, 'error');
      if (attempt < DEVICE_LOGIN_MAX_RETRY) {
        await sleep(DEVICE_LOGIN_RETRY_DELAY_MS);
      }
    }
  }

  const detail = lastError?.response?.data?.detail || '设备登录失败，请检查 local_user、land设备主机角色或后端配置';
  log(`最终失败: ${detail}`, 'error');
  restorePreviousKioskSession(previousSession);
  sessionStorage.removeItem(DEVICE_LOGIN_FLAG);
  deviceLoginInProgress = false;
  kioskLoginReady.value = false;
  if (!silent && !deviceLoginRetryTimer) {
    deviceLoginRetryTimer = setTimeout(() => {
      deviceLoginRetryTimer = null;
      tryDeviceLogin({ force, silent });
    }, 5000);
  }
  return false;
};

const kioskSessionRenewDue = () => {
  const loginTime = Number(authStore.loginTimestamp || 0);
  return !loginTime || Date.now() - loginTime >= KIOSK_SESSION_RENEW_AFTER_MS;
};

const ensureKioskDeviceSession = async () => {
  if (!kioskLoginRequired.value || deviceLoginInProgress) return;
  const needsLogin = !authStore.accessToken || !authStore.refreshToken || !authStore.user || kioskSessionRenewDue();
  if (!needsLogin) return;

  const hadReadyPage = kioskLoginReady.value;
  if (!authStore.accessToken || !authStore.user) {
    kioskLoginReady.value = false;
  }

  const ok = await tryDeviceLogin({ force: true, silent: true });
  if (ok) {
    kioskLoginReady.value = true;
    if (!activeSession.value) loadMachines();
  } else if (hadReadyPage && authStore.accessToken) {
    kioskLoginReady.value = true;
  }
};

const startKioskSessionGuard = () => {
  stopKioskSessionGuard();
  if (!kioskLoginRequired.value) return;
  kioskSessionGuardTimer = setInterval(ensureKioskDeviceSession, KIOSK_SESSION_CHECK_INTERVAL_MS);
};

const stopKioskSessionGuard = () => {
  if (!kioskSessionGuardTimer) return;
  clearInterval(kioskSessionGuardTimer);
  kioskSessionGuardTimer = null;
};

const loadMachines = async () => {
  isLoading.value = true;
  try {
    const res = await fetchRdpMachines();
    const list = res.data.results || res.data;
    // 预约页只显示启用中的主机（即使管理员账号也隐藏已停用）
    machines.value = (list || []).filter(m => m?.is_active !== false);
  } catch (e) {
    console.error("Failed to load machines", e);
  } finally {
    isLoading.value = false;
  }
};

const consumeSessionHandoffFromRoute = () => {
  const tokenParam = route.query?.[REMOTE_SESSION_HANDOFF_QUERY];
  const token = Array.isArray(tokenParam) ? tokenParam[0] : tokenParam;
  if (!token) return null;

  try {
    const storageKey = `${REMOTE_SESSION_HANDOFF_PREFIX}${token}`;
    const raw = localStorage.getItem(storageKey);
    localStorage.removeItem(storageKey);

    const cleanQuery = { ...route.query };
    delete cleanQuery[REMOTE_SESSION_HANDOFF_QUERY];
    router.replace({ query: cleanQuery }).catch(() => {});

    if (!raw) return null;
    const payload = JSON.parse(raw);
    if (!payload?.bookingData?.id || !payload?.bookingData?.machine) return null;
    return payload.bookingData;
  } catch {
    return null;
  }
};

const startPendingHandoffSession = () => {
  if (!pendingHandoffSession.value || activeSession.value) return;
  activeSession.value = pendingHandoffSession.value;
  pendingHandoffSession.value = null;
  componentKey.value++;
};

const isSameSessionTarget = (a, b) => {
  if (!a || !b) return false;
  const aid = Number(a.id);
  const bid = Number(b.id);
  if (Number.isFinite(aid) && Number.isFinite(bid) && aid === bid) return true;

  const amid = Number(a.machine?.id);
  const bmid = Number(b.machine?.id);
  return Number.isFinite(amid) && Number.isFinite(bmid) && amid === bmid;
};

const openSessionInNewTab = (bookingData) => {
  const token = `${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const storageKey = `${REMOTE_SESSION_HANDOFF_PREFIX}${token}`;
  try {
    localStorage.setItem(storageKey, JSON.stringify({
      createdAt: Date.now(),
      bookingData
    }));
  } catch {
    ElMessage.error('打开新连接失败：浏览器无法暂存连接信息');
    return false;
  }

  const url = new URL(window.location.href);
  url.searchParams.set(REMOTE_SESSION_HANDOFF_QUERY, token);
  const opened = window.open(url.toString(), '_blank');
  if (!opened) {
    localStorage.removeItem(storageKey);
    ElMessage.warning('浏览器拦截了新标签页，请允许弹窗后重试');
    return false;
  }

  ElMessage.success('新远程连接已在新标签页打开，当前连接会保留');
  return true;
};

const handleStartSession = (bookingData) => {
  // 只有 URL 明确带了本机 ID 时才用 ID 强制远程；用户名模式不再依赖机器 ID。
  try {
    const rawLocalId = route.query.local_machine_id;
    const hasLocalId = rawLocalId !== undefined && rawLocalId !== null && String(rawLocalId).trim() !== '';
    const localId = Number(rawLocalId);
    const targetId = Number(bookingData?.machine?.id);
    if (hasLocalId && Number.isFinite(localId) && Number.isFinite(targetId) && localId !== targetId) {
      bookingData = { ...bookingData, forceRemote: true };
    }
  } catch {}

  if (activeSession.value) {
    if (isSameSessionTarget(activeSession.value, bookingData)) {
      ElMessage.info('该主机连接已在当前标签页打开');
      return;
    }
    openSessionInNewTab(bookingData);
    return;
  }

  // 远程用户正常进入控制模式
  activeSession.value = bookingData;
};

// --- 强制环境重置 (防止样式残留) ---
const forceCleanDom = () => {
  document.body.classList.remove('el-popup-parent--hidden');
  document.body.style.overflow = '';
  document.body.style.paddingRight = '';
  document.body.style.pointerEvents = '';
  
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {});
  }
};

const handleSessionEnd = () => {
  activeSession.value = null;
  componentKey.value++; 
  nextTick(() => {
    forceCleanDom();
    loadMachines();
  });
};
</script>
