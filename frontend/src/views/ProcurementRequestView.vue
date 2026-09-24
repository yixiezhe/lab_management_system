<template>
  <el-card v-if="canSubmitRequest" class="form-container">
    <template #header>
      <h1>提交采购申请</h1>
    </template>

    <ProcurementForm :key="prefillKey" @submitSuccess="handleCreateSuccess" />

  </el-card>

  <el-card v-else class="form-container forbidden-container">
    <template #header>
      <h1>提交采购申请</h1>
    </template>
    <el-empty :image-size="100">
      <template #description>
        <p class="forbidden-message">请在 8:00 ~ 19:30 填写申请。</p>
      </template>
    </el-empty>
  </el-card>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'; // 导入 Vue hooks
import { useRoute, useRouter } from 'vue-router';
import ProcurementForm from '@/components/ProcurementForm.vue'; // 导入新组件
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const prefillKey = computed(() => String(route.query?.assistant_prefill || 'default'));

// 1. 创建一个响应式变量来存储时间检查结果
const isAllowedTime = ref(false);
const canSubmitRequest = computed(() => authStore.isSystemAdmin || isAllowedTime.value);
let timer = null; // 定时器变量

// 2. 检查时间的函数
const checkTime = () => {
  const now = new Date();
  const currentHour = now.getHours();
  const currentMinutes = now.getMinutes();

  // 8:00 对应的分钟数
  const startTimeInMinutes = 8 * 60; // 480
  // 19:30 对应的分钟数
  const endTimeInMinutes = 19 * 60 + 30; // 1170

  const currentTimeInMinutes = currentHour * 60 + currentMinutes;

  // 判断当前时间是否在范围内
  isAllowedTime.value = currentTimeInMinutes >= startTimeInMinutes && currentTimeInMinutes <= endTimeInMinutes;
};

// 3. 在组件挂载时立即检查，并设置定时器
onMounted(() => {
  checkTime(); // 立即检查一次
  // 设置一个定时器，每30秒检查一次，以动态更新状态
  timer = setInterval(checkTime, 30000);
});

// 4. 在组件卸载时清除定时器，防止内存泄漏
onUnmounted(() => {
  if (timer) {
    clearInterval(timer);
  }
});

const handleCreateSuccess = () => {
  // 当子组件通知我们提交成功后，我们在这里决定做什么
  // 例如，可以跳转到“我的申请”页面
  router.push({ name: 'my-requests' });
};
</script>

<style scoped>
/* 样式可以保留，以维持页面布局一致性 */
.form-container { max-width: 800px; margin: 40px auto; }
h1 { text-align: center; margin: 0; }

/* 为提示信息添加样式 */
.forbidden-container {
  text-align: center;
}
.forbidden-message {
  font-size: 1.1rem;
  color: #909399; /* Element UI 次要文字颜色 */
  margin-top: 10px;
}
</style>
