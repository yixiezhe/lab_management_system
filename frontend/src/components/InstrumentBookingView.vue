<!-- frontend/src/views/InstrumentBookingView.vue -->
<template>
  <el-card class="page">
    <template #header><h2>仪器预约</h2></template>

    <div class="toolbar">
      <el-select v-model="selectedId" placeholder="选择仪器" filterable style="width: 260px" @change="handleInstrumentChange">
        <el-option v-for="it in equipments" :key="it.id" :label="it.name" :value="it.id" />
      </el-select>

      <el-date-picker
        v-model="theDate"
        type="date"
        :disabled="!selected"
        :disabled-date="disableDate"
        placeholder="选择日期"
        style="margin-left: 12px"
        @change="loadAvailable"
      />

      <el-button
        type="primary"
        :disabled="selectedSlots.length === 0 || !selected || !theDate"
        style="margin-left: auto"
        @click="submitBookings"
      >
        预约所选时段
      </el-button>
    </div>

    <el-empty v-if="!selected" description="请选择仪器" />

    <template v-else>
      <el-alert
        type="info"
        :closable="false"
        class="hint"
        :title="`开放时间：${selected.open_time?.slice(0,5)} - ${selected.close_time?.slice(0,5)}；时间粒度：${selected.time_slot_minutes} 分钟；可提前预约：${selected.advance_days} 天`"
      />

      <div class="grid-wrap" v-loading="loadingSlots">
        <TimeSlotGrid
          v-if="slots.length"
          v-model="selectedSlots"
          :slots="slots"
          :occupied="occupied"
          :multi="true"
          @select="onSelectSlots"
        />
        <el-empty v-else description="该日期无可预约时段" />
      </div>

      <el-divider>我的预约</el-divider>
      <el-table :data="myBookings" size="small" v-loading="loadingMine">
        <el-table-column prop="equipment_name" label="仪器" width="160" />
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column label="时间" width="140">
          <template #default="{ row }">
            {{ row.start_time?.slice(0,5) }} - {{ row.end_time?.slice(0,5) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="danger" :disabled="row.status !== 'booked'" @click="cancel(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import TimeSlotGrid from '@/components/TimeSlotGrid.vue'
import {
  listEquipments, getEquipment, getAvailableSlots,
  bookOneSlot, listBookings, cancelBooking
} from '@/api/equipment'

const equipments = ref([])
const selectedId = ref(null)
const selected = ref(null)         // 选中的仪器详情
const theDate = ref(null)          // Date 对象

const slots = ref([])              // 全部时段（字符串）
const occupied = ref([])           // 已占用
const selectedSlots = ref([])      // 勾选的时段
const loadingSlots = ref(false)

const myBookings = ref([])
const loadingMine = ref(false)

onMounted(async () => {
  const { data } = await listEquipments({ is_active: true })
  equipments.value = data
  loadMine()
})

const disableDate = (d) => {
  if (!selected.value) return true
  const today = new Date(); today.setHours(0,0,0,0)
  const max = new Date(today); max.setDate(max.getDate() + (selected.value.advance_days ?? 7))
  return d < today || d > max
}

const handleInstrumentChange = async (id) => {
  selectedSlots.value = []
  slots.value = []
  occupied.value = []
  theDate.value = null
  const { data } = await getEquipment(id)
  selected.value = data
}

const loadAvailable = async () => {
  if (!selected.value || !theDate.value) return
  loadingSlots.value = true
  try {
    const ds = theDate.value.toISOString().slice(0,10)
    const { data } = await getAvailableSlots(selected.value.id, ds)
    // 后端返回 free 槽位数组（字符串），我们需要把“已占用”的做个差集
    slots.value = data.slots || []
    // 简单起见：occupied = all - free
    const allSet = new Set(buildAllSlots(selected.value.open_time, selected.value.close_time, selected.value.time_slot_minutes))
    const freeSet = new Set(slots.value)
    occupied.value = Array.from(allSet).filter(s => !freeSet.has(s))
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '加载可用时段失败')
  } finally {
    loadingSlots.value = false
  }
}

const onSelectSlots = (arr) => {
  selectedSlots.value = arr
}

const submitBookings = async () => {
  if (!selected.value || !theDate.value || selectedSlots.value.length === 0) return
  const ds = theDate.value.toISOString().slice(0,10)

  // 如果多选，逐个提交（后端是按粒度一格一格预约的）
  try {
    for (const s of selectedSlots.value) {
      const start = s.split('-')[0]
      await bookOneSlot(selected.value.id, { date: ds, start_time: start })
    }
    ElMessage.success('预约成功')
    selectedSlots.value = []
    await Promise.all([loadAvailable(), loadMine()])
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.response?.data?.error || '部分预约失败')
  }
}

const loadMine = async () => {
  loadingMine.value = true
  try {
    const { data } = await listBookings()
    myBookings.value = data || []
  } finally {
    loadingMine.value = false
  }
}

const cancel = async (row) => {
  await ElMessageBox.confirm(`取消 ${row.equipment_name} ${row.date} ${row.start_time?.slice(0,5)}-${row.end_time?.slice(0,5)} 的预约？`, '提示', { type: 'warning' })
  await cancelBooking(row.id)
  ElMessage.success('已取消')
  await Promise.all([loadAvailable(), loadMine()])
}

/** 把开放时间按粒度拆分 */
function buildAllSlots(open, close, slotMin) {
  if (!open || !close) return []
  const pad = (n) => String(n).padStart(2,'0')
  const [oh, om] = open.split(':').map(Number)
  const [ch, cm] = close.split(':').map(Number)
  const base = new Date()
  const start = new Date(base.getFullYear(), base.getMonth(), base.getDate(), oh, om, 0, 0)
  const end   = new Date(base.getFullYear(), base.getMonth(), base.getDate(), ch, cm, 0, 0)
  const out = []
  for (let t = new Date(start); t.getTime() + slotMin*60000 <= end.getTime(); t = new Date(t.getTime() + slotMin*60000)) {
    const e = new Date(t.getTime() + slotMin*60000)
    out.push(`${pad(t.getHours())}:${pad(t.getMinutes())}-${pad(e.getHours())}:${pad(e.getMinutes())}`)
  }
  return out
}
</script>

<style scoped>
.page { max-width: 980px; margin: 20px auto; }
.toolbar { display: flex; align-items: center; gap: 12px; }
.hint { margin: 14px 0; }
.grid-wrap { margin-top: 8px; }
</style>
