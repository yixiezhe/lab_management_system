<template>
  <el-dialog v-model="dialogVisible" title="编辑报销信息" width="700px" :close-on-click-modal="false" @close="handleClose">
    <el-form v-if="editingRequest" :model="editForm" ref="editFormRef" label-width="100px" class="edit-form">
      
      <template v-if="isMergedRequest">
        <div class="parent-section">
          <el-divider content-position="left"><strong>总体验收信息 (属于合并后总单)</strong></el-divider>
          <el-form-item label="验收单号" prop="inspection_number">
            <el-input v-model="editForm.inspection_number" placeholder="请输入总体验收单号" />
          </el-form-item>
          <el-form-item label="验收照片">
            <div class="image-upload-wrapper">
              <el-image v-if="editingRequest.inspection?.inspection_photo" lazy :src="editingRequest.inspection.inspection_photo" fit="cover" class="preview-image" />
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
            <el-form-item label="支付截图">
              <div class="image-upload-wrapper">
                <el-image v-if="child.original_payment_photo" lazy :src="child.original_payment_photo" fit="cover" class="preview-image" />
                <el-upload :auto-upload="false" :on-change="(file) => handleChildFileChange(file, index, 'payment_photo')" :limit="1" :file-list="child.payment_photo_list" action="#">
                  <el-button type="primary">选择新截图</el-button>
                  <template #tip><div class="el-upload__tip">上传新截图以覆盖旧的</div></template>
                </el-upload>
              </div>
            </el-form-item>
            <el-divider content-position="left" class="inner-divider">发票信息</el-divider>
            <el-form-item label="发票单号"><el-input v-model="child.invoice_number" placeholder="请输入发票单号" /></el-form-item>
            <el-form-item label="发票公司"><el-input v-model="child.invoice_company" placeholder="请输入发票公司" /></el-form-item>
            <el-form-item label="发票截图">
              <div class="image-upload-wrapper">
                <el-image v-if="child.original_invoice_image" lazy :src="child.original_invoice_image" fit="cover" class="preview-image" />
                <el-upload :auto-upload="false" :on-change="(file) => handleChildFileChange(file, index, 'invoice_image')" :limit="1" :file-list="child.invoice_image_list" action="#">
                  <el-button type="primary">选择新截图</el-button>
                  <template #tip><div class="el-upload__tip">上传新截图以覆盖旧的</div></template>
                </el-upload>
              </div>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </template>

      <template v-else>
        <template v-if="editingRequest.purchase_order">
          <el-divider content-position="left">请购信息</el-divider>
          <el-form-item label="请购单">
            <div class="image-upload-wrapper">
              <a :href="editingRequest.purchase_order.po_form" target="_blank" v-if="editingRequest.purchase_order.po_form" class="preview-link">
                <el-image :src="editingRequest.purchase_order.po_form" fit="cover" class="preview-image" lazy>
                  <template #error><div class="image-slot">文件</div></template>
                </el-image>
              </a>
              <el-upload :auto-upload="false" :on-change="(file) => handleEditFileChange(file, 'po_form')" :limit="1" :file-list="editForm.po_form_list" action="#">
                <el-button type="primary">选择新文件</el-button>
                <template #tip><div class="el-upload__tip">上传新文件以覆盖旧的</div></template>
              </el-upload>
            </div>
          </el-form-item>
        </template>

        <template v-if="editingRequest.contract">
            <el-divider content-position="left">合同信息</el-divider>
            <el-form-item label="合同文件">
              <div class="image-upload-wrapper">
                <a :href="editingRequest.contract.contract_form" target="_blank" v-if="editingRequest.contract.contract_form" class="preview-link">
                  <el-image :src="editingRequest.contract.contract_form" fit="cover" class="preview-image" lazy>
                    <template #error><div class="image-slot">文件</div></template>
                  </el-image>
                </a>
                <el-upload :auto-upload="false" :on-change="(file) => handleEditFileChange(file, 'contract_form')" :limit="1" :file-list="editForm.contract_form_list" action="#">
                  <el-button type="primary">选择新文件</el-button>
                   <template #tip><div class="el-upload__tip">上传新文件以覆盖旧的</div></template>
                </el-upload>
              </div>
            </el-form-item>
        </template>

        <el-divider content-position="left">付款信息</el-divider>
        <el-form-item label="支付截图">
          <div class="image-upload-wrapper">
            <el-image v-if="editingRequest.payment?.payment_photo" lazy :src="editingRequest.payment.payment_photo" fit="cover" class="preview-image" />
            <el-upload :auto-upload="false" :on-change="(file) => handleEditFileChange(file, 'payment_photo')" :limit="1" :file-list="editForm.payment_photo_list" action="#">
              <el-button type="primary">选择新图片</el-button>
              <template #tip><div class="el-upload__tip">上传新图片以覆盖旧的</div></template>
            </el-upload>
          </div>
        </el-form-item>

        <el-divider content-position="left">发票信息</el-divider>
        <el-form-item label="发票单号" prop="invoice_number"><el-input v-model="editForm.invoice_number" placeholder="请输入发票单号" /></el-form-item>
        <el-form-item label="发票公司" prop="invoice_company"><el-input v-model="editForm.invoice_company" placeholder="请输入发票公司" /></el-form-item>
        <el-form-item label="发票截图">
          <div class="image-upload-wrapper">
            <el-image v-if="editingRequest.invoice?.invoice_image" lazy :src="editingRequest.invoice.invoice_image" fit="cover" class="preview-image" />
            <el-upload :auto-upload="false" :on-change="(file) => handleEditFileChange(file, 'invoice_image')" :limit="1" :file-list="editForm.invoice_image_list" action="#">
              <el-button type="primary">选择新图片</el-button>
              <template #tip><div class="el-upload__tip">上传新图片以覆盖旧的</div></template>
            </el-upload>
          </div>
        </el-form-item>

        <el-divider content-position="left">验收信息</el-divider>
        <el-form-item label="验收单号" prop="inspection_number"><el-input v-model="editForm.inspection_number" placeholder="请输入验收单号" /></el-form-item>
        <el-form-item label="验收照片">
          <div class="image-upload-wrapper">
            <el-image v-if="editingRequest.inspection?.inspection_photo" lazy :src="editingRequest.inspection.inspection_photo" fit="cover" class="preview-image" />
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

