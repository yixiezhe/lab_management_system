<template>
  <el-dialog v-model="dialogVisible" title="编辑报销信息 (公共经费)" width="700px" :close-on-click-modal="false" @close="handleClose">
    <el-form v-if="editingRequest" :model="editForm" ref="editFormRef" label-width="100px" class="edit-form">
      
      <template v-if="isMergedRequest">
        <div class="parent-section">
          <el-divider content-position="left"><strong>总体验收信息 (属于合并后总单)</strong></el-divider>
          <el-form-item label="验收单号" prop="inspection_number">
            <el-input v-model="editForm.inspection_number" placeholder="请输入总体验收单号" />
          </el-form-item>
          <el-form-item label="验收照片">
            <div class="image-upload-wrapper">
              <el-image
                v-if="editingRequest.inspection?.inspection_photo"
                :src="resolvePreviewUrl(editingRequest.inspection.inspection_photo, editForm.inspection_photo)"
                :preview-src-list="[resolvePreviewUrl(editingRequest.inspection.inspection_photo, editForm.inspection_photo)]"
                fit="cover"
                class="preview-image"
                preview-teleported
              />
              <el-upload :auto-upload="false" :on-change="(file) => handleEditFileChange(file, 'inspection_photo')" :limit="1" :file-list="editForm.inspection_photo_list" action="#">
                <el-button type="primary">选择新照片</el-button>
                <template #tip><div class="el-upload__tip">上传新照片以覆盖旧的</div></template>
              </el-upload>
            </div>
          </el-form-item>
        </div>
        <el-divider content-position="left"><strong>各子申请信息</strong></el-divider>
        <el-collapse v-model="activeCollapse">
          <el-collapse-item v-for="(child, index) in editForm.children" :key="child.id" :name="child.id" :title="`子申请: ${child.order_number} (申请人: ${child.applicantName})`">
            <el-divider content-position="left" class="inner-divider">付款信息</el-divider>
            <el-form-item label="总金额">
              <el-input-number v-model="child.total_price" :min="0" :precision="2" :step="0.01" controls-position="right" />
            </el-form-item>
            <el-form-item label="支付截图">
              <div class="image-upload-wrapper">
                <el-image
                  v-if="child.original_payment_photo"
                  :src="resolvePreviewUrl(child.original_payment_photo, child.payment_photo)"
                  :preview-src-list="[resolvePreviewUrl(child.original_payment_photo, child.payment_photo)]"
                  fit="cover"
                  class="preview-image"
                  preview-teleported
                />
                <el-upload :auto-upload="false" :on-change="(file) => handleChildFileChange(file, index, 'payment_photo')" :limit="1" :file-list="child.payment_photo_list" action="#">
                  <el-button type="primary">选择新截图</el-button>
                  <template #tip><div class="el-upload__tip">上传新截图以覆盖旧的</div></template>
                </el-upload>
              </div>
            </el-form-item>
            <el-divider content-position="left" class="inner-divider">发票信息</el-divider>
            <div class="invoice-actions">
              <el-button type="primary" plain size="small" @click="addInvoiceForm(child.invoices)">新增发票信息</el-button>
            </div>
            <div v-for="(invoice, invoiceIndex) in child.invoices" :key="invoice.id || invoiceIndex" class="invoice-form-block">
              <el-divider content-position="left">发票信息 {{ invoiceIndex + 1 }}</el-divider>
              <el-form-item label="发票单号"><el-input v-model="invoice.invoice_number" placeholder="请输入发票单号" /></el-form-item>
              <el-form-item label="发票公司"><el-input v-model="invoice.company_name" placeholder="请输入发票公司" /></el-form-item>
              <el-form-item label="发票截图">
                <div class="image-upload-wrapper">
                  <el-image
                    v-if="invoice.original_invoice_image"
                    :src="resolvePreviewUrl(invoice.original_invoice_image, invoice.invoice_image)"
                    :preview-src-list="[resolvePreviewUrl(invoice.original_invoice_image, invoice.invoice_image)]"
                    fit="cover"
                    class="preview-image"
                    preview-teleported
                  />
                  <el-upload :auto-upload="false" :on-change="(file) => handleInvoiceFileChange(file, invoice)" :limit="1" :file-list="invoice.invoice_image_list" action="#">
                    <el-button type="primary">选择新截图</el-button>
                    <template #tip><div class="el-upload__tip">上传新截图以覆盖旧的</div></template>
                  </el-upload>
                </div>
              </el-form-item>
            </div>
          </el-collapse-item>
        </el-collapse>
      </template>

      <template v-else>
        <el-divider content-position="left">付款信息</el-divider>
        <el-form-item label="总金额">
          <el-input-number v-model="editForm.total_price" :min="0" :precision="2" :step="0.01" controls-position="right" />
        </el-form-item>
        <el-form-item label="支付截图">
          <div class="image-upload-wrapper">
            <el-image
              v-if="editingRequest.payment?.payment_photo"
              :src="resolvePreviewUrl(editingRequest.payment.payment_photo, editForm.payment_photo)"
              :preview-src-list="[resolvePreviewUrl(editingRequest.payment.payment_photo, editForm.payment_photo)]"
              fit="cover"
              class="preview-image"
              preview-teleported
            />
            <el-upload :auto-upload="false" :on-change="(file) => handleEditFileChange(file, 'payment_photo')" :limit="1" :file-list="editForm.payment_photo_list" action="#">
              <el-button type="primary">选择新图片</el-button>
              <template #tip><div class="el-upload__tip">上传新图片以覆盖旧的</div></template>
            </el-upload>
          </div>
        </el-form-item>

        <el-divider content-position="left">发票信息</el-divider>
        <div class="invoice-actions">
          <el-button type="primary" plain size="small" @click="addInvoiceForm(editForm.invoices)">新增发票信息</el-button>
        </div>
        <div v-for="(invoice, invoiceIndex) in editForm.invoices" :key="invoice.id || invoiceIndex" class="invoice-form-block">
          <el-divider content-position="left">发票信息 {{ invoiceIndex + 1 }}</el-divider>
          <el-form-item label="发票单号"><el-input v-model="invoice.invoice_number" placeholder="请输入发票单号" /></el-form-item>
          <el-form-item label="发票公司"><el-input v-model="invoice.company_name" placeholder="请输入发票公司" /></el-form-item>
          <el-form-item label="发票截图">
            <div class="image-upload-wrapper">
              <el-image
                v-if="invoice.original_invoice_image"
                :src="resolvePreviewUrl(invoice.original_invoice_image, invoice.invoice_image)"
                :preview-src-list="[resolvePreviewUrl(invoice.original_invoice_image, invoice.invoice_image)]"
                fit="cover"
                class="preview-image"
                preview-teleported
              />
              <el-upload :auto-upload="false" :on-change="(file) => handleInvoiceFileChange(file, invoice)" :limit="1" :file-list="invoice.invoice_image_list" action="#">
                <el-button type="primary">选择新图片</el-button>
                <template #tip><div class="el-upload__tip">上传新图片以覆盖旧的</div></template>
              </el-upload>
            </div>
          </el-form-item>
        </div>

        <el-divider content-position="left">验收信息</el-divider>
        <el-form-item label="验收单号" prop="inspection_number"><el-input v-model="editForm.inspection_number" placeholder="请输入验收单号" /></el-form-item>
        <el-form-item label="验收照片">
          <div class="image-upload-wrapper">
            <el-image
              v-if="editingRequest.inspection?.inspection_photo"
              :src="resolvePreviewUrl(editingRequest.inspection.inspection_photo, editForm.inspection_photo)"
              :preview-src-list="[resolvePreviewUrl(editingRequest.inspection.inspection_photo, editForm.inspection_photo)]"
              fit="cover"
              class="preview-image"
              preview-teleported
            />
            <el-upload :auto-upload="false" :on-change="(file) => handleEditFileChange(file, 'inspection_photo')" :limit="1" :file-list="editForm.inspection_photo_list" action="#">
              <el-button type="primary">选择新图片</el-button>
              <template #tip><div class="el-upload__tip">上传新图片以覆盖旧的</div></template>
            </el-upload>
          </div>
        </el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleEditSubmit" :loading="isSubmitting">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  request: { type: Object, default: null }
});

