<template>
  <el-card>
    <template #header>
      <h1>用户登录</h1>
    </template>

    <el-form ref="formRef" :model="loginData" label-width="100px" @submit.prevent="handleLogin">
      <el-form-item label="学号/工号">
        <el-input v-model="loginData.username" placeholder="请输入您的学号/工号"></el-input>
      </el-form-item>

      <el-form-item label="密码">
        <el-input v-model="loginData.password" type="password" show-password placeholder="请输入密码"></el-input>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleLogin" :loading="isLoading">登 录</el-button>
      </el-form-item>

      <el-form-item label-width="0">
        <div class="link-container">
          <router-link to="/register">还没有账号？立即注册</router-link>
          <el-link type="warning" @click="openResetDialog" style="margin-left: 20px;">忘记密码？申请重置</el-link>
          </div>
      </el-form-item>
    </el-form>
  </el-card>

  <el-dialog v-model="resetDialogVisible" title="申请重置密码" width="450px" :close-on-click-modal="false">
    <el-form ref="resetFormRef" :model="resetData" :rules="resetRules" label-width="100px">
      <el-form-item label="学号/工号" prop="username">
        <el-input v-model="resetData.username" placeholder="请输入您要重置密码的学号/工号"></el-input>
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="resetData.new_password" type="password" show-password placeholder="请输入您想设置的新密码"></el-input>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitResetRequest" :loading="isSubmitting">
          提交申请
        </el-button>
      </div>
    </template>
  </el-dialog>
  </template>

<script setup>
import { ref, reactive } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';

const loginData = ref({
  username: '',
  password: '',
});

// 【修改点】增加 loading 状态 ref
const isLoading = ref(false);

const authStore = useAuthStore();
const router = useRouter();

// 【修改点】重写 handleLogin 函数
const handleLogin = async () => {
  // 增加基础验证
  if (!loginData.value.username || !loginData.value.password) {
    ElMessage.error('请输入学号/工号和密码。');
    return;
  }
  
  isLoading.value = true;
  try {
    const success = await authStore.login(loginData.value.username, loginData.value.password);
    if (success) {
      router.push('/');
    } else {
      // 登录失败，清空密码框
      loginData.value.password = '';
    }
  } catch (e) {
      // 以防万一 store 的 login 方法抛出异常
      loginData.value.password = '';
  } finally {
    isLoading.value = false;
  }
};

// --- Logic for Password Reset ---
const resetDialogVisible = ref(false);
const isSubmitting = ref(false);
const resetFormRef = ref(null);
const resetData = ref({
  username: '',
  new_password: '',
});

const resetRules = reactive({
  username: [{ required: true, message: '请输入学号/工号', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
  ]
});

const openResetDialog = () => {
  resetData.value.username = loginData.value.username;
  resetData.value.new_password = '';
  resetDialogVisible.value = true;
};

const submitResetRequest = async () => {
  if (!resetFormRef.value) return;

  await resetFormRef.value.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      try {
        const response = await apiClient.post('/users/request-password-reset/', {
          username: resetData.value.username,
          new_password: resetData.value.new_password,
        });
        ElMessage.success(response.data.message || '申请已成功提交！');
        resetDialogVisible.value = false;
      } catch (error) {
        const errorMsg = error.response?.data?.error || '提交失败，请检查输入或联系管理员。';
        ElMessage.error(errorMsg);
      } finally {
        isSubmitting.value = false;
      }
    } else {
      ElMessage.error('请检查输入项是否符合要求。');
    }
  });
};
</script>

<style scoped>
h1 {
  text-align: center;
  margin: 0;
}
.link-container {
  width: 100%;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>