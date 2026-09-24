<template>
  <el-card>
    <template #header>
      <h1>用户注册</h1>
    </template>

    <el-form ref="formRef" :model="formData" label-width="100px">

      <el-form-item label="姓名">
        <el-input v-model="formData.name" placeholder="请输入您的真实姓名"></el-input>
      </el-form-item>

      <el-form-item label="学号/工号">
        <el-input v-model="formData.username" placeholder="将作为您的登录账号"></el-input>
      </el-form-item>

      <el-form-item label="邮箱">
        <el-input v-model="formData.email" placeholder="请输入您的常用邮箱"></el-input>
      </el-form-item>

      <el-form-item label="密码">
        <el-input v-model="formData.password" type="password" show-password placeholder="请输入密码"></el-input>
      </el-form-item>

      <el-form-item label="您的身份">
        <el-radio-group v-model="formData.identity">
          <el-radio-button label="学生" value="学生" />
          <el-radio-button label="导师" value="导师" />
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="formData.identity === '学生'" label="选择导师">
        <el-select v-model="formData.assigned_tutor_id" placeholder="请选择您的导师">
          <el-option
            v-for="tutor in tutorList"
            :key="tutor.id"
            :label="tutor.name"
            :value="tutor.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="submitForm">立即注册</el-button>
        <el-button>重置</el-button>
      </el-form-item>

    </el-form>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
// --- START: 核心修改 ---
// 删除了此文件中 'import axios from "axios"' 和本地的 apiClient 定义
// 导入我们在 src/api/index.js 中配置好的、使用IP地址的全局 apiClient
import apiClient from '@/api';
// --- END: 核心修改 ---

import { ElMessage } from 'element-plus';

// --- 以下是我们之前已经写好的代码 ---
const formData = ref({
  name: '',
  username: '',
  email: '',
  password: '',
  identity: '学生',
  assigned_tutor_id: null,
});

const tutorList = ref([]);
// ------------------------------------


// --- 新增功能 1：获取导师列表 ---
const fetchTutors = async () => {
  try {
    // 现在这个 apiClient 是全局的，它的 baseURL 已经正确地指向了您的IP地址
    const response = await apiClient.get('/users/tutors/');
    tutorList.value = response.data;
  } catch (error) {
    console.error('获取导师列表失败:', error);
    ElMessage.error('获取导师列表失败，请刷新页面重试。');
  }
};

// onMounted 是一个“生命周期钩子”，它会在组件（页面）加载完成后自动执行
// 我们在这里调用 fetchTutors 函数，以确保页面一打开就去获取导师列表
onMounted(() => {
  fetchTutors();
});
// ------------------------------------


// --- 更新功能 2：提交表单数据 ---
const submitForm = async () => {
  try {
    // 这里的 apiClient 同样是全局配置的 apiClient
    const response = await apiClient.post('/users/register/', formData.value);

    ElMessage({
      message: '恭喜，注册成功！',
      type: 'success',
    });

    console.log('注册成功:', response.data);
    // 在这里可以添加重置表单或跳转页面的逻辑

  } catch (error) {
    console.error('注册失败:', error.response ? error.response.data : error.message);

    let errorMessage = '注册失败，请检查您填写的信息。';
    if (error.response && error.response.data) {
        const errors = error.response.data;
        errorMessage = Object.values(errors).flat().join(' ');
    }
    ElMessage.error(errorMessage);
  }
};
// ------------------------------------

</script>

<style scoped>
h1 {
  text-align: center;
  margin: 0;
}
.el-select {
  width: 100%; /* 让下拉选择框占满整行 */
}
</style>