// 【新增修改】在表单状态中加入请购单和合同字段
const getInitialEditForm = () => ({
  po_form: null,
  po_form_list: [],
  contract_form: null,
  contract_form_list: [],
  payment_photo: null,
  invoice_number: '',
  invoice_company: '',
  invoice_image: null,
  inspection_number: '',
  inspection_photo: null,
  payment_photo_list: [],
  invoice_image_list: [],
  inspection_photo_list: [],
  children: [],
});
const editForm = reactive(getInitialEditForm());

const isMergedRequest = computed(() => editingRequest.value?.merged_children?.length > 0);

const resetForm = () => {
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
    
    if (isMergedRequest.value) {
      editForm.inspection_number = props.request.inspection?.inspection_number || '';
      editForm.children = props.request.merged_children.map(child => ({
        id: child.id,
        order_number: child.order_number,
        applicantName: child.applicant.name,
        invoice_number: child.invoice?.invoice_number || '',
        invoice_company: child.invoice?.company_name || child.invoice?.company || '',
        original_payment_photo: child.payment?.payment_photo || null,
        original_invoice_image: child.invoice?.invoice_image || null,
        payment_photo: null,
        invoice_image: null,
        payment_photo_list: [],
        invoice_image_list: [],
      }));
      if (props.request.merged_children.length > 0) {
        activeCollapse.value = [props.request.merged_children[0].id];
      }
    } else {
      editForm.invoice_number = props.request.invoice?.invoice_number || '';
      editForm.invoice_company = props.request.invoice?.company_name || props.request.invoice?.company || '';
      editForm.inspection_number = props.request.inspection?.inspection_number || '';
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

const handleEditSubmit = async () => {
  if (!editingRequest.value) return;
  isSubmitting.value = true;

  const formData = new FormData();
  const inspectionNumber = String(editForm.inspection_number || '').trim();
  
  if (isMergedRequest.value) {
    // Merged request logic...
    if (inspectionNumber) formData.append('inspection_number', inspectionNumber);
    if (editForm.inspection_photo) formData.append('inspection_photo', editForm.inspection_photo);
    const childrenUpdates = editForm.children.map(child => ({
      id: child.id,
      invoice_number: child.invoice_number,
      invoice_company: child.invoice_company,
    }));
    formData.append('children_updates', JSON.stringify(childrenUpdates));
    editForm.children.forEach(child => {
      if (child.payment_photo) formData.append(`child_${child.id}_payment_photo`, child.payment_photo);
      if (child.invoice_image) formData.append(`child_${child.id}_invoice_image`, child.invoice_image);
    });
  } else {
    // Non-merged request logic
    // 【新增修改】将请购单和合同文件加入表单数据
    if (editForm.po_form) formData.append('po_form', editForm.po_form);
    if (editForm.contract_form) formData.append('contract_form', editForm.contract_form);
    
    formData.append('invoice_number', editForm.invoice_number);
    formData.append('invoice_company', editForm.invoice_company);
    if (inspectionNumber) formData.append('inspection_number', inspectionNumber);
    if (editForm.payment_photo) formData.append('payment_photo', editForm.payment_photo);
    if (editForm.invoice_image) formData.append('invoice_image', editForm.invoice_image);
    if (editForm.inspection_photo) formData.append('inspection_photo', editForm.inspection_photo);
  }

  try {
    await apiClient.post(`/procurement/purchase-requests/${editingRequest.value.id}/update-reimbursement-details/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
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
    const errorMsg = error.response?.data?.error || '更新失败，请重试。';
    ElMessage.error(errorMsg);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.image-upload-wrapper { display: flex; align-items: center; }
.preview-image { width: 80px; height: 80px; margin-right: 10px; border-radius: 4px; border: 1px solid #dcdfe6; }
.edit-form .parent-section { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #e4e7ed; }
.edit-form .el-collapse { border-top: none; border-bottom: none; }
.edit-form .el-collapse-item__header { font-size: 14px; font-weight: 500; }
.edit-form .inner-divider { margin-top: 0; }
.preview-link { text-decoration: none; }
.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
