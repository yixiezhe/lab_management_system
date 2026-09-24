<template>
  <div class="instrument-entry-page">
    <div class="instrument-entry-shell">
      <div class="instrument-entry-header">
        <div>
          <h2>仪器预约</h2>
          <p>选择仪器进入预约界面</p>
        </div>
      </div>

      <div class="instrument-entry-grid" v-loading="loading">
        <button
          v-if="showEasterEgg"
          type="button"
          class="instrument-entry-button instrument-entry-button--egg"
          disabled
        >
          <span class="instrument-entry-image-wrap">
            <img
              v-if="eggImageSrc"
              :src="eggImageSrc"
              alt="彩蛋"
              class="instrument-entry-image"
              loading="lazy"
              decoding="async"
              fetchpriority="low"
              @error="markImageMissing('彩蛋')"
            >
            <span v-else class="instrument-entry-placeholder">彩</span>
          </span>
          <span class="instrument-entry-name">彩蛋</span>
        </button>

        <button
          v-for="(equipment, index) in equipmentRows"
          :key="equipment.id"
          type="button"
          class="instrument-entry-button"
          @click="openEquipment(equipment)"
        >
          <span class="instrument-entry-image-wrap">
            <img
              v-if="getEquipmentImage(equipment.name)"
              :src="getEquipmentImage(equipment.name)"
              :alt="equipment.name"
              class="instrument-entry-image"
              :loading="index < 5 ? 'eager' : 'lazy'"
              decoding="async"
              :fetchpriority="index === 0 ? 'high' : 'low'"
              @error="markImageMissing(equipment.name)"
            >
            <span v-else class="instrument-entry-placeholder">
              {{ getPlaceholderText(equipment.name) }}
            </span>
          </span>
          <span class="instrument-entry-name">{{ equipment.name }}</span>
          <span class="instrument-entry-mode">{{ getBookingModeLabel(equipment) }}</span>
        </button>
      </div>

      <el-empty
        v-if="!loading && !equipmentRows.length"
        description="暂无可预约仪器"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listEquipments } from '@/api/equipment'
import { useAuthStore } from '@/stores/auth'
import { isInstrumentBookingEntryEnabled } from './instrument-booking/entryPreference'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const imageModules = import.meta.glob('./instrument-booking/thumbnails/*.webp', {
  eager: true,
  import: 'default',
  query: '?url',
})

const imageMap = Object.fromEntries(
  Object.entries(imageModules).map(([path, url]) => {
    const fileName = path.split('/').pop() || ''
    return [fileName.replace(/\.webp$/i, ''), url]
  }),
)

const loading = ref(false)
const equipments = ref([])
const missingImages = ref({})
const now = ref(new Date())
let clockTimer = null

const equipmentRows = computed(() =>
  equipments.value.filter((item) => item?.is_active !== false),
)

const showEasterEgg = computed(() => {
  const current = now.value
  return current.getHours() === 0 && current.getMinutes() === 0
})

const eggImageSrc = computed(() => getEquipmentImage('彩蛋'))

function getDefaultEquipment(rows = equipmentRows.value) {
  return rows.find((item) => item?.booking_mode === 'planetary_ball_mill') || rows[0] || null
}

function getEquipmentImage(name) {
  const key = String(name || '').trim()
  if (!key || missingImages.value[key]) return ''
  return imageMap[key] || ''
}

function markImageMissing(name) {
  const key = String(name || '').trim()
  if (!key) return
  missingImages.value = { ...missingImages.value, [key]: true }
}

function getPlaceholderText(name) {
  const text = String(name || '').trim()
  return text ? text.slice(0, 1) : '仪'
}

function getBookingModeLabel(equipment) {
  if (equipment?.booking_mode === 'planetary_ball_mill') return '行星球磨机'
  if (equipment?.booking_mode === 'electrochemical_workstation') return '输力强电化学工作站'
  return '普通仪器'
}

function openEquipment(equipment) {
  if (!equipment?.id) return
  router.push({
    name: 'instruments-book',
    query: { equipment_id: equipment.id },
  })
}

async function loadEquipments() {
  loading.value = true
  try {
    if (!authStore.user && authStore.accessToken) {
      await authStore.fetchUser()
    }

    const { data } = await listEquipments({ is_active: true })
    equipments.value = Array.isArray(data) ? data : []

    if (route.query?.force !== '1' && !isInstrumentBookingEntryEnabled(authStore.user)) {
      const defaultEquipment = getDefaultEquipment()
      if (defaultEquipment) {
        openEquipment(defaultEquipment)
      }
    }
  } catch (error) {
    equipments.value = []
    ElMessage.error('获取仪器列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
  loadEquipments()
})

onUnmounted(() => {
  if (clockTimer) {
    window.clearInterval(clockTimer)
    clockTimer = null
  }
})
</script>

<style scoped>
.instrument-entry-page {
  min-height: calc(100vh - 120px);
  padding: 24px;
  background: #f5f5f5;
}

.instrument-entry-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.instrument-entry-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 18px;
}

.instrument-entry-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.instrument-entry-header p {
  margin: 6px 0 0;
  color: #606266;
}

.instrument-entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.instrument-entry-button {
  display: grid;
  grid-template-rows: 136px auto auto;
  gap: 8px;
  width: 100%;
  min-height: 218px;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  color: #303133;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.instrument-entry-button:hover,
.instrument-entry-button:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 8px 22px rgba(31, 45, 61, 0.12);
  transform: translateY(-1px);
  outline: none;
}

.instrument-entry-button:disabled {
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
  opacity: 0.78;
}

.instrument-entry-button--egg {
  border-style: dashed;
}

.instrument-entry-image-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 6px;
  background: #f3f5f8;
}

.instrument-entry-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.instrument-entry-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: #dfe6ef;
  color: #606266;
  font-size: 32px;
  font-weight: 600;
}

.instrument-entry-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 16px;
  font-weight: 600;
}

.instrument-entry-mode {
  color: #909399;
  font-size: 13px;
}

@media (max-width: 768px) {
  .instrument-entry-page {
    padding: 15px;
  }

  .instrument-entry-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }

  .instrument-entry-button {
    grid-template-rows: 112px auto auto;
    min-height: 190px;
  }
}
</style>
