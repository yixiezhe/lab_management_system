<template>
  <el-card>
    <template #header>
      <h1>{{ pageTitle }}</h1>
    </template>

    <div v-if="expenseType === 'public' && currentDutyPerson" class="duty-person-info">
      📌 本日采购人为：<strong>{{ currentDutyPerson }}</strong>
    </div>

    <div v-if="expenseType === 'public' && authStore.isSystemAdmin" class="duty-config-panel">
      <div class="duty-config-title">管理员设置：每周采购人</div>
      <el-table :data="dutySchedule" border size="small" class="duty-config-table">
        <el-table-column prop="label" label="星期" width="120" />
        <el-table-column label="本日采购人">
          <template #default="scope">
            <el-input v-model="scope.row.name" placeholder="请输入姓名" clearable />
          </template>
        </el-table-column>
      </el-table>
      <div class="duty-config-actions">
        <el-button type="primary" @click="saveDutySchedule" :loading="isDutySaving">保存设置</el-button>
        <el-button @click="resetDutySchedule" :loading="isDutySaving">恢复默认</el-button>
      </div>
    </div>

    <template v-if="hasAccess">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane name="pending_approval">
          <template #label>
            <el-badge :value="counts.pending" :hidden="counts.pending === 0" type="danger" class="tab-badge" :offset="badgeOffset">
              <span class="tab-badge__text">待审批</span>
            </el-badge>
          </template>
        </el-tab-pane>

        <template v-if="expenseType === 'c2c'">
          <el-tab-pane name="pending_purchase_order">
          <template #label>
            <el-badge :value="counts.purchaseOrder" :hidden="counts.purchaseOrder === 0" type="danger" class="tab-badge" :offset="badgeOffset">
              <span class="tab-badge__text">待请购</span>
            </el-badge>
          </template>
        </el-tab-pane>
        <el-tab-pane name="pending_contract">
          <template #label>
            <el-badge :value="counts.contract" :hidden="counts.contract === 0" type="danger" class="tab-badge" :offset="badgeOffset">
              <span class="tab-badge__text">待合同</span>
            </el-badge>
          </template>
        </el-tab-pane>
        </template>

        <el-tab-pane label="待收货" name="pending_receipt"></el-tab-pane>

        <el-tab-pane name="pending_invoicing">
           <template #label>
            <el-badge :value="counts.invoicing" :hidden="counts.invoicing === 0" type="danger" class="tab-badge" :offset="badgeOffset">
              <span class="tab-badge__text">待开票</span>
            </el-badge>
          </template>
        </el-tab-pane>

        <el-tab-pane name="pending_inspection">
           <template #label>
            <el-badge :value="counts.inspection" :hidden="counts.inspection === 0" type="danger" class="tab-badge" :offset="badgeOffset">
              <span class="tab-badge__text">待验收</span>
            </el-badge>
          </template>
        </el-tab-pane>

        <el-tab-pane name="pending_reimbursement">
           <template #label>
            <el-badge :value="counts.reimbursement" :hidden="counts.reimbursement === 0" type="danger" class="tab-badge" :offset="badgeOffset">
              <span class="tab-badge__text">待报销</span>
            </el-badge>
          </template>
        </el-tab-pane>

        <el-tab-pane name="pending_print">
           <template #label>
            <el-badge :value="counts.printing" :hidden="counts.printing === 0" type="danger" class="tab-badge" :offset="badgeOffset">
              <span class="tab-badge__text">投递打印</span>
            </el-badge>
          </template>
        </el-tab-pane>

        <el-tab-pane label="总览" name="overview"></el-tab-pane>
      </el-tabs>

      <div class="tab-content-wrapper" v-loading="loading">
        <div v-if="showC2cInvoiceSearch" class="c2c-invoice-search">
          <el-form :model="childFilters" inline class="controls-container">
            <el-form-item label="发票号">
              <el-input
                v-model="childFilters.invoiceNumber"
                placeholder="输入发票号实时搜索"
                clearable
                style="width: 220px;"
                @input="scheduleInvoiceSearch"
                @clear="scheduleInvoiceSearch"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </el-form-item>
          </el-form>
        </div>

        <div v-if="activeTab === 'overview' && authStore.isSystemAdmin" class="overview-actions">
           <el-button
              type="danger"
              :disabled="selectedRequests.length === 0"
              @click="handleDelete"
              :loading="isDeleting"
            >
              删除选中项
            </el-button>
        </div>

        <div v-if="activeTab === 'overview' && expenseType === 'c2c'" class="overview-export-panel">
          <el-form inline class="controls-container">
            <el-form-item label="平台导出">
              <el-select
                v-model="exportPlatform"
                placeholder="选择平台导出全部记录"
                clearable
                filterable
                :loading="isPlatformLoading"
                style="width: 220px;"
              >
                <el-option v-for="platform in platformOptions" :key="platform.id" :label="platform.name" :value="platform.name" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button
                type="success"
                :disabled="selectedRequests.length === 0"
                :loading="isExporting"
                @click="exportC2CRecords('selected')"
              >
                导出选中表格
              </el-button>
              <el-button
                type="primary"
                :disabled="!exportPlatform"
                :loading="isExporting"
                @click="exportC2CRecords('platform')"
              >
                导出该平台全部
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <div v-if="activeTab === 'overview'" class="overview-filters">
          <el-form :model="childFilters" inline class="controls-container">
            <el-form-item label="申请日期">
              <el-date-picker
                v-model="childFilters.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                clearable
                unlink-panels
              />
            </el-form-item>
            <el-form-item label="申请人">
              <el-select v-model="childFilters.applicant" placeholder="选择申请人" clearable filterable>
                <el-option v-for="user in applicantOptions" :key="user.id" :label="user.name" :value="user.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="采购人员">
              <el-select v-model="childFilters.handler" placeholder="选择采购人员" clearable filterable>
                <el-option v-for="user in procurementStaffOptions" :key="user.id" :label="user.name" :value="user.id" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="expenseType === 'c2c'" label="平台">
              <el-select
                v-model="childFilters.platform"
                placeholder="选择平台"
                clearable
                filterable
                :loading="isPlatformLoading"
                style="width: 180px;"
              >
                <el-option v-for="platform in platformOptions" :key="platform.id" :label="platform.name" :value="platform.name" />
              </el-select>
            </el-form-item>
            <el-form-item label="当前状态">
              <el-select v-model="childFilters.status" placeholder="选择状态" clearable filterable>
                <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="childFilters.searchQuery"
                placeholder="关键词搜索 (物品/单号等)"
                clearable
                @keyup.enter="applyOverviewFilters"
                style="width: 240px;"
              >
                <template #append>
                  <el-button @click="applyOverviewFilters"><el-icon><Search /></el-icon></el-button>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="applyOverviewFilters">筛选</el-button>
              <el-button @click="resetOverviewFilters">重置</el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <div v-if="requestList.length > 0">
          <PublicPendingApprovalTab v-if="activeTab === 'pending_approval' && expenseType === 'public'" :requests="requestList" @refresh-data="handleDataRefresh" />
          <C2cPendingApprovalTab v-else-if="activeTab === 'pending_approval' && expenseType === 'c2c'" :requests="requestList" @refresh-data="handleDataRefresh" />
          
          <el-table v-else-if="activeTab === 'pending_purchase_order'" :data="requestList" stripe border style="width: 100%" row-key="id">
            <el-table-column type="expand">
              <template #default="props">
                <RequestDetail :request="props.row" />
              </template>
            </el-table-column>
            <el-table-column prop="order_number" label="单号" />
            <el-table-column prop="applicant.name" label="申请人" width="120" />
            <el-table-column prop="request_date" label="申请日期" width="120" />
            <el-table-column label="操作" fixed="right" width="220">
              <template #default="scope">
                <el-button size="small" type="primary" @click="openUploadDialog('purchase_order', scope.row)">上传请购单</el-button>
                <el-button size="small" type="warning" @click="handleSkip('purchase_order', scope.row.id)">无需请购单</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <el-table v-else-if="activeTab === 'pending_contract'" :data="requestList" stripe border style="width: 100%" row-key="id">
            <el-table-column type="expand">
              <template #default="props">
                <RequestDetail :request="props.row" />
              </template>
            </el-table-column>
            <el-table-column prop="order_number" label="单号" />
            <el-table-column prop="applicant.name" label="申请人" width="120" />
            <el-table-column prop="request_date" label="申请日期" width="120" />
            <el-table-column label="操作" fixed="right" width="220">
              <template #default="scope">
                <el-button size="small" type="primary" @click="openUploadDialog('contract', scope.row)">上传合同</el-button>
                <el-button size="small" type="warning" @click="handleSkip('contract', scope.row.id)">无需合同</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <PendingInspectionTab v-else-if="activeTab === 'pending_inspection'" :requests="requestList" @refresh-data="handleDataRefresh" />
          <PendingInvoicingTab v-else-if="activeTab === 'pending_invoicing'" :requests="requestList" @refresh-data="handleDataRefresh" />
          <PendingReimbursementTab
            v-else-if="activeTab === 'pending_reimbursement'"
            :requests="requestList"
            :total="pagination.total"
            :page="pagination.page"
            :page-size="pagination.pageSize"
            :initial-filters="childFilters"
            :show-invoice-filter="!showC2cInvoiceSearch"
            @refresh-data="handleDataRefresh"
            @filter-change="handleFilterChange"
            @page-change="handlePageChange"
            @page-size-change="handlePageSizeChange"
          />
          <PendingReimbursementTab
            v-else-if="activeTab === 'pending_print'"
            mode="print"
            :requests="requestList"
            :total="pagination.total"
            :page="pagination.page"
            :page-size="pagination.pageSize"
            :initial-filters="childFilters"
            :show-invoice-filter="!showC2cInvoiceSearch"
            @refresh-data="handleDataRefresh"
            @filter-change="handleFilterChange"
            @page-change="handlePageChange"
            @page-size-change="handlePageSizeChange"
          />
          
          <el-table v-else :data="requestList" stripe border style="width: 100%" ref="genericTableRef" row-key="id" @selection-change="handleSelectionChange">
             <el-table-column v-if="activeTab === 'overview'" type="selection" width="55" align="center" />
             <el-table-column type="expand">
                <template #default="props">
                   <RequestDetail :request="props.row" />
                </template>
             </el-table-column>
             <el-table-column prop="order_number" label="单号" />
             <el-table-column v-if="expenseType === 'c2c'" prop="platform" label="平台" width="120" />
             <el-table-column label="采购人员" width="120">
               <template #default="scope">
                 {{ getHandlerName(scope.row) }}
               </template>
             </el-table-column>
             <el-table-column prop="applicant.name" label="申请人" width="120" />
             <el-table-column prop="request_date" label="申请日期" width="120" />
             <el-table-column label="当前状态" width="120">
                <template #default="scope">
                   <el-tag :type="getStatusTagType(scope.row.status)">
                      {{ statusMap[scope.row.status] || scope.row.status }}
                   </el-tag>
                </template>
             </el-table-column>
             <el-table-column prop="total_price" label="总价" width="120">
               <template #default="scope">{{ getOverviewTotalPriceDisplay(scope.row) }}</template>
             </el-table-column>
             <el-table-column label="操作" fixed="right" width="180">
               <template #default="scope">
                 <el-button type="primary" link size="small" @click="toggleRowExpansion(scope.row)">查看详情</el-button>
               </template>
             </el-table-column>
          </el-table>

          <el-pagination
            v-if="activeTab === 'overview' && pagination.total > 0"
            class="pagination"
            background
            layout="total, sizes, prev, pager, next, jumper"
            :total="pagination.total"
            :current-page="pagination.page"
            :page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="handlePageChange"
            @size-change="handlePageSizeChange"
          />
        </div>

        <p v-else-if="!loading" class="no-data">
          当前阶段暂无申请
        </p>
      </div>
    </template>

    <el-empty v-else description="您没有权限访问此页面" />

  </el-card>

  <el-dialog v-model="uploadDialog.visible" :title="uploadDialog.title" width="500px" :close-on-click-modal="false">
    <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadFormRules">
      <el-form-item :label="uploadDialog.formLabel" prop="file">
        <el-upload
          v-model:file-list="uploadFileList"
          action="#"
          list-type="picture-card"
          :auto-upload="false"
          :limit="1"
          :on-change="handleUploadFileChange"
        >
          <el-icon><Plus /></el-icon>
        </el-upload>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="uploadDialog.visible = false">取消</el-button>
      <el-button type="primary" @click="submitUploadForm" :loading="isSubmitting">确认提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, reactive, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useAuthStore } from '@/stores/auth';