const emit = defineEmits(['update:modelValue', 'saveSuccess']);

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
});

const editingRequest = ref(null);
const isSubmitting = ref(false);
const editFormRef = ref(null);
const activeCollapse = ref([]);

const getInitialEditForm = () => ({
  total_price: null,
  payment_photo: null,
  inspection_number: '',
  inspection_photo: null,
  payment_photo_list: [],
  inspection_photo_list: [],
  invoices: [],
  children: [],
});
const editForm = reactive(getInitialEditForm());

const isMergedRequest = computed(() => editingRequest.value?.merged_children?.length > 0);

const resolveImageUrl = (url) => {
  if (!url) return '';
  const raw = String(url);
  const normalized = raw.split('\\').join('/');
  const mediaIndex = normalized.indexOf('/media/');
  if (mediaIndex != -1) return normalized.slice(mediaIndex);
  const altIndex = normalized.indexOf('media/');
  if (altIndex != -1) return '/' + normalized.slice(altIndex);
  if (normalized.startsWith('/')) return normalized;
  if (normalized.startsWith('http://') || normalized.startsWith('https://')) return normalized;
  return `/media/${normalized.replace(/^\/+/, '')}`;
};

const imageVersion = ref(Date.now());
const previewUrlCache = new Map();

const getFilePreviewUrl = (file) => {
  if (!(file instanceof File)) return '';
  if (previewUrlCache.has(file)) return previewUrlCache.get(file);
  const url = URL.createObjectURL(file);
  previewUrlCache.set(file, url);
  return url;
};

