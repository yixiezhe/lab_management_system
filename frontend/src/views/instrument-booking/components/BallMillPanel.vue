<template>
  <div class="ball-mill-panel">
    <div class="ball-mill-form">
      <el-form
        :model="ballMillForm"
        label-width="120px"
        inline
        @submit.prevent
        @keydown.enter.prevent
      >
        <el-form-item label="球磨时间(分钟)">
          <el-input-number
            v-model="ballMillForm.milling_minutes"
            class="ball-mill-param-control"
            :min="1"
            :step="1"
            :max="Math.max(ballMillEffectiveMaxMillingMinutes, 1)"
          />
        </el-form-item>

        <el-form-item label="真实预约时间(分钟)">
          <el-input-number
            class="ball-mill-param-control"
            :model-value="ballMillActualDurationMinutes"
            :min="0"
            :step="1"
            disabled
          />
        </el-form-item>

        <el-form-item label="转速(r/min)">
          <el-input-number
            v-model="ballMillForm.rotation_speed_rpm"
            class="ball-mill-param-control"
            :min="ballMillRotationSpeedMin"
            :max="ballMillRotationSpeedInputMax"
            :step="10"
          />
        </el-form-item>

        <el-form-item v-if="isBallMillQueueMode" label="排队需求工位数">
          <el-input-number
            v-model="ballMillForm.queue_position_count"
            class="ball-mill-param-control"
            :min="1"
            :max="4"
            :step="1"
          />
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="ballMillForm.remark"
            class="ball-mill-param-control"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
    </div>

    <div v-if="selectedBallMillStartTime" class="ball-mill-selection-bar">
      <span>预计结束时间：{{ estimatedBallMillEndText }}</span>
      <span v-if="selectedBallMillPositionNos.length">
        已选工位：{{ selectedBallMillPositionText }}
      </span>
      <span v-if="selectedBallMillLimitHint">
        {{ selectedBallMillLimitHint }}
      </span>
      <el-button
        type="primary"
        class="ball-mill-top-book-btn"
        :disabled="!canBookSelectedBallMillWindow"
        :loading="loading.booking && Boolean(selectedBallMillStartTime)"
        @click="bookBallMill(selectedBallMillStartTime)"
      >
        {{ topDirectBookingButtonText }}
      </el-button>
    </div>

    <div v-if="isBallMillQueueMode && isSelectedDateInQueueApplyRange" class="ball-mill-queue-apply-bar">
      <span>当前排队：{{ selectedDateQueuePendingCount }} 人</span>
      <el-button
        type="warning"
        :disabled="!canSubmitBallMillQueueForDate"
        :loading="loading.booking"
        @click="submitBallMillQueueForDate"
      >
        {{
          canSubmitBallMillQueueForDate
            ? `提交总排队申请（${ballMillForm.queue_position_count} 个工位）`
            : queueSubmitDisabledText
        }}
      </el-button>
    </div>

    <el-empty
      v-if="!ballMillHourWindows.length"
      description="请先填写球磨时间，系统会按 24 小时整点展示每个工位的预约情况"
    />

    <div v-else class="hour-window-grid">
      <div
        v-for="window in ballMillHourWindows"
        :key="window.start"
        class="hour-window-card"
        :class="hourWindowClass(window)"
      >
        <div class="hour-window-header">
          <strong>{{ window.hour_label }}</strong>
          <div class="hour-window-header-right">
            <span
              v-if="isSelectedDateInQueueApplyRange && Number(window.queue_pending_count || 0) > 0"
              class="hour-window-queue-pill"
            >
              {{ queueBadgeText(window) }}
            </span>
            <span v-if="window.locked_speed_rpm" class="hour-window-speed">
              {{ window.locked_speed_rpm }} r/min
            </span>
          </div>
        </div>

        <div class="hour-window-summary">{{ hourWindowSummary(window) }}</div>

        <div class="hour-window-positions">
          <button
            v-for="position in window.positions"
            :key="`${window.start}-${position.position_no}`"
            type="button"
            class="hour-position"
            :class="hourPositionClass(window, position)"
            :disabled="loading.booking || !isBallMillPositionSelectable(window, position)"
            @click="selectBallMillPosition(window, position)"
          >
            <span class="hour-position-no">{{ position.position_no }}</span>
          </button>
        </div>

        <div class="hour-window-queue-preview">
          <template v-if="shouldShowQueueDispatchPreview && windowQueueDispatchPreviewTopRows(window).length">
            <div
              v-for="row in windowQueueDispatchPreviewTopRows(window)"
              :key="row.preview_key || `queue-dispatch-preview-${window.start}-${row.id}`"
              class="hour-window-queue-preview-item"
            >
              <span class="queue-preview-user">{{ row.user_name || '-' }}</span>
            </div>
            <div v-if="windowQueueDispatchPreviewMoreCount(window) > 0" class="hour-window-queue-preview-more">
              该小时其余 {{ windowQueueDispatchPreviewMoreCount(window) }} 人见排队情况
            </div>
          </template>

          <div v-else-if="shouldShowQueueDispatchPreview" class="hour-window-queue-preview-empty">
            {{ loading.queuePreview ? '计算中' : '无分配' }}
          </div>

          <template v-else-if="windowBookingPreviewTopRows(window).length">
            <div
              v-for="row in windowBookingPreviewTopRows(window)"
              :key="row.preview_key || `booking-preview-${window.start}-${row.id || row.position_no}`"
              class="hour-window-queue-preview-item"
            >
              <span class="queue-preview-user">{{ row.user_name || '-' }}</span>
            </div>
            <div v-if="windowBookingPreviewMoreCount(window) > 0" class="hour-window-queue-preview-more">
              其余 {{ windowBookingPreviewMoreCount(window) }} 人见预约详情
            </div>
          </template>

          <div v-else class="hour-window-queue-preview-empty">
            {{ windowPreviewEmptyText(window) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useInstrumentBookingController } from '../context'

const {
  ballMillForm,
  ballMillEffectiveMaxMillingMinutes,
  ballMillActualDurationMinutes,
  ballMillRotationSpeedMin,
  ballMillRotationSpeedInputMax,
  isBallMillQueueMode,
  selectedBallMillStartTime,
  selectedBallMillPositionNos,
  estimatedBallMillEndText,
  selectedBallMillPositionText,
  selectedBallMillLimitHint,
  canBookSelectedBallMillWindow,
  loading,
  bookBallMill,
  topDirectBookingButtonText,
  isSelectedDateInQueueApplyRange,
  selectedDateQueuePendingCount,
  canSubmitBallMillQueueForDate,
  submitBallMillQueueForDate,
  queueSubmitDisabledText,
  ballMillHourWindows,
  hourWindowClass,
  queueBadgeText,
  hourWindowSummary,
  hourPositionClass,
  isBallMillPositionSelectable,
  selectBallMillPosition,
  shouldShowQueueDispatchPreview,
  windowQueueDispatchPreviewTopRows,
  windowQueueDispatchPreviewMoreCount,
  windowBookingPreviewTopRows,
  windowBookingPreviewMoreCount,
  windowPreviewEmptyText,
} = useInstrumentBookingController()
</script>
