<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <h1>白名单管理</h1>
        <el-button v-if="authStore.canManageWhitelist || authStore.isTutor" type="primary" :icon="Plus" @click="handleCreate">新增项目</el-button>
      </div>
    </template>

    <div class="search-bar">
      <el-input v-model="searchQuery" placeholder="输入关键词搜索采购内容" clearable @clear="fetchWhitelist" @keyup.enter="fetchWhitelist" />
      <el-button type="primary" :icon="Search" @click="fetchWhitelist">搜索</el-button>
    </div>

    <el-table :data="whitelist" stripe border v-loading="loading" style="width: 100%">
      <el-table-column prop="content" label="采购内容" />
      <el-table-column prop="platform" label="平台/服务" />
      <el-table-column prop="main_category" label="主分类">
        <template #default="scope">{{ formatMainCategory(scope.row.main_category) }}</template>
      </el-table-column>
      <el-table-column prop="purchase_type" label="采购类型">
        <template #default="scope">{{ purchaseTypeMap[scope.row.purchase_type] }}</template>
      </el-table-column>
      <el-table-column v-if="authStore.canManageWhitelist || authStore.isTutor" label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
     <el-empty v-if="!loading && whitelist.length === 0" description="暂无白名单数据"></el-empty>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="50%">
    <el-form :model="currentItem" ref="whitelistFormRef" label-width="120px" style="max-width: 600px; margin: 0 auto;">
      <el-form-item label="采购内容" prop="content" :rules="[{ required: true, message: '采购内容不能为空', trigger: 'blur' }]">
        <el-input v-model="currentItem.content" placeholder="必填" />
      </el-form-item>
      
      <el-form-item label="平台/服务" prop="platform">
        <el-input v-model="currentItem.platform" placeholder="例如：淘宝、京东、具体公司名" />
      </el-form-item>
      
      <el-form-item label="主分类" prop="main_category" :rules="[{ required: true, type: 'array', min: 1, message: '请至少选择一个主分类', trigger: 'change' }]">
        <el-select 
          v-model="currentItem.main_category" 
          multiple 
          placeholder="请选择主分类 (可多选)"
          style="width: 100%;"
        >
          <el-option label="公对公" value="c2c" />
          <el-option label="公共经费" value="public" />
        </el-select>
      </el-form-item>

      <el-form-item label="采购类型" prop="purchase_type" :rules="[{ required: true, message: '请选择采购类型', trigger: 'change' }]">
        <el-select v-model="currentItem.purchase_type" placeholder="请选择采购类型">
          <el-option label="耗材" value="consumable" />
          <el-option label="药品" value="chemical" />
          <el-option label="设备" value="equipment" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      
      <el-form-item label="厂商" prop="manufacturer">
        <el-input v-model="currentItem.manufacturer" placeholder="选填" />
      </el-form-item>
      <el-form-item label="货号" prop="product_number">
        <el-input v-model="currentItem.product_number" placeholder="选填" />
      </el-form-item>
      <el-form-item label="CAS号" prop="cas_number">
        <el-input v-model="currentItem.cas_number" placeholder="选填" />
      </el-form-item>
      <el-form-item label="参数" prop="parameters">
        <el-input v-model="currentItem.parameters" placeholder="选填" />
      </el-form-item>
      <el-form-item label="规格" prop="specifications">
        <el-input v-model="currentItem.specifications" placeholder="选填" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const whitelist = ref([]);
const loading = ref(true);
const dialogVisible = ref(false);
const isEdit = ref(false);
const currentItem = ref({});
const searchQuery = ref('');
const whitelistFormRef = ref(null); // 【新】为 el-form 添加 ref

const mainCategoryMap = { c2c: '公对公', public: '公共经费' };
const purchaseTypeMap = { consumable: '耗材', chemical: '药品', equipment: '设备', other: '其他' };
const dialogTitle = computed(() => isEdit.value ? '编辑白名单项目' : '新增白名单项目');

