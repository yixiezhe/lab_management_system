// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import RegisterView from '../views/RegisterView.vue'
import LoginView from '../views/LoginView.vue'
import ProcurementRequestView from '../views/ProcurementRequestView.vue';
import MyRequestsView from '../views/MyRequestsView.vue';
import ProcurementApprovalView from '../views/ProcurementApprovalView.vue';
import StatisticsView from '../views/StatisticsView.vue';
import WhitelistManagementView from '../views/WhitelistManagementView.vue';
import InvoiceView from '../views/InvoiceView.vue';
import PaymentView from '../views/PaymentView.vue';
import TeamRequestView from '../views/TeamRequestView.vue';
import MyTeamRequestsView from '../views/MyTeamRequestsView.vue';
import TeamApprovalView from '../views/TeamApprovalView.vue';
import TeamManagementView from '../views/TeamManagementView.vue';
import TeamLedgerView from '../views/TeamLedgerView.vue';
import GroupAffairsView from '../views/GroupAffairsView.vue';
import PlatformManagementView from '../views/PlatformManagementView.vue';
import ProjectManagementView from '../views/ProjectManagementView.vue';
import AnnouncementManagementView from '../views/AnnouncementManagementView.vue';
import PublicExpenseReportView from '../views/PublicExpenseReportView.vue';
import FeedbackView from '../views/FeedbackView.vue';
import LabOpsAgentView from '../views/LabOpsAgentView.vue';

// === 仪器模块页面 ===
import InstrumentBookingEntryView from '../views/InstrumentBookingEntryView.vue';
import InstrumentBookingView from '../views/InstrumentBookingView.vue';
import InstrumentManagementView from '../views/InstrumentManagementView.vue';

// === 远程访问模块页面 ===
import RemoteBookingView from '../views/RemoteBookingView.vue';
import RemoteManagementView from '../views/RemoteManagementView.vue';

// === 走廊显示屏模块页面 ===
import CorridorScreenManageView from '../views/CorridorScreenManageView.vue';
import DisplayPreviewView from '../views/DisplayPreviewView.vue';

