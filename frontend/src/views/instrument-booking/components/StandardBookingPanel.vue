<template>
  <template v-if="!isBallMillMode">
    <div v-if="isXrdMode" class="xrd-booking-panel">
      <el-form :model="xrdForm" label-width="110px" class="xrd-booking-form">
        <el-form-item label="占用时段">
          <span>{{ selectedXrdTimeText }}</span>
        </el-form-item>

        <el-form-item label="占用时长">
          <span>{{ xrdEffectiveDurationMinutes }} 分钟</span>
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="xrdForm.remark" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading.booking"
            :disabled="!selectedEquipmentId || !xrdForm.start_time || !xrdForm.end_time || xrdEffectiveDurationMinutes <= 0"
            @click="bookXrd"
          >
            提交预约
          </el-button>
          <el-tooltip
            :content="xrdRemoteConnectDisabledReason"
            :disabled="xrdRemoteConnectAvailable"
            placement="top"
          >
            <span class="xrd-remote-connect-wrap">
              <el-button
                type="success"
                :loading="loading.xrdRemoteConnect"
                :disabled="!xrdRemoteConnectAvailable"
                @click="connectXrdRemote"
              >
                远程连接
              </el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            :content="xrdEndTestDisabledReason"
            :disabled="xrdEndTestAvailable"
            placement="top"
          >
            <span class="xrd-remote-connect-wrap">
              <el-button
                type="warning"
                :loading="loading.xrdEndTest"
                :disabled="!xrdEndTestAvailable"
                @click="endXrdTest"
              >
                结束测试
              </el-button>
            </span>
          </el-tooltip>
          <el-button class="xrd-tutorial-button" @click="openXrdTutorial">
            使用教程
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-else-if="isElectrochemicalMode" class="electrochemical-board-head">
      <div class="electrochemical-board-title">
        <span class="electrochemical-board-kicker">通道预约</span>
        <strong>{{ selectedElectrochemicalChannelText }}</strong>
      </div>
      <div class="electrochemical-board-stats">
        <span class="electrochemical-stat electrochemical-stat--free">
          <b>{{ electrochemicalSlotStats.free }}</b> 可预约
        </span>
        <span class="electrochemical-stat electrochemical-stat--selected">
          <b>{{ electrochemicalSlotStats.selected }}</b> 已选
        </span>
        <span class="electrochemical-stat electrochemical-stat--occupied">
          <b>{{ electrochemicalSlotStats.occupied }}</b> 已占用
        </span>
      </div>
    </div>

    <div v-if="isElectrochemicalMode && isSelectedElectrochemicalChannelOffline" class="channel-offline-tip">
      当前所选通道已被管理员临时下线，暂不可预约。
    </div>

    <div
      v-if="slots.length"
      class="slot-section"
      :class="{ 'slot-section--electrochemical': isElectrochemicalMode }"
    >
      <div
        class="slot-grid"
        :class="{ 'slot-grid--electrochemical': isElectrochemicalMode }"
      >
        <el-button
          v-for="s in slots"
          :key="`slot-${selectedElectrochemicalChannelNo}-${s.start}`"
          class="slot"
          :class="slotClass(s)"
          :type="buttonType(s)"
          :plain="!isSelected(s)"
          :disabled="isSlotDisabled(s)"
          @click="handleSlotClick(s)"
        >
          <template v-if="isElectrochemicalMode">
            <span class="slot-time">{{ formatSlotRange(s) }}</span>
            <span class="slot-meta">{{ slotStateText(s) }}</span>
          </template>
          <template v-else>
            {{ s.start }} - {{ s.end }}
            <span v-if="s.occupied">
              （{{ s.booked_by ? `${s.booked_by}已预约` : '已占用' }}）
            </span>
            <span v-else-if="isPastSlotForSelectedDate(s)">（时间已过）</span>
          </template>
        </el-button>
      </div>
    </div>

    <div v-else class="no-slots">
      当前日期暂无可预约时段
    </div>

    <el-dialog
      v-model="xrdTutorialVisible"
      title="XRD 使用教程"
      width="720px"
      class="xrd-tutorial-dialog"
    >
      <div v-if="isSystemAdmin" class="xrd-tutorial-editor">
        <el-tabs v-model="xrdTutorialEditorMode">
          <el-tab-pane label="预览编辑" name="visual">
            <div
              ref="xrdTutorialEditorRef"
              class="xrd-tutorial-editable"
              contenteditable="true"
              v-html="xrdTutorialDraftHtml"
              @input="handleXrdTutorialEditorInput"
            ></div>
          </el-tab-pane>
          <el-tab-pane label="HTML" name="html">
            <el-input
              v-model="xrdTutorialDraftHtml"
              type="textarea"
              :rows="10"
              resize="vertical"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
      <div v-else class="xrd-tutorial-content" v-html="xrdTutorialHtml"></div>
      <template #footer>
        <el-button @click="xrdTutorialVisible = false">关闭</el-button>
        <el-button
          v-if="isSystemAdmin"
          type="primary"
          :loading="loading.xrdTutorialSaving"
          @click="saveXrdTutorial"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </template>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { formatElectrochemicalTimeRange } from '../helpers'
