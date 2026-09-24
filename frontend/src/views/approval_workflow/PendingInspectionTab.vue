<template>
  <div class="pending-inspection-tab">
    <div class="table-actions">
      <el-button
        type="primary"
        @click="handleMerge"
        :disabled="selectedRequests.length < 2"
        :loading="isMerging"
      >
        合并选中项
      </el-button>
      <el-tooltip content="请至少选择 2 个“待验收”状态的项目进行合并" v-if="selectedRequests.length < 2" placement="top">
        <el-icon class="info-icon"><QuestionFilled /></el-icon>
      </el-tooltip>
    </div>

    <el-table :data="requests" style="width: 100%" row-key="id" ref="tableRef" @selection-change="handleSelectionChange" @expand-change="handleExpandChange">
      <el-table-column type="selection" width="55" align="center" :selectable="isRowSelectable" />

      <el-table-column type="expand" width="30">
        <template #default="props">
          <div v-loading="detailsState[props.row.id]?.isLoading" class="details-wrapper">
            <div v-if="detailsState[props.row.id]?.data" class="details-container">

              <div class="detail-actions-bar">
                <el-button
                  type="success"
                  :icon="FolderOpened"
                  @click="handlePackageAttachments(detailsState[props.row.id].data)"
                  :loading="isPackaging && currentPackagingId === props.row.id"
                >
                  一键打包所有附件
                </el-button>
              </div>

              <template v-if="detailsState[props.row.id].data.merged_children && detailsState[props.row.id].data.merged_children.length > 0">
                <div class="merged-view">
                  <el-descriptions title="合并后总览" :column="4" border>
                    <el-descriptions-item label="合并后申请人">{{ detailsState[props.row.id].data.applicant.name }}</el-descriptions-item>
                    <el-descriptions-item label="合并后单号" :span="3">{{ detailsState[props.row.id].data.order_number }}</el-descriptions-item>
                    <el-descriptions-item label="采购平台">
                      {{ [...new Set(detailsState[props.row.id].data.merged_children.map(c => c.platform))].join(', ') }}
                    </el-descriptions-item>
                    <el-descriptions-item label="合并后总金额" :span="3">¥{{ detailsState[props.row.id].data.total_price }}</el-descriptions-item>
                    <el-descriptions-item label="采购内容" :span="4">
                       <div v-for="(item, index) in detailsState[props.row.id].data.items" :key="`summary-${item.id}`" class="item-block-nested">
                         <p class="item-title">
                           <strong>物品 {{ index + 1 }}: {{ item.content }}</strong>
                           <span style="font-size: 12px; color: #909399;"> (原始申请人: {{ item.original_applicant_name || 'N/A' }})</span>
                         </p>
                         <el-descriptions :column="3" border size="small">
                            <el-descriptions-item label="采购类型">{{ item.purchase_type || 'N/A' }}</el-descriptions-item>
                            <el-descriptions-item label="厂商">{{ item.manufacturer || 'N/A' }}</el-descriptions-item>
                            <el-descriptions-item label="CAS号">{{ item.cas_number || 'N/A' }}</el-descriptions-item>
                            <el-descriptions-item label="货号">{{ item.product_number || 'N/A' }}</el-descriptions-item>
                            <el-descriptions-item label="参数">{{ item.parameters || 'N/A' }}</el-descriptions-item>
                            <el-descriptions-item label="规格">{{ item.specifications || 'N/A' }}</el-descriptions-item>
                            <el-descriptions-item label="数量">{{ item.quantity }}</el-descriptions-item>
                            <el-descriptions-item label="单价">¥{{ item.unit_price }}</el-descriptions-item>
                            <el-descriptions-item label="采购链接">
                              <el-link :href="item.purchase_link" type="primary" target="_blank" v-if="item.purchase_link">
                                点击跳转
                              </el-link>
                              <span v-else>N/A</span>
                            </el-descriptions-item>
                          </el-descriptions>
                       </div>
                    </el-descriptions-item>
                  </el-descriptions>

                  <div class="child-details-section section-divider">
                    <h3 class="child-details-title">原始子申请详情</h3>
                    <el-tabs v-model="activeChildTabs[props.row.id]" type="card">
                      <el-tab-pane
                        v-for="child in detailsState[props.row.id].data.merged_children"
                        :key="child.id"
                        :label="`子申请: ${child.order_number}`"
                        :name="child.id"
                      >
                        <el-descriptions title="1. 申请与收货信息" :column="4" border>
                          <el-descriptions-item label="申请人">{{ child.applicant.name }}</el-descriptions-item>
                          <el-descriptions-item label="申请导师">{{ child.applicant_tutor?.name || '无' }}</el-descriptions-item>
                          <el-descriptions-item label="单号" :span="2">{{ child.order_number }}</el-descriptions-item>
                          <el-descriptions-item v-if="child.acceptance" label="收货情况" :span="2">{{ child.acceptance.receiving_status || '未填写' }}</el-descriptions-item>
                          <el-descriptions-item v-if="child.acceptance" label="收货照片" :span="2">
                            <el-image v-if="child.acceptance.acceptance_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.acceptance.acceptance_photo)" :preview-src-list="[resolveMediaUrl(child.acceptance.acceptance_photo)]" fit="cover" preview-teleported />
                            <span v-else>未上传</span>
                          </el-descriptions-item>
                          <el-descriptions-item label="采购物品" :span="4">
                            <div>(该申请的物品已全部合并至父申请的总览中)</div>
                          </el-descriptions-item>
                        </el-descriptions>

                        <el-descriptions v-if="child.purchase_order" title="2. 请购单" :column="4" border class="section-divider">
                          <el-descriptions-item label="请购单文件" :span="4">
                            <el-image v-if="child.purchase_order.order_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.purchase_order.order_file)" :preview-src-list="[resolveMediaUrl(child.purchase_order.order_file)]" fit="cover" preview-teleported />
                            <span v-else>未上传</span>
                          </el-descriptions-item>
                        </el-descriptions>

                        <el-descriptions v-if="child.contract" title="3. 合同" :column="4" border class="section-divider">
                          <el-descriptions-item label="合同文件" :span="4">
                            <el-image v-if="child.contract.contract_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(child.contract.contract_file)" :preview-src-list="[resolveMediaUrl(child.contract.contract_file)]" fit="cover" preview-teleported />
                              <span v-else>未上传</span>
                          </el-descriptions-item>
                        </el-descriptions>

                        <template v-if="getInvoiceList(child).length">
                          <el-descriptions
                            v-for="(invoice, invoiceIndex) in getInvoiceList(child)"
                            :key="invoice.id || invoiceIndex"
                            :title="`4. 发票信息${getInvoiceList(child).length > 1 ? ' ' + (invoiceIndex + 1) : ''}`"
                            :column="4"
                            border
                            class="section-divider"
                          >
                            <el-descriptions-item label="发票单号">{{ invoice.invoice_number }}</el-descriptions-item>
                            <el-descriptions-item label="开票公司" :span="3">{{ invoice.company_name || invoice.company }}</el-descriptions-item>
                            <el-descriptions-item label="发票文件" :span="4">
                              <template v-if="invoice.invoice_image">
                                <el-link v-if="isPdfUrl(invoice.invoice_image)" :href="resolveMediaUrl(invoice.invoice_image)" type="primary" target="_blank">查看PDF发票</el-link>
                                <el-image v-else lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(invoice.invoice_image)" :preview-src-list="[resolveMediaUrl(invoice.invoice_image)]" fit="cover" preview-teleported />
                              </template>
                              <span v-else>未上传</span>
                            </el-descriptions-item>
                          </el-descriptions>
                        </template>
                      </el-tab-pane>
                    </el-tabs>
                  </div>
                </div>
              </template>

              <template v-else>
                <el-descriptions title="1. 申请与收货信息" :column="4" border>
                  <el-descriptions-item label="申请人">{{ detailsState[props.row.id].data.applicant.name }}</el-descriptions-item>
                  <el-descriptions-item label="申请导师">{{ detailsState[props.row.id].data.applicant.assigned_tutor?.name || '无' }}</el-descriptions-item>
                  <el-descriptions-item v-if="detailsState[props.row.id].data.approved_by" label="审批人">{{ detailsState[props.row.id].data.approved_by.name }}</el-descriptions-item>
                  <el-descriptions-item label="申请日期">{{ new Date(detailsState[props.row.id].data.request_date).toLocaleDateString() }}</el-descriptions-item>
                  <el-descriptions-item label="采购平台">{{ detailsState[props.row.id].data.platform }}</el-descriptions-item>
                  <el-descriptions-item label="单号">{{ detailsState[props.row.id].data.order_number }}</el-descriptions-item>
                  <el-descriptions-item label="总金额" :span="2">¥{{ detailsState[props.row.id].data.total_price }}</el-descriptions-item>
                  <el-descriptions-item v-if="detailsState[props.row.id].data.acceptance" label="收货情况" :span="2">{{ detailsState[props.row.id].data.acceptance.receiving_status || '未填写' }}</el-descriptions-item>
                  <el-descriptions-item v-if="detailsState[props.row.id].data.acceptance" label="收货照片" :span="2">
                    <el-image v-if="detailsState[props.row.id].data.acceptance.acceptance_photo" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.acceptance.acceptance_photo)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.acceptance.acceptance_photo)]" fit="cover" preview-teleported />
                    <span v-else>未上传</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="采购物品" :span="4">
                    <div v-for="(item, index) in detailsState[props.row.id].data.items" :key="item.id" class="item-block-nested">
                      <p class="item-title"><strong>物品 {{ index + 1 }}: {{ item.content }}</strong></p>
                      <el-descriptions :column="3" border size="small">
                        <el-descriptions-item label="采购类型">{{ item.purchase_type || 'N/A' }}</el-descriptions-item>
                        <el-descriptions-item label="厂商">{{ item.manufacturer || 'N/A' }}</el-descriptions-item>
                        <el-descriptions-item label="CAS号">{{ item.cas_number || 'N/A' }}</el-descriptions-item>
                        <el-descriptions-item label="货号">{{ item.product_number || 'N/A' }}</el-descriptions-item>
                        <el-descriptions-item label="参数">{{ item.parameters || 'N/A' }}</el-descriptions-item>
                        <el-descriptions-item label="规格">{{ item.specifications || 'N/A' }}</el-descriptions-item>
                        <el-descriptions-item label="数量">{{ item.quantity }}</el-descriptions-item>
                        <el-descriptions-item label="单价">¥{{ item.unit_price }}</el-descriptions-item>
                        <el-descriptions-item label="采购链接">
                          <el-link :href="item.purchase_link" type="primary" target="_blank" v-if="item.purchase_link">
                            点击跳转
                          </el-link>
                          <span v-else>N/A</span>
                        </el-descriptions-item>
                      </el-descriptions>
                    </div>
                  </el-descriptions-item>
                </el-descriptions>

                <el-descriptions v-if="detailsState[props.row.id].data.purchase_order" title="2. 请购单" :column="4" border class="section-divider">
                  <el-descriptions-item label="请购单文件" :span="4">
                    <el-image v-if="detailsState[props.row.id].data.purchase_order.order_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.purchase_order.order_file)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.purchase_order.order_file)]" fit="cover" preview-teleported />
                    <span v-else>未上传</span>
                  </el-descriptions-item>
                </el-descriptions>

                <el-descriptions v-if="detailsState[props.row.id].data.contract" title="3. 合同" :column="4" border class="section-divider">
                  <el-descriptions-item label="合同文件" :span="4">
                    <el-image v-if="detailsState[props.row.id].data.contract.contract_file" lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(detailsState[props.row.id].data.contract.contract_file)" :preview-src-list="[resolveMediaUrl(detailsState[props.row.id].data.contract.contract_file)]" fit="cover" preview-teleported />
                      <span v-else>未上传</span>
                  </el-descriptions-item>
                </el-descriptions>

                <template v-if="getInvoiceList(detailsState[props.row.id].data).length">
                  <el-descriptions
                    v-for="(invoice, invoiceIndex) in getInvoiceList(detailsState[props.row.id].data)"
                    :key="invoice.id || invoiceIndex"
                    :title="`4. 发票信息${getInvoiceList(detailsState[props.row.id].data).length > 1 ? ' ' + (invoiceIndex + 1) : ''}`"
                    :column="4"
                    border
                    class="section-divider"
                  >
                    <el-descriptions-item label="发票单号">{{ invoice.invoice_number }}</el-descriptions-item>
                    <el-descriptions-item label="开票公司" :span="3">{{ invoice.company_name || invoice.company }}</el-descriptions-item>
                    <el-descriptions-item label="发票文件" :span="4">
                      <template v-if="invoice.invoice_image">
                        <el-link v-if="isPdfUrl(invoice.invoice_image)" :href="resolveMediaUrl(invoice.invoice_image)" type="primary" target="_blank">查看PDF发票</el-link>
                        <el-image v-else lazy style="width: 50px; height: 50px" :src="resolveMediaUrl(invoice.invoice_image)" :preview-src-list="[resolveMediaUrl(invoice.invoice_image)]" fit="cover" preview-teleported />
                      </template>
                      <span v-else>未上传</span>
                    </el-descriptions-item>
                  </el-descriptions>
                </template>
              </template>

              <el-form v-if="detailsState[props.row.id]?.isInspecting" :ref="(el) => inspectionFormRefs[props.row.id] = el" :model="inspectionFormsData[props.row.id]" :rules="inspectionFormRules" label-width="100px" class="inspection-form">
                <el-form-item label="验收单号" prop="inspection_number">
                  <el-input v-model="inspectionFormsData[props.row.id].inspection_number" placeholder="请输入验收单号或相关凭证号" />
                </el-form-item>
                <el-form-item label="验收照片" prop="inspection_photo" required>
                  <el-upload
                    :ref="(el) => uploadRefs[props.row.id] = el"
                    :file-list="fileLists[props.row.id]"
                    action="#"
                    drag
                    list-type="picture"
                    :auto-upload="false"
                    :limit="1"
                    :on-change="(file, files) => handleFileChange(file, files, props.row.id)"
                    :on-remove="(file, files) => handleFileRemove(file, files, props.row.id)"
                    :on-exceed="(files) => handleFileExceed(files, props.row.id)"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">
                      将验收照片拖到此处，或<em>点击上传</em>
                    </div>
                    <template #tip>
                      <div class="el-upload__tip">
                        只能上传一张图片
                      </div>
                    </template>
                  </el-upload>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="submitInspectionForm(props.row.id)" :loading="isSubmitting">提交验收</el-button>
                  <el-button @click="toggleInspectionForm(props.row)">取消</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="order_number" label="单号" width="250" />
      <el-table-column prop="applicant.name" label="申请人" width="180" />
      <el-table-column prop="request_date" label="申请日期" width="120" />
      <el-table-column prop="total_price" label="总价" width="120">
        <template #default="scope">¥{{ scope.row.total_price }}</template>
      </el-table-column>
      <el-table-column label="物品 (摘要)" min-width="200">
        <template #default="scope">
           <span v-if="scope.row.items && scope.row.items.length > 0">{{ scope.row.items.map(item => item.content).join(', ') }}</span>
         <span v-else-if="scope.row.merged_children && scope.row.merged_children.length > 0">(合并申请)</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button type="primary" link size="small" @click="toggleInspectionForm(scope.row)">
            {{ detailsState[scope.row.id]?.isInspecting ? '收起表单' : '填写验收信息' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
// 【修改】导入 UploadFilled
import { Plus, QuestionFilled, FolderOpened, UploadFilled } from '@element-plus/icons-vue';

const props = defineProps({
  requests: { type: Array, required: true },
});

const emit = defineEmits(['refresh-data']);

const tableRef = ref(null);
const selectedRequests = ref([]);
const isSubmitting = ref(false);
const isMerging = ref(false);
const expandedRows = ref([]);
const isPackaging = ref(false);
const currentPackagingId = ref(null);
const activeChildTabs = reactive({});

const detailsState = reactive({});
const inspectionFormRefs = ref({});
const uploadRefs = ref({}); // 【新】
const inspectionFormsData = reactive({});
const fileLists = reactive({});

const isRowSelectable = (row) => {
  return row.status === 'invoiced' && !row.parent_request;
};

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

const getFileExtension = (url = '') => {
  const cleanUrl = String(url).split('?')[0].split('#')[0];
  const index = cleanUrl.lastIndexOf('.');
  return index === -1 ? '' : cleanUrl.slice(index + 1).toLowerCase();
};

const isPdfUrl = (url) => getFileExtension(url) === 'pdf';

const getInvoiceList = (row) => {
  const list = row?.invoices;
  if (Array.isArray(list) && list.length > 0) return list;
  if (row?.invoice) return [row.invoice];
  return [];
};

// 【修改】添加自定义照片验证
const validatePhoto = (rule, value, callback) => {
  const requestId = rule.field.split('.')[0]; // 从 prop 动态获取 requestId
  if (!inspectionFormsData[requestId]?.inspection_photo && fileLists[requestId]?.length === 0) {
      callback(new Error('请上传验收照片'));
  } else {
      callback();
  }
};

const inspectionFormRules = {
  inspection_number: [{ required: true, message: '验收单号不能为空', trigger: 'blur' }],
  inspection_photo: [{ validator: validatePhoto, trigger: 'change' }], // 【修改】使用自定义验证
};
// 【修改结束】

const handleSelectionChange = (selection) => {
  selectedRequests.value = selection;
};

const handleMerge = () => {
  const selectedIds = selectedRequests.value.map(req => req.id);
  ElMessageBox.confirm(
    `确定要将选中的 ${selectedIds.length} 个申请合并为一个新的采购申请吗？`,
    '确认合并',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
  ).then(async () => {
    isMerging.value = true;
    try {
      await apiClient.post('/procurement/merge-requests/', { request_ids: selectedIds });
      ElMessage.success('合并成功！新的合并申请已生成。');
      emit('refresh-data');
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '合并失败，请重试。');
    } finally {
      isMerging.value = false;
    }
  }).catch(() => ElMessage.info('已取消合并操作'));
};

const fetchDetails = async (request) => {
    const requestId = request.id;
    if (!detailsState[requestId]) {
        detailsState[requestId] = { isLoading: false, data: null, isInspecting: false };
    }
    detailsState[requestId].isLoading = true;
    try {
        const response = await apiClient.get(`/procurement/full-process-requests/${requestId}/`);
        detailsState[requestId].data = response.data;
        if (response.data.merged_children && response.data.merged_children.length > 0) {
          activeChildTabs[requestId] = response.data.merged_children[0].id;
        }
    } catch (error) {
        ElMessage.error('获取申请详情失败！');
        if (tableRef.value) tableRef.value.toggleRowExpansion(request, false);
    } finally {
        detailsState[requestId].isLoading = false;
    }
};

const handleExpandChange = (row, currentExpandedRows) => {
    expandedRows.value = currentExpandedRows;
    const isExpanded = currentExpandedRows.some(r => r.id === row.id);
    
    if (isExpanded) {
        fetchDetails(row);
    } 
    else {
        if (detailsState[row.id]) {
            detailsState[row.id].isInspecting = false;
        }
    }
};

const toggleInspectionForm = async (request) => {
    const requestId = request.id;
    if (!detailsState[requestId] || !detailsState[requestId].data) {
       if (tableRef.value) {
           const isCurrentlyExpanded = expandedRows.value.some(r => r.id === requestId);
           if (!isCurrentlyExpanded) {
               tableRef.value.toggleRowExpansion(request, true);
           }
       }
       await fetchDetails(request);
    }
    
    const newValue = !detailsState[requestId].isInspecting;
    detailsState[requestId].isInspecting = newValue;

    if (newValue) {
        // 【修改】初始化表单数据
        const existingInspection = detailsState[requestId].data?.inspection;
        inspectionFormsData[requestId] = { 
            inspection_number: existingInspection?.inspection_number || '', 
            inspection_photo: null 
        };
        fileLists[requestId] = existingInspection?.inspection_photo 
            ? [{ name: 'existing_photo.jpg', url: existingInspection.inspection_photo, status: 'success' }] 
            : [];
    } else {
        // （可选）清除数据
        // delete inspectionFormsData[requestId];
        // delete fileLists[requestId];
    }
};

const handlePackageAttachments = async (request) => {
  isPackaging.value = true;
  currentPackagingId.value = request.id;
  try {
    const response = await apiClient.get(
      `/procurement/requests/${request.id}/package-attachments/`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    let filename = `${request.order_number || 'download'}_附件.zip`;
    const disposition = response.headers['content-disposition'];
    if (disposition) {
      const filenameMatch = disposition.match(/filename="(.+?)"/);
      if (filenameMatch && filenameMatch.length > 1) {
        filename = decodeURIComponent(filenameMatch[1]);
      }
    }
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    ElMessage.error('打包文件失败，请检查文件是否存在或联系管理员。');
    console.error("Packaging error:", error);
  } finally {
    isPackaging.value = false;
    currentPackagingId.value = null;
  }
};

// --- 【修改】更新文件处理函数 ---
const handleFileChange = (uploadFile, uploadFiles, requestId) => {
  inspectionFormsData[requestId].inspection_photo = uploadFile.raw;
  fileLists[requestId] = uploadFiles.slice(-1); // 保持列表只有一个文件
  if (inspectionFormRefs.value[requestId]) {
    inspectionFormRefs.value[requestId].validateField('inspection_photo');
  }
};

const handleFileRemove = (uploadFile, uploadFiles, requestId) => {
  inspectionFormsData[requestId].inspection_photo = null;
  fileLists[requestId] = uploadFiles; // 此时 uploadFiles 应为空
  if (inspectionFormRefs.value[requestId]) {
    inspectionFormRefs.value[requestId].validateField('inspection_photo');
  }
};

const handleFileExceed = (files, requestId) => {
  const uploadComponent = uploadRefs.value[requestId];
  if (uploadComponent) {
    uploadComponent.clearFiles(); // 清除旧文件
    const newFile = files[0];
    uploadComponent.handleStart(newFile); // 手动添加新文件
    // handleStart 会触发 on-change, on-change 会更新数据和 fileList
    ElMessage.warning('已替换为新选择的图片。');
  }
};
// --- 【修改结束】 ---

const submitInspectionForm = async (requestId) => {
  const formInstance = inspectionFormRefs.value[requestId];
  if (!formInstance) return;

  // 【修改】确保在提交时，如果 fileList 为空，photo 也为空
  if (fileLists[requestId].length === 0) {
      inspectionFormsData[requestId].inspection_photo = null;
  }

  await formInstance.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      const formData = new FormData();
      formData.append('purchase_request', requestId);
      formData.append('inspection_number', inspectionFormsData[requestId].inspection_number);
      
      const photoData = inspectionFormsData[requestId].inspection_photo;
      if (photoData instanceof File) {
        formData.append('inspection_photo', photoData);
      } else if (!photoData && fileLists[requestId].length === 0) {
          // (理论上 validator 会捕获，但作为双重检查)
          ElMessage.error('请上传验收照片');
          isSubmitting.value = false;
          return;
      }
      // 如果 photoData 为 null 但 fileLists 有内容, 说明是旧照片, 不发送该字段

      try {
        // 【修改】根据是新建还是编辑，使用 POST 或 PATCH
        const existingInspection = detailsState[requestId].data?.inspection;
        if (existingInspection) {
            // 编辑
            await apiClient.patch(`/inspection/inspections/${existingInspection.id}/`, formData);
        } else {
            // 新建
            await apiClient.post('/inspection/inspections/', formData);
        }
        ElMessage.success('验收信息提交成功！');
        emit('refresh-data');
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '提交失败，请重试。');
      } finally {
        isSubmitting.value = false;
      }
    }
  });
};
</script>