import { Plus, Search } from '@element-plus/icons-vue';
import PendingInspectionTab from './approval_workflow/PendingInspectionTab.vue';
import PendingInvoicingTab from './approval_workflow/PendingInvoicingTab.vue';
import PendingReimbursementTab from './approval_workflow/PendingReimbursementTab.vue';
import PublicPendingApprovalTab from './approval_workflow/PublicPendingApprovalTab.vue';
import C2cPendingApprovalTab from './approval_workflow/C2cPendingApprovalTab.vue';
import RequestDetail from '@/components/RequestDetail.vue';
import {
  DEFAULT_PUBLIC_DUTY_SCHEDULE,
  fetchPublicDutySchedule,
  getTodayPublicDutyPerson,
  publicDutySchedulePayload,
  PUBLIC_DUTY_SCHEDULE_API,
  normalizePublicDutySchedule,
} from '@/utils/publicDutySchedule';

const loading = ref(true);
const activeTab = ref('pending_approval');
const requestList = ref([]);
const defaultFilters = {
  dateRange: null,
  applicant: null,
  handler: null,
  platform: null,
  status: null,
  amountSort: null,
  invoiceNumber: '',
  searchQuery: '',
};
const childFilters = ref({ ...defaultFilters });
const genericTableRef = ref(null);
const authStore = useAuthStore();
const route = useRoute();

