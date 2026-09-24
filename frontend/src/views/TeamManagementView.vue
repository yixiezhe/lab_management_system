<template>
  <el-card>
    <template #header>
      <h1>小组成员管理</h1>
    </template>

    <el-table :data="students" stripe v-loading="loading">
      <el-table-column prop="username" label="学号/工号" width="180" />
      <el-table-column prop="name" label="姓名" width="180" />
      <el-table-column label="角色">
        <template #default="scope">
          <el-tag v-if="isTeamProcurementOfficer(scope.row)" type="success">
            小组采购人员
          </el-tag>
          <el-tag v-else type="info">
            普通成员
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250">
        <template #default="scope">
          <el-button
            v-if="!isTeamProcurementOfficer(scope.row)"
            type="primary"
            size="small"
            @click="manageRole(scope.row, 'assign')"
            :loading="scope.row.loading"
          >
            设为小组采购人员
          </el-button>
          <el-button
            v-else
            type="danger"
            size="small"
            @click="manageRole(scope.row, 'remove')"
            :loading="scope.row.loading"
          >
            移除采购员资格
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';

const students = ref([]);
const loading = ref(false);

// 检查学生是否具有“小组采购人员”角色
const isTeamProcurementOfficer = (student) => {
  return student.roles.some(role => role.name === '小组采购人员');
};

// 获取导师名下的学生列表
const fetchStudents = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/users/my-students/');
    // 为每个学生对象添加一个loading状态，用于控制按钮的加载动画
    students.value = response.data.map(s => ({ ...s, loading: false }));
  } catch (error) {
    console.error('获取学生列表失败:', error);
    ElMessage.error('获取学生列表失败，请稍后重试。');
  } finally {
    loading.value = false;
  }
};

// 管理学生角色的核心方法
const manageRole = async (student, action) => {
  student.loading = true; // 开始加载动画
  try {
    const url = `/users/my-students/${student.id}/manage-role/`;
    let response;
    if (action === 'assign') {
      response = await apiClient.post(url);
    } else {
      response = await apiClient.delete(url);
    }
    ElMessage.success(response.data.message);
    // 操作成功后，刷新列表以获取最新的角色状态
    await fetchStudents();
  } catch (error) {
    console.error('角色操作失败:', error.response?.data);
    const errorMsg = error.response?.data?.error || '操作失败，请稍后重试。';
    ElMessage.error(errorMsg);
  } finally {
    // 无论成功或失败，都停止按钮的加载动画
    // 注意：因为fetchStudents会重新生成列表，所以需要找到新列表中的对应学生来停止loading，
    // 但为了简单起见，直接在fetchStudents内部将loading状态重置为false即可。
    // 如果不重新fetch, 则可以 student.loading = false;
  }
};

onMounted(fetchStudents);
</script>

<style scoped>
h1 {
  text-align: center;
  margin: 0;
}
</style>