<template>
  <div class="common-layout">
    <el-container style="height: 100vh;">
      <el-aside
        width="220px"
        class="aside"
        :class="{ 'floating-aside': isFullScreen }"
        v-if="showAside"
      >
        <div class="sidebar-header">
          <img src="/logo.svg" alt="Logo" class="sidebar-logo">
          <span>实验室管理</span>
        </div>

        <el-menu :default-active="$route.path" class="el-menu-vertical-demo" router>
          <el-menu-item index="/" v-if="!isLandHost">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </el-menu-item>

          <el-menu-item index="/project-management" v-if="!isLandHost && authStore.isProjectAdmin">
            <el-icon><Collection /></el-icon>
            <span>项目管理</span>
          </el-menu-item>

          <el-menu-item index="/announcement-management" v-if="!isLandHost && authStore.isAnnouncementAdmin">
            <el-icon><ChatLineSquare /></el-icon>
            <span>公告管理</span>
          </el-menu-item>

          <el-menu-item index="/group-affairs" v-if="!isLandHost && authStore.canAccessGroupAffairs">
            <el-icon><User /></el-icon>
            <span>小组事务</span>
          </el-menu-item>

          <el-menu-item index="/procurement/request" v-if="!isLandHost">
            <el-icon><ShoppingCart /></el-icon>
            <span>公共请购申请</span>
          </el-menu-item>

          <el-menu-item index="/my-requests" class="menu-item-with-badge" v-if="!isLandHost">
            <span>我的公共申请</span>
            <el-badge
              :value="userInProgressCount"
              :hidden="userInProgressCount === 0"
              type="danger"
              class="sidebar-badge"
            />
          </el-menu-item>

          <el-sub-menu index="/approval" v-if="!isLandHost && authStore.isApprover">
            <template #title>
              <el-icon><Postcard /></el-icon>
              <span>公共采购审核</span>
            </template>
            <el-menu-item index="/approval/public-funding" v-if="authStore.canAccessPublicWorkflow" class="menu-item-with-badge">
              <span>公共经费采购流程</span>
              <el-badge
                :value="publicWorkflowPendingCount"
                :hidden="publicWorkflowPendingCount === 0"
                type="danger"
                class="sidebar-badge"
              />
            </el-menu-item>
            <el-menu-item index="/approval/c2c" v-if="authStore.canAccessC2CWorkflow" class="menu-item-with-badge">
              <span>公对公采购流程</span>
              <el-badge
                :value="c2cWorkflowPendingCount"
                :hidden="c2cWorkflowPendingCount === 0"
                type="danger"
                class="sidebar-badge"
              />
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/whitelist-management" v-if="!isLandHost">
            <el-icon><Postcard /></el-icon>
            <span>白名单管理</span>
          </el-menu-item>

          <el-menu-item index="/instruments/book" v-if="!isLandHost">
            <el-icon><Calendar /></el-icon>
            <span>仪器预约</span>
          </el-menu-item>

          <el-menu-item v-if="!isLandHost && authStore.isSystemAdmin" index="/instruments/manage">
            <el-icon><Setting /></el-icon>
            <span>仪器管理</span>
          </el-menu-item>

          <el-menu-item index="/remote-booking">
            <el-icon><Connection /></el-icon>
            <span>远程主机预约</span>
          </el-menu-item>

          <el-menu-item v-if="!isLandHost && authStore.isSystemAdmin" index="/remote-management">
            <el-icon><Setting /></el-icon>
            <span>远程主机管理</span>
          </el-menu-item>

          <el-menu-item v-if="!isLandHost && canSeeCorridorManage" index="/corridor-screen/manage">
            <el-icon><Setting /></el-icon>
            <span>走廊显示屏管理</span>
          </el-menu-item>

          <el-menu-item index="/display-preview" v-if="!isLandHost">
            <el-icon><Postcard /></el-icon>
            <span>显示预览</span>
          </el-menu-item>

          <el-menu-item v-if="!isLandHost && authStore.isChiefSteward" index="/platform-management">
            <el-icon><Postcard /></el-icon>
            <span>平台管理</span>
          </el-menu-item>

          <el-sub-menu index="/team-procurement" v-if="!isLandHost && authStore.isTeamProcurementModuleEnabled">
            <template #title>
              <el-icon><User /></el-icon>
              <span>小组请购管理</span>
            </template>
            <el-menu-item index="/team-procurement/request">小组请购申请</el-menu-item>
            <el-menu-item index="/my-team-requests">我的小组申请</el-menu-item>
            <el-menu-item v-if="authStore.isTeamApprover" index="/team-procurement/approval">小组采购审核</el-menu-item>
            <el-menu-item v-if="authStore.isTeamApprover" index="/team-ledger">小组采购台账</el-menu-item>
            <el-menu-item v-if="authStore.isTutor" index="/team-management">小组成员管理</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="/statistics-group" v-if="!isLandHost && (authStore.canViewLedger || authStore.isPayer)">
            <template #title>
              <el-icon><DataLine /></el-icon>
              <span>财务与流程</span>
            </template>
            <el-sub-menu index="/ledger" v-if="authStore.canViewLedger">
              <template #title>
                <el-icon><Tickets /></el-icon>
                <span>采购台账</span>
              </template>
              <el-menu-item index="/ledger/c2c">公对公台账</el-menu-item>
              <el-menu-item index="/ledger/public">公共经费台账</el-menu-item>
            </el-sub-menu>
            <el-menu-item v-if="authStore.isSystemAdmin" index="/reports/public-expense">公共经费报表</el-menu-item>
            <el-menu-item v-if="authStore.isPayer" index="/payment">付款管理</el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/feedback" v-if="!isLandHost" class="feedback-menu-item">
            <el-icon><ChatLineSquare /></el-icon>
            <span>公告和反馈</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <div
        v-if="isFullScreen && sidebarVisible && !isMobile"
        class="sidebar-backdrop"
        @click="sidebarVisible = false"
      ></div>

      <el-drawer
        v-if="isMobile"
        v-model="drawerVisible"
        title="导航菜单"
        direction="ltr"
        :with-header="false"
        size="220px"
      >
        <div class="sidebar-header">
          <img src="/logo.svg" alt="Logo" class="sidebar-logo">
          <span>实验室管理</span>
        </div>

        <el-menu :default-active="$route.path" class="el-menu-vertical-demo" router>
          <el-menu-item index="/" v-if="!isLandHost">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </el-menu-item>

          <el-menu-item index="/project-management" v-if="!isLandHost && authStore.isProjectAdmin">
            <el-icon><Collection /></el-icon>
            <span>项目管理</span>
          </el-menu-item>
          <el-menu-item index="/announcement-management" v-if="!isLandHost && authStore.isAnnouncementAdmin">
            <el-icon><ChatLineSquare /></el-icon>
            <span>公告管理</span>
          </el-menu-item>

          <el-menu-item index="/group-affairs" v-if="!isLandHost && authStore.canAccessGroupAffairs">
            <el-icon><User /></el-icon>
            <span>小组事务</span>
          </el-menu-item>

          <el-menu-item index="/procurement/request" v-if="!isLandHost">
            <el-icon><ShoppingCart /></el-icon>
            <span>公共请购申请</span>
          </el-menu-item>

          <el-menu-item index="/my-requests" class="menu-item-with-badge highlight-item" v-if="!isLandHost">
            <span>我的申请</span>
            <el-badge
              :value="userInProgressCount"
              :hidden="userInProgressCount === 0"
              type="danger"
              class="sidebar-badge"
            />
          </el-menu-item>

          <el-sub-menu index="/approval" v-if="!isLandHost && authStore.isApprover">
            <template #title>
              <el-icon><Postcard /></el-icon>
              <span>公共采购审核</span>
            </template>
            <el-menu-item index="/approval/public-funding" v-if="authStore.canAccessPublicWorkflow" class="menu-item-with-badge">
              <span>公共经费采购流程</span>
              <el-badge
                :value="publicWorkflowPendingCount"
                :hidden="publicWorkflowPendingCount === 0"
                type="danger"
                class="sidebar-badge"
              />
            </el-menu-item>
            <el-menu-item index="/approval/c2c" v-if="authStore.canAccessC2CWorkflow" class="menu-item-with-badge">
              <span>公对公采购流程</span>
              <el-badge
                :value="c2cWorkflowPendingCount"
                :hidden="c2cWorkflowPendingCount === 0"
                type="danger"
                class="sidebar-badge"
              />
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/whitelist-management" v-if="!isLandHost">
            <el-icon><Postcard /></el-icon>
            <span>白名单管理</span>
          </el-menu-item>

          <el-menu-item index="/instruments/book" v-if="!isLandHost">
            <el-icon><Calendar /></el-icon>
            <span>仪器预约</span>
          </el-menu-item>
          <el-menu-item v-if="!isLandHost && authStore.isSystemAdmin" index="/instruments/manage">
            <el-icon><Setting /></el-icon>
            <span>仪器管理</span>
          </el-menu-item>

          <el-menu-item index="/remote-booking">
            <el-icon><Connection /></el-icon>
            <span>远程主机预约</span>
          </el-menu-item>

          <el-menu-item v-if="!isLandHost && authStore.isSystemAdmin" index="/remote-management">
            <el-icon><Setting /></el-icon>
            <span>远程主机管理</span>
          </el-menu-item>

          <el-menu-item v-if="!isLandHost && canSeeCorridorManage" index="/corridor-screen/manage">
            <el-icon><Setting /></el-icon>
            <span>走廊显示屏管理</span>
          </el-menu-item>

          <el-menu-item index="/display-preview" v-if="!isLandHost">
            <el-icon><Postcard /></el-icon>
            <span>显示预览</span>
          </el-menu-item>

          <el-menu-item v-if="!isLandHost && authStore.isChiefSteward" index="/platform-management">
            <el-icon><Postcard /></el-icon>
            <span>平台管理</span>
          </el-menu-item>

          <el-sub-menu index="/team-procurement" v-if="!isLandHost && authStore.isTeamProcurementModuleEnabled">
            <template #title>
              <el-icon><User /></el-icon>
              <span>小组请购管理</span>
            </template>
            <el-menu-item index="/team-procurement/request">小组请购申请</el-menu-item>
            <el-menu-item index="/my-team-requests">我的小组申请</el-menu-item>
            <el-menu-item v-if="authStore.isTeamApprover" index="/team-procurement/approval">小组采购审核</el-menu-item>
            <el-menu-item v-if="authStore.isTeamApprover" index="/team-ledger">小组采购台账</el-menu-item>
            <el-menu-item v-if="authStore.isTutor" index="/team-management">小组成员管理</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="/statistics-group" v-if="!isLandHost && (authStore.canViewLedger || authStore.isPayer)">
            <template #title>
              <el-icon><DataLine /></el-icon>
              <span>财务与流程</span>
            </template>
            <el-sub-menu index="/ledger" v-if="authStore.canViewLedger">
              <template #title>
                <el-icon><Tickets /></el-icon>
                <span>采购台账</span>
              </template>
              <el-menu-item index="/ledger/c2c">公对公台账</el-menu-item>
              <el-menu-item index="/ledger/public">公共经费台账</el-menu-item>
            </el-sub-menu>
            <el-menu-item v-if="authStore.isSystemAdmin" index="/reports/public-expense">公共经费报表</el-menu-item>
            <el-menu-item v-if="authStore.isPayer" index="/payment">付款管理</el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/feedback" v-if="!isLandHost" class="feedback-menu-item">
            <el-icon><ChatLineSquare /></el-icon>
            <span>公告和反馈</span>
          </el-menu-item>
        </el-menu>
      </el-drawer>

      <el-container class="right-panel">
        <el-header class="header" v-if="!isFullScreen">
          <div class="header-left">
            <el-icon class="hamburger" v-if="isMobile" @click="drawerVisible = true"><Menu /></el-icon>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="$route.meta.title">{{ $route.meta.title }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>

          <div class="header-center" v-if="!isMobile">
            <span>实验室管理系统</span>
          </div>

          <div class="header-right">
            <el-dropdown @command="handleCommand">
              <span class="el-dropdown-link">
                {{ authStore.user?.name || '未登录' }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout" v-if="authStore.accessToken">退出登录</el-dropdown-item>
                  <el-dropdown-item command="login" v-else>立即登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="main-content-area" :class="{ 'fullscreen-main': isFullScreen }">
          <router-view></router-view>
        </el-main>
      </el-container>

      <div
        v-if="showSidebarToggleButton"
        class="sidebar-fab"
        @click="toggleSidebar"
        title="导航"
      >
        <el-icon><Menu /></el-icon>
      </div>
    </el-container>
    <LabOpsAgentSidebar v-if="showLabOpsAgentSidebar" />
  </div>
</template>

<script setup>
import { h, ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth';
import { storeToRefs } from 'pinia';
import apiClient from '@/api';
import LabOpsAgentSidebar from '@/components/LabOpsAgentSidebar.vue';
import {
  House, ShoppingCart, DataLine, ArrowDown, Menu, User, Tickets, Postcard,
  Collection, ChatLineSquare, Calendar, Setting, Connection
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus';

const authStore = useAuthStore();
const $route = useRoute();
const router = useRouter();

const { userInProgressCount, pendingReceiptCount, publicWorkflowPendingCount, c2cWorkflowPendingCount } = storeToRefs(authStore);

const isMobile = ref(window.innerWidth < 768);
const drawerVisible = ref(false);

const isFullScreen = computed(() => $route.meta?.fullScreen === true);
const hideSidebarByRoute = computed(() => $route.meta?.hideSidebar === true);
const showSidebarToggleButton = computed(() => $route.meta?.sidebarToggleButton === true);

// 使用 store 里的计算属性判定 Land 主机账号
const isLandHost = computed(() => authStore.isLandHost);
const showLabOpsAgentSidebar = computed(() => Boolean(
  authStore.accessToken &&
  authStore.isSystemAdmin &&
  !isLandHost.value &&
  !isFullScreen.value &&
  $route.name !== 'labops-agent'
));

const canSeeCorridorManage = computed(() => {
  const u = authStore.user;
  if (!u) return false;
  if (u.is_corridor_screen_manager === true) return true;
  if (u.is_system_admin === true) return true;
  if (authStore.isSystemAdmin === true) return true;
  const roles = u.roles || [];
  return roles.some(r => ['系统管理员', '走廊显示屏管理人员'].includes(r.name));
});

const sidebarVisible = ref(false);

const showAside = computed(() => {
  if (isMobile.value) return false;
  if (!hideSidebarByRoute.value) return true;
  return sidebarVisible.value;
});

const toggleSidebar = () => {
  if (isMobile.value) {
    drawerVisible.value = !drawerVisible.value;
    return;
  }
  sidebarVisible.value = !sidebarVisible.value;
};

// 自动登出逻辑
const LOGOUT_TIMEOUT = 12 * 60 * 60 * 1000;
const logoutTimer = ref(null);

const isKioskDeviceRoute = computed(() => {
  if ($route.path !== '/remote-booking') return false;
  if ($route.query.kiosk_mode !== 'true') return false;
  return !!(
    $route.query.local_user ||
    $route.query.local_machine_id ||
    $route.query.local_machine_name ||
    $route.query.device_secret
  );
});

const checkLoginTimeout = () => {
  // Land 主机账号和被控主机 kiosk 页面不参与普通用户 12 小时自动登出
  if (authStore.isLandHost || isKioskDeviceRoute.value) return;

  const loginTime = authStore.loginTimestamp;
  const token = authStore.accessToken;
  if (token && loginTime > 0) {
    const timeElapsed = Date.now() - loginTime;
    if (timeElapsed >= LOGOUT_TIMEOUT) {
      ElMessage.warning('您已长时间未操作，系统已自动登出。');
      authStore.logout();
      router.push('/login');
    }
  } else if (logoutTimer.value) {
    clearInterval(logoutTimer.value);
    logoutTimer.value = null;
  }
};

const startLogoutTimer = () => {
  if (logoutTimer.value) {
    clearInterval(logoutTimer.value);
    logoutTimer.value = null;
  }
  if (authStore.accessToken && authStore.loginTimestamp > 0) {
    checkLoginTimeout();
    showUnreadGroupAffairPopups();
    logoutTimer.value = setInterval(() => {
      checkLoginTimeout();
      showUnreadGroupAffairPopups();
    }, 60 * 1000);
  }
};

const handleResize = () => {
  isMobile.value = window.innerWidth < 768;
  if (!isMobile.value) drawerVisible.value = false;
};

onMounted(() => {
  window.addEventListener('resize', handleResize);
  startLogoutTimer();
});
onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (logoutTimer.value) clearInterval(logoutTimer.value);
});

watch($route, () => {
  if (isMobile.value) drawerVisible.value = false;
  if (hideSidebarByRoute.value) sidebarVisible.value = false;
});

const hasShownPendingReceiptAlert = ref(false);
const isShowingAnnouncementPopup = ref(false);
const isShowingGroupAffairPopup = ref(false);
const isCheckingGroupAffairPopup = ref(false);
const lastAnnouncementPopupLoginKey = ref(null);
const ANNOUNCEMENT_POPUP_LOGIN_KEY = 'announcementPopupCheckedLoginTimestamp';

const ensureUserLoaded = async () => {
  if (!authStore.user) {
    await authStore.fetchUser();
  }
};

const showPendingReceiptAlert = async () => {
  if (hasShownPendingReceiptAlert.value) return;
  await ensureUserLoaded();
  await authStore.fetchPendingReceiptCount();
  if (pendingReceiptCount.value > 0) {
    hasShownPendingReceiptAlert.value = true;
    ElMessageBox.alert(
      `您还有 ${pendingReceiptCount.value} 条待收货的请购信息，请及时处理。`,
      '待收货提醒',
      { confirmButtonText: '我知道了', type: 'warning' }
    );
  }
};

const normalizeListResponse = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const formatDateTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

const buildAnnouncementPopupMessage = (announcements) => h(
  'div',
  { class: 'announcement-popup-list' },
  announcements.map(item => h(
    'section',
    { class: 'announcement-popup-item', key: item.id },
    [
      h('h3', { class: 'announcement-popup-title' }, item.title || '公告'),
      h('div', { class: 'announcement-popup-meta' }, formatDateTime(item.updated_at || item.created_at)),
      h('div', { class: 'announcement-popup-content' }, item.content || ''),
    ]
  ))
);

const markPopupAnnouncementsRead = async (announcements) => {
  const ids = announcements.map(item => item.id).filter(Boolean);
  await Promise.allSettled(
    ids.map(id => apiClient.post(`/procurement/announcements/${id}/mark-read/`))
  );
};

const buildGroupAffairPopupMessage = (payload) => {
  const sections = [];
  const dutyReminder = payload?.duty_reminder;
  const notices = normalizeListResponse(payload?.notices);
  const purchaseReminders = normalizeListResponse(payload?.purchase_reminders);

  if (dutyReminder) {
    sections.push(h(
      'section',
      { class: 'announcement-popup-item', key: 'duty-reminder' },
      [
        h('h3', { class: 'announcement-popup-title' }, '值日提醒'),
        h(
          'div',
          { class: 'announcement-popup-meta' },
          `${dutyReminder.duty_date} ${dutyReminder.weekday_label || ''} · ${dutyReminder.tutor_name || ''}小组`
        ),
        h('div', { class: 'announcement-popup-content' }, `${dutyReminder.name || '您'}今天值日，请及时处理。`),
      ]
    ));
  }

  notices.forEach((item) => {
    sections.push(h(
      'section',
      { class: 'announcement-popup-item', key: `notice-${item.id}` },
      [
        h('h3', { class: 'announcement-popup-title' }, item.title || '小组提醒'),
        h(
          'div',
          { class: 'announcement-popup-meta' },
          `${item.board_tutor_name || ''}小组 · ${formatDateTime(item.created_at)}`
        ),
        h('div', { class: 'announcement-popup-content' }, item.content || ''),
      ]
    ));
  });

  purchaseReminders.forEach((item) => {
    sections.push(h('section', { class: 'announcement-popup-item', key: `purchase-${item.type}-${item.purchase_id}` }, [
      h('h3', { class: 'announcement-popup-title' }, item.title || '组内采购提醒'),
      h('div', { class: 'announcement-popup-meta' }, `采购单 #${item.purchase_id}`),
      h('div', { class: 'announcement-popup-content' }, item.content || ''),
    ]));
  });

  return h('div', { class: 'announcement-popup-list' }, sections);
};

const markGroupAffairPopupsRead = async (payload) => {
  const notices = normalizeListResponse(payload?.notices);
  const tasks = notices
    .filter(item => item.board && item.id)
    .map(item => apiClient.post(`/group-affairs/boards/${item.board}/notices/${item.id}/mark-read/`));

  normalizeListResponse(payload?.purchase_reminders).forEach((item) => {
    tasks.push(apiClient.post('/group-affairs/popups/purchase/mark-read/', {
      purchase_id: item.purchase_id,
      type: item.type,
      reminder_date: item.reminder_date,
    }));
  });

  if (payload?.duty_reminder?.duty_date) {
    tasks.push(apiClient.post('/group-affairs/popups/duty-reminder/mark-read/', {
      duty_date: payload.duty_reminder.duty_date,
    }));
  }

  await Promise.allSettled(tasks);
};

const showUnreadGroupAffairPopups = async () => {
  if (!authStore.accessToken) return;
  if (isCheckingGroupAffairPopup.value || isShowingGroupAffairPopup.value || isShowingAnnouncementPopup.value) return;

  isCheckingGroupAffairPopup.value = true;
  try {
    await ensureUserLoaded();
    if (authStore.isLandHost || !authStore.canAccessGroupAffairs) return;

    const response = await apiClient.get('/group-affairs/popups/unread/');
    const notices = normalizeListResponse(response.data?.notices);
    const payload = {
      notices,
      duty_reminder: response.data?.duty_reminder || null,
      purchase_reminders: normalizeListResponse(response.data?.purchase_reminders),
    };

    if (notices.length === 0 && !payload.duty_reminder && payload.purchase_reminders.length === 0) return;

    isShowingGroupAffairPopup.value = true;
    try {
      await ElMessageBox.alert(
        buildGroupAffairPopupMessage(payload),
        '小组事务提醒',
        {
          confirmButtonText: '我知道了',
          customClass: 'announcement-popup-message-box',
        }
      );
    } catch (error) {
      // 关闭弹窗也视为已读，避免同一条提醒反复打扰。
    } finally {
      await markGroupAffairPopupsRead(payload);
      isShowingGroupAffairPopup.value = false;
    }
  } catch (error) {
    isShowingGroupAffairPopup.value = false;
  } finally {
    isCheckingGroupAffairPopup.value = false;
  }
};

const showUnreadAnnouncementPopups = async () => {
  const loginKey = String(authStore.loginTimestamp || '');
  if (!authStore.accessToken || !loginKey || loginKey === '0') return;
  if (isShowingAnnouncementPopup.value) return;
  if (lastAnnouncementPopupLoginKey.value === loginKey) return;
  if (sessionStorage.getItem(ANNOUNCEMENT_POPUP_LOGIN_KEY) === loginKey) return;

  lastAnnouncementPopupLoginKey.value = loginKey;

  try {
    await ensureUserLoaded();
    if (authStore.isLandHost) {
      sessionStorage.setItem(ANNOUNCEMENT_POPUP_LOGIN_KEY, loginKey);
      return;
    }

    const response = await apiClient.get('/procurement/announcements/unread-popup/');
    const announcements = normalizeListResponse(response.data);
    sessionStorage.setItem(ANNOUNCEMENT_POPUP_LOGIN_KEY, loginKey);
    if (announcements.length === 0) return;

    isShowingAnnouncementPopup.value = true;
    try {
      await ElMessageBox.alert(
        buildAnnouncementPopupMessage(announcements),
        '公告',
        {
          confirmButtonText: '我知道了',
          customClass: 'announcement-popup-message-box',
        }
      );
    } catch (error) {
      // 关闭弹窗也视为已读，避免同一次登录重复打扰。
    } finally {
      await markPopupAnnouncementsRead(announcements);
      isShowingAnnouncementPopup.value = false;
    }
  } catch (error) {
    lastAnnouncementPopupLoginKey.value = null;
  }
};

watch(() => authStore.accessToken, (newToken) => {
  if (newToken) {
    ensureUserLoaded().then(() => {
      authStore.fetchUserRejectedCount();
      authStore.fetchUserInProgressCount();
      authStore.fetchWorkflowPendingCounts();
      showPendingReceiptAlert();
      showUnreadGroupAffairPopups();
    });
    startLogoutTimer();
  } else if (logoutTimer.value) {
    clearInterval(logoutTimer.value);
    logoutTimer.value = null;
    hasShownPendingReceiptAlert.value = false;
  }
}, { immediate: true });

watch(
  [() => authStore.accessToken, () => authStore.loginTimestamp],
  ([token, loginTimestamp]) => {
    if (token && loginTimestamp > 0) {
      showUnreadAnnouncementPopups();
    }
  },
  { immediate: true }
);

const handleCommand = (command) => {
  if (command === 'logout') {
    authStore.logout();
    router.push('/login');
  }
  if (command === 'login') {
    router.push('/login');
  }
};
</script>

<style scoped>
.aside {
  background-color: #f0f2f5;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e6e6e6;
  transition: width 0.3s;
}

.floating-aside {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 2001;
}

.sidebar-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.25);
  z-index: 2000;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 15px 20px;
  font-size: 18px;
  font-weight: bold;
  white-space: nowrap;
}
.sidebar-logo { height: 32px; width: 32px; margin-right: 10px; }
.el-menu-vertical-demo {
  border-right: none;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
.right-panel { display: flex; flex-direction: column; height: 100vh; }

.header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e6e6e6;
  background-color: #fff;
  padding-left: 20px;
  padding-right: 20px;
}