const counts = reactive({
  pending: 0,
  purchaseOrder: 0, // Added for C2C
  contract: 0,      // Added for C2C
  invoicing: 0,
  inspection: 0,
  reimbursement: 0,
  printing: 0
});
const badgeOffset = [8, 0];

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
});

let invoiceSearchTimer = null;

const applicantOptions = ref([]);
const procurementStaffOptions = ref([]);
const platformOptions = ref([]);
const isPlatformLoading = ref(false);

const selectedRequests = ref([]);
const isDeleting = ref(false);
const isExporting = ref(false);
const exportPlatform = ref(null);

const currentDutyPerson = ref('');
const dutySchedule = ref(DEFAULT_PUBLIC_DUTY_SCHEDULE.map(item => ({ ...item })));
const isDutySaving = ref(false);

const applyTodayDutyPerson = () => {
  currentDutyPerson.value = getTodayPublicDutyPerson(dutySchedule.value);
};

const loadDutySchedule = async () => {
  if (expenseType.value !== 'public') return;

  try {
    dutySchedule.value = await fetchPublicDutySchedule();
  } catch (error) {
    dutySchedule.value = DEFAULT_PUBLIC_DUTY_SCHEDULE.map(item => ({ ...item }));
    ElMessage.error('获取每周采购人设置失败，已回退到默认值。');
  } finally {
    applyTodayDutyPerson();
  }
};

