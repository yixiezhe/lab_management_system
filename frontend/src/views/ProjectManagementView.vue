<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>项目管理</span>
        <div class="header-buttons">
          <el-button type="success" @click="handlePublishAll" :loading="isPublishing">
            <el-icon style="margin-right: 5px;"><Promotion /></el-icon>
            发布列表到首页
          </el-button>
          <el-button type="warning" @click="handleWithdraw" :loading="isWithdrawing">
            <el-icon style="margin-right: 5px;"><Back /></el-icon>
            撤回发布
          </el-button>
          <el-button type="primary" @click="handleOpenAddDialog">
            <el-icon style="margin-right: 5px;"><Plus /></el-icon>
            新增项目
          </el-button>
        </div>
      </div>
    </template>

    <el-table :data="projects" v-loading="loading" style="width: 100%" border>
      <el-table-column prop="project_number" label="项目号" width="180" />
      <el-table-column prop="name" label="项目名" />
      <el-table-column prop="description" label="项目说明" show-overflow-tooltip />
      <el-table-column prop="author.name" label="创建/修改人" width="120" />
      
      <el-table-column prop="updated_at" label="最后更新" width="180">
         <template #default="scope">
         {{ new Date(scope.row.updated_at).toLocaleDateString('sv-SE') }}
       </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right" align="center">
        <template #default="scope">
          <el-button type="primary" link size="small" @click="handleOpenEditDialog(scope.row)">编辑</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="isEditMode ? '编辑项目' : '新增项目'" width="600px" :close-on-click-modal="false">
    <el-form ref="formRef" :model="currentProject" :rules="formRules" label-width="120px">
      <el-form-item label="项目号" prop="project_number">
        <el-input v-model="currentProject.project_number" placeholder="请输入项目号"></el-input>
      </el-form-item>
      <el-form-item label="项目名" prop="name">
        <el-input v-model="currentProject.name" placeholder="请输入项目名"></el-input>
      </el-form-item>
      <el-form-item label="项目说明" prop="description">
        <el-input
          v-model="currentProject.description"
          type="textarea"
          :rows="4"
          placeholder="请输入项目说明"
        ></el-input>
      </el-form-item>
      
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="isSubmitting">
          保存
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
// 【修改】导入新图标
import { Plus, Promotion, Back } from '@element-plus/icons-vue';

// State
const projects = ref([]);
const loading = ref(true);
const isSubmitting = ref(false);
const isPublishing = ref(false); 
const isWithdrawing = ref(false); // 【新】撤回按钮的 loading 状态

const dialogVisible = ref(false);
const isEditMode = ref(false);
const formRef = ref(null);
const currentProject = ref({});

const formRules = reactive({
  project_number: [{ required: true, message: '项目号不能为空', trigger: 'blur' }],
  name: [{ required: true, message: '项目名不能为空', trigger: 'blur' }],
});

// --- API Functions ---
const fetchProjects = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/projects/projects/');
    projects.value = response.data;
  } catch (error) {
    ElMessage.error('获取项目列表失败。');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchProjects);

// --- Dialog and Form Functions ---
const resetCurrentProject = () => {
  currentProject.value = {
    project_number: '',
    name: '',
    description: '',
  };
};

const handleOpenAddDialog = () => {
  resetCurrentProject();
  isEditMode.value = false;
  dialogVisible.value = true;
};

const handleOpenEditDialog = (project) => {
  currentProject.value = { ...project }; // Create a copy to avoid reactive changes to the table
  isEditMode.value = true;
  dialogVisible.value = true;
};

const handleSubmit = async () => {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      
      const payload = {
        project_number: currentProject.value.project_number,
        name: currentProject.value.name,
        description: currentProject.value.description,
      };

      try {
        if (isEditMode.value) {
          await apiClient.patch(`/projects/projects/${currentProject.value.id}/`, payload);
          ElMessage.success('项目更新成功！');
        } else {
          await apiClient.post('/projects/projects/', payload);
          ElMessage.success('项目创建成功！');
        }
        dialogVisible.value = false;
        await fetchProjects(); // Refresh table data
      } catch (error) {
        const errorMsg = error.response?.data?.project_number?.[0] || '操作失败，请重试。';
        ElMessage.error(errorMsg);
      } finally {
        isSubmitting.value = false;
      }
    } else {
      ElMessage.error('请检查表单输入项。');
    }
  });
};

const handleDelete = async (projectId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个项目吗？此操作不可撤销。',
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    await apiClient.delete(`/projects/projects/${projectId}/`);
    ElMessage.success('项目删除成功！');
    await fetchProjects(); // Refresh table data

  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请重试。');
    }
  }
};

// 处理“发布列表到首页”的函数
const handlePublishAll = async () => {
  isPublishing.value = true;
  try {
    await apiClient.post('/projects/projects/publish-list-to-homepage/');
    ElMessage.success('已成功将项目列表同步到首页！');
  } catch (error) {
    if (error.response && error.response.status === 404) {
        ElMessage.error('发布失败：API 路径未找到(404)。请检查后端路由。');
    } else {
        ElMessage.error('发布失败，请联系管理员。');
    }
    console.error("发布失败:", error);
  } finally {
    isPublishing.value = false;
  }
};

// 【新】处理“撤回发布”的函数
const handleWithdraw = async () => {
  isWithdrawing.value = true;
  try {
    // 假设一个新 API，用于触发后端将首页公告设为 "未发布"
    await apiClient.post('/projects/projects/withdraw-homepage-publication/');
    ElMessage.success('已成功从首页撤回项目列表！');
  } catch (error) {
     if (error.response && error.response.status === 404) {
        ElMessage.error('撤回失败：API 路径未找到(404)。');
    } else {
        ElMessage.error('撤回失败，请联系管理员。');
    }
    console.error("撤回失败:", error);
  } finally {
    isWithdrawing.value = false;
  }
};
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
/* 【新】确保按钮组正确排列 */
.header-buttons {
  display: flex;
  gap: 10px; /* 按钮间距 */
}
</style>