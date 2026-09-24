<template>
  <aside class="ball-mill-sidebar-rail">
    <div class="ball-mill-calendar-shell" v-loading="loading.monthSummary">
      <div class="calendar-shell-caption">预约日历</div>
      <div class="calendar-card-header">
        <div>
          <strong>按天查看预约情况</strong>
          <div class="calendar-card-tip">
            黄色表示当天有预约，白色表示当天无预约，灰色表示过去日期
          </div>
        </div>
        <div class="calendar-card-date">{{ selectedDate }}</div>
      </div>

      <el-calendar
        v-model="ballMillCalendarValue"
        class="ball-mill-calendar"
        @update:model-value="handleBallMillCalendarChange"
      >
        <template #header>
          <div class="ball-mill-calendar-header">
            <el-button size="small" @click="changeBallMillCalendarMonth(-1)">
              上个月
            </el-button>
            <strong>{{ ballMillCalendarPanelMonthText }}</strong>
            <el-button size="small" @click="changeBallMillCalendarMonth(1)">
              下个月
            </el-button>
          </div>
        </template>
        <template #date-cell="{ data }">
          <div class="ball-mill-date-cell" :class="calendarDayClass(data)">
            <span class="ball-mill-date-number">
              {{ Number(data.day.slice(-2)) }}
            </span>
            <span class="ball-mill-date-mark">
              {{ getCalendarDayMark(data.day) }}
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
import { useInstrumentBookingController } from '../context'

const {
  loading,
  selectedDate,
  ballMillCalendarValue,
  handleBallMillCalendarChange,
  changeBallMillCalendarMonth,
  ballMillCalendarPanelMonthText,
  calendarDayClass,
  getCalendarDayMark,
} = useInstrumentBookingController()
</script>
