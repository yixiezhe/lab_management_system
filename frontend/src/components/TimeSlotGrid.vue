<!-- frontend/src/components/TimeSlotGrid.vue -->
<template>
  <div class="grid">
    <div
      v-for="slot in slots"
      :key="slot"
      class="cell"
      :class="{
        selected: isSelected(slot),
        disabled: disabledSet.has(slot),
        occupied: occupiedSet.has(slot)
      }"
      @click="toggle(slot)"
    >
      {{ slotText(slot) }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 所有时间段，例如 ["08:00-09:00", ...]
  slots: { type: Array, default: () => [] },

  // 已被预约的时间段（占用）
  occupied: { type: Array, default: () => [] },

  // v-model 选中的时间段
  modelValue: { type: Array, default: () => [] },

  // 是否允许多选
  multi: { type: Boolean, default: true },

  // ✅ 新增：额外禁用的时间段（例如当天已经过去的时间）
  extraDisabled: { type: Array, default: () => [] },

  // ✅ 新增：占用者信息映射，如 { "09:00-10:00": "张三" }
  // 如果存在，将显示为 “09:00-10:00（张三已预约）”
  occupiedLabels: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'select'])

// 已被预约的 set
const occupiedSet = computed(() => new Set(props.occupied))

// 禁用的 set = 已预约 + 额外禁用
const disabledSet = computed(() => {
  const set = new Set()
  props.occupied.forEach(s => set.add(s))
  props.extraDisabled.forEach(s => set.add(s))
  return set
})

const isSelected = (slot) => props.modelValue.includes(slot)

// 显示文本：带上预约者信息
const slotText = (slot) => {
  const who = props.occupiedLabels[slot]
  if (who) {
    return `${slot}（${who}已预约）`
  }
  if (occupiedSet.value.has(slot)) {
    return `${slot}（已预约）`
  }
  return slot
}

const toggle = (slot) => {
  if (disabledSet.value.has(slot)) return

  const cur = new Set(props.modelValue)
  if (cur.has(slot)) cur.delete(slot)
  else {
    if (!props.multi) cur.clear()
    cur.add(slot)
  }
  const out = Array.from(cur).sort()
  emit('update:modelValue', out)
  emit('select', out)
}
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.cell {
  padding: 10px 8px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  text-align: center;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.cell:hover { background: #eef2f6; }
.cell.selected {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
}
.cell.disabled {
  background: #f2f2f2;
  color: #bbb;
  cursor: not-allowed;
}
.cell.occupied {
  background: #ffecec;
  border-color: #ffbfbf;
  color: #f56c6c;
}
</style>
