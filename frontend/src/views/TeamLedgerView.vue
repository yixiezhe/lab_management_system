<template>
  <div>
    <el-card>
      <template #header>
        <h1>小组采购台账</h1>
      </template>

      <el-form :model="filters" inline class="controls-container">
        <el-form-item label="申请日期">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
          />
        </el-form-item>
        <el-form-item label="申请人">
            <el-select v-model="filters.applicant" placeholder="选择申请人" clearable filterable>
                <el-option v-for="user in applicantOptions" :key="user.id" :label="user.name" :value="user.id" />
            </el-select>
        </el-form-item>
        <el-form-item label="导师">
            <el-select v-model="filters.tutor" placeholder="选择导师" clearable filterable>
                <el-option v-for="user in tutorOptions" :key="user.id" :label="user.name" :value="user.id" />
            </el-select>
        </el-form-item>
        <el-form-item>
            <el-input v-model="searchQuery" placeholder="关键词搜索 (物品/规格等)" clearable @keyup.enter="handleSearch" style="width: 240px;">
                 <template #append>
                     <el-button @click="handleSearch">
                         <el-icon><Search /></el-icon>
                     </el-button>
                 </template>
            </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="requests" v-loading="loading" style="width: 100%" border row-key="id">
        <el-table-column type="expand">
          <template #default="props">
            <div class="details-container">
              <el-descriptions title="申请详情" :column="3" border>
                <el-descriptions-item label="申请人">{{ props.row.applicant.name }}</el-descriptions-item>
                <el-descriptions-item label="所属导师">{{ props.row.tutor.name }}</el-descriptions-item>
                <el-descriptions-item label="申请日期">{{ new Date(props.row.request_date).toLocaleDateString() }}</el-descriptions-item>
                <el-descriptions-item label="审批人">{{ props.row.approved_by?.name || 'N/A' }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                    <el-tag :type="getStatusType(props.row.status)">{{ getStatusText(props.row.status) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="总金额">¥{{ props.row.total_price }}</el-descriptions-item>
                <el-descriptions-item label="采购物品" :span="3">
                  <ul>
                    <li v-for="item in props.row.items" :key="item.id">
                      {{ item.content }} ({{ item.specifications }}) - ¥{{ item.unit_price }} x {{ item.quantity }}
                    </li>
                  </ul>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="序号" width="70" align="center">
            <template #default="scope">
                {{ (pagination.currentPage - 1) * pagination.pageSize + scope.$index + 1 }}
            </template>
        </el-table-column>

        <el-table-column prop="request_date" label="日期" width="120"/>
        <el-table-column prop="applicant.name" label="申请人" width="120" />
        <el-table-column prop="tutor.name" label="所属导师" width="120" />
        <el-table-column label="内容概览">
            <template #default="scope">
                {{ scope.row.items.map(item => item.content).join(', ') }}
            </template>
        </el-table-column>
        <el-table-column label="总价" width="120">
            <template #default="scope">¥{{ parseFloat(scope.row.total_price).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
            <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
            </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="pagination.totalItems"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { Search } from '@element-plus/icons-vue';

const requests = ref([]);
const loading = ref(true);

const applicantOptions = ref([]);
const tutorOptions = ref([]);

const pagination = reactive({
    currentPage: 1,
    pageSize: 20,
    totalItems: 0,
});

const filters = reactive({
  dateRange: null,
  applicant: null,
  tutor: null,
});

const searchQuery = ref('');

const fetchData = async () => {
  loading.value = true;
  
  const params = {
    page: pagination.currentPage,
    page_size: pagination.pageSize,
    search: searchQuery.value || undefined,
    applicant: filters.applicant || undefined,
    tutor: filters.tutor || undefined,
    request_date_after: filters.dateRange ? filters.dateRange[0] : undefined,
    request_date_before: filters.dateRange ? filters.dateRange[1] : undefined,
  };

  try {
    const response = await apiClient.get('/team-procurement/full-process-requests/', { params });
    requests.value = response.data.results;
    pagination.totalItems = response.data.count;
  } catch (error) {
    ElMessage.error('获取小组台账数据失败！');
  } finally {
    loading.value = false;
  }
};

const fetchFilterOptions = async () => {
    try {
        const [usersRes, tutorsRes] = await Promise.all([
            apiClient.get('/users/'),
            apiClient.get('/users/tutors/'),
        ]);
        applicantOptions.value = usersRes.data;
        tutorOptions.value = tutorsRes.data;
    } catch (error) {
        ElMessage.error('获取筛选选项失败！');
    }
};

const applyFilters = () => {
    pagination.currentPage = 1;
    fetchData();
};

const resetFilters = () => {
    filters.dateRange = null;
    filters.applicant = null;
    filters.tutor = null;
    searchQuery.value = '';
    pagination.currentPage = 1;
    fetchData();
};

const handleSearch = () => {
    pagination.currentPage = 1;
    fetchData();
};

const handleSizeChange = (val) => {
    pagination.pageSize = val;
    pagination.currentPage = 1;
    fetchData();
};

const handleCurrentChange = (val) => {
    pagination.currentPage = val;
    fetchData();
};

onMounted(() => {
    fetchFilterOptions();
    fetchData();
});

const getStatusText = (status) => {
    const map = {
        approved: '已批准',
        paid: '已支付',
        ordered: '已下单',
        invoiced: '已报销',
        // 【修改点】将 '已验收' 改为 '已收货'
        accepted: '已收货'
    };
    return map[status] || status;
};
const getStatusType = (status) => {
    const map = {
        approved: 'primary',
        accepted: 'success',
    };
    return map[status] || 'info';
}
</script>

<style scoped>
h1 { text-align: center; margin: 0; }
.details-container { padding: 16px; background-color: #fafafa; }
.details-container ul { list-style-type: none; padding-left: 0; margin: 0; }
.details-container li { margin-bottom: 5px; }

.controls-container {
    margin-bottom: 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
}
.pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 20px;
}
</style>