import { useInstrumentBookingController } from '../context'

const {
  isBallMillMode,
  isElectrochemicalMode,
  isXrdMode,
  isSelectedElectrochemicalChannelOffline,
  selectedElectrochemicalChannelText,
  selectedElectrochemicalChannelNo,
  slots,
  selectedSlots,
  selectedEquipmentId,
  xrdForm,
  xrdEffectiveDurationMinutes,
  xrdRemoteConnectAvailable,
  xrdRemoteConnectDisabledReason,
  xrdEndTestAvailable,
  xrdEndTestDisabledReason,
  xrdTutorialVisible,
  xrdTutorialDraftHtml,
  xrdTutorialHtml,
  isSystemAdmin,
  selectXrdSlot,
  connectXrdRemote,
  endXrdTest,
  openXrdTutorial,
  saveXrdTutorial,
  loading,
  buttonType,
  isSelected,
  isSlotDisabled,
  toggleSlot,
  bookXrd,
  isPastSlotForSelectedDate,
} = useInstrumentBookingController()

const xrdTutorialEditorMode = ref('visual')
const xrdTutorialEditorRef = ref(null)

watch(xrdTutorialEditorMode, (mode) => {
  if (mode === 'visual' && xrdTutorialEditorRef.value) {
    xrdTutorialEditorRef.value.innerHTML = xrdTutorialDraftHtml.value || ''
  }
})

const electrochemicalSlotStats = computed(() => {
  const rows = Array.isArray(slots.value) ? slots.value : []
  const isOffline = isSelectedElectrochemicalChannelOffline.value
  return {
    free: rows.filter((slot) => !isOffline && !slot.occupied && !isPastSlotForSelectedDate(slot)).length,
    selected: selectedSlots.value.length,
    occupied: rows.filter((slot) => slot.occupied).length,
  }
})

const selectedXrdTimeText = computed(() => {
  if (!xrdForm.value.start_time || !xrdForm.value.end_time) {
    return '请在下方时段按钮中选择开始和结束时段'
  }
  return `${xrdForm.value.start_time} - ${xrdForm.value.end_time}`
})

function formatSlotRange(slot) {
  return formatElectrochemicalTimeRange(slot?.start, slot?.end)
}

function handleSlotClick(slot) {
  if (isXrdMode.value) {
    selectXrdSlot(slot)
    return
  }
  toggleSlot(slot)
}

function handleXrdTutorialEditorInput(event) {
  xrdTutorialDraftHtml.value = event.target?.innerHTML || ''
}

function slotStateText(slot) {
  if (isSelectedElectrochemicalChannelOffline.value) return '通道已下线'
  if (slot.occupied) return slot.booked_by ? `${slot.booked_by}已预约` : '已占用'
  if (isSelected(slot)) return '已选'
  if (isPastSlotForSelectedDate(slot)) return '时间已过'
  return '空闲'
}

function slotClass(slot) {
  if (isXrdMode.value) {
    return {
      'slot--selected': isSelected(slot),
      'slot--occupied': Boolean(slot.occupied),
      'slot--past': !slot.occupied && isPastSlotForSelectedDate(slot),
    }
  }
  if (!isElectrochemicalMode.value) return {}
  return {
    'slot--electrochemical': true,
    'slot--selected': isSelected(slot),
    'slot--occupied': Boolean(slot.occupied),
    'slot--offline': isSelectedElectrochemicalChannelOffline.value,
    'slot--past': !slot.occupied && !isSelectedElectrochemicalChannelOffline.value && isPastSlotForSelectedDate(slot),
  }
}
</script>


<style scoped>
.xrd-booking-panel {
  max-width: 640px;
}

.xrd-booking-form {
  padding-top: 8px;
}

.xrd-remote-connect-wrap {
  display: inline-flex;
  margin-left: 8px;
}

.xrd-tutorial-button {
  margin-left: 8px;
}

.xrd-tutorial-content,
.xrd-tutorial-editable {
  min-height: 220px;
  line-height: 1.7;
  word-break: break-word;
}

.xrd-tutorial-editable {
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  outline: none;
}

.xrd-tutorial-editable:focus {
  border-color: var(--el-color-primary);
}
</style>
