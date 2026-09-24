import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getEquipmentTestClock } from '@/api/equipment'
import {
  extractApiErrorMessage,
  getTodayStr,
  parseDateString,
  toLocalDateString,
} from '../helpers'

export function useBookingCore() {
  const authStore = useAuthStore()

  const testClockState = ref({
    mock_enabled: false,
    mock_datetime: null,
    effective_now: null,
    effective_today: getTodayStr(),
  })

  const todayStr = ref(getTodayStr())
  const equipments = ref([])
  const selectedEquipmentId = ref(null)
  const selectedDate = ref(todayStr.value)
  const selectedElectrochemicalChannelNo = ref(1)
  const electrochemicalChannels = ref([])
  const electrochemicalCalendarValue = ref(parseDateString(todayStr.value))
  const electrochemicalCalendarPanelMonth = ref(todayStr.value.slice(0, 7))
  const electrochemicalCalendarSwitchingMonth = ref(false)
  const electrochemicalMonthSummaryDays = ref([])

  const rawAvailable = ref(null)
  const slots = ref([])
  const selectedSlots = ref([])
  const xrdForm = ref({
    start_time: '',
    end_time: '',
    remark: '',
  })

  const ballMillForm = ref({
    operation_type: 'grinding',
    milling_minutes: 12,
    rotation_speed_rpm: 300,
    queue_position_count: 1,
    remark: '',
  })
  const ballMillHourWindows = ref([])
  const selectedBallMillStartTime = ref('')
  const selectedBallMillPositionNos = ref([])
  const ballMillCalendarValue = ref(parseDateString(todayStr.value))
  const ballMillCalendarPanelMonth = ref(todayStr.value.slice(0, 7))
  const ballMillCalendarSwitchingMonth = ref(false)
  const ballMillMonthSummaryDays = ref([])
  const ballMillDayBookings = ref([])
  const ballMillQueueRequests = ref([])
  const ballMillQueueDispatchPreviewRows = ref([])
  const ballMillQueueDispatchPreviewMeta = ref({})

  const myBookings = ref([])
  const historyVisible = ref(false)
  const historyDateRange = ref([])
  const historyBookings = ref([])
  const xrdTutorStatsVisible = ref(false)
  const xrdTutorStatsRows = ref([])
  const xrdTutorStatsMonth = ref(todayStr.value.slice(0, 7))
  const selectedXrdStudentStats = ref(null)
  const xrdTutorialVisible = ref(false)
  const xrdTutorialDraftHtml = ref("")

  const loading = reactive({
    equipments: false,
    available: false,
    booking: false,
    myBookings: false,
    history: false,
    monthSummary: false,
    dayBookings: false,
    queue: false,
    queuePreview: false,
    clearingAll: false,
    channelToggle: false,
    xrdTutorStats: false,
    xrdRemoteConnect: false,
    xrdEndTest: false,
    xrdTutorialSaving: false,
  })

  const requestSeq = reactive({
    standardAvailability: 0,
    ballMillAvailability: 0,
    ballMillMonthSummary: 0,
    ballMillDayBookings: 0,
    ballMillQueueRequests: 0,
    ballMillQueuePreview: 0,
    electrochemicalMonthSummary: 0,
  })

  function getEffectiveNow() {
    const fromServer = testClockState.value?.effective_now
    if (fromServer) {
      const parsed = new Date(fromServer)
      if (!Number.isNaN(parsed.getTime())) return parsed
    }
    return new Date()
  }

  const testClockEnabled = computed(() => Boolean(testClockState.value?.mock_enabled))

  const testClockDisplayText = computed(() => {
    const now = getEffectiveNow()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    const hh = String(now.getHours()).padStart(2, '0')
    const mm = String(now.getMinutes()).padStart(2, '0')
    return [y, m, d].join('-') + ' ' + hh + ':' + mm
  })

  function applyTestClockState(payload = {}) {
    const fallbackToday = getTodayStr()
    testClockState.value = {
      mock_enabled: Boolean(payload?.mock_enabled),
      mock_datetime: payload?.mock_datetime || null,
      effective_now: payload?.effective_now || null,
      effective_today: payload?.effective_today || fallbackToday,
    }
    todayStr.value = testClockState.value.effective_today || fallbackToday
  }

  async function refreshTestClockState(options = {}) {
    const { silent = false } = options
    try {
      const { data } = await getEquipmentTestClock()
      applyTestClockState(data || {})
    } catch (error) {
      if (!silent) {
        ElMessage.error(extractApiErrorMessage(error, '读取测试系统日期失败'))
      }
      applyTestClockState({
        mock_enabled: false,
        mock_datetime: null,
        effective_now: null,
        effective_today: getTodayStr(),
      })
    }
  }

  const selectedEquipment = computed(() =>
    equipments.value.find((item) => item.id === selectedEquipmentId.value) || null,
  )

  const isBallMillMode = computed(
    () => selectedEquipment.value?.booking_mode === 'planetary_ball_mill',
  )

  const isElectrochemicalMode = computed(
    () => selectedEquipment.value?.booking_mode === 'electrochemical_workstation',
  )

  const isXrdMode = computed(
    () => selectedEquipment.value?.booking_mode === 'xrd',
  )

  const currentUserId = computed(() => Number(authStore.user?.id || 0))
  const isSystemAdmin = computed(() => Boolean(authStore.isSystemAdmin))
  const isTutor = computed(() => Boolean(authStore.isTutor))
  const canViewXrdTutorStats = computed(() => isSystemAdmin.value || isTutor.value)

  function canCurrentUserUseEquipment(item) {
    if (!item) return false
    if (isSystemAdmin.value) return true
    const allowedUsers = Array.isArray(item.booking_allowed_users) ? item.booking_allowed_users : []
    if (!allowedUsers.length) return true
    return allowedUsers.map((id) => Number(id)).includes(currentUserId.value)
  }

  const canBookSelectedEquipment = computed(() =>
    canCurrentUserUseEquipment(selectedEquipment.value),
  )

  const selectedElectrochemicalChannelText = computed(() => {
    const selected = electrochemicalChannels.value.find(
      (channel) => Number(channel.channel_no || 0) === Number(selectedElectrochemicalChannelNo.value || 0),
    )
    if (selected?.name) return selected.name
    return `通道${Number(selectedElectrochemicalChannelNo.value || 0) || 1}`
  })

  const isSelectedElectrochemicalChannelOffline = computed(() =>
    electrochemicalChannels.value.some(
      (channel) => (
        Number(channel.channel_no || 0) === Number(selectedElectrochemicalChannelNo.value || 0) &&
        Boolean(channel.offline)
      ),
    ),
  )

  const equipmentInfo = computed(() => {
    const selected = selectedEquipment.value
    const apiEquipment = rawAvailable.value?.equipment || {}
    if (!selected && !apiEquipment?.id) return null

    return {
      openStart: (apiEquipment.open_time_start || selected?.open_time || '').slice(0, 5),
      openEnd: (apiEquipment.open_time_end || selected?.close_time || '').slice(0, 5),
      timeUnit: apiEquipment.time_unit_minutes || selected?.time_slot_minutes || 60,
      maxAdvance:
        apiEquipment.effective_max_advance_days ??
        selected?.effective_max_advance_days ??
        apiEquipment.max_advance_days ??
        selected?.advance_days ??
        7,
      ballMillMaxActualMinutes:
        apiEquipment.ball_mill_max_actual_minutes ??
        selected?.ball_mill_max_actual_minutes ??
        2880,
      ballMillMinRotationSpeedRpm:
        apiEquipment.ball_mill_min_rotation_speed_rpm ??
        selected?.ball_mill_min_rotation_speed_rpm ??
        1,
      ballMillMaxRotationSpeedRpm:
        apiEquipment.ball_mill_max_rotation_speed_rpm ??
        selected?.ball_mill_max_rotation_speed_rpm ??
        null,
      ballMillMonthlyMaxActualMinutes:
        apiEquipment.ball_mill_monthly_max_actual_minutes ??
        selected?.ball_mill_monthly_max_actual_minutes ??
        null,
      ballMillQueueEnabled:
        apiEquipment.ball_mill_queue_enabled ??
        selected?.ball_mill_queue_enabled ??
        false,
      ballMillQueuePublishTime:
        (apiEquipment.ball_mill_queue_publish_time || selected?.ball_mill_queue_publish_time || '12:00').slice(0, 5),
      ballMillQueueRequestWindowDays:
        apiEquipment.ball_mill_queue_request_window_days ??
        selected?.ball_mill_queue_request_window_days ??
        14,
      ballMillQueueAllocateWindowDays:
        apiEquipment.ball_mill_queue_allocate_window_days ??
        selected?.ball_mill_queue_allocate_window_days ??
        10,
      ballMillQueueDispatchCursorDate:
        apiEquipment.ball_mill_queue_dispatch_cursor_date ??
        selected?.ball_mill_queue_dispatch_cursor_date ??
        null,
      ballMillQueuePublishLeadDays:
        apiEquipment.ball_mill_queue_publish_lead_days ??
        selected?.ball_mill_queue_publish_lead_days ??
        3,
      ballMillQueueDayStartTime:
        (apiEquipment.ball_mill_queue_day_start_time || selected?.ball_mill_queue_day_start_time || '07:00').slice(0, 5),
      ballMillQueueDayEndTime:
        (apiEquipment.ball_mill_queue_day_end_time || selected?.ball_mill_queue_day_end_time || '22:00').slice(0, 5),
      ballMillQueueHeavyThresholdMinutes:
        apiEquipment.ball_mill_queue_heavy_user_threshold_minutes ??
        selected?.ball_mill_queue_heavy_user_threshold_minutes ??
        4320,
      ballMillDirectBookingWindowDays:
        apiEquipment.ball_mill_direct_booking_window_days ??
        selected?.ball_mill_direct_booking_window_days ??
        7,
      ballMillDirectBookingCutoffTime:
        (apiEquipment.ball_mill_direct_booking_cutoff_time ||
          selected?.ball_mill_direct_booking_cutoff_time ||
          '07:00').slice(0, 5),
      ballMillMaxMillingMinutes:
        apiEquipment.ball_mill_max_milling_minutes ??
        selected?.ball_mill_max_milling_minutes ??
        1920,
      ballMillCycleRunMinutes:
        apiEquipment.ball_mill_cycle_run_minutes ??
        selected?._raw?.ball_mill_cycle_run_minutes ??
        12,
      ballMillCyclePauseMinutes:
        apiEquipment.ball_mill_cycle_pause_minutes ??
        selected?._raw?.ball_mill_cycle_pause_minutes ??
        6,
      electrochemicalChannelCount:
        apiEquipment.electrochemical_channel_count ??
        selected?.electrochemical_channel_count ??
        8,
      myRecent30dUsageMinutes: Number(rawAvailable.value?.my_recent_30d_usage_minutes ?? 0),
      myRecent30dUsageWindowEnd: rawAvailable.value?.my_recent_30d_usage_window_end || '',
    }
  })

  const isBallMillQueueMode = computed(
    () => isBallMillMode.value && Boolean(equipmentInfo.value?.ballMillQueueEnabled),
  )

  return {
    authStore,
    testClockState,
    todayStr,
    equipments,
    selectedEquipmentId,
    selectedDate,
    selectedElectrochemicalChannelNo,
    electrochemicalChannels,
    electrochemicalCalendarValue,
    electrochemicalCalendarPanelMonth,
    electrochemicalCalendarSwitchingMonth,
    electrochemicalMonthSummaryDays,
    rawAvailable,
    slots,
    selectedSlots,
    xrdForm,
    ballMillForm,
    ballMillHourWindows,
    selectedBallMillStartTime,
    selectedBallMillPositionNos,
    ballMillCalendarValue,
    ballMillCalendarPanelMonth,
    ballMillCalendarSwitchingMonth,
    ballMillMonthSummaryDays,
    ballMillDayBookings,
    ballMillQueueRequests,
    ballMillQueueDispatchPreviewRows,
    ballMillQueueDispatchPreviewMeta,
    myBookings,
    historyVisible,
    historyDateRange,
    historyBookings,
    xrdTutorStatsVisible,
    xrdTutorStatsRows,
    xrdTutorStatsMonth,
    selectedXrdStudentStats,
    xrdTutorialVisible,
    xrdTutorialDraftHtml,
    loading,
    requestSeq,
    getEffectiveNow,
    testClockEnabled,
    testClockDisplayText,
    applyTestClockState,
    refreshTestClockState,
    selectedEquipment,
    isBallMillMode,
    isElectrochemicalMode,
    isXrdMode,
    isBallMillQueueMode,
    currentUserId,
    isSystemAdmin,
    isTutor,
    canViewXrdTutorStats,
    canCurrentUserUseEquipment,
    canBookSelectedEquipment,
    selectedElectrochemicalChannelText,
    isSelectedElectrochemicalChannelOffline,
    equipmentInfo,
    parseDateString,
    toLocalDateString,
  }
}
