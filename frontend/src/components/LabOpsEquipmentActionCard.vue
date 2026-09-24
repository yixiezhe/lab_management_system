<template>
  <section class="action-card">
    <header>
      <span class="action-icon"><el-icon><Calendar /></el-icon></span>
      <div>
        <strong>{{ action.title || '预填仪器预约' }}</strong>
        <small>系统已检查当前可预约状态</small>
      </div>
      <el-tag type="warning" size="small" effect="light">待提交</el-tag>
    </header>

    <div v-if="preview" class="summary-grid">
      <span>仪器</span><strong>{{ preview.equipment_name }}</strong>
      <template v-if="preview.position_no">
        <span>通道</span><strong>通道 {{ preview.position_no }}</strong>
      </template>
      <span>日期</span><strong>{{ preview.target_date }}</strong>
      <span>时段</span><strong>{{ preview.start_time }}–{{ preview.end_time }}</strong>
      <span>时长</span><strong>{{ durationText }}</strong>
    </div>

    <footer>
      <span>只预填页面，不会自动提交预约</span>
      <el-button type="primary" size="small" @click="$emit('open')">
        {{ action.confirm_label || '打开预约页并预填' }}
      </el-button>
    </footer>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { Calendar } from '@element-plus/icons-vue'

const props = defineProps({
  action: { type: Object, required: true },
})

defineEmits(['open'])

const preview = computed(() => props.action.preview || null)
const durationText = computed(() => {
  const minutes = Number(preview.value?.duration_minutes || 0)
  if (minutes >= 60 && minutes % 60 === 0) return `${minutes / 60} 小时`
  return `${minutes} 分钟`
})
</script>

<style scoped>
.action-card { margin-top: 10px; overflow: hidden; border: 1px solid #b3d8ff; border-radius: 12px; background: #fff; box-shadow: 0 4px 14px rgba(51, 126, 204, .08); }
header { display: flex; align-items: center; gap: 9px; padding: 11px 12px; border-bottom: 1px solid #d9ecff; background: #ecf5ff; }
header > div { flex: 1; min-width: 0; }
header strong, header small { display: block; }
header strong { color: #303133; font-size: 13px; }
header small { margin-top: 2px; color: #909399; font-size: 10px; }
.action-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; color: #337ecc; background: #d9ecff; }
.summary-grid { display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: 7px 10px; padding: 11px 12px; font-size: 12px; }
.summary-grid span { color: #909399; }
.summary-grid strong { overflow-wrap: anywhere; color: #303133; }
footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px 12px; border-top: 1px solid #ebeef5; }
footer span { color: #909399; font-size: 10px; line-height: 1.4; }
</style>
