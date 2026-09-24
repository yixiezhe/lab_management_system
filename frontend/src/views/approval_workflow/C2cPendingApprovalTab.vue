<template>
  <div>
    <el-table :data="requests" stripe border style="width: 100%" row-key="id">
      <el-table-column type="expand">
        <template #default="props">
          <RequestDetail :request="props.row" />
        </template>
      </el-table-column>
      <el-table-column prop="order_number" label="单号" />
      <el-table-column prop="applicant.name" label="申请人" width="120" />
      <el-table-column prop="request_date" label="申请日期" width="120" />
      <el-table-column label="状态" width="120">
        <template #default="scope">
          <el-tag :type="getStatusTagType(scope.row.status)">
            {{ statusMap[scope.row.status] || scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="platform" label="采购平台" width="150" />
      <el-table-column label="操作" fixed="right" width="180">
        <template #default="scope">
          <el-button size="small" type="success" @click="handleApprove(scope.row)">批准</el-button>
          <el-button size="small" type="danger" @click="handleReject(scope.row.id)">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>
    </div>
</template>

<script setup>
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useAuthStore } from '@/stores/auth';
import RequestDetail from '@/components/RequestDetail.vue';

const props = defineProps({
  requests: {
    type: Array,
    required: true,
  },
});
const emit = defineEmits(['refresh-data']);
const authStore = useAuthStore();

const statusMap = {
  'pending': '待审批',
  'payment_rejected': '付款被驳回',
};
const getStatusTagType = (status) => {
  switch (status) {
    case 'pending': case 'payment_rejected': return 'warning';
    default: return 'info';
  }
};

const handleApprove = (request) => {
  ElMessageBox.confirm(
    '确定要批准此采购申请吗？批准后将进入“待请购”环节。',
    '确认批准',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info',
    }
  ).then(async () => {
      try {
        ElMessage({ type: 'info', message: '正在处理...' });
        // 【已修改】使用新的 "c2c" 流程 API 地址
        await apiClient.post(`/procurement/c2c-purchase-requests/${request.id}/approve/`, {});
        ElMessage.success('操作成功：已批准');
        emit('refresh-data');
        authStore.fetchApproverPendingCount();
      } catch(error) {
        const errorMsg = error.response?.data?.error || '操作失败，请重试。';
        ElMessage.error(errorMsg);
      }
  }).catch(() => {
    ElMessage.info('已取消操作');
  });
};

const handleReject = (id) => {
  ElMessageBox.prompt('请输入驳回原因', '驳回申请', {
    confirmButtonText: '确定驳回',
    cancelButtonText: '取消',
    inputValidator: (value) => {
      if (!value || value.trim().length === 0) return '必须填写驳回原因';
      return true;
    }
  }).then(async ({ value }) => {
    try {
      // 【已修改】使用新的 "c2c" 流程 API 地址
      await apiClient.post(`/procurement/c2c-purchase-requests/${id}/reject/`, { reason: value });
      ElMessage.success('操作成功：已驳回');
      emit('refresh-data');
      authStore.fetchApproverPendingCount();
    } catch (error) {
      ElMessage.error('操作失败');
    }
  }).catch(() => {
     ElMessage.info('已取消操作');
  });
};
</script>

<style scoped>
/* 样式保持不变 */
</style>