const clearPreviewUrls = () => {
  previewUrlCache.forEach((url) => URL.revokeObjectURL(url));
  previewUrlCache.clear();
};

const resolvePreviewUrl = (originalUrl, file) => {
  if (file instanceof File) return getFilePreviewUrl(file);
  const resolved = resolveImageUrl(originalUrl);
  if (!resolved) return '';
  const separator = resolved.includes('?') ? '&' : '?';
  return `${resolved}${separator}v=${imageVersion.value}`;
};

const createInvoiceForm = (invoice = {}) => {
  const resolvedImage = resolveImageUrl(invoice.invoice_image || '');
  return {
    id: invoice.id || null,
    invoice_number: invoice.invoice_number || '',
    company_name: invoice.company_name || invoice.company || '',
    original_invoice_image: resolvedImage || null,
    invoice_image: null,
    invoice_image_list: resolvedImage ? [{ name: 'existing_invoice.jpg', url: resolvedImage }] : [],
  };
};

const sortInvoices = (list) => {
  if (!Array.isArray(list)) return [];
  return [...list].sort((a, b) => {
    const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
    const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
    if (Number.isNaN(aTime) && Number.isNaN(bTime)) return 0;
    if (Number.isNaN(aTime)) return 1;
    if (Number.isNaN(bTime)) return -1;
    return bTime - aTime;
  });
};

const normalizeInvoices = (request) => {
  const list = Array.isArray(request?.invoices) && request.invoices.length
    ? request.invoices
    : (request?.invoice ? [request.invoice] : []);
  const sorted = sortInvoices(list);
  return sorted.length ? sorted.map(createInvoiceForm) : [createInvoiceForm()];
};

const addInvoiceForm = (list) => {
  if (Array.isArray(list)) list.push(createInvoiceForm());
};

const handleInvoiceFileChange = (file, invoice) => {
  if (!invoice) return;
  invoice.invoice_image = file.raw;
  invoice.invoice_image_list = [file];
};

const resetForm = () => {
  clearPreviewUrls();
  Object.assign(editForm, getInitialEditForm());
};

const handleClose = () => {
  dialogVisible.value = false;
  resetForm();
};

watch(() => props.modelValue, (isVisible) => {
  if (isVisible && props.request) {
    editingRequest.value = props.request;
    Object.assign(editForm, getInitialEditForm());
    imageVersion.value = Date.now();

    if (isMergedRequest.value) {
      editForm.inspection_number = props.request.inspection?.inspection_number || '';
      editForm.children = props.request.merged_children.map(child => ({
        id: child.id,
        order_number: child.order_number,
        applicantName: child.applicant.name,
        total_price: child.total_price ?? 0,
        original_payment_photo: child.payment?.payment_photo || null,
        payment_photo: null,
        payment_photo_list: [],
        invoices: normalizeInvoices(child),
      }));
      if (props.request.merged_children.length > 0) {
        activeCollapse.value = [props.request.merged_children[0].id];
      }
    } else {
      editForm.total_price = props.request.total_price ?? 0;
      editForm.inspection_number = props.request.inspection?.inspection_number || '';
      editForm.invoices = normalizeInvoices(props.request);
    }
  }
});

const handleEditFileChange = (file, field) => {
  editForm[field] = file.raw;
  editForm[`${field}_list`] = [file];
};

const handleChildFileChange = (file, childIndex, field) => {
  editForm.children[childIndex][field] = file.raw;
  editForm.children[childIndex][`${field}_list`] = [file];
};

const getErrorMessage = (error) => {
  const data = error?.response?.data;
  if (!data) return error?.message || '更新失败，请重试。';
  if (typeof data === 'string') return data;
  if (data.error) return data.error;
  if (data.detail) return data.detail;
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
    return data.non_field_errors.join(' ');
  }
  const firstKey = Object.keys(data)[0];
  if (firstKey) {
    const value = data[firstKey];
    if (Array.isArray(value)) return value.join(' ');
    return String(value);
  }
  return error?.message || '更新失败，请重试。';
};

