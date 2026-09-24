<template>
  <el-dialog
    :model-value="visible"
    :title="dialogTitle"
    width="600px"
    :close-on-click-modal="false"
    @update:modelValue="$emit('update:visible', $event)"
    @close="onDialogClose"
  >
    <el-form ref="invoiceFormRef" :model="invoiceForm" :rules="invoiceFormRules" label-width="120px">
      <el-form-item label="发票单号" prop="invoice_number">
        <el-input v-model="invoiceForm.invoice_number" placeholder="请输入发票单号" />
      </el-form-item>
      <el-form-item label="发票公司" prop="company_name">
        <el-input v-model="invoiceForm.company_name" placeholder="请输入开票公司全称" />
      </el-form-item>
      <el-form-item label="付款链接" prop="payment_link">
        <el-input v-model="invoiceForm.payment_link" placeholder="请输入付款的网址链接 (选填)" />
      </el-form-item>
      <el-form-item label="是否需要验收" prop="requires_acceptance">
        <el-switch v-model="invoiceForm.requires_acceptance" />
        <el-alert
          title="根据规定，单价大于300元或总价大于1000元的耗材需要验收，请酌情勾选。"
          type="info"
          show-icon
          :closable="false"
          style="margin-top: 8px; line-height: 1.5;"
        />
      </el-form-item>
      <el-form-item label="发票截图" prop="invoice_image">
        <el-upload
          v-model:file-list="invoiceFileList"
          action="#"
          list-type="picture-card"
          :auto-upload="false"
          :limit="1"
          :on-change="handleInvoiceFileChange"
        >
          <el-icon><Plus /></el-icon>
        </el-upload>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="handleInvoiceSubmit" :loading="isSaving">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, reactive, computed } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';

const props = defineProps({
  visible: {
    type: Boolean,
    required: true,
  },
  requestData: {
    type: Object,
    default: () => null,
  },
});

const emit = defineEmits(['update:visible', 'success']);

const isSaving = ref(false);
const invoiceFormRef = ref(null);
const invoiceFileList = ref([]);

const invoiceForm = reactive({
  id: null,
  invoice_number: '',
  company_name: '',
  payment_link: '',
  requires_acceptance: false,
  invoice_image: null,
});

const invoiceFormRules = {
  invoice_number: [{ required: true, message: '请输入发票单号', trigger: 'blur' }],
  company_name: [{ required: true, message: '请输入开票公司全称', trigger: 'blur' }],
  payment_link: [{ type: 'url', message: '请输入有效的网址链接', trigger: 'blur' }],
};

const dialogTitle = computed(() => {
  return props.requestData?.invoice ? '编辑发票信息' : '填写发票信息';
});

// 监听传入的 requestData，当弹窗打开时填充表单
watch(() => props.visible, (newVal) => {
  if (newVal && props.requestData) {
    // 重置表单和文件列表
    invoiceFileList.value = [];
    if (props.requestData.invoice) {
      Object.assign(invoiceForm, props.requestData.invoice);
      if (props.requestData.invoice.invoice_image) {
        invoiceFileList.value = [{ name: 'existing.jpg', url: props.requestData.invoice.invoice_image }];
      }
    } else {
      // 重置为初始状态
      Object.assign(invoiceForm, {
        id: null,
        invoice_number: '',
        company_name: '',
        payment_link: '',
        requires_acceptance: false,
        invoice_image: null,
      });
    }
  }
});

const handleInvoiceFileChange = (file) => {
  invoiceForm.invoice_image = file.raw;
};

const handleInvoiceSubmit = async () => {
  if (!invoiceFormRef.value) return;
  await invoiceFormRef.value.validate(async (valid) => {
    if (valid) {
      isSaving.value = true;
      const formData = new FormData();

      Object.entries(invoiceForm).forEach(([key, value]) => {
        if (key !== 'invoice_image' && value !== null) {
          formData.append(key, value);
        }
      });

      if (!invoiceForm.id) {
        formData.append('purchase_request', props.requestData.id);
      }

      if (invoiceForm.invoice_image instanceof File) {
        formData.append('invoice_image', invoiceForm.invoice_image);
      }

      try {
        const url = invoiceForm.id ? `/invoice/invoices/${invoiceForm.id}/` : '/invoice/invoices/';
        const method = invoiceForm.id ? 'patch' : 'post';
        await apiClient[method](url, formData, { headers: { 'Content-Type': 'multipart/form-data' } });

        emit('update:visible', false);
        emit('success');
        ElMessage.success('发票信息保存成功！');
      } catch (error) {
        ElMessage.error('提交失败！');
      } finally {
        isSaving.value = false;
      }
    }
  });
};

const onDialogClose = () => {
    // 确保表单验证状态在关闭时被清除
    if(invoiceFormRef.value) {
        invoiceFormRef.value.clearValidate();
    }
}
</script>