const saveDutySchedule = async () => {
  const normalized = normalizePublicDutySchedule(dutySchedule.value);
  dutySchedule.value = normalized;
  isDutySaving.value = true;

  try {
    await apiClient.put(PUBLIC_DUTY_SCHEDULE_API, {
      weekly_duty: publicDutySchedulePayload(normalized),
    });
    applyTodayDutyPerson();
    ElMessage.success('已保存本日采购人设置。');
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败，请稍后重试。');
  } finally {
    isDutySaving.value = false;
  }
};

const resetDutySchedule = async () => {
  isDutySaving.value = true;

  try {
    const defaults = DEFAULT_PUBLIC_DUTY_SCHEDULE.map(item => ({ ...item }));
    await apiClient.put(PUBLIC_DUTY_SCHEDULE_API, {
      weekly_duty: publicDutySchedulePayload(defaults),
    });
    dutySchedule.value = defaults;
    applyTodayDutyPerson();
    ElMessage.success('已恢复默认采购人设置。');
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '恢复默认失败，请稍后重试。');
  } finally {
    isDutySaving.value = false;
  }
};

const handleSelectionChange = (selection) => {
    selectedRequests.value = selection;
};

const handleDelete = () => {
    const selectedIds = selectedRequests.value.map(req => req.id);
    const count = selectedIds.length;
    ElMessageBox.confirm(
        `确定要永久删除这 ${count} 条申请记录吗？此操作不可逆，合并的子申请也会一并删除。`,
        '高危操作确认',
        { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    ).then(async () => {
        isDeleting.value = true;
        try {
            await apiClient.post('/procurement/bulk-delete-requests/', { request_ids: selectedIds });
            ElMessage.success(`成功删除了 ${count} 条记录。`);
            handleDataRefresh();
        } catch (error) {
            ElMessage.error(error.response?.data?.error || '删除失败，请重试。');
        } finally {
            isDeleting.value = false;
        }
    }).catch(() => {
        ElMessage.info('已取消删除操作');
    });
};

const expenseType = computed(() => route.meta.expenseType);
const pageTitle = computed(() => route.meta.title || '采购流程');

const hasAccess = computed(() => {
  if (!authStore.user?.roles) return false;
  
  const currentExpenseType = expenseType.value;
  
  if (currentExpenseType === 'public') {
    return authStore.user.roles.some(r => ['采购人员', '导师用户', '系统管理员'].includes(r.name));
  }
  
  if (currentExpenseType === 'c2c') {
    return authStore.isC2CPlatformManager || authStore.isTutor || authStore.user.roles.some(r => r.name === '系统管理员');
  }
  
  return false;
});


const statusMap = {
  'pending': '待审批',
  'approved': '待支付',
  'pending_purchase_order': '待请购',
  'pending_contract': '待合同',
  'paid': '待收货',
  'goods_received': '待开票',
  'invoiced': '待验收',
  'accepted': '待报销',
  'inspection_skipped': '待报销 (无需验收)',
  'reimbursed': '已报销',
  'rejected': '已驳回',
  'withdrawn': '已撤回',
  'payment_rejected': '付款被驳回',
  'completed': '已完成',
  'merged': '已合并',
};

const statusOptions = computed(() => {
  return Object.entries(statusMap).map(([value, label]) => ({ value, label }));
});

const c2cInvoiceSearchTabs = ['overview', 'pending_inspection', 'pending_reimbursement', 'pending_print'];
const showC2cInvoiceSearch = computed(() => (
  expenseType.value === 'c2c' && c2cInvoiceSearchTabs.includes(activeTab.value)
));

const getStatusTagType = (status) => {
  switch (status) {
    case 'pending': case 'payment_rejected': return 'warning';
    case 'rejected': return 'danger';
    case 'approved': case 'paid': return 'primary';
    case 'goods_received': case 'invoiced': return 'primary';
    case 'accepted': case 'inspection_skipped': return 'primary';
    case 'pending_purchase_order': return 'primary';
    case 'pending_contract': return 'primary';
    case 'reimbursed': case 'completed': return 'success';
    default: return 'info';
  }
};

const formatMoney = (value) => {
  if (value === null || value === undefined || value === '') return '未填写';
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return `¥${value}`;
  return `¥${numberValue.toFixed(2)}`;
};

const getOverviewTotalPriceDisplay = (row) => {
  const value = expenseType.value === 'c2c' && activeTab.value === 'overview'
    ? (row.actual_payment_amount ?? row.total_price)
    : row.total_price;
  return formatMoney(value);
};

const fetchAllCounts = async () => {
  if (!hasAccess.value) return;

  Object.keys(counts).forEach(key => counts[key] = 0);

  const getCount = async (statusParams) => {
    const currentExpenseType = expenseType.value;
    if (!currentExpenseType) return 0;

    let endpoint = '';
    if (currentExpenseType === 'public') {
      endpoint = '/procurement/public-purchase-requests/';
    } else if (currentExpenseType === 'c2c') {
      endpoint = '/procurement/c2c-purchase-requests/';
    } else {
      return 0;
    }

    const params = { ...statusParams, scope: 'all', page_size: 1 };

    try {
      const response = await apiClient.get(endpoint, { params });
      return response.data.count || 0;
    } catch (error) {
      console.error(`获取数量失败 for status ${JSON.stringify(statusParams)}:`, error);
      return 0;
    }
  };

  const commonPromises = [
    getCount({ status__in: 'pending,payment_rejected' }),
    getCount({ status: 'goods_received' }),
    getCount({ status: 'invoiced' }),
    getCount({ status: 'pending_reimbursement' }),
    getCount({ status: 'reimbursed' })
  ];
  const [pending, invoicing, inspection, reimbursement, printing] = await Promise.all(commonPromises);
  counts.pending = pending;
  counts.invoicing = invoicing;
  counts.inspection = inspection;
  counts.reimbursement = reimbursement;
  counts.printing = printing;

  if (expenseType.value === 'c2c') {
    const c2cPromises = [
      getCount({ status: 'pending_purchase_order' }),
      getCount({ status: 'pending_contract' })
    ];
    const [purchaseOrder, contract] = await Promise.all(c2cPromises);
    counts.purchaseOrder = purchaseOrder;
    counts.contract = contract;
  }
};

const fetchRequests = async () => {
  if (!hasAccess.value) {
    loading.value = false;
    requestList.value = [];
    pagination.total = 0;
    return;
  }

  loading.value = true;
  
  const currentExpenseType = expenseType.value;
  if (!currentExpenseType) {
    loading.value = false;
    return;
  }

  const params = {
    scope: 'all',
    applicant: childFilters.value.applicant || undefined,
    handler: childFilters.value.handler || undefined,
    platform: childFilters.value.platform || undefined,
    status: childFilters.value.status || undefined,
    search: childFilters.value.searchQuery || undefined,
    ordering: childFilters.value.amountSort || undefined,
    invoice_number: childFilters.value.invoiceNumber || undefined,
    request_date_after: childFilters.value.dateRange ? childFilters.value.dateRange[0] : undefined,
    request_date_before: childFilters.value.dateRange ? childFilters.value.dateRange[1] : undefined,
    requires_inspection: childFilters.value.requires_inspection ?? undefined,
  };
  
  if (activeTab.value !== 'overview') {
      switch (activeTab.value) {
        case 'pending_approval':
          params.status__in = 'pending,payment_rejected';
          break;
        case 'pending_purchase_order':
          params.status = 'pending_purchase_order';
          break;
        case 'pending_contract':
          params.status = 'pending_contract';
          break;
        case 'pending_receipt':
          params.status = 'paid';
          break;
        case 'pending_invoicing':
          params.status = 'goods_received';
          break;
        case 'pending_inspection':
          params.status = 'invoiced';
          break;
        case 'pending_reimbursement':
          params.status = 'pending_reimbursement';
          break;
        case 'pending_print':
          params.status = 'reimbursed';
          break;
        default:
          loading.value = false;
          return;
      }
  }

  try {
    let endpoint = '';
    if (currentExpenseType === 'public') {
        endpoint = '/procurement/public-purchase-requests/';
    } else if (currentExpenseType === 'c2c') {
        endpoint = '/procurement/c2c-purchase-requests/';
    } else {
        throw new Error('Unknown expense type');
    }
    
    const isPagedTab = ['pending_reimbursement', 'pending_print', 'overview'].includes(activeTab.value);
    if (isPagedTab) {
      params.page = pagination.page;
      params.page_size = pagination.pageSize;
    } else {
      pagination.total = 0;
    }

    const response = await apiClient.get(endpoint, { params });
    const responseData = response.data;
    requestList.value = responseData.results || responseData;
    if (isPagedTab) {
      if (typeof responseData.count === 'number') {
        pagination.total = responseData.count;
      } else if (Array.isArray(requestList.value)) {
        pagination.total = requestList.value.length;
      } else {
        pagination.total = 0;
      }
    }

  } catch (error) {
    ElMessage.error('获取列表失败，请稍后重试。');
  } finally {
    loading.value = false;
  }
};

const handleTabChange = () => {
  clearInvoiceSearchTimer();
  childFilters.value = { ...defaultFilters };
  pagination.page = 1;
  fetchRequests();
};

const handleDataRefresh = () => {
    fetchRequests();
    fetchAllCounts();
}

const handleFilterChange = (filters) => {
    clearInvoiceSearchTimer();
    childFilters.value = { ...defaultFilters, ...filters };
    pagination.page = 1;
    fetchRequests();
}

const applyOverviewFilters = () => {
  clearInvoiceSearchTimer();
  pagination.page = 1;
  fetchRequests();
};

const resetOverviewFilters = () => {
  clearInvoiceSearchTimer();
  childFilters.value = { ...defaultFilters };
  pagination.page = 1;
  fetchRequests();
};

const clearInvoiceSearchTimer = () => {
  if (invoiceSearchTimer) {
    clearTimeout(invoiceSearchTimer);
    invoiceSearchTimer = null;
  }
};

const scheduleInvoiceSearch = () => {
  clearInvoiceSearchTimer();
  invoiceSearchTimer = setTimeout(() => {
    invoiceSearchTimer = null;
    pagination.page = 1;
    fetchRequests();
  }, 300);
};

const handlePageChange = (newPage) => {
  pagination.page = newPage;
  fetchRequests();
};

const handlePageSizeChange = (newSize) => {
  pagination.pageSize = newSize;
  pagination.page = 1;
  fetchRequests();
};

const toggleRowExpansion = (row) => {
    if (genericTableRef.value) {
        genericTableRef.value.toggleRowExpansion(row);
    }
}

watch(() => route.path, () => {
    clearInvoiceSearchTimer();
    activeTab.value = 'pending_approval';
    childFilters.value = { ...defaultFilters };
    pagination.page = 1;
    if (expenseType.value === 'public') {
      loadDutySchedule();
      platformOptions.value = [];
      exportPlatform.value = null;
    } else {
      currentDutyPerson.value = '';
      fetchPlatformOptions();
    }
    handleDataRefresh();
});

const fetchUserOptions = async () => {
  try {
    const res = await apiClient.get('/users/');
    applicantOptions.value = res.data;
    procurementStaffOptions.value = res.data.filter(
      user => Array.isArray(user.roles) && user.roles.some(role => role.name === '采购人员')
    );
  } catch (error) {
    ElMessage.error('获取用户列表失败，请稍后重试。');
  }
};

const fetchPlatformOptions = async () => {
  if (expenseType.value !== 'c2c') {
    platformOptions.value = [];
    exportPlatform.value = null;
    return;
  }

  isPlatformLoading.value = true;
  try {
    const response = await apiClient.get('/procurement/platforms/', { params: { category: 'c2c' } });
    const data = response.data?.results || response.data;
    platformOptions.value = Array.isArray(data) ? data : [];
  } catch (error) {
    platformOptions.value = [];
    ElMessage.error('获取平台列表失败，请稍后重试。');
  } finally {
    isPlatformLoading.value = false;
  }
};

const getHandlerName = (row) => {
  if (row?.handler?.name) return row.handler.name;
  if (row?.handler_name) return row.handler_name;
  if (row?.handler) {
    const matched = procurementStaffOptions.value.find(user => user.id === row.handler)
      || applicantOptions.value.find(user => user.id === row.handler);
    return matched ? matched.name : String(row.handler);
  }
  return '未指定';
};

const getFilenameFromDisposition = (disposition, fallback) => {
  if (!disposition) return fallback;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const asciiMatch = disposition.match(/filename="?([^";]+)"?/i);
  return asciiMatch?.[1] || fallback;
};

