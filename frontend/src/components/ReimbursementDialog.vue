<template>
  <el-dialog
    title="上传报销单"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    width="500px"
    :close-on-click-modal="false"
    @open="resetForm"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="110px" v-loading="isLoading">
      <el-form-item label="报销单号" prop="reimbursement_number">
        <el-input v-model="form.reimbursement_number" placeholder="请输入报销单号" />
      </el-form-item>
      <el-form-item v-if="!isMerged" label="报销实际金额" prop="actual_amount">
        <el-input-number
          v-model="form.actual_amount"
          :min="0"
          :precision="2"
          :step="0.01"
          style="width: 200px;"
          controls-position="right"
          placeholder="请输入实际报销金额"
        />
        <span class="amount-hint" v-if="singleRequestTotal">
          申请金额：¥{{ singleRequestTotal }}
        </span>
      </el-form-item>

      <div v-else class="merged-amounts">
        <div class="merged-header">
          <span>合并申请实际报销金额</span>
          <el-button size="small" @click="fillAmountsFromTotals">一键填充申请金额</el-button>
        </div>
        <el-table :data="requestInfos" size="small" border>
          <el-table-column prop="order_number" label="单号" min-width="160" />
          <el-table-column prop="total_price" label="申请金额" width="120">
            <template #default="scope">¥{{ scope.row.total_price }}</template>
          </el-table-column>
          <el-table-column label="实际报销金额" min-width="160">
            <template #default="scope">
              <el-input-number
                v-model="perRequestAmounts[scope.row.id]"
                :min="0"
                :precision="2"
                :step="0.01"
                controls-position="right"
                style="width: 140px;"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-form-item label="报销单照片" prop="reimbursement_photo">
        <el-upload
          class="reimbursement-uploader"
          drag
          action="#" 
          :auto-upload="false"
          :limit="1"
          list-type="picture"
          :on-exceed="handleExceed"
          v-model:file-list="fileList"
          accept="image/*"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传一张图片文件
            </div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="isLoading">提交</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import apiClient from '@/api';

const props = defineProps({
  modelValue: Boolean, // 用于 v-model
  requestId: [Number, String, Array] // 传入的采购申请ID
});

const emit = defineEmits(['update:modelValue', 'upload-success']);

const formRef = ref(null);
const isLoading = ref(false);
const fileList = ref([]); // 存储 el-upload 的文件列表

// 表单数据
const form = reactive({
  reimbursement_number: '',
  actual_amount: null,
});

const requestInfos = ref([]);
const perRequestAmounts = reactive({});
const isMerged = computed(() => requestInfos.value.length > 1);
const singleRequestTotal = computed(() => {
  if (requestInfos.value.length !== 1) return '';
  const value = Number(requestInfos.value[0]?.total_price || 0);
  return Number.isFinite(value) ? value.toFixed(2) : '';
});

// 表单验证规则
const rules = reactive({
  reimbursement_number: [
    { required: true, message: '请输入报销单号', trigger: 'blur' }
  ],
  actual_amount: [
    { required: true, message: '请输入报销实际金额', trigger: 'blur' }
  ],
  // 我们将通过检查 fileList.value 的长度来手动验证图片
});

// 处理文件超出限制
const handleExceed = (files) => {
  // 替换掉已有的文件
  fileList.value = [files[0]];
  ElMessage.warning('已替换当前文件');
};

// 重置表单（在弹窗打开时调用）
const resetForm = () => {
  // 清空表单输入
  if (formRef.value) {
    formRef.value.resetFields();
  }
  form.actual_amount = null;
  // 清空上传列表
  fileList.value = [];
  isLoading.value = false;
  requestInfos.value = [];
  Object.keys(perRequestAmounts).forEach((key) => delete perRequestAmounts[key]);
};

const normalizeRequestIds = () => {
  const ids = Array.isArray(props.requestId) ? props.requestId : [props.requestId];
  return ids.filter((id) => id !== null && id !== undefined && id !== '');
};

