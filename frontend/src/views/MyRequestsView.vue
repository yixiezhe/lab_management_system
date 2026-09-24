<template>
  <el-card>
    <template #header>
      <h1>我的申请</h1>
    </template>

    <el-tabs v-model="activeExpenseType" @tab-change="handleTopTabChange">
      <el-tab-pane name="public">
        <template #label>
          <el-badge :value="topTabCounts.public" :hidden="topTabCounts.public === 0" type="danger" class="tab-badge">
            <span>公共经费申请</span>
          </el-badge>
        </template>
      </el-tab-pane>
      <el-tab-pane name="c2c">
        <template #label>
          <el-badge :value="topTabCounts.c2c" :hidden="topTabCounts.c2c === 0" type="danger" class="tab-badge">
            <span>公对公申请</span>
          </el-badge>
        </template>
      </el-tab-pane>
    </el-tabs>

    <el-tabs v-model="activeStatusTab" @tab-change="fetchMyRequests">
      <el-tab-pane name="inProgress">
        <template #label>
          <el-badge :value="counts.inProgress" :hidden="counts.inProgress === 0" type="danger" class="tab-badge">
            <span>进行中</span>
          </el-badge>
        </template>
      </el-tab-pane>
      <el-tab-pane name="toBeProcessed">
        <template #label>
          <el-badge :value="counts.toBeProcessed" :hidden="counts.toBeProcessed === 0" type="danger" class="tab-badge">
            <span>待处理 (被驳回)</span>
          </el-badge>
        </template>
      </el-tab-pane>
      <el-tab-pane label="已完成" name="completed"></el-tab-pane>
    </el-tabs>

    <el-table :data="requestList" stripe style="width: 100%" v-loading="loading" row-key="id">
      <el-table-column type="expand" width="50">
        <template #default="props">
          <RequestDetail :request="props.row" />
        </template>
      </el-table-column>

      <el-table-column prop="request_date" label="申请日期" width="160" />
      
      <el-table-column label="状态" width="160">
        <template #default="scope">
          <el-tag :type="activeStatusTab === 'completed' ? 'success' : getStatusTagType(scope.row.status)">
            {{ activeStatusTab === 'completed' ? '已收货' : statusMap[scope.row.status] || scope.row.status }}
          </el-tag>
          <div v-if="scope.row.status === 'rejected' && scope.row.rejection_reason" class="reason-text">
            {{ scope.row.rejection_reason }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="申请物品概览">
        <template #default="scope">
          <ul>
            <li v-for="item in scope.row.items" :key="item.id">
              {{ item.content }} (数量: {{ item.quantity }})
            </li>
          </ul>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" align="center">
        <template #default="scope">
          <div v-if="activeStatusTab === 'inProgress'">
            <el-button 
              v-if="scope.row.status === 'paid'" 
              size="small" 
              type="primary"
              @click="openReceiptDialog(scope.row)">
              确认收货
            </el-button>
            <span v-else>—</span>
          </div>
          <div v-if="activeStatusTab === 'toBeProcessed'">
             <el-button 
               v-if="scope.row.status === 'rejected'" 
               size="small" 
               type="primary" 
               @click="handleEdit(scope.row)">
               修改并重新提交
             </el-button>
          </div>
          <div v-if="activeStatusTab === 'completed'">
            <el-button
              v-if="scope.row.acceptance"
              size="small"
              type="primary"
              plain
              @click="openModifyReceiptDialog(scope.row)">
              修改收货信息
            </el-button>
            <span v-else>—</span>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && requestList.length === 0" class="no-data">
      当前分类下暂无申请记录
    </p>
  </el-card>

  <el-dialog v-model="dialogVisible" title="编辑请购申请" width="75%" :close-on-click-modal="false">
    <ProcurementForm v-if="dialogVisible" :initialData="currentItem" @submitSuccess="handleUpdateSuccess" />
  </el-dialog>

  <el-dialog v-model="receiptDialogVisible" :title="receiptDialogTitle" width="600px" :close-on-click-modal="false">
    <el-form 
      ref="receiptFormRef" 
      :model="receiptForm" 
      :rules="receiptRules" 
      label-width="100px">
      <el-form-item label="收货情况" prop="receiving_status">
        <el-input 
          v-model="receiptForm.receiving_status" 
          type="textarea" 
          rows="4"
          placeholder="请详细描述物品接收情况，如数量、完好度等" />
      </el-form-item>
      
      <el-form-item label="收货照片" prop="acceptance_photo" required> 
        <el-upload
          v-model:file-list="fileList"
          action="#"
          drag
          list-type="picture"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :on-exceed="handleFileExceed"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将收货照片拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传一张图片
            </div>
          </template>
        </el-upload>
      </el-form-item>
      </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="receiptDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleReceiptSubmit" :loading="submitLoading">
          提交
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import {ref, onMounted, reactive, computed} from 'vue';
import { ElMessage } from 'element-plus';
import { Plus, UploadFilled } from '@element-plus/icons-vue';
import { cloneDeep } from 'lodash-es';
import apiClient from '@/api';
import ProcurementForm from '@/components/ProcurementForm.vue';
import RequestDetail from '@/components/RequestDetail.vue';

const loading = ref(false);
const requestList = ref([]);
const dialogVisible = ref(false);
const currentItem = ref(null);
const activeExpenseType = ref('public'); 
const activeStatusTab = ref('inProgress'); 

const counts = reactive({
  inProgress: 0,
  toBeProcessed: 0,
});
const topTabCounts = reactive({
  public: 0,
  c2c: 0,
});

const isEditMode = ref(false); 
const receiptDialogVisible = ref(false);
const currentRequestForReceipt = ref(null);
const receiptFormRef = ref(null);
const fileList = ref([]);
const submitLoading = ref(false);
const receiptForm = reactive({
  receiving_status: '',
  acceptance_photo: null, 
});

// --- 自定义照片验证函数 ---
const validatePhoto = (rule, value, callback) => {
  if (!receiptForm.acceptance_photo && fileList.value.length === 0 && !isEditMode.value) {
      callback(new Error('请上传收货照片'));
  } else if (!receiptForm.acceptance_photo && fileList.value.length === 0 && isEditMode.value && !currentRequestForReceipt.value?.acceptance?.acceptance_photo){
      callback(new Error('请上传收货照片'));
  }
   else {
      callback(); 
  }
};

// --- 照片验证规则 ---
const receiptRules = reactive({
  receiving_status: [{ required: true, message: '请填写收货情况', trigger: 'blur' }],
  acceptance_photo: [{ validator: validatePhoto, trigger: 'change' }] 
});

const receiptDialogTitle = computed(() => isEditMode.value ? '修改收货信息' : '确认收货信息');

const statusMap = {
  'pending': '待审批', 'approved': '待支付', 'paid': '待收货', 'goods_received': '待开票',
  'accepted': '已验收', 'inspection_skipped': '无需验收', 'invoiced': '待报销',
  'reimbursed': '已报销', 'rejected': '已驳回', 'withdrawn': '已撤回',
  'payment_rejected': '付款被驳回', 'completed': '已完成', 
  'pending_purchase_order': '待请购', 'pending_contract': '待合同',
};

const getStatusTagType = (status) => {
  switch (status) {
    case 'pending': case 'payment_rejected': return 'warning';
    case 'rejected': return 'danger';
    case 'approved': case 'paid': return 'primary';
    case 'goods_received': case 'invoiced': return '';
    case 'accepted': case 'inspection_skipped': case 'reimbursed': case 'completed': return 'success';
    case 'pending_purchase_order': return 'primary';
    case 'pending_contract': return 'primary';
    default: return 'info';
  }
};

const getEndpointByType = (expenseType) => {
  if (expenseType === 'public') return '/procurement/public-purchase-requests/';
  if (expenseType === 'c2c') return '/procurement/c2c-purchase-requests/';
  return '';
};

const getInProgressStatusParams = (expenseType) => {
  if (expenseType === 'c2c') {
    return { status__in: 'pending,payment_rejected,pending_purchase_order,pending_contract,paid' };
  }
  return { status__in: 'pending,payment_rejected,paid' };
};

const getCount = async (expenseType, statusParams) => {
  const endpoint = getEndpointByType(expenseType);
  if (!endpoint) return 0;
  const params = { ...statusParams, page_size: 1 };
  try {
    const response = await apiClient.get(endpoint, { params });
    return response.data.count || 0;
  } catch (error) {
    console.error(`获取数量失败 for status ${JSON.stringify(statusParams)}:`, error);
    return 0;
  }
};

const fetchAllCounts = async () => {
  const [inProgressCount, toBeProcessedCount] = await Promise.all([
    getCount(activeExpenseType.value, getInProgressStatusParams(activeExpenseType.value)),
    getCount(activeExpenseType.value, { status: 'rejected' }),
  ]);

  counts.inProgress = inProgressCount;
  counts.toBeProcessed = toBeProcessedCount;
};

const fetchTopTabCounts = async () => {
  const [publicCount, c2cCount] = await Promise.all([
    getCount('public', getInProgressStatusParams('public')),
    getCount('c2c', getInProgressStatusParams('c2c')),
  ]);
  topTabCounts.public = publicCount;
  topTabCounts.c2c = c2cCount;
};


const fetchMyRequests = async () => {
  loading.value = true;
  const params = {};
  switch (activeStatusTab.value) {
    case 'inProgress':
      Object.assign(params, getInProgressStatusParams(activeExpenseType.value));
      break;
    case 'toBeProcessed':
      params.status = 'rejected';
      break;
    case 'completed':
      params.status__in = 'goods_received,accepted,inspection_skipped,invoiced,reimbursed,completed';
      break;
  }

  let endpoint = '';
  if (activeExpenseType.value === 'public') {
    endpoint = '/procurement/public-purchase-requests/';
  } else if (activeExpenseType.value === 'c2c') {
    endpoint = '/procurement/c2c-purchase-requests/';
  } else {
    ElMessage.error('未知的申请类型！');
    loading.value = false;
    return;
  }

  try {
    const response = await apiClient.get(endpoint, { params });
    requestList.value = response.data.results || [];
  } catch (error) {
    ElMessage.error('获取申请列表失败。');
    requestList.value = [];
  } finally {
    loading.value = false;
  }
};

const handleDataRefresh = () => {
  fetchMyRequests();
  fetchAllCounts();
  fetchTopTabCounts();
}

onMounted(handleDataRefresh);

const handleTopTabChange = () => {
  activeStatusTab.value = 'inProgress';
  handleDataRefresh();
}

const handleEdit = (row) => {
  currentItem.value = cloneDeep(row);
  dialogVisible.value = true;
};

const handleUpdateSuccess = () => {
  dialogVisible.value = false;
  handleDataRefresh();
};

const openReceiptDialog = (request) => {
  isEditMode.value = false;
  currentRequestForReceipt.value = request;
  receiptForm.receiving_status = '';
  receiptForm.acceptance_photo = null;
  fileList.value = [];
  receiptDialogVisible.value = true;
  if (receiptFormRef.value) {
      receiptFormRef.value.resetFields();
  }
};

const openModifyReceiptDialog = (request) => {
  isEditMode.value = true;
  currentRequestForReceipt.value = request;
  if (request.acceptance) {
    receiptForm.receiving_status = request.acceptance.receiving_status;
    fileList.value = request.acceptance.acceptance_photo ? [{ name: 'existing_photo', url: request.acceptance.acceptance_photo, status: 'success' }] : [];
  } else {
    receiptForm.receiving_status = '';
    fileList.value = [];
  }
  receiptForm.acceptance_photo = null; 
  receiptDialogVisible.value = true;
  if (receiptFormRef.value) {
      receiptFormRef.value.resetFields();
  }
};


const handleFileChange = (uploadFile, uploadFiles) => {
  receiptForm.acceptance_photo = uploadFile.raw;
  fileList.value = uploadFiles.slice(-1); 
  if (receiptFormRef.value) {
      receiptFormRef.value.validateField('acceptance_photo');
  }
};

const handleFileRemove = (uploadFile, uploadFiles) => {
  receiptForm.acceptance_photo = null;
  fileList.value = uploadFiles;
   if (receiptFormRef.value) {
      receiptFormRef.value.validateField('acceptance_photo');
  }
}

const handleFileExceed = (files, uploadFiles) => {
    const newFile = files[0];
    fileList.value = [{ name: newFile.name, raw: newFile, url: URL.createObjectURL(newFile) }]; 
    receiptForm.acceptance_photo = newFile; 
    ElMessage.warning('已替换为新选择的照片');
    if (receiptFormRef.value) {
        receiptFormRef.value.validateField('acceptance_photo');
    }
}

const handleReceiptSubmit = async () => {
  if (!receiptFormRef.value) return;
  
  if (fileList.value.length === 0) {
      receiptForm.acceptance_photo = null;
  }

  await receiptFormRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true;
      const formData = new FormData();
      formData.append('receiving_status', receiptForm.receiving_status);

      if (receiptForm.acceptance_photo instanceof File) {
        formData.append('acceptance_photo', receiptForm.acceptance_photo);
      } else if (!isEditMode.value && !receiptForm.acceptance_photo) {
          ElMessage.error('请上传收货照片');
          submitLoading.value = false;
          return;
      }

      try {
        if (isEditMode.value) {
          await apiClient.patch(`/acceptance/acceptances/${currentRequestForReceipt.value.acceptance.id}/`, formData);
          ElMessage.success('收货信息修改成功！');
        } else {
          formData.append('purchase_request', currentRequestForReceipt.value.id);
          await apiClient.post('/acceptance/acceptances/', formData);
          ElMessage.success('收货信息提交成功！');
        }
        receiptDialogVisible.value = false;
        handleDataRefresh();
      } catch (error) {
        ElMessage.error(error?.response?.data?.detail || '操作失败，请重试。');
      } finally {
        submitLoading.value = false;
      }
    } else {
        ElMessage.error('请检查表单输入项。');
    }
  });
};
</script>

<style scoped>
.reason-text {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 4px;
}
.no-data {
  text-align: center;
  color: #909399;
  padding: 20px;
}
ul {
  padding-left: 1.2em;
  margin: 0;
}
.tab-badge :deep(.el-badge__content) {
    top: 1px;
    transform: translateX(160%);
    z-index: 1;
}
/* 样式，使拖拽框在弹窗内宽度 100% */
:deep(.el-upload-dragger) {
  width: 100%;
}

/* --- 【修改】修复 el-upload-list 中长文件名溢出的问题 (增强版) --- */
:deep(.el-upload-list__item-name) {
  /* 1. 允许在任意字符处换行 (标准) */
  overflow-wrap: break-word;
  /* 2. 允许在 CJK 字符间换行 (备选) */
  word-break: break-all;
  /* 3. 覆盖 el-upload 默认的 nowrap */
  white-space: normal;
  /* 4. 【关键】确保 flex item 在内容溢出时可以正确收缩 */
  min-width: 0;
  /* 5. 调整行高以便换行后正常显示 */
  line-height: 1.2;
}
/* --- 【修改结束】 --- */
</style>