.main-content-area {
  flex-grow: 1;
  overflow-y: auto;
  background-color: #f5f5f5;
  padding: 24px;
}

.fullscreen-main {
  padding: 0 !important;
  background-color: transparent !important;
}

.header-left { display: flex; align-items: center; flex-shrink: 0; }

.header-center {
  flex-shrink: 1;
  padding: 0 20px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  text-align: center;
}

.header-right { display: flex; align-items: center; flex-shrink: 0; }
.el-dropdown-link { cursor: pointer; display: flex; align-items: center; }
.hamburger { font-size: 24px; cursor: pointer; margin-right: 15px; }
:global(.el-drawer__body) { padding: 0; }
:global(.el-drawer .el-menu) { border-right: none; }

.menu-item-with-badge { display: flex; justify-content: space-between; align-items: center; }
.sidebar-badge { line-height: normal; transform: scale(1.15); }
.highlight-item span { font-weight: 700; }
.feedback-menu-item {
  margin-top: auto;
  border-top: 1px solid #e6e6e6;
}

.sidebar-fab {
  position: fixed;
  left: 16px;
  bottom: 16px;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #e6e6e6;
  box-shadow: 0 8px 20px rgba(0,0,0,0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2100;
}

:global(.announcement-popup-message-box) {
  max-width: min(720px, calc(100vw - 32px));
}

:global(.announcement-popup-list) {
  max-height: 56vh;
  overflow-y: auto;
  padding-right: 6px;
}

:global(.announcement-popup-item + .announcement-popup-item) {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

:global(.announcement-popup-title) {
  margin: 0;
  color: #303133;
  font-size: 17px;
  line-height: 1.4;
}

:global(.announcement-popup-meta) {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
}

:global(.announcement-popup-content) {
  margin-top: 10px;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 1200px) {
  .header-left .el-breadcrumb { display: none; }
}
@media (max-width: 767px) {
  .main-content-area { padding: 15px; }
  .header { padding-left: 15px; padding-right: 15px; }
  .fullscreen-main { padding: 0 !important; }
}
</style>