const getBlobErrorMessage = async (error) => {
  const data = error.response?.data;
  if (!(data instanceof Blob)) {
    return error.response?.data?.error || error.response?.data?.detail || '导出失败，请稍后重试。';
  }

  try {
    const text = await data.text();
    const parsed = JSON.parse(text);
    return parsed.error || parsed.detail || '导出失败，请稍后重试。';
  } catch {
    return '导出失败，请稍后重试。';
  }
};

const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

const exportC2CRecords = async (mode) => {
  if (expenseType.value !== 'c2c') return;

  const payload = {};
  if (mode === 'selected') {
    const ids = selectedRequests.value.map(item => item.id);
    if (ids.length === 0) {
      ElMessage.warning('请先勾选要导出的记录。');
      return;
    }
    payload.request_ids = ids;
  } else {
    if (!exportPlatform.value) {
      ElMessage.warning('请先选择要导出的平台。');
      return;
    }
    payload.platform = exportPlatform.value;
  }

  isExporting.value = true;
  try {
    const response = await apiClient.post('/procurement/c2c-platform-records-export/', payload, {
      responseType: 'blob',
    });
    const filename = getFilenameFromDisposition(
      response.headers?.['content-disposition'],
      `公对公购买记录_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`
    );
    downloadBlob(response.data, filename);
    ElMessage.success('表格已生成。');
  } catch (error) {
    ElMessage.error(await getBlobErrorMessage(error));
  } finally {
    isExporting.value = false;
  }
};

