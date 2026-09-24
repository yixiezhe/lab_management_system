<template>
  <div>
    <el-card>
      <template #header>
        <h1>{{ pageTitle }}</h1>
      </template>

      <el-form :model="filters" inline class="controls-container">
        <el-form-item label="申请日期"><el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" clearable unlink-panels /></el-form-item>
        <el-form-item label="申请人"><el-select v-model="filters.applicant" placeholder="选择申请人" clearable filterable><el-option v-for="user in applicantOptions" :key="user.id" :label="user.name" :value="user.id" /></el-select></el-form-item>
        <el-form-item label="导师"><el-select v-model="filters.tutor" placeholder="选择导师" clearable filterable><el-option v-for="user in tutorOptions" :key="user.id" :label="user.name" :value="user.id" /></el-select></el-form-item>
        <el-form-item label="支付状态"><el-select v-model="filters.is_paid" placeholder="支付状态" clearable style="width: 120px;"><el-option label="已支付" :value="true" /><el-option label="未支付" :value="false" /></el-select></el-form-item>
        <el-form-item label="报销状态"><el-select v-model="filters.is_invoiced" placeholder="报销状态" clearable style="width: 120px;"><el-option label="已报销" :value="true" /><el-option label="未报销" :value="false" /></el-select></el-form-item>
        <el-form-item label="收货状态"><el-select v-model="filters.is_accepted" placeholder="收货状态" clearable style="width: 120px;"><el-option label="已收货" :value="true" /><el-option label="未收货" :value="false" /></el-select></el-form-item>
        <el-form-item><el-input v-model="searchQuery" placeholder="关键词搜索 (物品/单号等)" clearable @keyup.enter="handleSearch" style="width: 240px;"><template #append><el-button @click="handleSearch"><el-icon><Search /></el-icon></el-button></template></el-input></el-form-item>
        <el-form-item><el-button type="primary" @click="applyFilters">筛选</el-button><el-button @click="resetFilters">重置</el-button></el-form-item>
        <el-form-item><el-button type="success" @click="handlePackage" :disabled="selectedRequests.length === 0" :loading="isPackaging"><el-icon style="margin-right: 5px;"><Box /></el-icon>一键打包</el-button></el-form-item>
      </el-form>

      <el-table :data="requests" v-loading="loading" style="width: 100%" border row-key="id" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column type="expand">
          <template #default="props">
            <div class="details-container">
              <el-descriptions title="1. 申请与验收信息" :column="3" border>
                <template #extra><el-button v-if="isSystemAdmin" type="primary" size="small" @click="openReceiptDialog(props.row)">{{ props.row.acceptance ? '编辑收货信息' : '填写收货信息' }}</el-button></template>
                <el-descriptions-item label="申请人">{{ props.row.applicant.name }}</el-descriptions-item>
                <el-descriptions-item label="申请导师">{{ props.row.applicant.assigned_tutor?.name || '无' }}</el-descriptions-item>
                <el-descriptions-item label="申请日期">{{ new Date(props.row.request_date).toLocaleDateString() }}</el-descriptions-item>
                <el-descriptions-item label="采购平台">{{ props.row.platform }}</el-descriptions-item>
                <el-descriptions-item label="单号">{{ props.row.order_number }}</el-descriptions-item>
                <el-descriptions-item label="总金额">¥{{ props.row.total_price }}</el-descriptions-item>
                <el-descriptions-item label="采购物品" :span="3">
                  <ul><li v-for="item in props.row.items" :key="item.id">{{ item.content }} ({{ item.specifications }}) - ¥{{ item.unit_price }} x {{ item.quantity }}</li></ul>
                </el-descriptions-item>
                <el-descriptions-item label="收货情况" :span="2">{{ props.row.acceptance?.receiving_status || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="收货照片">
                  <el-image v-if="props.row.acceptance?.acceptance_photo" style="width: 50px; height: 50px" :src="props.row.acceptance.acceptance_photo" :preview-src-list="[props.row.acceptance.acceptance_photo]" fit="cover" />
                  <span v-else>未上传</span>
                </el-descriptions-item>
              </el-descriptions>

              <el-descriptions title="2. 采购人填写" :column="3" border class="section-divider">
                <template #extra><el-button v-if="isSystemAdmin" type="primary" size="small" @click="openInvoiceDialog(props.row)">{{ props.row.invoice ? '编辑发票信息' : '填写发票信息' }}</el-button></template>
                <el-descriptions-item label="采购负责人">{{ props.row.approved_by?.name || 'N/A' }}</el-descriptions-item>
                <el-descriptions-item label="发票单号">{{ props.row.invoice?.invoice_number || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="发票公司">{{ props.row.invoice?.company_name || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="付款链接"><a v-if="props.row.invoice?.payment_link" :href="props.row.invoice.payment_link" target="_blank">点击查看</a><span v-else>未填写</span></el-descriptions-item>
                <el-descriptions-item label="是否需要验收"><el-tag :type="props.row.invoice?.requires_acceptance ? 'success' : 'info'">{{ props.row.invoice?.requires_acceptance ? '是' : '否' }}</el-tag></el-descriptions-item>
                <el-descriptions-item label="发票截图"><el-image v-if="props.row.invoice?.invoice_image" style="width: 50px; height: 50px" :src="props.row.invoice.invoice_image" :preview-src-list="[props.row.invoice.invoice_image]" fit="cover" /><span v-else>未上传</span></el-descriptions-item>
              </el-descriptions>
              <el-descriptions v-if="props.row.payment" title="3. 付款人填写" :column="2" border class="section-divider">
                <el-descriptions-item label="支付人">{{ props.row.payment.paid_by?.name || 'N/A' }}</el-descriptions-item>
                <el-descriptions-item label="支付时间">{{ new Date(props.row.payment.paid_at).toLocaleString() }}</el-descriptions-item>
                <el-descriptions-item label="支付截图" :span="2"><el-image v-if="props.row.payment.payment_photo" style="width: 50px; height: 50px" :src="props.row.payment.payment_photo" :preview-src-list="[props.row.payment.payment_photo]" fit="cover" /><span v-else>未上传</span></el-descriptions-item>
              </el-descriptions>
              
              </div>
          </template>
        </el-table-column>
        <el-table-column label="序号" width="70" align="center"><template #default="scope">{{ (pagination.currentPage - 1) * pagination.pageSize + scope.$index + 1 }}</template></el-table-column>
        <el-table-column prop="request_date" label="日期" width="120"/>
        <el-table-column prop="applicant.name" label="申请人" width="100" />
        <el-table-column prop="applicant.assigned_tutor.name" label="导师" width="100" />
        <el-table-column prop="platform" label="平台" width="120" />
        <el-table-column prop="order_number" label="单号" />
        <el-table-column label="总价" width="120"><template #default="scope">¥{{ parseFloat(scope.row.total_price).toFixed(2) }}</template></el-table-column>
        <el-table-column label="状态" width="220"><template #default="scope"><el-tag :type="scope.row.payment ? 'success' : 'info'">{{ scope.row.payment ? '已支付' : '待支付' }}</el-tag><el-tag :type="scope.row.invoice ? 'success' : 'warning'" style="margin-left: 5px;">{{ scope.row.invoice ? '已报销' : '待报销' }}</el-tag><el-tag :type="scope.row.acceptance ? 'success' : 'info'" style="margin-left: 5px;">{{ scope.row.acceptance ? '已收货' : '待收货' }}</el-tag></template></el-table-column>
      </el-table>

      <div class="pagination-container"><el-pagination v-model:current-page="pagination.currentPage" v-model:page-size="pagination.pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" :total="pagination.totalItems" @size-change="handleSizeChange" @current-change="handleCurrentChange"/></div>
    </el-card>

    <InvoiceFormDialog
      v-model:visible="invoiceDialog.visible"
      :request-data="currentRequest"
      @success="onInvoiceSuccess"
    />

    <el-dialog v-model="receiptDialog.visible" :title="receiptDialog.title" width="600px" :close-on-click-modal="false">
      <el-form ref="receiptFormRef" :model="receiptForm" :rules="receiptFormRules" label-width="120px">
        <el-form-item label="收货情况" prop="receiving_status"><el-input v-model="receiptForm.receiving_status" type="textarea" rows="4" placeholder="请详细描述物品接收情况，如数量、完好度等" /></el-form-item>
        <el-form-item label="收货照片" prop="acceptance_photo">
          <el-upload v-model:file-list="receiptFileList" action="#" list-type="picture-card" :auto-upload="false" :limit="1" :on-change="handleReceiptFileChange">
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="receiptDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleReceiptSubmit" :loading="receiptDialog.isSaving">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, computed, reactive, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { Plus, Search, Box } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import InvoiceFormDialog from '@/components/InvoiceFormDialog.vue';

const authStore = useAuthStore();
const requests = ref([]);
const loading = ref(true);
const route = useRoute();

const isSystemAdmin = computed(() => {
  return authStore.user && authStore.user.roles.some(role => role.name === '系统管理员');
});

const pageTitle = computed(() => {
  if (route.name === 'ledger-c2c') return '公对公采购台账';
  if (route.name === 'ledger-public') return '公共经费采购台账';
  return '采购全流程追踪台账';
});

const selectedRequests = ref([]);
const isPackaging = ref(false);
const applicantOptions = ref([]);
const tutorOptions = ref([]);
const pagination = reactive({ currentPage: 1, pageSize: 20, totalItems: 0 });
const filters = reactive({ dateRange: null, applicant: null, tutor: null, is_paid: null, is_invoiced: null, is_accepted: null });
const searchQuery = ref('');

const currentRequest = ref(null);

const invoiceDialog = reactive({ visible: false });

const receiptDialog = reactive({ visible: false, title: '', isSaving: false });
const receiptFormRef = ref(null);
const receiptFileList = ref([]);
const receiptForm = reactive({
  id: null,
  receiving_status: '',
  acceptance_photo: null,
});
const receiptFormRules = {
  receiving_status: [{ required: true, message: '请填写收货情况', trigger: 'blur' }],
};


const fetchData = async () => {
  loading.value = true;
  const params = {
    page: pagination.currentPage, page_size: pagination.pageSize,
    expense_type: route.name === 'ledger-c2c' ? 'c2c' : 'public',
    search: searchQuery.value || undefined, applicant: filters.applicant || undefined,
    tutor: filters.tutor || undefined, request_date_after: filters.dateRange ? filters.dateRange[0] : undefined,
    request_date_before: filters.dateRange ? filters.dateRange[1] : undefined,
    is_paid: filters.is_paid === null ? undefined : filters.is_paid,
    is_invoiced: filters.is_invoiced === null ? undefined : filters.is_invoiced,
    is_accepted: filters.is_accepted === null ? undefined : filters.is_accepted,
  };
  try {
    const response = await apiClient.get('/procurement/full-process-requests/', { params });
    requests.value = response.data.results;
    pagination.totalItems = response.data.count;
  } catch (error) { ElMessage.error('获取台账数据失败！'); }
  finally { loading.value = false; }
};

const fetchFilterOptions = async () => {
  try {
    const [usersRes, tutorsRes] = await Promise.all([
      apiClient.get('/users/'),
      apiClient.get('/users/tutors/'),
    ]);
    applicantOptions.value = usersRes.data;
    tutorOptions.value = tutorsRes.data;
  } catch (error) { ElMessage.error('获取筛选选项失败！'); }
};

const applyFilters = () => { pagination.currentPage = 1; fetchData(); };
const resetFilters = () => { Object.assign(filters, { dateRange: null, applicant: null, tutor: null, is_paid: null, is_invoiced: null, is_accepted: null }); searchQuery.value = ''; pagination.currentPage = 1; fetchData(); };
const handleSearch = () => { pagination.currentPage = 1; fetchData(); };
const handleSizeChange = (val) => { pagination.pageSize = val; pagination.currentPage = 1; fetchData(); };
const handleCurrentChange = (val) => { pagination.currentPage = val; fetchData(); };

watch(() => route.path, () => {
  if (route.name === 'ledger-c2c' || route.name === 'ledger-public') { resetFilters(); }
}, { immediate: true });

onMounted(fetchFilterOptions);

const handleSelectionChange = (selection) => { selectedRequests.value = selection; };

const extractBlobErrorMessage = async (error, fallbackMessage) => {
  const responseData = error?.response?.data;
  if (responseData instanceof Blob) {
    try {
      const text = await responseData.text();
      const parsed = JSON.parse(text);
      if (parsed?.error) return parsed.error;
      if (parsed?.detail) return parsed.detail;
    } catch (parseError) {
      // ignore parse errors and use fallback below
    }
  }
  return error?.response?.data?.error || error?.response?.data?.detail || fallbackMessage;
};

const handlePackage = async () => {
  if (selectedRequests.value.length === 0) { ElMessage.warning('请至少勾选一个需要打包的申请。'); return; }
  isPackaging.value = true;
  try {
    const request_ids = selectedRequests.value.map(req => req.id);
    const response = await apiClient.post('/procurement/package-receipts/', { request_ids }, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const today = new Date().toISOString().slice(0, 10);
    link.setAttribute('download', `采购报销附件_${today}.zip`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    ElMessage.success('文件包已开始下载！');
  } catch (error) { ElMessage.error(await extractBlobErrorMessage(error, '打包失败，请稍后重试。')); }
  finally { isPackaging.value = false; }
};

const openInvoiceDialog = (request) => {
  currentRequest.value = request;
  invoiceDialog.visible = true;
};

const onInvoiceSuccess = () => {
    fetchData();
};

const openReceiptDialog = (request) => {
  currentRequest.value = request;
  receiptDialog.title = request.acceptance ? '编辑收货信息' : '填写收货信息';

  receiptFileList.value = [];
  if (request.acceptance) {
    Object.assign(receiptForm, request.acceptance);
    if (request.acceptance.acceptance_photo) {
      receiptFileList.value = [{ name: 'existing.jpg', url: request.acceptance.acceptance_photo }];
    }
  } else {
    Object.assign(receiptForm, { id: null, receiving_status: '', acceptance_photo: null });
  }
  receiptDialog.visible = true;
};

const handleReceiptFileChange = (file) => {
  receiptForm.acceptance_photo = file.raw;
};

const handleReceiptSubmit = async () => {
  if (!receiptFormRef.value) return;
  await receiptFormRef.value.validate(async (valid) => {
    if (valid) {
      receiptDialog.isSaving = true;
      const formData = new FormData();
      formData.append('receiving_status', receiptForm.receiving_status);
      if (!receiptForm.id) {
        formData.append('purchase_request', currentRequest.value.id);
      }
      if (receiptForm.acceptance_photo instanceof File) {
        formData.append('acceptance_photo', receiptForm.acceptance_photo);
      }

      try {
        const url = receiptForm.id ? `/acceptance/acceptances/${receiptForm.id}/` : '/acceptance/acceptances/';
        const method = receiptForm.id ? 'patch' : 'post';
        await apiClient[method](url, formData, { headers: { 'Content-Type': 'multipart/form-data' } });

        receiptDialog.visible = false;
        ElMessage.success('收货信息保存成功！');
        await fetchData();
      } catch (error) { ElMessage.error('提交失败！'); }
      finally { receiptDialog.isSaving = false; }
    }
  });
};
</script>

<style scoped>
h1 { text-align: center; margin: 0; }
.details-container { padding: 16px; background-color: #fafafa; }
.section-divider { margin-top: 20px; }
.details-container ul { list-style-type: none; padding-left: 0; margin: 0; }
.details-container li { margin-bottom: 5px; }
.controls-container { margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 15px; }
.pagination-container { display: flex; justify-content: center; margin-top: 20px; }
</style>
