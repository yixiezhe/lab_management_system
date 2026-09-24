<template>
  <div class="pending-invoicing-tab">
    <el-card v-for="request in requests" :key="request.id" class="request-card">
      <div class="card-summary">
        <div class="info-section">
          <span><strong>单号:</strong> {{ request.order_number || 'N/A' }}</span>
          <span><strong>申请人:</strong> {{ request.applicant.name }}</span>
          <span><strong>当前状态:</strong>
            <el-tag :type="getStatusTagType(request.status)" size="small">
              {{ statusMap[request.status] || '未知' }}
            </el-tag>
          </span>
        </div>
        <div class="action-section">
          <el-button type="primary" size="small" @click="handleStartInvoicing(request)">
            {{ (invoicingState[request.id]?.details?.invoices?.length || invoicingState[request.id]?.details?.invoice) ? '编辑发票信息' : '填写发票信息' }}
          </el-button>
        </div>
      </div>

      <el-collapse-transition>
        <div v-if="invoicingState[request.id]?.isEditing">
          <el-divider />
          <div v-loading="invoicingState[request.id]?.isLoadingDetails" class="details-wrapper">
            <template v-if="invoicingState[request.id]?.details">
              <div class="details-container">

                <el-descriptions title="1. 申请与收货信息" :column="3" border>
                  <el-descriptions-item label="申请人">{{ invoicingState[request.id].details.applicant.name }}</el-descriptions-item>
                  <el-descriptions-item label="申请导师">{{ invoicingState[request.id].details.applicant.assigned_tutor?.name || '无' }}</el-descriptions-item>
                  
                  <el-descriptions-item v-if="invoicingState[request.id].details.approved_by" label="审批人">{{ invoicingState[request.id].details.approved_by.name }}</el-descriptions-item>

                  <el-descriptions-item label="申请日期">{{ new Date(invoicingState[request.id].details.request_date).toLocaleDateString() }}</el-descriptions-item>
                  <el-descriptions-item label="采购平台">{{ invoicingState[request.id].details.platform }}</el-descriptions-item>
                  <el-descriptions-item label="单号">{{ invoicingState[request.id].details.order_number }}</el-descriptions-item>
                  <el-descriptions-item label="总金额">¥{{ invoicingState[request.id].details.total_price }}</el-descriptions-item>

                  <el-descriptions-item label="采购物品" :span="3">
                    <div v-for="(item, index) in invoicingState[request.id].details.items" :key="item.id" class="item-block">
                      <p class="item-title"><strong>物品 {{ index + 1 }}: {{ item.content }}</strong></p>
                      <el-descriptions :column="2" border size="small">
                        <el-descriptions-item label="采购类型">{{ item.purchase_type }}</el-descriptions-item>
                        <el-descriptions-item label="厂商">{{ item.manufacturer || '未填写' }}</el-descriptions-item>
                        <el-descriptions-item label="CAS号">{{ item.cas_number || '未填写' }}</el-descriptions-item>
                        <el-descriptions-item label="货号">{{ item.product_number || '未填写' }}</el-descriptions-item>
                        <el-descriptions-item label="参数">{{ item.parameters || '未填写' }}</el-descriptions-item>
                        <el-descriptions-item label="规格">{{ item.specifications || '未填写' }}</el-descriptions-item>
                        <el-descriptions-item label="数量">{{ item.quantity }}</el-descriptions-item>
                        <el-descriptions-item label="单价">¥{{ item.unit_price }}</el-descriptions-item>
                      </el-descriptions>
                    </div>
                  </el-descriptions-item>

                  <el-descriptions-item label="收货情况" :span="3">{{ invoicingState[request.id].details.acceptance?.receiving_status || '未填写' }}</el-descriptions-item>
                  <el-descriptions-item label="收货照片">
                      <el-image
                        v-if="invoicingState[request.id].details.acceptance?.acceptance_photo"
                        style="width: 50px; height: 50px"
                        :src="resolveMediaUrl(invoicingState[request.id].details.acceptance.acceptance_photo)"
                        :preview-src-list="[resolveMediaUrl(invoicingState[request.id].details.acceptance.acceptance_photo)]"
                        fit="cover"
                        preview-teleported
                      />
                    <span v-else>未上传</span>
                  </el-descriptions-item>
                  </el-descriptions>

                <el-form
                  v-if="isC2cRequest(invoicingState[request.id].details)"
                  label-width="120px"
                  class="actual-payment-form"
                >
                  <el-form-item label="实际支付金额" required>
                    <el-input-number
                      v-model="actualPaymentAmounts[request.id]"
                      :min="0"
                      :precision="2"
                      :step="0.01"
                      controls-position="right"
                      placeholder="请输入实际支付金额"
                      style="width: 220px;"
                    />
                  </el-form-item>
                </el-form>

                <div v-if="invoiceFormsData[request.id]">
                  <div v-for="(invoiceForm, formIndex) in invoiceFormsData[request.id]" :key="invoiceForm.id || formIndex" class="invoice-form-block">
                    <el-divider content-position="left">发票信息 {{ formIndex + 1 }}</el-divider>
                    <el-form
                      :ref="(el) => setInvoiceFormRef(request.id, formIndex, el)"
                      :model="invoiceForm"
                      :rules="invoiceFormRules"
                      label-width="120px"
                      class="invoice-form"
                    >
                      <el-form-item label="发票单号" prop="invoice_number">
                        <el-input v-model="invoiceForm.invoice_number" placeholder="请输入发票单号" />
                      </el-form-item>
                      <el-form-item label="发票公司" prop="company_name">
                        <el-input v-model="invoiceForm.company_name" placeholder="请输入开票公司全称" />
                      </el-form-item>

                      <el-form-item label="是否需要验收" prop="requires_acceptance">
                        <el-switch v-model="invoiceForm.requires_acceptance" />
                        <el-alert
                          title="根据规定，单价大于300元或总价大于1000元的耗材需要验收，请酌情勾选。"
                          type="info" show-icon :closable="false" style="margin-top: 8px; line-height: 1.5;"
                        />
                      </el-form-item>

                      <el-form-item label="发票文件" prop="invoice_image">
                        <el-upload
                          :ref="(el) => setUploadRef(request.id, formIndex, el)"
                          :file-list="fileLists[request.id][formIndex]"
                          action="#"
                          drag
                          list-type="picture"
                          :accept="INVOICE_FILE_ACCEPT"
                          :auto-upload="false"
                          :limit="1"
                          :on-change="(file, files) => handleFileChange(file, files, request.id, formIndex)"
                          :on-remove="(file, files) => handleFileRemove(file, files, request.id, formIndex)"
                          :on-exceed="(files) => handleFileExceed(files, request.id, formIndex)"
                        >
                          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                          <div class="el-upload__text">
                            将发票图片或PDF拖到此处，或<em>点击上传</em>
                          </div>
                          <template #tip>
                            <div class="el-upload__tip">
                              支持图片或 PDF，只能上传一个文件
                            </div>
                          </template>
                        </el-upload>
                      </el-form-item>
                      <el-form-item>
                        <el-button type="primary" @click="submitInvoiceForm(request.id, formIndex)" :loading="isSubmitting">提交发票</el-button>
                        <el-button @click="handleCancelInvoicing(request.id)">取消</el-button>
                        <el-button type="primary" plain @click="addInvoiceForm(request.id)">新增发票信息</el-button>
                        <el-button
                          v-if="!invoiceForm.id"
                          type="danger"
                          plain
                          @click="removeInvoiceForm(request.id, formIndex)"
                          :icon="Close"
                        >
                          删除此条
                        </el-button>
                      </el-form-item>
                    </el-form>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </el-collapse-transition>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { UploadFilled, Close } from '@element-plus/icons-vue';