onMounted(() => {
  if (expenseType.value === 'public') {
    loadDutySchedule();
  } else if (expenseType.value === 'c2c') {
    fetchPlatformOptions();
  }
  fetchUserOptions();
  handleDataRefresh();
});

onBeforeUnmount(() => {
  clearInvoiceSearchTimer();
});


const isSubmitting = ref(false);
const uploadDialog = reactive({ visible: false, title: '', formLabel: '', type: '' });
const uploadFormRef = ref(null);
const uploadFileList = ref([]);
const uploadForm = reactive({ file: null, purchase_request: null });
const uploadFormRules = { file: [{ required: true, message: '请上传文件', trigger: 'change' }] };

const openUploadDialog = (type, request) => {
  uploadDialog.type = type;
  uploadDialog.visible = true;
  uploadForm.purchase_request = request.id;
  uploadFileList.value = [];
  if (uploadFormRef.value) uploadFormRef.value.resetFields();

  if (type === 'purchase_order') {
    uploadDialog.title = '上传请购单';
    uploadDialog.formLabel = '请购单文件';
  } else {
    uploadDialog.title = '上传合同';
    uploadDialog.formLabel = '合同文件';
  }
};

const handleUploadFileChange = (file) => {
  uploadForm.file = file.raw;
  if(uploadFormRef.value) {
    uploadFormRef.value.validateField('file');
  }
};