<style scoped>
.table-actions { margin-bottom: 16px; display: flex; align-items: center; }
.info-icon { margin-left: 8px; color: #909399; }
.details-wrapper { min-height: 100px; }
.details-container { padding: 20px; background-color: #fafafa; }
.section-divider { margin-top: 20px; } 
.inspection-form { margin-top: 20px; padding-top: 20px; border-top: 1px solid #e4e7ed; }
.item-list { list-style: none; padding: 0; margin: 0; }
.item-list li { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-block-nested { margin-bottom: 12px; }
.item-block-nested:last-child { margin-bottom: 0; }
.item-title { margin: 0 0 8px 0; font-size: 14px; color: #303133; }
.child-details-section { margin-top: 20px; }
.detail-actions-bar {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
}
.child-details-title {
  margin-bottom: 16px;
  font-size: 16px;
  color: #303133;
}
/* 【新】为 el-upload[drag] 设置宽度 (在 el-form-item 内) */
:deep(.el-upload) {
  width: 100%;
}
:deep(.el-upload-dragger) {
  width: 100%; 
}
/* 【新】修复 el-upload-list 中长文件名溢出的问题 */
:deep(.el-upload-list__item-name) {
  overflow-wrap: break-word;
  word-break: break-all;
  white-space: normal;
  min-width: 0;
  line-height: 1.2;
}
</style>