const props = defineProps({
  requests: { type: Array, required: true },
});
const emit = defineEmits(['refresh-data']);

const invoicingState = reactive({});
const isSubmitting = ref(false);
const invoiceFormRefs = ref({});
const uploadRefs = ref({}); // 【新】存储 el-upload 组件的引用

const invoiceFormsData = reactive({});
const fileLists = reactive({});
const actualPaymentAmounts = reactive({});
const INVOICE_FILE_ACCEPT = 'image/*,.pdf,application/pdf';
const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tif', 'tiff']);

const resolveMediaUrl = (url) => {
  if (!url) return '';
  const raw = String(url);
  const normalized = raw.split('\\').join('/');
  const mediaIndex = normalized.indexOf('/media/');
  if (mediaIndex !== -1) return normalized.slice(mediaIndex);
  if (normalized.includes('media/')) return '/' + normalized.slice(normalized.indexOf('media/'));
  if (normalized.startsWith('/')) return normalized;
  if (normalized.startsWith('http://') || normalized.startsWith('https://')) return normalized;
  return `/media/${normalized.replace(/^\/+/, '')}`;
};

const invoiceFormRules = {
  invoice_number: [{ required: true, message: '请输入发票单号', trigger: 'blur' }],
  company_name: [{ required: true, message: '请输入开票公司全称', trigger: 'blur' }],
  invoice_image: [{ required: true, message: '请上传发票文件', trigger: 'change' }],
};

const getFileExtension = (name = '') => {
  const cleanName = String(name).split('?')[0].split('#')[0];
  const index = cleanName.lastIndexOf('.');
  return index === -1 ? '' : cleanName.slice(index + 1).toLowerCase();
};

