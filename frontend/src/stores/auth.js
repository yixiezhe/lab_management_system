// frontend/src/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('accessToken') || null);
  const refreshToken = ref(localStorage.getItem('refreshToken') || null);
  const user = ref(JSON.parse(localStorage.getItem('user')) || null);
  // --- 【保持】登录时间戳 ---
  const loginTimestamp = ref(parseInt(localStorage.getItem('loginTimestamp') || '0'));
  // --- END ---

  const approverPendingCount = ref(0);
  const userRejectedCount = ref(0);
  const userInProgressCount = ref(0);
  const pendingReceiptCount = ref(0);
  const publicWorkflowPendingCount = ref(0);
  const c2cWorkflowPendingCount = ref(0);

  // --- 基础角色判断 ---
  const isSystemAdmin = computed(() => {
    const v = user.value?.is_system_admin;
    if (v === true || v === false) return v;
    return !!user.value?.roles?.some(role => role.name === '系统管理员');
  });

  // === 【新增精华】Land设备主机角色判断 ===
  const isLandHost = computed(() => {
    const v = user.value?.is_land_host;
    if (v === true || v === false) return v;
    // 兼容旧数据，通过角色名称判断
    return !!user.value?.roles?.some(role => role.name === 'land设备主机');
  });
  // =====================================

  const isTutor = computed(() => user.value?.roles?.some(role => role.name === '导师用户'));
  const isPayer = computed(() => user.value?.roles?.some(role => role.name === '付款人'));
  const isChiefSteward = computed(() => user.value?.roles?.some(role => role.name === '大总管'));
  const isProjectAdmin = computed(() => user.value?.roles?.some(role => role.name === '项目管理员'));
  const isAnnouncementAdmin = computed(() => isProjectAdmin.value || isSystemAdmin.value);
  const isTeamApprover = computed(() => user.value?.roles?.some(r => ['导师用户', '小组采购人员'].includes(r.name)));

  // === 走廊显示屏管理权限 ===
  const isCorridorScreenManager = computed(() => {
    const v = user.value?.is_corridor_screen_manager;
    if (v === true || v === false) return v;
    const hasRole = !!user.value?.roles?.some(role => role.name === '走廊显示屏管理人员');
    return isSystemAdmin.value || hasRole;
  });

  // --- 复合权限判断 ---
  const isC2CPlatformManager = computed(() => user.value?.is_c2c_platform_manager || false);

  const isApprover = computed(() => {
    const approverRoleNames = ['导师用户', '采购人员', '系统管理员'];
    return user.value?.roles?.some(role => approverRoleNames.includes(role.name)) || isC2CPlatformManager.value;
  });

  const canManageWhitelist = computed(() => user.value?.roles?.some(r => ['系统管理员', '大总管'].includes(r.name)));
  const canViewLedger = computed(() => isApprover.value || isChiefSteward.value);

  const isTeamProcurementModuleEnabled = computed(() => {
    if (!user.value) return false;
    if (isTutor.value) return user.value.team_procurement_enabled;
    return user.value.assigned_tutor?.team_procurement_enabled || false;
  });

  const canAccessGroupAffairs = computed(() => {
    if (!user.value) return false;
    return isSystemAdmin.value || isTutor.value || !!user.value.assigned_tutor;
  });

  const canAccessPublicWorkflow = computed(() => {
    const requiredRoles = ['采购人员', '导师用户', '系统管理员'];
    return user.value?.roles?.some(role => requiredRoles.includes(role.name));
  });

  const canAccessC2CWorkflow = computed(() => {
    const hasAdminOrTutorRole = user.value?.roles?.some(role => ['系统管理员', '导师用户'].includes(role.name));
    return hasAdminOrTutorRole || isC2CPlatformManager.value;
  });

  // --- 函数 ---
  function updateTeamProcurementStatus(newStatus) {
    if (user.value) user.value.team_procurement_enabled = newStatus;
  }

  function setAccessToken(newToken) {
    accessToken.value = newToken;
    localStorage.setItem('accessToken', newToken);
  }

  function setTokens(access, refresh) {
    accessToken.value = access;
    refreshToken.value = refresh;
    localStorage.setItem('accessToken', access);
    localStorage.setItem('refreshToken', refresh);
  }

  function clearTokensSilently() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
  }

  async function fetchUser() {
    if (accessToken.value) {
      try {
        const response = await apiClient.get('/users/me/');
        user.value = response.data;
        localStorage.setItem('user', JSON.stringify(user.value));
      } catch (error) {
        console.error('Failed to fetch user info:', error);
        logout();
      }
    }
  }

  async function login(username, password) {
    try {
      const response = await apiClient.post('/token/', { username, password });
      accessToken.value = response.data.access;
      refreshToken.value = response.data.refresh;
      localStorage.setItem('accessToken', accessToken.value);
      localStorage.setItem('refreshToken', refreshToken.value);
      await fetchUser(); 

      // --- 记录登录时间 ---
      if (user.value) { 
        const now = Date.now();
        loginTimestamp.value = now;
        localStorage.setItem('loginTimestamp', now.toString());
      } else {
        logout();
        return false;
      }

      ElMessage.success('登录成功！');
      return true;
    } catch (error) {
      const detail = error.response?.data?.detail || '用户名或密码错误。';
      ElMessage.error(`登录失败: ${detail}`);
      return false;
    }
  }

  function logout() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    approverPendingCount.value = 0;
    userRejectedCount.value = 0;
    userInProgressCount.value = 0;
    pendingReceiptCount.value = 0;
    publicWorkflowPendingCount.value = 0;
    c2cWorkflowPendingCount.value = 0;
    loginTimestamp.value = 0;
    localStorage.removeItem('loginTimestamp');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    ElMessage.info('您已退出登录。');
  }

  async function fetchApproverPendingCount() {
    if (isApprover.value) {
      try {
        const response = await apiClient.get('/procurement/dashboard-stats/');
        approverPendingCount.value = response.data.awaiting_approval_count || 0;
      } catch (error) {
        approverPendingCount.value = 0;
      }
    }
  }

  async function fetchUserRejectedCount() {
    if (user.value) {
      try {
        const response = await apiClient.get('/procurement/public-purchase-requests/', {
          params: { status: 'rejected', scope: 'mine' }
        });
        userRejectedCount.value = response.data.count || 0;
      } catch (error) {
        userRejectedCount.value = 0;
      }
    }
  }

  const getMyCount = async (endpoint, params) => {
    const response = await apiClient.get(endpoint, {
      params: { ...params, scope: 'mine', page_size: 1 }
    });
    return response.data.count || 0;
  };

  async function fetchUserInProgressCount() {
    if (!user.value) return;
    try {
      const [publicCount, c2cCount] = await Promise.all([
        getMyCount('/procurement/public-purchase-requests/', { status__in: 'pending,payment_rejected,paid' }),
        getMyCount('/procurement/c2c-purchase-requests/', { status__in: 'pending,payment_rejected,pending_purchase_order,pending_contract,paid' }),
      ]);
      userInProgressCount.value = publicCount + c2cCount;
    } catch (error) {
      userInProgressCount.value = 0;
    }
  }

  async function fetchPendingReceiptCount() {
    if (!user.value) return;
    try {
      const [publicCount, c2cCount] = await Promise.all([
        getMyCount('/procurement/public-purchase-requests/', { status: 'paid' }),
        getMyCount('/procurement/c2c-purchase-requests/', { status: 'paid' }),
      ]);
      pendingReceiptCount.value = publicCount + c2cCount;
    } catch (error) {
      pendingReceiptCount.value = 0;
    }
  }

  async function fetchWorkflowPendingCounts() {
    if (!user.value) return;
    const workflowStatuses = 'pending,payment_rejected,pending_purchase_order,pending_contract,approved,goods_received,invoiced,accepted,inspection_skipped';
    const publicApprovalStatuses = 'pending,payment_rejected';
    const publicHandledStatuses = 'approved,goods_received,invoiced,accepted,inspection_skipped';
    const roleNames = user.value?.roles?.map(role => role.name) || [];
    const canSeePublic = roleNames.some(name => ['采购人员', '导师用户', '系统管理员'].includes(name));
    const canSeeC2C = isC2CPlatformManager.value || roleNames.some(name => ['系统管理员', '导师用户'].includes(name));

    try {
      if (canSeePublic) {
        const [approvalRes, handledRes] = await Promise.all([
          apiClient.get('/procurement/public-purchase-requests/', {
            params: { status__in: publicApprovalStatuses, scope: 'all', page_size: 1 }
          }),
          apiClient.get('/procurement/public-purchase-requests/', {
            params: { status__in: publicHandledStatuses, scope: 'all', page_size: 1 }
          }),
        ]);
        const approvalCount = approvalRes.data.count || 0;
        const handledCount = handledRes.data.count || 0;
        publicWorkflowPendingCount.value = approvalCount + handledCount;
      } else {
        publicWorkflowPendingCount.value = 0;
      }
    } catch (error) {
      publicWorkflowPendingCount.value = 0;
    }

    try {
      if (canSeeC2C) {
        const response = await apiClient.get('/procurement/c2c-purchase-requests/', {
          params: { status__in: workflowStatuses, scope: 'all', page_size: 1 }
        });
        c2cWorkflowPendingCount.value = response.data.count || 0;
      } else {
        c2cWorkflowPendingCount.value = 0;
      }
    } catch (error) {
      c2cWorkflowPendingCount.value = 0;
    }
  }

  if (accessToken.value && !user.value) {
    fetchUser();
  }

  return {
    accessToken, refreshToken, user, login, logout, setAccessToken, setTokens, clearTokensSilently, fetchUser,
    loginTimestamp, 
    approverPendingCount, userRejectedCount, userInProgressCount, pendingReceiptCount,
    publicWorkflowPendingCount, c2cWorkflowPendingCount,
    fetchApproverPendingCount, fetchUserRejectedCount, fetchUserInProgressCount, fetchPendingReceiptCount, fetchWorkflowPendingCounts,
    isApprover,
    canManageWhitelist,
    canViewLedger,
    isPayer,
    isTeamApprover,
    isTutor,
    isChiefSteward,
    isProjectAdmin,
    isAnnouncementAdmin,
    isC2CPlatformManager,
    isSystemAdmin,
    isCorridorScreenManager,
    isLandHost, // 【新增导出】
    isTeamProcurementModuleEnabled,
    canAccessGroupAffairs,
    updateTeamProcurementStatus,
    canAccessPublicWorkflow,
    canAccessC2CWorkflow,
  }
});
