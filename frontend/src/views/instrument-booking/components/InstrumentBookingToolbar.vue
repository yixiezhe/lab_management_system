<template>
  <div class="header">
    <h2>仪器预约</h2>
    <div class="tools">
      <el-button
        type="info"
        plain
        class="tool-btn"
        @click="goToBookingEntry"
      >
        返回入口
      </el-button>

      <el-button
        type="warning"
        plain
        class="tool-btn"
        @click="toggleBookingEntryEnabled"
      >
        {{ bookingEntryEnabled ? '关闭入口界面' : '开启入口界面' }}
      </el-button>

      <el-select
        v-model="selectedEquipmentId"
        placeholder="选择仪器"
        class="tool-select"
        :loading="loading.equipments"
        filterable
        @change="handleEquipmentChange"
      >
        <el-option
          v-for="eq in equipments"
          :key="eq.id"
          :label="eq.name"
          :value="eq.id"
        />
      </el-select>

      <el-date-picker
        v-if="!isBallMillMode && !isElectrochemicalMode"
        v-model="selectedDate"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择日期"
        class="tool-date-picker tool-spaced"
        :disabled-date="disabledDate"
        @change="fetchCurrentAvailability"
      />

      <el-select
        v-if="isElectrochemicalMode"
        v-model="selectedElectrochemicalChannelNo"
        placeholder="选择通道"
        class="tool-select tool-spaced"
        @change="handleElectrochemicalChannelChange"
      >
        <el-option
          v-for="channel in electrochemicalChannels"
          :key="`electrochemical-channel-${channel.channel_no}`"
          :label="channelOptionLabel(channel)"
          :value="channel.channel_no"
        >
          <div class="electrochemical-channel-option">
            <span class="electrochemical-channel-option-name">{{ channel.name }}</span>
            <el-tag
              v-if="channel.offline"
              size="small"
              type="info"
              effect="plain"
            >
              下线
            </el-tag>
            <el-tag
              v-else-if="channel.current_status_available"
              size="small"
              :type="channel.current_occupied ? 'danger' : 'success'"
              effect="plain"
            >
              {{ channelOptionStatusText(channel) }}
            </el-tag>
          </div>
        </el-option>
      </el-select>

      <el-button
        v-if="isElectrochemicalMode && isSystemAdmin"
        :type="isSelectedElectrochemicalChannelOffline ? 'success' : 'warning'"
        plain
        class="tool-btn tool-spaced"
        :loading="loading.channelToggle"
        :disabled="!selectedElectrochemicalChannelNo"
        @click="toggleElectrochemicalChannelStatus"
      >
        {{ isSelectedElectrochemicalChannelOffline ? '上线当前通道' : '下线当前通道' }}
      </el-button>

      <el-button
        v-if="!isBallMillMode && !isXrdMode"
        type="primary"
        :disabled="selectedSlots.length === 0 || !selectedEquipmentId"
        class="tool-btn tool-spaced"
        @click="bookSelected"
      >
        预约所选时段
      </el-button>

      <el-button
        v-if="isXrdMode && canViewXrdTutorStats"
        type="success"
        plain
        class="tool-btn tool-spaced"
        @click="openXrdTutorStats"
      >
        导师统计
      </el-button>

      <el-button
        type="info"
        plain
        class="tool-btn tool-spaced"
        @click="openHistoryDialog"
      >
        历史预约记录
      </el-button>

      <el-button
        v-if="isBallMillMode && isSystemAdmin"
        type="warning"
        plain
        class="tool-btn tool-spaced"
        @click="setTestClockByPrompt"
      >
        手动系统日期
      </el-button>

      <el-button
        v-if="isBallMillMode && isBallMillQueueMode && isSystemAdmin"
        type="primary"
        plain
        class="tool-btn tool-tight-spaced"
        @click="dispatchQueueNow"
      >
        立即放榜
      </el-button>

      <el-button
        v-if="isBallMillMode && isSystemAdmin"
        type="danger"
        plain
        class="tool-btn tool-tight-spaced"
        :loading="loading.clearingAll"
        @click="clearAllBallMillData"
      >
        一键清空排队和预约
      </el-button>

      <el-button
        v-if="isBallMillMode && testClockEnabled && isSystemAdmin"
        type="danger"
        plain
        class="tool-btn tool-tight-spaced"
        @click="resetTestClock"
      >
        恢复真实日期
      </el-button>

      <div v-if="isBallMillMode && equipmentInfo" class="tool-note tool-note--ball-mill">
        <span class="tool-note-primary">
          近 30 天累计预约 {{ formatDuration(equipmentInfo.myRecent30dUsageMinutes) }}
        </span>
        <span v-if="ballMillRecentUsageAnchorLabel" class="tool-note-secondary">
          统计截止至 {{ ballMillRecentUsageAnchorLabel }}，下次放榜前不变
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useInstrumentBookingController } from '../context'

const {
  selectedEquipmentId,
  loading,
  equipments,
  handleEquipmentChange,
  isBallMillMode,
  selectedDate,
  disabledDate,
  fetchCurrentAvailability,
  isElectrochemicalMode,
  isXrdMode,
  selectedElectrochemicalChannelNo,
  electrochemicalChannels,
  handleElectrochemicalChannelChange,
  isSystemAdmin,
  isSelectedElectrochemicalChannelOffline,
  toggleElectrochemicalChannelStatus,
  selectedSlots,
  bookSelected,
  canViewXrdTutorStats,
  openXrdTutorStats,
  openHistoryDialog,
  setTestClockByPrompt,
  isBallMillQueueMode,
  dispatchQueueNow,
  clearAllBallMillData,
  testClockEnabled,
  resetTestClock,
  equipmentInfo,
  formatDuration,
  ballMillRecentUsageAnchorLabel,
  bookingEntryEnabled,
  goToBookingEntry,
  toggleBookingEntryEnabled,
} = useInstrumentBookingController()

function channelOptionStatusText(channel) {
  if (!channel?.current_status_available) return ''
  if (channel.current_occupied) {
    const endTime = String(channel.current_booking_end_time || '').slice(0, 5) || '--:--'
    return `已预约至 ${endTime}`
  }
  return '当前空闲'
}

function channelOptionLabel(channel) {
  if (!channel) return ''
  if (channel.offline) return `${channel.name}（下线）`
  const statusText = channelOptionStatusText(channel)
  return statusText ? `${channel.name}（${statusText}）` : channel.name
}
</script>
