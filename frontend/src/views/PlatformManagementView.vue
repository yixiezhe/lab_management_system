<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <h1>平台管理</h1>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新增平台</el-button>
      </div>
    </template>

    <el-table :data="platformList" stripe border v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="平台名称" />
      <el-table-column prop="prefix" label="单号前缀" width="120" />
      <el-table-column prop="category" label="所属经费类型">
        <template #default="scope">
          <el-tag :type="scope.row.category === 'c2c' ? 'primary' : 'success'">
            {{ categoryMap[scope.row.category] }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="平台负责人">
        <template #default="scope">
          <div v-if="scope.row.managers_details && scope.row.managers_details.length > 0">
            <el-tag
              v-for="manager in scope.row.managers_details"
              :key="manager.id"
              class="manager-tag"
              size="small"
            >
              {{ manager.name }}
            </el-tag>
          </div>
          <span v-else class="no-manager-text">未指定</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px" :close-on-click-modal="false">
    <el-form ref="formRef" :model="currentItem" :rules="formRules" label-width="120px">
      <el-form-item label="平台名称" prop="name">
        <el-input v-model="currentItem.name" placeholder="请输入平台名称" />
      </el-form-item>
      <el-form-item label="所属经费类型" prop="category">
        <el-select v-model="currentItem.category" placeholder="请选择经费类型" style="width: 100%;">
          <el-option label="公对公" value="c2c" />
          <el-option label="公共经费" value="public" />
        </el-select>
      </el-form-item>
      <el-form-item label="单号前缀" prop="prefix">
        <el-input v-model="currentItem.prefix" placeholder="单个大写英文字母 (选填)" />
      </el-form-item>
      
      <el-form-item v-if="currentItem.category === 'c2c'" label="平台负责人" prop="managers">
        <el-select
          v-model="currentItem.managers"
          multiple
          filterable
          clearable
          placeholder="可选择多个负责人"
          :loading="isUsersLoading"
          style="width: 100%;"
        >
          <el-option
            v-for="user in userList"
            :key="user.id"
            :label="user.name"
            :value="user.id"
          />
        </el-select>
      </el-form-item>
      </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="isSaving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';

// State
const platformList = ref([]);
const loading = ref(true);
const dialogVisible = ref(false);
const isEdit = ref(false);
const isSaving = ref(false);
const currentItem = ref({});
const formRef = ref(null);
// --- MODIFICATION START: Add state for users ---
const userList = ref([]);
const isUsersLoading = ref(false);
// --- MODIFICATION END ---


// Mappings and Titles
const categoryMap = { c2c: '公对公', public: '公共经费' };
const dialogTitle = computed(() => (isEdit.value ? '编辑平台' : '新增平台'));

const validatePrefix = (rule, value, callback) => {
    if (!value) {
        return callback();
    }
    if (!/^[A-Z]$/.test(value)) {
        return callback(new Error('前缀必须是单个大写英文字母'));
    }
    return callback();
};

const formRules = ref({
  name: [{ required: true, message: '平台名称不能为空', trigger: 'blur' }],
  category: [{ required: true, message: '必须选择所属经费类型', trigger: 'change' }],
  prefix: [{ validator: validatePrefix, trigger: 'blur' }],
});

// API Calls
const fetchPlatforms = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/procurement/platforms/');
    platformList.value = response.data;
  } catch (error) {
    ElMessage.error('获取平台列表失败');
  } finally {
    loading.value = false;
  }
};

// --- MODIFICATION START: Add function to fetch users ---
const fetchUsers = async () => {
  isUsersLoading.value = true;
  try {
    const response = await apiClient.get('/users/');
    userList.value = response.data;
  } catch (error) {
    ElMessage.error('获取用户列表失败');
  } finally {
    isUsersLoading.value = false;
  }
};
// --- MODIFICATION END ---


onMounted(() => {
  fetchPlatforms();
  fetchUsers(); // Fetch users on component mount
});

const handleCreate = () => {
  isEdit.value = false;
  // --- MODIFICATION: Initialize managers array ---
  currentItem.value = { name: '', category: '', prefix: '', managers: [] };
  dialogVisible.value = true;
};

const handleEdit = (item) => {
  isEdit.value = true;
  currentItem.value = { ...item };
  // --- MODIFICATION: Extract manager IDs for the select component ---
  if (item.managers_details) {
      currentItem.value.managers = item.managers_details.map(manager => manager.id);
  } else {
      currentItem.value.managers = [];
  }
  dialogVisible.value = true;
};

const handleSave = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      isSaving.value = true;
      try {
        // Prepare payload, remove details field before sending
        const payload = { ...currentItem.value };
        delete payload.managers_details;
        
        if (isEdit.value) {
          await apiClient.put(`/procurement/platforms/${payload.id}/`, payload);
          ElMessage.success('更新成功');
        } else {
          await apiClient.post('/procurement/platforms/', payload);
          ElMessage.success('新增成功');
        }
        dialogVisible.value = false;
        await fetchPlatforms();
      } catch (error) {
        let errorMsg = '操作失败';
        if (error.response && error.response.data) {
          const errors = error.response.data;
          const fieldErrors = Object.entries(errors).map(([field, messages]) => `${field}: ${messages.join(', ')}`);
          if (fieldErrors.length > 0) {
            errorMsg = `保存失败: ${fieldErrors.join('; ')}`;
          }
        }
        ElMessage.error(errorMsg);
      } finally {
        isSaving.value = false;
      }
    }
  });
};

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个平台吗？此操作不可逆。', '警告', { type: 'warning' });
    await apiClient.delete(`/procurement/platforms/${id}/`);
    ElMessage.success('删除成功');
    await fetchPlatforms();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
};
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
h1 {
  margin: 0;
  font-size: 1.5em;
}
.manager-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}
.no-manager-text {
  color: #909399;
}
</style>