const isSupportedInvoiceFile = (file) => {
  if (!file) return false;
  const type = (file.type || '').toLowerCase();
  const ext = getFileExtension(file.name);
  return type.startsWith('image/') || type === 'application/pdf' || ext === 'pdf' || IMAGE_EXTENSIONS.has(ext);
};

const getInvoiceFileName = (url) => {
  const normalized = String(url || '').split('\\').join('/');
  const name = normalized.split('/').pop()?.split('?')[0] || '发票文件';
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
};

const ensureRequestState = (requestId) => {
  if (!invoiceFormsData[requestId]) invoiceFormsData[requestId] = [];
  if (!fileLists[requestId]) fileLists[requestId] = [];
  if (!invoiceFormRefs.value[requestId]) invoiceFormRefs.value[requestId] = [];
  if (!uploadRefs.value[requestId]) uploadRefs.value[requestId] = [];
};

const setInvoiceFormRef = (requestId, formIndex, el) => {
  ensureRequestState(requestId);
  invoiceFormRefs.value[requestId][formIndex] = el;
};

const setUploadRef = (requestId, formIndex, el) => {
  ensureRequestState(requestId);
  uploadRefs.value[requestId][formIndex] = el;
};

const createEmptyInvoiceForm = (request) => ({
  id: null,
  invoice_number: '',
  company_name: '',
  invoice_image: null,
  requires_acceptance: request?.expense_type === 'c2c',
});

const addInvoiceForm = (requestId) => {
  const request = invoicingState[requestId]?.details || props.requests.find(item => item.id === requestId);
  ensureRequestState(requestId);
  invoiceFormsData[requestId].push(createEmptyInvoiceForm(request));
  fileLists[requestId].push([]);
};

const removeInvoiceForm = (requestId, formIndex) => {
  if (!invoiceFormsData[requestId]) return;
  invoiceFormsData[requestId].splice(formIndex, 1);
  if (fileLists[requestId]) {
    fileLists[requestId].splice(formIndex, 1);
  }
  if (invoiceFormRefs.value[requestId]) {
    invoiceFormRefs.value[requestId].splice(formIndex, 1);
  }
  if (uploadRefs.value[requestId]) {
    uploadRefs.value[requestId].splice(formIndex, 1);
  }
  if (invoiceFormsData[requestId].length === 0) {
    addInvoiceForm(requestId);
  }
};

const statusMap = { 'goods_received': '待开票' };
const getStatusTagType = (status) => {
  return status === 'goods_received' ? 'primary' : 'info';
}

const handleStartInvoicing = async (request) => {
  const requestId = request.id;
  if (invoicingState[requestId]?.isEditing) {
    invoicingState[requestId].isEditing = false;
    return;
  }

  invoicingState[requestId] = { isEditing: true, isLoadingDetails: true, details: null };

  try {
    const response = await apiClient.get(`/procurement/full-process-requests/${requestId}/`);
    const details = response.data;
    invoicingState[requestId].details = details;
    actualPaymentAmounts[requestId] = normalizeAmountInput(details.actual_payment_amount ?? details.total_price);

    ensureRequestState(requestId);
    invoiceFormsData[requestId] = [];
    fileLists[requestId] = [];

    const existingInvoices = Array.isArray(details.invoices) && details.invoices.length
      ? details.invoices
      : (details.invoice ? [details.invoice] : []);

    if (existingInvoices.length) {
      existingInvoices.forEach((invoice) => {
        invoiceFormsData[requestId].push({
          id: invoice.id,
          invoice_number: invoice.invoice_number || '',
          company_name: invoice.company_name || invoice.company || '',
          invoice_image: invoice.invoice_image || null,
          requires_acceptance: invoice.requires_acceptance ?? (request.expense_type === 'c2c'),
        });
        fileLists[requestId].push(invoice.invoice_image ? [{
          name: getInvoiceFileName(invoice.invoice_image),
          url: resolveMediaUrl(invoice.invoice_image),
          status: 'success'
        }] : []);
      });
    } else {
      addInvoiceForm(requestId);
    }
  } catch (error) {
    ElMessage.error('获取申请详情失败！');
    invoicingState[requestId].isEditing = false;
  } finally {
    invoicingState[requestId].isLoadingDetails = false;
  }
};

const handleCancelInvoicing = (requestId) => {
  invoicingState[requestId].isEditing = false;
};

const isC2cRequest = (request) => request?.expense_type === 'c2c';

const normalizeAmountInput = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? Number(numberValue.toFixed(2)) : null;
};

