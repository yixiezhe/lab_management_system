<template>
  <el-card>
    <template #header>
      <h1>我的小组申请</h1>
    </template>

    <el-tabs v-model="activeTab" @tab-change="fetchMyRequests">
      <el-tab-pane label="待处理" name="pending"></el-tab-pane>
      <el-tab-pane label="已处理" name="processed"></el-tab-pane>
      <el-tab-pane label="已撤回" name="withdrawn"></el-tab-pane>
    </el-tabs>

    <el-table :data="requestList" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="request_date" label="申请日期" width="180" />
      <el-table-column prop="status" label="状态" width="180">
        <template #default="scope">
          <el-tooltip v-if="scope.row.status === 'rejected' && scope.row.rejection_reason"
            :content="`驳回原因: ${scope.row.rejection_reason}`" placement="top">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ statusMap[scope.row.status] || scope.row.status }}
            </el-tag>
          </el-tooltip>
          <el-tag v-else :type="getStatusTagType(scope.row.status)">
            {{ statusMap[scope.row.status] || scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="申请物品详情">
        <template #default="scope">
          <ul><li v-for="item in scope.row.items" :key="item.id">{{ item.content }} (数量: {{ item.quantity }})</li></ul>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <div v-if="scope.row.status === 'pending'">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleWithdraw(scope.row.id)">撤回</el-button>
          </div>
          <el-button v-if="scope.row.status === 'rejected'" size="small" type="primary" @click="handleEdit(scope.row)">
            修改并重新提交
          </el-button>
        </template>
      </el-table-column>
    </el-table>
     <p v-if="!loading && requestList.length === 0" class="no-data">
        当前分类下暂无申请记录
     </p>
  </el-card>

  <el-dialog v-model="dialogVisible" title="编辑小组请购申请" width="75%" :close-on-click-modal="false">
    <TeamProcurementForm v-if="dialogVisible" :initialData="currentItem" @submitSuccess="handleUpdateSuccess" />
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { cloneDeep } from 'lodash-es';
import TeamProcurementForm from '@/components/TeamProcurementForm.vue';

const loading = ref(false);
const requestList = ref([]);
const dialogVisible = ref(false);
const currentItem = ref(null);

// 【修改点 2】新增一个状态来追踪当前选中的 Tab
const activeTab = ref('pending');

const statusMap = { 
  'pending': '待审批', 
  'approved': '已批准', 
  'rejected': '已驳回', 
  'completed': '已完成',
  'withdrawn': '已撤回',
};

const getStatusTagType = (status) => {
  const map = { 
    'pending': 'warning', 
    'approved': '', 
    'completed': 'success', 
    'rejected': 'danger',
    'withdrawn': 'info',
  };
  return map[status] || 'info';
};

// 【修改点 3】重构数据请求函数，使其根据 Tab 请求不同状态的数据
const fetchMyRequests = async () => {
  loading.value = true;
  
  const params = {};
  if (activeTab.value === 'pending') {
    params.status__in = 'pending,rejected';
  } else if (activeTab.value === 'processed') {
    // 小组申请流程简化，已处理只包含 approved
    params.status__in = 'approved,completed';
  } else if (activeTab.value === 'withdrawn') {
    params.status = 'withdrawn';
  }

  try {
    const response = await apiClient.get('/team-procurement/requests/', { params });
    requestList.value = response.data;
  } catch (error) {
    ElMessage.error('获取申请列表失败');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchMyRequests);

const handleEdit = (row) => {
  currentItem.value = cloneDeep(row);
  dialogVisible.value = true;
};

const handleUpdateSuccess = () => {
  dialogVisible.value = false;
  fetchMyRequests();
};

const handleWithdraw = async (id) => {
  try {
    await ElMessageBox.confirm(
      '您确定要撤回此条申请吗？此操作不可逆。',
      '确认撤回',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    await apiClient.post(`/team-procurement/requests/${id}/withdraw/`);
    ElMessage.success('申请已成功撤回');
    fetchMyRequests();

  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败');
    } else {
      ElMessage.info('已取消操作');
    }
  }
};
</script>

<style scoped>
h1 { text-align: center; margin: 0; }
ul { padding-left: 0; list-style-type: none; margin: 0; }
/* 【修改点 4】新增 no-data 样式 */
.no-data {
    text-align: center;
    color: #909399;
    padding: 20px;
}
</style>