const formatMainCategory = (categories) => {
    if (!Array.isArray(categories)) {
        return mainCategoryMap[categories] || categories || '';
    }
    return categories.map(cat => mainCategoryMap[cat] || cat).join(', ');
};

const fetchWhitelist = async () => {
  if (!authStore.accessToken) {
      console.log("No access token, skipping fetchWhitelist.");
      loading.value = false;
      whitelist.value = [];
      return;
  }
  
  loading.value = true;
  whitelist.value = [];

  try {
    const response = await apiClient.get('/procurement/whitelist-items/', {
      params: { search: searchQuery.value }
    });
    whitelist.value = Array.isArray(response.data) ? response.data : response.data.results || [];
  } catch (error) {
      if (error.response?.status !== 401) {
          ElMessage.error('获取白名单列表失败');
          console.error("Error fetching whitelist:", error);
      } else {
          console.log("Initial fetchWhitelist failed with 401, waiting for token refresh...");
      }
      whitelist.value = [];
  }
  finally { loading.value = false; }
};

const handleCreate = () => {
  isEdit.value = false;
  currentItem.value = {
    content: '', platform: '', main_category: [], purchase_type: '',
    manufacturer: '', product_number: '', cas_number: '', parameters: '', specifications: ''
  };
  dialogVisible.value = true;
  // 清除上次的校验结果 (如果存在)
  if (whitelistFormRef.value) {
      whitelistFormRef.value.resetFields();
  }
};

const handleEdit = (item) => {
  isEdit.value = true;
  currentItem.value = { ...item };
  if (typeof currentItem.value.main_category === 'string') {
    currentItem.value.main_category = [currentItem.value.main_category];
  } else if (!Array.isArray(currentItem.value.main_category)) {
      currentItem.value.main_category = [];
  }
  dialogVisible.value = true;
   // 清除上次的校验结果 (如果存在)
  if (whitelistFormRef.value) {
      whitelistFormRef.value.resetFields();
  }
};

const handleSave = async () => {
  // 【修改】使用 Element Plus 的表单验证
  if (!whitelistFormRef.value) return;

  await whitelistFormRef.value.validate(async (valid) => {
      if (valid) {
          // 验证通过，执行 API 调用
          try {
              if (isEdit.value) {
                  await apiClient.put(`/procurement/whitelist-items/${currentItem.value.id}/`, currentItem.value);
                  ElMessage.success('更新成功');
              } else {
                  await apiClient.post('/procurement/whitelist-items/', currentItem.value);
                  ElMessage.success('新增成功');
              }
              dialogVisible.value = false;
              fetchWhitelist(); // Refresh list after save
          } catch (error) {
              const errorMsg = error.response?.data?.detail || error.response?.data?.content?.[0] || '操作失败，请检查输入。';
              ElMessage.error(errorMsg);
          }
      } else {
          // 验证失败，提示用户
          ElMessage.error('请检查表单输入项。');
          return false; // 阻止继续执行
      }
  });
};

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个项目吗？', '警告', { type: 'warning' });
    await apiClient.delete(`/procurement/whitelist-items/${id}/`);
    ElMessage.success('删除成功');
    fetchWhitelist(); // Refresh list after delete
  } catch (error) {
    if (error !== 'cancel') { ElMessage.error('删除失败'); }
  }
};

watch(() => authStore.accessToken, (newToken, oldToken) => {
  console.log("Auth token changed:", { old: !!oldToken, new: !!newToken }); // Debug log
  if (newToken && (!oldToken || whitelist.value.length === 0)) {
    console.log("Access token available, fetching whitelist...");
    fetchWhitelist(); // Fetch data now that token is valid
  } else if (!newToken && oldToken) {
      console.log("Access token removed (logout), clearing whitelist data.");
      whitelist.value = [];
      loading.value = false;
  }
}, { immediate: true });

</script>

<style scoped>
.card-header, .search-bar { display: flex; justify-content: space-between; align-items: center; }
.search-bar { margin-bottom: 20px; }
h1 { margin: 0; font-size: 1.5em; }
</style>