// --- 【修改】修正 file-list 更新逻辑 ---
const handleFileChange = (uploadFile, uploadFiles, requestId, formIndex) => {
  if (uploadFile.raw && !isSupportedInvoiceFile(uploadFile.raw)) {
    ElMessage.error('仅支持上传图片或PDF格式的发票文件');
    if (fileLists[requestId]) {
      fileLists[requestId][formIndex] = (fileLists[requestId][formIndex] || []).filter(file => file.uid !== uploadFile.uid);
    }
    invoiceFormRefs.value[requestId]?.[formIndex]?.validateField('invoice_image');
    return;
  }

  const form = invoiceFormsData[requestId]?.[formIndex];
  if (form) {
    form.invoice_image = uploadFile.raw;
  }
  if (fileLists[requestId]) {
    fileLists[requestId][formIndex] = uploadFiles.slice(-1);
  }
  invoiceFormRefs.value[requestId]?.[formIndex]?.validateField('invoice_image');
};

const handleFileRemove = (uploadFile, uploadFiles, requestId, formIndex) => {
  const form = invoiceFormsData[requestId]?.[formIndex];
  if (form) {
    form.invoice_image = null;
  }
  if (fileLists[requestId]) {
    fileLists[requestId][formIndex] = uploadFiles;
  }
  invoiceFormRefs.value[requestId]?.[formIndex]?.validateField('invoice_image');
};

const handleFileExceed = (files, requestId, formIndex) => {
  const newFile = files[0];
  if (!isSupportedInvoiceFile(newFile)) {
    ElMessage.error('仅支持上传图片或PDF格式的发票文件');
    return;
  }

  const uploadComponent = uploadRefs.value[requestId]?.[formIndex];
  if (uploadComponent) {
    uploadComponent.clearFiles();
    uploadComponent.handleStart(newFile);
    const form = invoiceFormsData[requestId]?.[formIndex];
    if (form) {
       form.invoice_image = newFile;
    }
    ElMessage.warning('已替换为新选择的文件。');
  }
};
// --- 【修改结束】 ---


const submitInvoiceForm = async (requestId, formIndex) => {
  const formInstance = invoiceFormRefs.value[requestId]?.[formIndex];
  const currentFormData = invoiceFormsData[requestId]?.[formIndex];
  const currentFileList = fileLists[requestId]?.[formIndex] || [];
  const requestDetails = invoicingState[requestId]?.details;
  if (!formInstance || !currentFormData) return;

  const actualPaymentAmount = normalizeAmountInput(actualPaymentAmounts[requestId]);
  if (isC2cRequest(requestDetails) && actualPaymentAmount === null) {
    ElMessage.error('请输入实际支付金额');
    return;
  }

  if (currentFileList.length === 0) {
      ElMessage.error('请上传发票文件');
      formInstance.validateField('invoice_image');
      return;
  }

  await formInstance.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      const formData = new FormData();

      formData.append('purchase_request', requestId);
      formData.append('invoice_number', currentFormData.invoice_number);
      formData.append('company_name', currentFormData.company_name);
      formData.append('requires_acceptance', currentFormData.requires_acceptance);
      if (isC2cRequest(requestDetails)) {
        formData.append('actual_payment_amount', actualPaymentAmount.toFixed(2));
      }

      if (currentFormData.invoice_image instanceof File) {
        formData.append('invoice_image', currentFormData.invoice_image);
      } else if (!currentFormData.invoice_image && currentFormData.id) {
        formData.append('invoice_image', '');
      }

      try {
        const url = currentFormData.id ? `/invoice/invoices/${currentFormData.id}/` : '/invoice/invoices/';
        const method = currentFormData.id ? 'patch' : 'post';

        await apiClient[method](url, formData, { headers: { 'Content-Type': 'multipart/form-data' } });

        ElMessage.success('发票信息保存成功！');
        emit('refresh-data');
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '提交失败！');
      } finally {
        isSubmitting.value = false;
      }
    }
  });
};
</script>

<style scoped>
.request-card { margin-bottom: 16px; }
.card-summary { display: flex; justify-content: space-between; align-items: center; }
.info-section { display: flex; gap: 20px; font-size: 14px; color: #606266; align-items: center; }
.details-wrapper { min-height: 100px; }
.details-container { padding: 16px; background-color: #fafafa; }
.section-divider { margin-top: 20px; }
.actual-payment-form { margin-top: 20px; }
.invoice-form { margin-top: 20px; padding-top: 20px; border-top: 1px solid #e4e7ed; }
.invoice-form-block { margin-top: 12px; }

.item-block {
  margin-bottom: 12px;
}
.item-block:last-child {
  margin-bottom: 0;
}
.item-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #303133;
}

:deep(.el-upload-dragger) {
  width: 360px; 
}

/* 【新】确保 .el-upload--picture 类型的拖拽框正确显示 */
:deep(.el-upload) {
  width: 100%;
}
:deep(.el-upload-dragger) {
  width: 100%; /* 覆盖之前的 360px，让它在表单项中正常显示 */
}
/* 【新】当使用 list-type="picture" 时，文件列表会显示在拖拽框下方，这是默认且正确的行为 */
</style>