import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 仪表盘
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { title: '仪表盘', requiresAuth: true }
    },
    {
      path: '/labops-agent',
      name: 'labops-agent',
      component: LabOpsAgentView,
      meta: { title: '智能助手', requiresAuth: true, requiresSystemAdmin: true }
    },

    // 认证
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { title: '用户注册' }
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { title: '用户登录' }
    },

    // 管理
    {
      path: '/project-management',
      name: 'project-management',
      component: ProjectManagementView,
      meta: { title: '项目管理', requiresAuth: true, requiresProjectAdmin: true }
    },
    {
      path: '/announcement-management',
      name: 'announcement-management',
      component: AnnouncementManagementView,
      meta: { title: '公告管理', requiresAuth: true, requiresAnnouncementAdmin: true }
    },

    // 公共请购
    {
      path: '/procurement',
      redirect: '/procurement/request',
      meta: { requiresAuth: true }
    },
    {
      path: '/procurement/request',
      name: 'procurement-request',
      component: ProcurementRequestView,
      meta: { title: '公共请购申请', requiresAuth: true }
    },
    {
      path: '/my-requests',
      name: 'my-requests',
      component: MyRequestsView,
      meta: { title: '我的申请', requiresAuth: true }
    },

    // 审核
    {
      path: '/approval',
      redirect: '/approval/public-funding',
      meta: { requiresAuth: true, requiresApprover: true }
    },
    {
      path: '/approval/public-funding',
      name: 'approval-public-funding',
      component: ProcurementApprovalView,
      meta: {
        title: '公共经费采购流程',
        requiresAuth: true,
        requiresApprover: true,
        expenseType: 'public'
      }
    },
    {
      path: '/approval/c2c',
      name: 'approval-c2c',
      component: ProcurementApprovalView,
      meta: {
        title: '公对公采购流程',
        requiresAuth: true,
        requiresApprover: true,
        expenseType: 'c2c'
      }
    },

    // 小组请购
    {
      path: '/team-procurement/request',
      name: 'team-procurement-request',
      component: TeamRequestView,
      meta: { title: '小组请购申请', requiresAuth: true }
    },
    {
      path: '/my-team-requests',
      name: 'my-team-requests',
      component: MyTeamRequestsView,
      meta: { title: '我的小组申请', requiresAuth: true }
    },
    {
      path: '/team-procurement/approval',
      name: 'team-procurement-approval',
      component: TeamApprovalView,
      meta: { title: '小组采购审核', requiresAuth: true, requiresTeamApprover: true }
    },
    {
      path: '/team-management',
      name: 'team-management',
      component: TeamManagementView,
      meta: { title: '小组成员管理', requiresAuth: true, requiresTutor: true }
    },
    {
      path: '/team-ledger',
      name: 'team-ledger',
      component: TeamLedgerView,
      meta: { title: '小组采购台账', requiresAuth: true, requiresTeamApprover: true }
    },
    {
      path: '/group-affairs',
      name: 'group-affairs',
      component: GroupAffairsView,
      meta: { title: '小组事务', requiresAuth: true, requiresGroupAffairs: true }
    },

    // 台账 / 其他
    {
      path: '/ledger/c2c',
      name: 'ledger-c2c',
      component: StatisticsView,
      meta: { title: '公对公台账', requiresAuth: true, requiresLedgerViewer: true }
    },
    {
      path: '/ledger/public',
      name: 'ledger-public',
      component: StatisticsView,
      meta: { title: '公共经费台账', requiresAuth: true, requiresLedgerViewer: true }
    },
    {
      path: '/reports/public-expense',
      name: 'public-expense-report',
      component: PublicExpenseReportView,
      meta: { title: '公共经费报表', requiresAuth: true, requiresSystemAdmin: true }
    },
    {
      path: '/whitelist-management',
      name: 'whitelist-management',
      component: WhitelistManagementView,
      meta: { title: '白名单管理', requiresAuth: true }
    },
    {
      path: '/platform-management',
      name: 'platform-management',
      component: PlatformManagementView,
      meta: { title: '平台管理', requiresAuth: true, requiresChiefSteward: true }
    },
    {
      path: '/invoices',
      name: 'invoices',
      component: InvoiceView,
      meta: { title: '发票报销管理', requiresAuth: true, requiresApprover: true }
    },
    {
      path: '/payment',
      name: 'payment',
      component: PaymentView,
      meta: { title: '付款管理', requiresAuth: true, requiresPayer: true }
    },
    {
      path: '/feedback',
      name: 'feedback',
      component: FeedbackView,
      meta: { title: '公告和反馈', requiresAuth: true }
    },

    // 仪器模块
    {
      path: '/instruments/book',
      name: 'instruments-book-entry',
      component: InstrumentBookingEntryView,
      meta: { title: '仪器预约入口', requiresAuth: true }
    },
    {
      path: '/instruments/book/detail',
      name: 'instruments-book',
      component: InstrumentBookingView,
      meta: { title: '仪器预约', requiresAuth: true }
    },
    {
      path: '/instruments/manage',
      name: 'instruments-manage',
      component: InstrumentManagementView,
      meta: { title: '仪器管理', requiresAuth: true, requiresSystemAdmin: true }
    },

    // 远程访问模块
    {
      path: '/remote-booking',
      name: 'remote-booking',
      component: RemoteBookingView,
      meta: { title: '远程主机预约', requiresAuth: true }
    },
    {
      path: '/remote-management',
      name: 'remote-management',
      component: RemoteManagementView,
      meta: {
        title: '远程主机管理',
        requiresAuth: true,
        requiresSystemAdmin: true
      }
    },

    // 走廊显示屏
    {
      path: '/corridor-screen/manage',
      name: 'corridor-screen-manage',
      component: CorridorScreenManageView,
      meta: {
        title: '走廊显示屏管理',
        requiresAuth: true,
        requiresCorridorScreenManager: true
      }
    },

    // 显示预览
    {
      path: '/display-preview',
      name: 'display-preview',
      component: DisplayPreviewView,
      meta: {
        title: '显示预览',
        fullScreen: true,
        hideSidebar: true,
        sidebarToggleButton: true
      }
    },
  ]
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  const isAuthenticated = !!authStore.accessToken;
  const hasKioskIdentity =
    !!to.query?.local_user ||
    !!to.query?.local_machine_id ||
    !!to.query?.local_machine_name;
  const isKioskAutoLogin =
    to.path === '/remote-booking' &&
    to.query?.kiosk_mode === 'true' &&
    hasKioskIdentity;

  const hasAnyRole = (names) => {
    const roles = authStore.user?.roles || [];
    return roles.some(r => names.includes(r.name));
  };

  // 1) 基础登录判断
  if (to.meta.requiresAuth && !isAuthenticated) {
    if (isKioskAutoLogin) return next();
    ElMessage.error('请先登录。');
    return next({ name: 'login' });
  }

  // === 【核心修改】Land设备主机角色特殊拦截逻辑 ===
  // 该角色允许访问的路径白名单（去掉了首页 '/'）
  if (isAuthenticated && authStore.isLandHost === true) {
    const allowedPaths = ['/remote-booking', '/login', '/register', '/display-preview'];
    
    // 检查目标路径是否完全匹配白名单，或者是 /remote-booking 的子路由
    const isAllowed = allowedPaths.includes(to.path) || to.path.startsWith('/remote-booking');

    if (!isAllowed) {
        // 如果尝试访问其他页面（包括被 App.vue 隐藏的主页），直接拦截并引导至远程预约页
        ElMessage.warning('设备主机账号仅限访问远程预约功能。');
        return next({ name: 'remote-booking' });
    }
  }
  // ===========================================

  // 2) 其他角色权限校验逻辑 (保持不变)
  if (to.meta.requiresApprover && !authStore.isApprover) {
    ElMessage.error('您没有权限访问此审批页面。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresProjectAdmin && !authStore.isProjectAdmin) {
    ElMessage.error('只有项目管理员可以访问此页面。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresAnnouncementAdmin && !authStore.isAnnouncementAdmin) {
    ElMessage.error('只有管理员可以访问公告管理页面。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresLedgerViewer && !authStore.canViewLedger) {
    ElMessage.error('您没有权限访问台账页面。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresPayer && !authStore.isPayer) {
    ElMessage.error('您没有权限访问付款管理页面。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresChiefSteward && !authStore.isChiefSteward) {
    ElMessage.error('只有大总管可以访问此页面。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresTeamApprover && !authStore.isTeamApprover) {
    ElMessage.error('您没有权限访问小组审批页面。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresGroupAffairs && !authStore.canAccessGroupAffairs) {
    ElMessage.error('您没有权限访问小组事务。');
    return next(from.name ? false : { name: 'home' });
  }
  if (to.meta.requiresTutor && !authStore.isTutor) {
    ElMessage.error('只有导师可以访问此页面。');
    return next(from.name ? false : { name: 'home' });
  }

  if (to.meta.requiresSystemAdmin && authStore.isSystemAdmin === false) {
    ElMessage.error('只有系统管理员可以访问此页面。');
    return next(from.name ? false : { name: 'home' });
  }

  if (to.meta.requiresCorridorScreenManager) {
    const ok =
      authStore.user?.is_corridor_screen_manager === true ||
      authStore.user?.is_system_admin === true ||
      authStore.isSystemAdmin === true ||
      hasAnyRole(['系统管理员', '走廊显示屏管理人员']);

    if (!ok) {
      ElMessage.error('只有系统管理员或走廊显示屏管理人员可以访问此页面。');
      return next(from.name ? false : { name: 'home' });
    }
  }

  next();
});

export default router
