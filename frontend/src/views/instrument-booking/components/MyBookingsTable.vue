<template>
  <div class="my-bookings-panel">
    <h3 style="margin-bottom: 10px">{{ titleText }}</h3>
    <el-table
      :data="tableRows"
      v-loading="loading.myBookings"
      size="small"
      empty-text="暂无可取消的预约"
    >
      <el-table-column prop="equipment_name" label="仪器" min-width="150" />
      <el-table-column label="操作" min-width="180">
        <template #default="{ row }">
          <div class="booking-admin-actions">
            <el-button
              v-if="row.booking_mode === 'electrochemical_workstation'"
              link
              type="warning"
              :disabled="!canEndBookingEarly(row)"
              @click="endBookingEarly(row)"
            >
              提前结束
            </el-button>
            <el-popconfirm :title="getCancelBookingConfirmText(row)" @confirm="cancelBooking(row)">
              <template #reference>
                <el-button link type="danger" :disabled="!canCancelBooking(row)">取消</el-button>
              </template>
            </el-popconfirm>
            <el-popconfirm
              v-if="isSystemAdmin"
              title="确定彻底删除该预约吗？删除后不可恢复。"
              @confirm="forceDeleteBooking(row)"
            >
              <template #reference>
                <el-button link type="danger" :disabled="!canModifyBooking(row)">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="日期" min-width="160">
        <template #default="{ row }">
          {{ formatBookingDate(row) }}
        </template>
      </el-table-column>
      <el-table-column label="时间" min-width="150">
        <template #default="{ row }">
          {{ formatBookingTime(row) }}
        </template>
      </el-table-column>
      <el-table-column label="详情" min-width="220">
        <template #default="{ row }">
          {{ formatBookingDetails(row) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" min-width="100">
        <template #default="{ row }">
          <el-tag :type="getBookingStatusType(row)">
            {{ getBookingStatusLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useInstrumentBookingController } from '../context'

const props = defineProps({
  currentElectrochemicalChannelOnly: {
    type: Boolean,
    default: false,
  },
})

const {
  myBookingsDisplay,
  currentElectrochemicalChannelBookingsDisplay,
  loading,
  getCancelBookingConfirmText,
  canModifyBooking,
  canCancelBooking,
  canEndBookingEarly,
  cancelBooking,
  endBookingEarly,
  isSystemAdmin,
  forceDeleteBooking,
  formatBookingDate,
  formatBookingTime,
  formatBookingDetails,
  getBookingStatusType,
  getBookingStatusLabel,
} = useInstrumentBookingController()

const tableRows = computed(() => (
  props.currentElectrochemicalChannelOnly
    ? currentElectrochemicalChannelBookingsDisplay.value
    : myBookingsDisplay.value
))

const titleText = computed(() => (
  props.currentElectrochemicalChannelOnly ? '当前通道我的预约' : '我的预约'
))
</script>
