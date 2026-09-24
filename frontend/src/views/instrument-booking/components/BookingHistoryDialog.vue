<template>
  <el-dialog
    v-model="historyVisible"
    title="历史预约记录"
    width="92vw"
    class="history-dialog"
  >
    <div class="history-toolbar">
      <el-date-picker
        v-model="historyDateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        class="history-date-range"
        @change="fetchHistoryBookings"
      />
      <div class="history-toolbar-right">
        <el-button size="small" @click="clearHistoryFilter">清空筛选</el-button>
        <el-button size="small" type="primary" @click="fetchHistoryBookings">刷新</el-button>
      </div>
    </div>

    <el-table :data="historyBookings" v-loading="loading.history" size="small" height="420">
      <el-table-column prop="equipment_name" label="仪器" min-width="180" />
      <el-table-column label="日期" min-width="190">
        <template #default="{ row }">
          {{ formatBookingDate(row) }}
        </template>
      </el-table-column>
      <el-table-column label="时间" min-width="180">
        <template #default="{ row }">
          {{ formatBookingTime(row) }}
        </template>
      </el-table-column>
      <el-table-column label="详情" min-width="240">
        <template #default="{ row }">
          {{ formatBookingDetails(row) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" min-width="100">
        <template #default>
          <el-tag type="info">已完成</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup>
import { useInstrumentBookingController } from '../context'

const {
  historyVisible,
  historyDateRange,
  fetchHistoryBookings,
  clearHistoryFilter,
  historyBookings,
  loading,
  formatBookingDate,
  formatBookingTime,
  formatBookingDetails,
} = useInstrumentBookingController()
</script>