const saveInvoices = async (requestId, invoices) => {
  if (!Array.isArray(invoices) || invoices.length === 0) return [];

  const warnings = [];
  const tasks = invoices
    .filter(invoice => invoice)
    .map((invoice, index) => {
      const hasAnyData = invoice.invoice_number || invoice.company_name || invoice.invoice_image || invoice.original_invoice_image || invoice.id;
      if (!hasAnyData) return null;

      const number = (invoice.invoice_number || '').trim();
      const company = (invoice.company_name || '').trim();
      const hasImage = invoice.invoice_image instanceof File;
      const isNew = !invoice.id;

      if (isNew) {
        if (!number || !company) {
          warnings.push(`第${index + 1}张发票信息未填写完整，已跳过。`);
          return null;
        }
        if (!hasImage) {
          warnings.push(`第${index + 1}张发票未上传截图，已跳过。`);
          return null;
        }
      } else if (!number && !company && !hasImage) {
        return null;
      }

      const formData = new FormData();
      if (number) formData.append('invoice_number', number);
      if (company) formData.append('company_name', company);
      if (isNew) {
        formData.append('purchase_request', requestId);
      }
      if (hasImage) {
        formData.append('invoice_image', invoice.invoice_image);
      }
      const url = isNew ? '/invoice/invoices/' : `/invoice/invoices/${invoice.id}/`;
      const method = isNew ? 'post' : 'patch';
      return {
        index: index + 1,
        promise: apiClient[method](url, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      };
    })
    .filter(Boolean);

  if (tasks.length > 0) {
    const results = await Promise.allSettled(tasks.map(item => item.promise));
    results.forEach((result, idx) => {
      if (result.status === 'rejected') {
        const invoiceIndex = tasks[idx].index;
        const serverMessage = getErrorMessage(result.reason);
        warnings.push(`第${invoiceIndex}张发票保存失败：${serverMessage}`);
      }
    });
  }
  return warnings;
};

const handleEditSubmit = async () => {
  if (!editingRequest.value) return;
  isSubmitting.value = true;

  const formData = new FormData();
  const inspectionNumber = String(editForm.inspection_number || '').trim();
  
  if (isMergedRequest.value) {
    if (inspectionNumber) formData.append('inspection_number', inspectionNumber);
    if (editForm.inspection_photo) formData.append('inspection_photo', editForm.inspection_photo);
    const childrenUpdates = editForm.children.map(child => ({
      id: child.id,
      total_price: child.total_price,
    }));
    formData.append('children_updates', JSON.stringify(childrenUpdates));
    editForm.children.forEach(child => {
      if (child.payment_photo) formData.append(`child_${child.id}_payment_photo`, child.payment_photo);
    });
  } else {
    if (editForm.total_price !== null && editForm.total_price !== '') {
      formData.append('total_price', editForm.total_price);
    }
    if (inspectionNumber) formData.append('inspection_number', inspectionNumber);
    if (editForm.payment_photo) formData.append('payment_photo', editForm.payment_photo);
    if (editForm.inspection_photo) formData.append('inspection_photo', editForm.inspection_photo);
  }

  try {
    await apiClient.post(`/procurement/public-purchase-requests/${editingRequest.value.id}/update-reimbursement-details/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    let invoiceWarnings = [];
    if (isMergedRequest.value) {
      const results = await Promise.all(editForm.children.map(child => saveInvoices(child.id, child.invoices)));
      invoiceWarnings = results.flat().filter(Boolean);
    } else {
      invoiceWarnings = await saveInvoices(editingRequest.value.id, editForm.invoices);
    }

    if (invoiceWarnings.length > 0) {
      ElMessage.warning(invoiceWarnings.join(' '));
    }

    let refreshedRequest = null;
    try {
      const res = await apiClient.get(`/procurement/full-process-requests/${editingRequest.value.id}/`);
      refreshedRequest = res.data;
    } catch (fetchError) {
      refreshedRequest = null;
    }

    ElMessage.success('信息更新成功！');
    emit('saveSuccess', refreshedRequest);
    handleClose();
  } catch (error) {
    const errorMsg = getErrorMessage(error);
    ElMessage.error(errorMsg);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
/* 样式保持不变 */
.image-upload-wrapper { display: flex; align-items: center; }
.preview-image { width: 80px; height: 80px; margin-right: 10px; border-radius: 4px; border: 1px solid #dcdfe6; }
.edit-form .parent-section { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #e4e7ed; }
.edit-form .el-collapse { border-top: none; border-bottom: none; }
.edit-form .el-collapse-item__header { font-size: 14px; font-weight: 500; }
.edit-form .inner-divider { margin-top: 0; }
.invoice-actions { margin-top: 8px; }
.invoice-form-block { margin-top: 12px; }
</style>