const submitUploadForm = async () => {
  if (!uploadFormRef.value) return;
  await uploadFormRef.value.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      const formData = new FormData();
      const isPO = uploadDialog.type === 'purchase_order';
      const endpoint = isPO ? '/purchase-orders/purchase-orders/' : '/contracts/contracts/';
      const fieldName = isPO ? 'po_form' : 'contract_form';
      
      formData.append(fieldName, uploadForm.file);
      formData.append('purchase_request', uploadForm.purchase_request);

      try {
        await apiClient.post(endpoint, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
        ElMessage.success('文件上传成功！');
        uploadDialog.visible = false;
        await handleDataRefresh();
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || error.response?.data?.[fieldName]?.[0] || '提交失败，请重试。');
      } finally {
        isSubmitting.value = false;
      }
    }
  });
};

const handleSkip = (type, requestId) => {
  const typeText = type === 'purchase_order' ? '请购单' : '合同';
  ElMessageBox.confirm(`确定要跳过此申请的【${typeText}】环节吗？`, '确认操作', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    const endpoint = `/procurement/c2c-purchase-requests/${requestId}/${ type === 'purchase_order' ? 'skip_purchase_order' : 'skip_contract' }/`;
    try {
      await apiClient.post(endpoint);
      ElMessage.success(`已成功跳过${typeText}环节！`);
      await handleDataRefresh();
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '操作失败，请重试。');
    }
  }).catch(() => { ElMessage.info('已取消操作'); });
};
</script>

