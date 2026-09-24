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

    <el-dialog v-model="approveDialogVisible" title="批准并上传支付截图" width="50%" :close-on-click-modal="false">
      <div>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-exceed="handleExceed"
          v-model:file-list="fileList"
          list-type="picture"
          drag
          action="#"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将支付截图拖到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              批准后将直接进入“待收货”环节，请上传支付成功的截图。
            </div>
          </template>
        </el-upload>
      </div>
      <template #footer>
        <el-button @click="approveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitApproval" :loading="submitLoading">确认批准</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useAuthStore } from '@/stores/auth';
import { UploadFilled } from '@element-plus/icons-vue';
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

const approveDialogVisible = ref(false);
const submitLoading = ref(false);
const currentRequest = ref(null);
const uploadRef = ref(null);
const fileList = ref([]);

const handleApprove = (request) => {
  currentRequest.value = request;
  fileList.value = [];
  approveDialogVisible.value = true;
};

const handleExceed = (files) => {
  uploadRef.value.clearFiles();
  const file = files[0];
  uploadRef.value.handleStart(file);
};

const submitApproval = async () => {
  submitLoading.value = true;
  try {
    if (fileList.value.length === 0) {
      ElMessage.warning('请选择要上传的支付截图');
      submitLoading.value = false;
      return;
    }
    const formData = new FormData();
    formData.append('payment_photo', fileList.value[0].raw);

    await apiClient.post(`/procurement/public-purchase-requests/${currentRequest.value.id}/approve/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    ElMessage.success('操作成功：已批准');
    approveDialogVisible.value = false;
    emit('refresh-data');
    authStore.fetchApproverPendingCount();

  } catch (error) {
    const errorMsg = error.response?.data?.error || '操作失败，请重试。';
    ElMessage.error(errorMsg);
  } finally {
    submitLoading.value = false;
  }
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
      await apiClient.post(`/procurement/public-purchase-requests/${id}/reject/`, { reason: value });
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
/* Styles can be minimal as detail is handled by child component */
</style>