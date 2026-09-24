<template>
  <div v-loading="isLoading" class="detail-container">
    <div v-if="error" class="error-message">{{ error }}</div>

    <div v-if="detailedRequest">
      <el-descriptions :column="4" border title="申请与采购信息">
        <el-descriptions-item label="申请人">{{ detailedRequest.applicant.name }}</el-descriptions-item>
        <el-descriptions-item label="申请导师">{{ detailedRequest.applicant_tutor?.name || '无' }}</el-descriptions-item>
        <el-descriptions-item v-if="detailedRequest.approved_by" label="审批人">{{ detailedRequest.approved_by.name }}</el-descriptions-item>
        <el-descriptions-item label="申请日期">{{ new Date(detailedRequest.request_date).toLocaleDateString() }}</el-descriptions-item>
        <el-descriptions-item label="采购平台">{{ detailedRequest.platform }}</el-descriptions-item>
        <el-descriptions-item label="总金额">¥{{ detailedRequest.total_price }}</el-descriptions-item>
        <el-descriptions-item label="单号" :span="2">{{ detailedRequest.order_number || 'N/A' }}</el-descriptions-item>
      </el-descriptions>

      <el-descriptions
        v-if="detailedRequest.reimbursement_details"
        :column="4"
        border
        title="报销信息"
        class="item-detail-section"
      >
        <el-descriptions-item label="报销单号">{{ detailedRequest.reimbursement_details.reimbursement_number || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="实际报销金额">
          {{ formatActualAmount(detailedRequest.reimbursement_details.actual_amount) }}
        </el-descriptions-item>
        <el-descriptions-item label="报销单照片" :span="4">
          <el-image
            v-if="detailedRequest.reimbursement_details.reimbursement_photo"
            style="width: 50px; height: 50px"
            :src="detailedRequest.reimbursement_details.reimbursement_photo"
            :preview-src-list="[detailedRequest.reimbursement_details.reimbursement_photo]"
            fit="cover"
            preview-teleported
          />
          <span v-else>未上传</span>
        </el-descriptions-item>
      </el-descriptions>

      <div v-for="(item, index) in detailedRequest.items" :key="item.id" class="item-detail-section">
        <el-descriptions :column="3" border :title="`物品 ${index + 1}: ${item.content}`">
          <el-descriptions-item label="采购类型">{{ item.purchase_type || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="厂商">{{ item.manufacturer || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="CAS号">{{ item.cas_number || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="货号">{{ item.product_number || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="参数">{{ item.parameters || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="规格">{{ item.specifications || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="数量">{{ item.quantity }}</el-descriptions-item>
          <el-descriptions-item label="单价">¥{{ item.unit_price }}</el-descriptions-item>

          <!-- 采购链接：将“复制”按钮放到 label 区域 -->
          <el-descriptions-item :span="3">
            <template #label>
              <span>采购链接</span>
              <el-button
                class="copy-btn-on-label"
                size="small"
                type="primary"
                plain
                :disabled="!item.purchase_link"
                @click.stop="copyPurchaseLink(item.purchase_link)"
              >
                复制
              </el-button>
            </template>

            <template v-if="item.purchase_link">
              <a
                :href="item.purchase_link"
                target="_blank"
                rel="noopener noreferrer"
                class="purchase-link-anchor"
                @click.prevent
              >
                {{ item.purchase_link }}
              </a>
              <span class="copy-hint"></span>
            </template>
            <template v-else>
              <span>N/A</span>
            </template>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';

const props = defineProps({
  request: {
    type: Object,
    required: true,
  },
});

const isLoading = ref(false);
const detailedRequest = ref(null);
const error = ref('');

/** 复制文本：优先 Clipboard API；失败则回退 execCommand */
const copyText = async (text) => {
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) { /* 回退 */ }
  }
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    textarea.style.top = '0';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
    const ok = document.execCommand('copy');
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
};

const copyPurchaseLink = async (link) => {
  if (!link) return;
  const ok = await copyText(link);
  if (ok) ElMessage.success('已复制到剪贴板');
  else ElMessage.error('复制失败，请手动选择并复制');
};

const formatActualAmount = (amount) => {
  if (amount === null || amount === undefined || amount === '') {
    return '未填写';
  }
  const value = Number(amount);
  const display = Number.isFinite(value) ? value.toFixed(2) : String(amount);
  return `¥${display}`;
};

const fetchDetails = async () => {
  if (!props.request?.id) {
    error.value = '无效的申请数据';
    return;
  }
  isLoading.value = true;
  error.value = '';
  try {
    const response = await apiClient.get(`/procurement/full-process-requests/${props.request.id}/`);
    detailedRequest.value = response.data;
  } catch (err) {
    error.value = '获取申请详情失败！';
    ElMessage.error('获取申请详情失败！');
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchDetails();
});
</script>

<style scoped>
.detail-container {
  padding: 20px;
  background-color: #fafafa;
  border-radius: 4px;
  min-height: 150px;
}
.item-detail-section {
  margin-top: 16px;
}
.error-message {
  color: #f56c6c;
  text-align: center;
  padding: 20px;
}
/* 链接样式 */
.purchase-link-anchor {
  color: var(--el-color-primary);
  text-decoration: none;
  word-break: break-all;
  cursor: text; /* 防误点打开 */
}
.purchase-link-anchor:hover {
  text-decoration: underline;
}
/* 标签里的复制按钮 */
.copy-btn-on-label {
  margin-left: 8px;
  vertical-align: middle;
  padding: 3px 10px;
}
/* 提示文字 */
.copy-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
</style>
