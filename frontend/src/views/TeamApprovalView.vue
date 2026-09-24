<template>
  <el-card>
    <template #header>
      <h1>小组采购审核</h1>
    </template>

    <el-tabs v-model="activeTab" @tab-change="fetchRequests">
      <el-tab-pane label="待审批" name="pending"></el-tab-pane>
      <el-tab-pane label="已处理" name="processed"></el-tab-pane>
    </el-tabs>

    <el-table :data="requestList" stripe border style="width: 100%" v-loading="loading">
      <el-table-column type="expand">
        <template #default="props">
          <div class="expanded-content">
            <div v-for="(item, index) in props.row.items" :key="item.id" class="item-description-block">
              <el-descriptions :title="`物品明细 ${index + 1}`" :column="2" border size="small">
                <el-descriptions-item label="采购内容">{{ item.content }}</el-descriptions-item>
                <el-descriptions-item label="规格">{{ item.specifications || '未填写' }}</el-descriptions-item>
                <el-descriptions-item label="数量">{{ item.quantity }}</el-descriptions-item>
                <el-descriptions-item label="单价">¥ {{ item.unit_price }}</el-descriptions-item>
                <el-descriptions-item label="采购链接" :span="2">
                  <a v-if="item.purchase_link" :href="item.purchase_link" target="_blank" rel="noopener noreferrer">{{ item.purchase_link }}</a>
                  <span v-else>未提供</span>
                </el-descriptions-item>
              </el-descriptions>
            </div>
            <div class="total-price">
              <strong>总价:</strong> ¥ {{ props.row.total_price }}
            </div>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column prop="applicant.name" label="申请人" width="120" />
      <el-table-column prop="applicant.assigned_tutor.name" label="申请人导师" width="120" />
      <el-table-column prop="request_date" label="申请日期" width="120" />
      <el-table-column label="申请内容概览">
        <template #default="scope">
          {{ scope.row.items.map(item => item.content).join('; ') }}
        </template>
      </el-table-column>
      <el-table-column prop="total_price" label="总价" width="120">
        <template #default="scope">¥{{ scope.row.total_price }}</template>
      </el-table-column>
      
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <div v-if="scope.row.status === 'pending'">
            <el-button size="small" type="success" @click="handleApprove(scope.row.id)">批准</el-button>
            <el-button size="small" type="danger" @click="handleReject(scope.row.id)">驳回</el-button>
          </div>
          <el-tag v-else-if="scope.row.status === 'approved'" type="success">已批准</el-tag>
          <el-tag v-else-if="scope.row.status === 'rejected'" type="danger">已驳回</el-tag>
        </template>
      </el-table-column>
    </el-table>
     <p v-if="!loading && requestList.length === 0" class="no-data">
       {{ activeTab === 'pending' ? '暂无待审批的申请' : '暂无已处理的申请' }}
     </p>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';

const loading = ref(true);
const activeTab = ref('pending');
const requestList = ref([]);

const fetchRequests = async () => {
  loading.value = true;
  let params = {};
  // 检查后端 TeamPurchaseRequestViewSet 的 get_queryset 逻辑
  // 审批者默认看到 'pending'，所以可以不传
  if (activeTab.value === 'pending') {
    // params = { status: 'pending' }; 
  } else {
    params = { status__in: 'approved,rejected' };
  }
  try {
    const response = await apiClient.get('/team-procurement/requests/', { params });
    requestList.value = response.data;
  } catch (error) {
    ElMessage.error('获取列表失败');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchRequests);

const handleApprove = async (id) => {
  try {
    await apiClient.post(`/team-procurement/requests/${id}/approve/`);
    ElMessage.success('操作成功：已批准');
    fetchRequests();
  } catch (error) {
    ElMessage.error('操作失败');
  }
};

const handleReject = (id) => {
  ElMessageBox.prompt('请输入驳回原因', '驳回申请', {
    confirmButtonText: '确定驳回', cancelButtonText: '取消',
    inputValidator: (value) => { if (!value || value.trim() === '') return '必须填写驳回原因'; return true; },
  })
  .then(async ({ value }) => {
    try {
      await apiClient.post(`/team-procurement/requests/${id}/reject/`, { reason: value });
      ElMessage.success('操作成功：已驳回');
      fetchRequests();
    } catch (error) {
      ElMessage.error('操作失败');
    }
  })
  .catch(() => { ElMessage.info('已取消驳回操作'); });
};
</script>

<style scoped>
h1 { text-align: center; margin: 0; }
.no-data { text-align: center; color: #909399; padding: 20px; }
.expanded-content { padding: 16px; background-color: #f9f9f9; }
.item-description-block { margin-bottom: 24px; }
.item-description-block:last-child { margin-bottom: 0; }
.total-price { text-align: right; margin-top: 16px; font-size: 16px; color: #e6a23c; }
a { color: #409eff; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>