<style scoped>
/* 【新】添加提示信息样式 */
.duty-person-info {
  margin-bottom: 15px; /* 与下方 Tabs 的间距 */
  padding: 8px 12px;
  background-color: #f0f9eb; /* Element Plus 成功提示的背景色 */
  color: #67c23a; /* Element Plus 成功提示的文字颜色 */
  border-radius: 4px;
  font-size: 14px;
}
.duty-person-info strong {
  font-weight: 600;
}
.duty-config-panel {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafafa;
}
.duty-config-title {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.duty-config-table {
  margin-bottom: 10px;
}
.duty-config-actions {
  display: flex;
  gap: 8px;
}
/* (其他样式保持不变) */
.tab-content-wrapper { margin-top: 20px; }
.c2c-invoice-search { margin-bottom: 12px; }
.overview-filters { margin-bottom: 12px; }
.controls-container { margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 15px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
.no-data { text-align: center; color: #909399; padding: 20px; }
.overview-actions {
    margin-bottom: 16px;
}
.overview-export-panel {
    margin-bottom: 12px;
}
:deep(.el-tabs__item) {
    margin-right: 12px;
    overflow: visible;
}
:deep(.el-tabs__nav-wrap),
:deep(.el-tabs__nav-scroll),
:deep(.el-tabs__nav) {
    overflow: visible;
}
</style>