const loadRequestInfos = async () => {
  const ids = normalizeRequestIds();
  if (ids.length === 0) {
    requestInfos.value = [];
    return;
  }
  isLoading.value = true;
  try {
    const responses = await Promise.all(
      ids.map((id) => apiClient.get(`/procurement/full-process-requests/${id}/`))
    );
    requestInfos.value = responses.map((res) => res.data);
    if (requestInfos.value.length === 1) {
      const info = requestInfos.value[0];
      const fallback = Number(info?.total_price || 0);
      const existing = info?.reimbursement_details?.actual_amount;
      form.actual_amount = existing !== null && existing !== undefined
        ? Number(existing)
        : (Number.isFinite(fallback) ? Number(fallback) : null);
    } else {
      requestInfos.value.forEach((info) => {
        const fallback = Number(info?.total_price || 0);
        const existing = info?.reimbursement_details?.actual_amount;
        perRequestAmounts[info.id] = existing !== null && existing !== undefined
          ? Number(existing)
          : (Number.isFinite(fallback) ? Number(fallback) : null);
      });
    }
  } catch (error) {
    ElMessage.error('获取申请详情失败，无法初始化报销金额。');
    requestInfos.value = [];
  } finally {
    isLoading.value = false;
  }
};

const fillAmountsFromTotals = () => {
  requestInfos.value.forEach((info) => {
    const fallback = Number(info?.total_price || 0);
    perRequestAmounts[info.id] = Number.isFinite(fallback) ? Number(fallback) : null;
  });
};

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return;

  // 1. 手动验证 el-upload
  if (fileList.value.length === 0) {
    ElMessage.error('请上传报销单照片');
    return;
  }

  // 2. 验证 el-form
  formRef.value.validate(async (valid) => {
    if (valid) {
      isLoading.value = true;
      
      // 3. 创建 FormData
      const validRequestIds = normalizeRequestIds();
      if (validRequestIds.length === 0) {
        ElMessage.error('未找到需要上传的报销申请。');
        isLoading.value = false;
        return;
      }

      if (requestInfos.value.length > 1) {
        const missing = requestInfos.value.find((info) => {
          const value = perRequestAmounts[info.id];
          return value === null || value === undefined || value === '';
        });
        if (missing) {
          ElMessage.error('请填写所有合并申请的实际报销金额。');
          isLoading.value = false;
          return;
        }
      } else if (form.actual_amount === null || form.actual_amount === undefined || form.actual_amount === '') {
        ElMessage.error('请输入报销实际金额');
        isLoading.value = false;
        return;
      }

      try {
        const uploadPromises = validRequestIds.map((requestId) => {
          const formData = new FormData();
          formData.append('reimbursement_number', form.reimbursement_number);
          if (requestInfos.value.length > 1) {
            formData.append('actual_amount', perRequestAmounts[requestId]);
          } else {
            formData.append('actual_amount', form.actual_amount);
          }
          // reimbursement_photo must be a File object (fileList.value[0].raw)
          formData.append('reimbursement_photo', fileList.value[0].raw);
          // purchase_request is the related request ID for backend
          formData.append('purchase_request', requestId);
          return apiClient.post('/reimbursement/reimbursements/', formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          });
        });
        await Promise.all(uploadPromises);

        ElMessage.success('报销单上传成功！');
        emit('upload-success'); // 通知父组件刷新
        emit('update:modelValue', false); // 关闭弹窗
      } catch (error) {
        console.error('报销单提交失败:', error);
        ElMessage.error('报销单提交失败，请检查网络或联系管理员。');
      } finally {
        isLoading.value = false;
      }
    } else {
      ElMessage.error('请检查表单是否填写完整');
    }
  });
};

// 监听弹窗v-model的变化，如果变为true（即打开），则重置表单
watch(() => props.modelValue, (newValue) => {
  if (newValue) {
    resetForm();
    loadRequestInfos();
  }
});

watch(() => props.requestId, () => {
  if (props.modelValue) {
    loadRequestInfos();
  }
});
</script>

<style scoped>
.reimbursement-uploader {
  width: 100%;
}
.amount-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}
.merged-amounts {
  margin-bottom: 16px;
}
.merged-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}
/* 确保 el-upload 拖拽框撑满宽度 */
:deep(.el-upload-dragger) {
  width: 100%;
  padding: 20px;
}
.el-upload__tip {
  text-align: center;
}
</style>
