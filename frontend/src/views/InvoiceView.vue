<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-header">
          <span>发票报销管理</span>
        </div>
      </template>

      <!-- 数据表格 -->
      <el-table :data="requests" v-loading="loading" style="width: 100%" border>
        <!-- 展开行 -->
        <el-table-column type="expand">
          <template #default="props">
            <div style="padding: 15px 20px;">
              <h4>采购物品详情</h4>
              <ul>
                <li v-for="item in props.row.items" :key="item.id">
                  {{ item.content }} (厂商: {{ item.manufacturer || '未填写' }}) - 单价: ¥{{ item.unit_price }} x {{ item.quantity }}
                </li>
              </ul>
            </div>
          </template>
        </el-table-column>
        
        <!-- START: 修改点1 - 移除 "申请ID" 列 -->
        <!-- <el-table-column prop="id" label="申请ID" width="80" /> -->
        <!-- END: 修改点1 -->

        <el-table-column prop="applicant_name" label="申请人" width="120" />
        <el-table-column prop="created_at" label="申请日期" width="180">
           <template #default="scope">
            {{ new Date(scope.row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="total_price" label="总金额" width="120">
          <template #default="scope">
            ¥{{ parseFloat(scope.row.total_price).toFixed(2) }}
          </template>
        </el-table-column>

        <el-table-column label="报销状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.invoice ? 'success' : 'warning'">
              {{ scope.row.invoice ? '已报销' : '待报销' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" fixed="right" width="180">
          <template #default="scope">
            <el-button type="primary" size="small" @click="openInvoiceDialog(scope.row)">
              {{ scope.row.invoice ? '编辑报销信息' : '填写报销信息' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="invoiceFormRef"
        :model="invoiceForm"
        :rules="invoiceFormRules"
        label-width="120px"
      >
        <el-form-item label="发票单号" prop="invoice_number">
          <el-input v-model="invoiceForm.invoice_number" placeholder="请输入发票单号" />
        </el-form-item>
        <el-form-item label="发票公司" prop="company_name">
          <el-input v-model="invoiceForm.company_name" placeholder="请输入开票公司全称" />
        </el-form-item>
        
        <!-- START: 修改点2 - 新增付款链接 -->
        <el-form-item label="付款链接" prop="payment_link">
          <el-input v-model="invoiceForm.payment_link" placeholder="请输入付款的网址链接 (选填)" />
        </el-form-item>
        <!-- END: 修改点2 -->
        
        <!-- START: 修改点3 - 优化“是否需要验收” -->
        <el-form-item prop="requires_acceptance">
          <template #label>
            <span>是否需要验收 </span>
            <el-tooltip
              content="单件物品单价超过300元，或采购总价超过1000元时，建议进行验收"
              placement="top"
            >
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <el-switch v-model="invoiceForm.requires_acceptance" />
        </el-form-item>
        <!-- END: 修改点3 -->

        <el-form-item label="发票截图" prop="invoice_image">
          <el-upload
            ref="uploadRef"
            v-model:file-list="fileList"
            action="#"
            :auto-upload="false"
            list-type="picture-card"
            :limit="1"
            :on-exceed="handleExceed"
            :on-change="handleFileChange"
            :on-preview="handlePictureCardPreview"
            :on-remove="handleRemove"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitInvoiceForm" :loading="isSubmitting">
            确认提交
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <el-dialog v-model="previewVisible">
      <img w-full :src="previewImageUrl" alt="Preview Image" style="width: 100%" />
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { Plus, QuestionFilled } from '@element-plus/icons-vue'; // 导入新图标

const requests = ref([]);
const loading = ref(true);
const dialogVisible = ref(false);
const isSubmitting = ref(false);
const currentRequest = ref({});
const dialogTitle = computed(() => currentRequest.value.invoice ? '编辑报销信息' : '填写报销信息');

const invoiceFormRef = ref(null);
const uploadRef = ref(null);

// START: 修改点4 - 在表单数据中增加 payment_link
const initialFormState = () => ({
  id: null,
  purchase_request: null,
  invoice_number: '',
  company_name: '',
  payment_link: '', // 新增
  requires_acceptance: false,
  invoice_image: null,
});
// END: 修改点4
const invoiceForm = ref(initialFormState());

const fileList = ref([]);
const newFile = ref(null);
const previewImageUrl = ref('');
const previewVisible = ref(false);

// START: 修改点5 - 为付款链接添加可选的URL验证
const invoiceFormRules = {
  invoice_number: [{ required: true, message: '请输入发票单号', trigger: 'blur' }],
  company_name: [{ required: true, message: '请输入发票公司', trigger: 'blur' }],
  payment_link: [{ type: 'url', message: '请输入有效的网址链接', trigger: 'blur' }], // 新增
};
// END: 修改点5

const fetchRequests = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/invoice/full-info-requests/');
    requests.value = response.data;
  } catch (error) {
    ElMessage.error('获取待报销列表失败！');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchRequests);

// START: 修改点6 - 升级 openInvoiceDialog 方法
const openInvoiceDialog = (request) => {
  currentRequest.value = request;
  if (request.invoice) {
    invoiceForm.value = { ...request.invoice };
    if (request.invoice.invoice_image) {
      fileList.value = [{ name: 'invoice.jpg', url: request.invoice.invoice_image }];
    }
  } else {
    invoiceForm.value = initialFormState();
    invoiceForm.value.purchase_request = request.id;

    // --- 智能预勾选“是否需要验收”的逻辑 ---
    const shouldAccept = 
      parseFloat(request.total_price) > 1000 || 
      request.items.some(item => parseFloat(item.unit_price) > 300);
    
    if (shouldAccept) {
      invoiceForm.value.requires_acceptance = true;
      ElMessage.info('根据规定，该采购需要验收，已为您自动勾选。');
    }
    // ------------------------------------
  }
  dialogVisible.value = true;
};
// END: 修改点6

const handleDialogClose = () => {
  invoiceFormRef.value.resetFields();
  fileList.value = [];
  newFile.value = null;
};

const handleFileChange = (uploadFile) => {
  newFile.value = uploadFile.raw;
};
const handleRemove = () => {
  newFile.value = null;
};
const handleExceed = () => {
  ElMessage.warning('只能上传一张发票截图，请先删除现有图片。');
};
const handlePictureCardPreview = (uploadFile) => {
  previewImageUrl.value = uploadFile.url;
  previewVisible.value = true;
};

// START: 修改点7 - 升级 submitInvoiceForm 方法
const submitInvoiceForm = async () => {
  if (!invoiceFormRef.value) return;

  await invoiceFormRef.value.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      const formData = new FormData();
      formData.append('invoice_number', invoiceForm.value.invoice_number);
      formData.append('company_name', invoiceForm.value.company_name);
      formData.append('requires_acceptance', invoiceForm.value.requires_acceptance);
      
      // 只有当 payment_link 不为空时才提交
      if (invoiceForm.value.payment_link) {
        formData.append('payment_link', invoiceForm.value.payment_link);
      }
      
      if (!invoiceForm.value.id) {
          formData.append('purchase_request', invoiceForm.value.purchase_request);
      }
      
      if (newFile.value) {
        formData.append('invoice_image', newFile.value);
      }

      try {
        if (invoiceForm.value.id) {
          await apiClient.patch(`/invoice/invoices/${invoiceForm.value.id}/`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          ElMessage.success('报销信息更新成功！');
        } else {
          await apiClient.post('/invoice/invoices/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          ElMessage.success('报销信息提交成功！');
        }
        
        dialogVisible.value = false;
        fetchRequests();

      } catch (error) {
        console.error("提交失败:", error.response?.data);
        ElMessage.error('提交失败，请检查您的输入。');
      } finally {
        isSubmitting.value = false;
      }
    }
  });
};
// END: 修改点7
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.el-table ul {
  padding-left: 20px;
  margin: 0;
}
.el-table li {
  padding: 4px 0;
}
</style>