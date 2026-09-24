<template>
  <aside class="ball-mill-sidebar-rail electrochemical-sidebar-rail">
    <div class="ball-mill-calendar-shell" v-loading="loading.monthSummary">
      <div class="calendar-shell-caption">预约日历</div>
      <div class="calendar-card-header">
        <div>
          <strong>{{ calendarTitle }}</strong>
          <div class="calendar-card-tip">
            黄色表示当天有预约，白色表示当天无预约，灰色表示过去日期
          </div>
        </div>
        <div class="calendar-card-date">{{ selectedDate }}</div>
      </div>

      <el-calendar
        :key="calendarKey"
        v-model="electrochemicalCalendarValue"
        class="ball-mill-calendar"
        @update:model-value="handleElectrochemicalCalendarChange"
      >
        <template #header>
          <div class="ball-mill-calendar-header">
            <el-button size="small" @click="changeElectrochemicalCalendarMonth(-1)">
              上个月
            </el-button>
            <strong>{{ electrochemicalCalendarPanelMonthText }}</strong>
            <el-button size="small" @click="changeElectrochemicalCalendarMonth(1)">
              下个月
            </el-button>
          </div>
        </template>
        <template #date-cell="{ data }">
          <div class="ball-mill-date-cell" :class="electrochemicalCalendarDayClass(data)">
            <span class="ball-mill-date-number">
              {{ Number(data.day.slice(-2)) }}
            </span>
            <span class="ball-mill-date-mark">
              {{ getElectrochemicalCalendarDayMark(data.day) }}
            </span>
          </div>
        </template>
      </el-calendar>

      <div class="calendar-legend">
        <span class="legend-chip legend-chip--white">无预约</span>
        <span class="legend-chip legend-chip--yellow">已有预约</span>
        <span class="legend-chip legend-chip--gray">过去日期</span>
        <span class="legend-chip legend-chip--blue">当前选中</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useInstrumentBookingController } from '../context'

const {
  loading,
  selectedDate,
  selectedEquipment,
  isXrdMode,
  selectedElectrochemicalChannelNo,
  selectedElectrochemicalChannelText,
  electrochemicalCalendarValue,
  handleElectrochemicalCalendarChange,
  changeElectrochemicalCalendarMonth,
  electrochemicalCalendarPanelMonthText,
  electrochemicalCalendarDayClass,
  getElectrochemicalCalendarDayMark,
} = useInstrumentBookingController()

const calendarTitle = computed(() => (
  isXrdMode.value
    ? `${selectedEquipment.value?.name || 'XRD'}预约日历`
    : `${selectedElectrochemicalChannelText.value}预约日历`
))

const calendarKey = computed(() => (
  isXrdMode.value
    ? `xrd-calendar-${selectedEquipment.value?.id || 'none'}`
    : `electrochemical-calendar-${selectedElectrochemicalChannelNo.value}`
))
</script>
