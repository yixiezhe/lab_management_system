<template>
  <el-card class="form-container">
    <template #header>
      <h1>提交小组请购申请</h1>
    </template>
    
    <TeamProcurementForm @submitSuccess="handleCreateSuccess" />
    
  </el-card>
</template>

<script setup>
import { useRouter } from 'vue-router';
import TeamProcurementForm from '@/components/TeamProcurementForm.vue';

const router = useRouter();

const handleCreateSuccess = () => {
  router.push({ name: 'my-team-requests' });
};
</script>

<style scoped>
.form-container { max-width: 1000px; margin: 40px auto; }
h1 { text-align: center; margin: 0; }
</style>