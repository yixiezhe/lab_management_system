<template>
  <el-card>
    <template #header>
      <h1>付款管理</h1>
    </template>

    <el-table :data="requestList" v-loading="loading" style="width: 100%" border row-key="id">
      <el-table-column type="expand">
        <template #default="props">
          <div class="expanded-content">
            <strong>采购物品详情:</strong>
            <ul>
              <li v-for="item in props.row.items" :key="item.id" class="item-detail-li">
                <div>
                  <span>{{ item.content }} ({{ item.specifications }}) - ¥{{ item.unit_price }} x {{ item.quantity }}</span>
                </div>
                <div v-if="item.purchase_link" class="link-display-area">
                  <strong class="link-label">采购链接:</strong>
                  <div class="link-text-box">
                    {{ item.purchase_link }}
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="applicant.name" label="申请人" />
      <el-table-column prop="applicant.assigned_tutor.name" label="申请人导师" />
      <el-table-column prop="request_date" label="申请日期" />
      <el-table-column prop="platform" label="采购平台" />
      <el-table-column prop="total_price" label="总金额">
        <template #default="scope">¥{{ scope.row.total_price }}</template>
      </el-table-column>
      
      <el-table-column label="支付状态" width="120">
        <template #default="scope">
          <el-tag :type="scope.row.payment ? 'success' : 'danger'">
            {{ scope.row.payment ? '已上传' : '未上传' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="220" fixed="right">
        <template #default="scope">
          <el-button size="small" type="primary" @click="handlePay(scope.row)">
            {{ scope.row.payment ? '修改支付信息' : '确认支付' }}
          </el-button>
          <el-button v-if="!scope.row.payment" size="small" type="danger" @click="handleReject(scope.row)">
            驳回
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="requestList.length === 0 && !loading" class="no-data">暂无待支付的申请</p>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="400px" :close-on-click-modal="false">
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
        将文件拖到此处，或 <em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">
          请上传支付成功的截图（仅限一张图片）
        </div>
      </template>
    </el-upload>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitPayment" :loading="isSubmitting">确认上传</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';

const loading = ref(true);
const isSubmitting = ref(false);
const requestList = ref([]);
const dialogVisible = ref(false);
const currentRequest = ref(null);
const uploadRef = ref(null);
const fileList = ref([]);
const authStore = useAuthStore();

const dialogTitle = computed(() => currentRequest.value?.payment ? '修改支付截图' : '上传支付截图');

const fetchRequests = async () => {
  loading.value = true;
  try {
    // --- START OF FIX ---
    // 重构为单次、高效的API调用
    // 1. 直接请求 full-process-requests 接口以获取所有详细信息。
    // 2. 使用 status__in 参数筛选出 "待支付(approved)" 和 "已支付(paid)" 两种状态。
    // 3. 正确处理分页后的数据结构 `response.data.results`。
    const response = await apiClient.get('/procurement/full-process-requests/', {
      params: { 
        status__in: 'approved,paid',
        expense_type: 'public', // 付款管理只处理公共经费
      }
    });
    requestList.value = response.data.results || []; // 使用 response.data.results
    // --- END OF FIX ---
  } catch (error) {
    ElMessage.error('获取待支付列表失败');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchRequests);

const handleReject = async (request) => {
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入驳回原因（例如：付款链接已失效，请采购员更新）。该原因将反馈给采购审批人。',
      '驳回采购申请',
      {
        confirmButtonText: '确定驳回',
        cancelButtonText: '取消',
        inputValidator: (val) => {
          if (!val || val.trim() === '') {
            return '必须填写驳回原因';
          }
          return true;
        },
      }
    );

    // 注意：这个驳回功能可能需要一个专用的后端API，这里暂时假设一个接口路径
    // 如果这个接口不存在，您需要告诉我，我们可以创建它。
    await apiClient.post(`/procurement/purchase-requests/${request.id}/reject_payment/`, { reason: value });
    
    ElMessage.success('该申请已成功驳回');
    await fetchRequests();
    authStore.fetchApproverPendingCount();

  } catch (error) {
    if (error === 'cancel') {
      ElMessage.info('已取消驳回操作');
    } else {
      const errorMsg = error.response?.data?.error || '驳回操作失败，请重试';
      ElMessage.error(errorMsg);
    }
  }
};


const handlePay = (request) => {
  currentRequest.value = request;
  fileList.value = [];
  dialogVisible.value = true;
};

const handleExceed = (files) => {
  uploadRef.value.clearFiles();
  const file = files[0];
  uploadRef.value.handleStart(file);
};

const submitPayment = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择要上传的支付截图');
    return;
  }

  isSubmitting.value = true;
  const formData = new FormData();
  formData.append('purchase_request', currentRequest.value.id);
  formData.append('payment_photo', fileList.value[0].raw);

  try {
    const isUpdate = !!currentRequest.value.payment;
    
    if (isUpdate) {
      await apiClient.patch(`/payment/payments/${currentRequest.value.payment.id}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      ElNotification({ title: '成功', message: '支付信息修改成功！', type: 'success' });
    } else {
      await apiClient.post('/payment/payments/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      ElNotification({ title: '成功', message: '支付记录上传成功！', type: 'success' });
    }
    
    dialogVisible.value = false;
    await fetchRequests();

  } catch (error) {
    ElMessage.error('操作失败，请稍后重试');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
h1 { text-align: center; margin: 0; }
.no-data { text-align: center; color: #909399; padding: 20px; }
.expanded-content { padding: 10px 20px; }
.expanded-content ul { list-style-type: none; padding-left: 0; }

.item-detail-li {
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid #f0f2f5;
}
.item-detail-li:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.link-display-area {
  margin-top: 8px;
}
.link-label {
  font-weight: 500;
  font-size: 14px;
  color: #303133;
}
.link-text-box {
  background-color: #f4f4f5;
  padding: 8px 10px;
  border-radius: 4px;
  margin-top: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}
</style>