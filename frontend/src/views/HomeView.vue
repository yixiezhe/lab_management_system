<template>
  <div>
    <el-card shadow="never" style="margin-bottom: 24px;">
      <div class="welcome-container">
        <h2 class="welcome-message">您好，{{ authStore.user?.name || '用户' }}！欢迎使用实验室管理系统。</h2>
        <div class="maintenance-info">网站维护请联系--示例成员21</div>
        <div class="teacher-info">
          指导老师：庞越鹏教授
        </div>
      </div>
    </el-card>

    <el-card v-if="!loadingAnnouncement && announcements.length > 0" shadow="never" style="margin-bottom: 24px;">
      <template #header>
        <div class="card-header">
          <span>📢 全站公告</span>
        </div>
      </template>
      <div class="home-announcement-list">
        <article v-for="item in announcements" :key="item.id" class="home-announcement-item">
          <h3>{{ item.title }}</h3>
          <div class="announcement-content">{{ item.content }}</div>
        </article>
      </div>
    </el-card>

    <el-card shadow="never" style="margin-bottom: 24px;" v-loading="loadingPendingInfo">
      <template #header>
        <div class="card-header">
          <span>📝 待处理信息</span>
        </div>
      </template>
      <el-row :gutter="16" class="pending-list">
        <el-col :span="24" v-for="item in pendingItems" :key="item.key">
          <el-card shadow="hover" class="pending-item-card">
            <el-statistic :title="item.label" :value="item.count">
              <template #suffix><span class="stat-unit">项</span></template>
            </el-statistic>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-card v-if="!loadingProjects" shadow="never" style="margin-bottom: 24px;">
      <template #header>
        <div class="card-header">
          <span><el-icon><Tickets /></el-icon> 项目列表</span> </div>
      </template>
      <el-table :data="projects" stripe border style="width: 100%">
        <el-table-column prop="project_number" label="项目号" width="180" />
        <el-table-column prop="name" label="项目名" />
        <el-table-column prop="description" label="项目说明" show-overflow-tooltip />
        <el-table-column prop="author.name" label="创建/修改人" width="120" />
        <el-table-column prop="updated_at" label="最后更新" width="180">
          <template #default="scope">
            {{ new Date(scope.row.updated_at).toLocaleDateString('sv-SE') }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loadingProjects && projects.length === 0" description="暂无发布的项目列表" />
    </el-card>

    <el-row v-if="authStore.isTutor" style="margin-top: 24px;">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>导师设置</span>
            </div>
          </template>
          <div class="setting-item">
            <span>启用小组请购功能</span>
            <el-switch
              v-if="authStore.user"
              v-model="authStore.user.team_procurement_enabled"
              :loading="isSwitchLoading"
              @change="toggleTeamProcurement"
            />
          </div>
          <div class="setting-description">
            开启后，您的小组成员将可以看到“小组请购管理”菜单并提交申请。
          </div>
        </el-card>
      </el-col>
    </el-row>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { Tickets } from '@element-plus/icons-vue'; // 导入图标

const authStore = useAuthStore();
const isSwitchLoading = ref(false);

const projects = ref([]);
const loadingProjects = ref(true);

const pendingInfo = ref({
  myPublic: 0,
  myC2c: 0,
  publicWorkflow: 0,
  c2cWorkflow: 0,
});
const loadingPendingInfo = ref(false);

const isProcurementStaff = computed(() => authStore.user?.roles?.some(role => role.name === '采购人员'));

const pendingItems = computed(() => {
  const items = [
    { key: 'myPublic', label: '我的公共经费申请（进行中）', count: pendingInfo.value.myPublic },
    { key: 'myC2c', label: '我的公对公申请（进行中）', count: pendingInfo.value.myC2c },
  ];
  if (isProcurementStaff.value) {
    items.push({ key: 'publicWorkflow', label: '公共经费采购流程待处理', count: pendingInfo.value.publicWorkflow });
  }
  if (authStore.isC2CPlatformManager) {
    items.push({ key: 'c2cWorkflow', label: '公对公采购流程待处理', count: pendingInfo.value.c2cWorkflow });
  }
  return items;
});

// --- 公告相关状态 ---
const announcements = ref([]);
const loadingAnnouncement = ref(true);
// --- END ---

const fetchAnnouncement = async () => {
  loadingAnnouncement.value = true;
  try {
    const response = await apiClient.get('/procurement/announcements/home/');
    announcements.value = normalizeListResponse(response.data);
  } catch (error) {
    console.error("Failed to fetch announcement:", error);
    announcements.value = [];
  } finally {
    loadingAnnouncement.value = false;
  }
};

const normalizeListResponse = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

// 【修改】获取项目列表的函数，指向新API
const fetchProjects = async () => {
  loadingProjects.value = true;
  try {
    // 【重要修改】指向新的、待创建的后端 API 地址
    const response = await apiClient.get('/projects/published-list/'); // <-- 假设的新API地址

    if (Array.isArray(response.data)) {
      projects.value = response.data;
    } else {
      console.error("Failed to fetch projects: API did not return an array.");
      projects.value = [];
    }
  } catch (error) {
     if (error.response && error.response.status === 404) {
         console.log("Published project list API not found (404), maybe not published yet or API not ready.");
         projects.value = []; // 404 也视为空列表
     } else {
        console.error("Failed to fetch projects:", error);
        projects.value = [];
     }
  } finally {
    loadingProjects.value = false;
  }
};

const getCount = async (endpoint, params) => {
  try {
    const response = await apiClient.get(endpoint, { params: { ...params, page_size: 1 } });
    return response.data.count || 0;
  } catch (error) {
    return 0;
  }
};

const fetchPendingInfo = async () => {
  loadingPendingInfo.value = true;
  const myPublicStatuses = 'pending,payment_rejected,paid';
  const myC2cStatuses = 'pending,payment_rejected,pending_purchase_order,pending_contract,paid';
  const workflowStatuses = 'pending,payment_rejected,pending_purchase_order,pending_contract,approved,goods_received,invoiced,accepted,inspection_skipped';
  const publicApprovalStatuses = 'pending,payment_rejected';
  const publicHandledStatuses = 'approved,goods_received,invoiced,accepted,inspection_skipped';

  const [myPublicCount, myC2cCount] = await Promise.all([
    getCount('/procurement/public-purchase-requests/', { scope: 'mine', status__in: myPublicStatuses }),
    getCount('/procurement/c2c-purchase-requests/', { scope: 'mine', status__in: myC2cStatuses }),
  ]);
  pendingInfo.value.myPublic = myPublicCount;
  pendingInfo.value.myC2c = myC2cCount;

  if (isProcurementStaff.value) {
    const [approvalCount, handledCount] = await Promise.all([
      getCount('/procurement/public-purchase-requests/', { scope: 'all', status__in: publicApprovalStatuses }),
      getCount('/procurement/public-purchase-requests/', { scope: 'all', status__in: publicHandledStatuses }),
    ]);
    pendingInfo.value.publicWorkflow = approvalCount + handledCount;
  } else {
    pendingInfo.value.publicWorkflow = 0;
  }

  if (authStore.isC2CPlatformManager) {
    pendingInfo.value.c2cWorkflow = await getCount('/procurement/c2c-purchase-requests/', { scope: 'all', status__in: workflowStatuses });
  } else {
    pendingInfo.value.c2cWorkflow = 0;
  }

  loadingPendingInfo.value = false;
};


onMounted(async () => {
  // 【修改】同时调用 fetchAnnouncement 和 fetchProjects
  fetchAnnouncement();
  fetchPendingInfo();
  fetchProjects();
});

const toggleTeamProcurement = async (newValue) => {
  isSwitchLoading.value = true;
  try {
    const response = await apiClient.post('/users/toggle-team-procurement/');
    authStore.updateTeamProcurementStatus(response.data.team_procurement_enabled);
    ElMessage.success('Settings updated successfully!');
  } catch (error) {
    ElMessage.error('Failed to update settings. Please try again.');
    if (authStore.user) {
      authStore.user.team_procurement_enabled = !newValue;
    }
  } finally {
    isSwitchLoading.value = false;
  }
};
</script>

<style scoped>
/* 原 h2 样式 */
.welcome-message {
  margin: 0;
  font-weight: 400;
  font-size: 1.5rem; /* 保持 h2 的视觉效果 */
}

/* 维护信息样式 */
.maintenance-info {
  font-size: 14px;
  color: #909399; /* Element UI 次要文字颜色 */
  margin-top: 8px; /* 添加间距 */
}
.teacher-info {
  font-size: 14px;
  color: #909399; /* Element UI 次要文字颜色 */
  margin-top: 8px; /* 与上一行保持间距 */
}
/* (统计卡片等样式保持不变) */
.stat-card {
  text-align: center;
}
.stat-unit {
  font-size: 16px;
  margin-left: 4px;
}
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
}
.setting-description {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
.card-header {
  display: flex;
  align-items: center; /* 垂直居中图标和文字 */
}
.card-header span {
    display: flex; /* 让图标和文字在 span 内水平排列 */
    align-items: center;
}
.card-header .el-icon {
    margin-right: 5px; /* 图标和文字间距 */
}

.home-announcement-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.home-announcement-item + .home-announcement-item {
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.home-announcement-item h3 {
  margin: 0 0 8px;
  color: #303133;
  font-size: 17px;
  line-height: 1.4;
}

.announcement-content {
  padding: 0 5px;
  color: #606266;
  white-space: pre-wrap; /* 尊重原文的换行和空格 */
  line-height: 1.6;
  word-break: break-word; /* 长单词换行 */
}

.pending-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pending-item-card {
  text-align: center;
}
</style>
