import { computed } from 'vue'
import {
  addDays,
  compareOptionalRank,
  formatDateOnly,
  formatDateRange,
  formatDuration,
  getWeekMonday,
  normalizePositiveRank,
  parseDateString,
  startOfDay,
  toLocalDateString,
} from '../helpers'

export function useBallMillLogic(ctx) {
  const {
    ballMillForm,
    selectedDate,
    selectedBallMillStartTime,
    selectedBallMillPositionNos,
    ballMillCalendarValue,
    ballMillCalendarPanelMonth,
    ballMillMonthSummaryDays,
    ballMillDayBookings,
    ballMillHourWindows,
    rawAvailable,
    equipmentInfo,
    loading,
    isBallMillMode,
    isBallMillQueueMode,
    canBookSelectedEquipment,
    getEffectiveNow,
    todayStr,
  } = ctx

  const ballMillMaxMillingMinutes = computed(
    () => equipmentInfo.value?.ballMillMaxMillingMinutes || 1920,
  )

  const ballMillRotationSpeedMin = computed(() =>
    Math.max(Number(equipmentInfo.value?.ballMillMinRotationSpeedRpm ?? 1) || 1, 1),
  )

  const ballMillRotationSpeedMax = computed(() => {
    const rawMax = equipmentInfo.value?.ballMillMaxRotationSpeedRpm
    if (rawMax == null || rawMax === '') return null
    const normalizedMax = Number(rawMax)
    return Number.isFinite(normalizedMax) ? normalizedMax : null
  })

  const ballMillRotationSpeedInputMax = computed(() => ballMillRotationSpeedMax.value ?? undefined)

  const ballMillRotationSpeedRangeText = computed(() => {
    const minRpm = ballMillRotationSpeedMin.value
    const maxRpm = ballMillRotationSpeedMax.value
    if (maxRpm == null) return `${minRpm} r/min 起`
    return `${minRpm} - ${maxRpm} r/min`
  })

  function getBallMillRotationSpeedValidationMessage(rotationSpeed = ballMillForm.value.rotation_speed_rpm) {
    const normalizedSpeed = Number(rotationSpeed || 0)
    if (!normalizedSpeed) return '请填写转速'
    if (normalizedSpeed < ballMillRotationSpeedMin.value) {
      return `转速不能低于 ${ballMillRotationSpeedMin.value} r/min`
    }
    if (
      ballMillRotationSpeedMax.value != null &&
      normalizedSpeed > ballMillRotationSpeedMax.value
    ) {
      return `转速不能高于 ${ballMillRotationSpeedMax.value} r/min`
    }
    return ''
  }

  const isBallMillRotationSpeedValid = computed(
    () => !getBallMillRotationSpeedValidationMessage(),
  )

  function calculateBallMillActualMinutesByInput(millingMinutes) {
    const runMinutes = Number(equipmentInfo.value?.ballMillCycleRunMinutes || 12)
    const pauseMinutes = Number(equipmentInfo.value?.ballMillCyclePauseMinutes || 6)
    const milling = Number(millingMinutes || 0)
    if (!milling || milling <= 0 || runMinutes <= 0) return 0
    const pauseCount = Math.floor(milling / runMinutes)
    return milling + pauseCount * pauseMinutes
  }

  function calculateBallMillMaxMillingByActualLimit(actualLimitMinutes) {
    const runMinutes = Number(equipmentInfo.value?.ballMillCycleRunMinutes || 12)
    const pauseMinutes = Number(equipmentInfo.value?.ballMillCyclePauseMinutes || 6)
    const limit = Math.max(Number(actualLimitMinutes || 0), 0)
    if (!limit || runMinutes <= 0) return 0
    let low = 0
    let high = limit
    while (low < high) {
      const mid = Math.floor((low + high + 1) / 2)
      const pauses = Math.floor(mid / runMinutes)
      const actual = mid + pauses * pauseMinutes
      if (actual <= limit) {
        low = mid
      } else {
        high = mid - 1
      }
    }
    return low
  }

  const selectedBallMillDynamicMaxActualMinutes = computed(() => {
    const startTime = selectedBallMillStartTime.value
    const selectedPositions = selectedBallMillPositionNos.value || []
    const globalMaxActual = Number(equipmentInfo.value?.ballMillMaxActualMinutes || 2880)
    if (!selectedDate.value || !startTime || !selectedPositions.length) return globalMaxActual
    if (isQueueWindowForAction(startTime)) return globalMaxActual

    const startAt = new Date(`${selectedDate.value}T${startTime}:00`)
    if (Number.isNaN(startAt.getTime())) return globalMaxActual

    let maxActual = globalMaxActual
    for (const booking of ballMillDayBookings.value || []) {
      const positionNo = Number(booking?.position_no)
      if (!selectedPositions.includes(positionNo)) continue
      const bookingStart = new Date(booking?.start_at || '')
      if (Number.isNaN(bookingStart.getTime())) continue
      if (bookingStart <= startAt) continue

      const gapMinutes = Math.floor((bookingStart.getTime() - startAt.getTime()) / 60000)
      if (gapMinutes < maxActual) {
        maxActual = Math.max(gapMinutes, 0)
      }
    }
    return Math.max(maxActual, 0)
  })

  const ballMillEffectiveMaxMillingMinutes = computed(() => {
    const globalMax = Number(ballMillMaxMillingMinutes.value || 1920)
    const dynamicActualMax = selectedBallMillDynamicMaxActualMinutes.value
    const dynamicMillingMax = calculateBallMillMaxMillingByActualLimit(dynamicActualMax)
    return Math.max(Math.min(globalMax, dynamicMillingMax || globalMax), 0)
  })

  const selectedBallMillLimitHint = computed(() => {
    const startTime = selectedBallMillStartTime.value
    if (!startTime || !selectedBallMillPositionNos.value.length) return ''
    if (isQueueWindowForAction(startTime)) return ''

    const maxMilling = ballMillEffectiveMaxMillingMinutes.value
    const maxActual = calculateBallMillActualMinutesByInput(maxMilling)
    if (!maxMilling || !maxActual) return '当前工位组合已无可用连续时段，请换工位或开始时间'
    return `当前工位组合上限：球磨 ${maxMilling} 分钟（真实 ${maxActual} 分钟）`
  })

  const ballMillCalculation = computed(() => {
    const millingMinutes = Number(ballMillForm.value.milling_minutes || 0)
    const runMinutes = equipmentInfo.value?.ballMillCycleRunMinutes || 12
    const pauseMinutes = equipmentInfo.value?.ballMillCyclePauseMinutes || 6
    if (!millingMinutes || millingMinutes <= 0) {
      return {
        millingMinutes: 0,
        pauseCount: 0,
        pauseMinutesTotal: 0,
        actualMinutes: 0,
      }
    }
    const pauseCount = Math.floor(millingMinutes / runMinutes)
    const pauseMinutesTotal = pauseCount * pauseMinutes
    return {
      millingMinutes,
      pauseCount,
      pauseMinutesTotal,
      actualMinutes: millingMinutes + pauseMinutesTotal,
    }
  })

  const ballMillActualDurationMinutes = computed(
    () => Number(ballMillCalculation.value.actualMinutes || 0),
  )

  const estimatedBallMillEndText = computed(() => {
    if (!selectedDate.value || !selectedBallMillStartTime.value || !ballMillActualDurationMinutes.value) {
      return '-'
    }
    const start = new Date(`${selectedDate.value}T${selectedBallMillStartTime.value}:00`)
    if (Number.isNaN(start.getTime())) return '-'
    const end = new Date(start.getTime() + ballMillActualDurationMinutes.value * 60 * 1000)
    return `${toLocalDateString(end)} ${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`
  })

  function isWednesdayPublished(anchorDate = getEffectiveNow()) {
    const weekMonday = getWeekMonday(anchorDate)
    const publishAt = startOfDay(addDays(weekMonday, 2))
    return startOfDay(anchorDate).getTime() >= publishAt.getTime()
  }

  function getBallMillDirectBookingWindowRange(anchorDate = getEffectiveNow()) {
    const weekMonday = getWeekMonday(anchorDate)
    if (isWednesdayPublished(anchorDate)) {
      return { start: addDays(weekMonday, 0), end: addDays(weekMonday, 13) }
    }
    return { start: addDays(weekMonday, 0), end: addDays(weekMonday, 6) }
  }

  function getBallMillQueueApplyWindowRange(anchorDate = getEffectiveNow()) {
    const weekMonday = getWeekMonday(anchorDate)
    const startOffsetDays = isWednesdayPublished(anchorDate) ? 14 : 7
    const start = addDays(weekMonday, startOffsetDays)
    return { start, end: addDays(start, 6) }
  }

  function getBallMillActionRange(anchorDate = getEffectiveNow()) {
    const directRange = getBallMillDirectBookingWindowRange(anchorDate)
    const queueRange = getBallMillQueueApplyWindowRange(anchorDate)
    return { start: startOfDay(directRange.start), end: startOfDay(queueRange.end) }
  }

  function isDateInRange(dateValue, range) {
    if (!dateValue || !range?.start || !range?.end) return false
    const dateStart = startOfDay(dateValue)
    if (Number.isNaN(dateStart.getTime())) return false
    return dateStart >= startOfDay(range.start) && dateStart <= startOfDay(range.end)
  }

  function isDateTimeInBallMillActionRange(dateTimeValue) {
    if (!dateTimeValue) return false
    const date = new Date(dateTimeValue)
    if (Number.isNaN(date.getTime())) return false
    const now = getEffectiveNow()
    const currentHourStart = new Date(now)
    currentHourStart.setMinutes(0, 0, 0)
    if (date.getTime() < currentHourStart.getTime()) return false
    const range = getBallMillActionRange()
    const start = startOfDay(range.start)
    const endExclusive = startOfDay(addDays(range.end, 1))
    return date >= start && date < endExclusive
  }

  function formatBallMillRecentUsageAnchor(value) {
    if (!value) return ''
    const windowEnd = new Date(value)
    if (Number.isNaN(windowEnd.getTime())) return ''
    return `${formatDateOnly(addDays(startOfDay(windowEnd), -1))} 24:00`
  }

  const ballMillRecentUsageAnchorLabel = computed(() =>
    formatBallMillRecentUsageAnchor(equipmentInfo.value?.myRecent30dUsageWindowEnd),
  )

  const selectedDateQueuePendingCount = computed(() =>
    Number(rawAvailable.value?.queue_pending_total || 0),
  )

  const isSelectedDateInQueueApplyRange = computed(() => {
    if (!isBallMillQueueMode.value || !selectedDate.value) return false
    return isDateInRange(parseDateString(selectedDate.value), getBallMillQueueApplyWindowRange())
  })

  const canSubmitBallMillQueueForDate = computed(() => Boolean(
    isBallMillQueueMode.value &&
    canBookSelectedEquipment.value &&
    isSelectedDateInQueueApplyRange.value &&
    Number(ballMillForm.value.queue_position_count || 0) >= 1 &&
    Number(ballMillForm.value.queue_position_count || 0) <= 4 &&
    Number(ballMillForm.value.milling_minutes || 0) > 0 &&
    isBallMillRotationSpeedValid.value,
  ))

  const queueSubmitDisabledText = computed(() => {
    if (!canBookSelectedEquipment.value) return '你不在该设备的可预约用户范围内'
    if (!isSelectedDateInQueueApplyRange.value) return '仅支持当前排队申请周的日期提交排队申请'
    if (Number(ballMillForm.value.milling_minutes || 0) <= 0) return '请填写球磨时间'
    const rotationSpeedMessage = getBallMillRotationSpeedValidationMessage()
    if (rotationSpeedMessage) return rotationSpeedMessage
    const count = Number(ballMillForm.value.queue_position_count || 0)
    if (!count || count < 1 || count > 4) return '请填写 1-4 个工位'
    return '信息不完整'
  })

  function getBallMillWindowStage(startTime = selectedBallMillStartTime.value) {
    if (!isBallMillQueueMode.value) return 'direct'
    if (!selectedDate.value || !startTime) return 'direct'
    const start = new Date(`${selectedDate.value}T${startTime}:00`)
    if (Number.isNaN(start.getTime())) return 'direct'
    if (!isDateTimeInBallMillActionRange(start)) return 'blocked'

    const queueRange = getBallMillQueueApplyWindowRange()
    const queueStart = startOfDay(queueRange.start)
    const queueEnd = startOfDay(addDays(queueRange.end, 1))
    if (start >= queueStart && start < queueEnd) return 'queue'

    const directRange = getBallMillDirectBookingWindowRange()
    const directStart = startOfDay(directRange.start)
    const directEnd = startOfDay(addDays(directRange.end, 1))
    if (start >= directStart && start < directEnd) return 'direct'

    return 'blocked'
  }

  function shouldQueueForBallMillStart(startTime = selectedBallMillStartTime.value) {
    return getBallMillWindowStage(startTime) === 'queue'
  }

  function isBlockedWindowForAction(startTime = selectedBallMillStartTime.value) {
    if (!selectedDate.value || !startTime) return true
    const start = new Date(`${selectedDate.value}T${startTime}:00`)
    return !isDateTimeInBallMillActionRange(start)
  }

  function isQueueWindowForAction(startTime) {
    return shouldQueueForBallMillStart(startTime)
  }

  function isQueueWindowForDisplay(startTime) {
    return shouldQueueForBallMillStart(startTime)
  }

  const selectedBallMillPositionText = computed(() => {
    if (!selectedBallMillPositionNos.value.length) return '-'
    return selectedBallMillPositionNos.value
      .slice()
      .sort((a, b) => a - b)
      .map((positionNo) => `${positionNo}`)
      .join('、')
  })

  const ballMillMonthSummaryMap = computed(() =>
    Object.fromEntries((ballMillMonthSummaryDays.value || []).map((item) => [item.date, item])),
  )

  const ballMillCalendarPanelMonthText = computed(() => {
    const [year, month] = (ballMillCalendarPanelMonth.value || todayStr.value.slice(0, 7)).split('-')
    return `${year} 年 ${Number(month)} 月`
  })

  function syncBallMillCalendarValue(dateStr = selectedDate.value) {
    if (!dateStr) return
    const current = toLocalDateString(ballMillCalendarValue.value)
    if (current === dateStr) return
    ballMillCalendarValue.value = parseDateString(dateStr)
  }

  function getCalendarDayMark(dayStr) {
    const summary = ballMillMonthSummaryMap.value[dayStr]
    return summary?.has_booking ? '已约' : ''
  }

  function calendarDayClass(data) {
    const summary = ballMillMonthSummaryMap.value[data.day]
    const isPast = startOfDay(data.date).getTime() < startOfDay(getEffectiveNow()).getTime()
    return {
      'ball-mill-date-cell--booked': Boolean(summary?.has_booking),
      'ball-mill-date-cell--free': !summary?.has_booking,
      'ball-mill-date-cell--past': isPast,
      'ball-mill-date-cell--selected': data.isSelected,
      'ball-mill-date-cell--adjacent': data.type !== 'current-month',
      'ball-mill-date-cell--disabled': disabledBallMillCalendarDate(data.date),
    }
  }

  function shiftMonth(monthStr, offset) {
    const [year, month] = monthStr.split('-').map(Number)
    const date = new Date(year, month - 1 + offset, 1)
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
  }

  const canBookBallMill = computed(() => Boolean(
    canBookSelectedEquipment.value &&
    selectedDate.value &&
    selectedBallMillStartTime.value &&
    selectedBallMillPositionNos.value.length > 0 &&
    ballMillForm.value.operation_type &&
    Number(ballMillForm.value.milling_minutes) > 0 &&
    isBallMillRotationSpeedValid.value,
  ))

  const selectedBallMillWindow = computed(() => {
    if (!selectedBallMillStartTime.value) return null
    return (ballMillHourWindows.value || []).find(
      (window) => window.start === selectedBallMillStartTime.value,
    ) || null
  })

  function canBookBallMillForWindow(window) {
    return Boolean(
      canBookBallMill.value &&
      window &&
      selectedBallMillStartTime.value === window.start &&
      !isQueueWindowForAction(window.start) &&
      !isBlockedWindowForAction(window.start),
    )
  }

  const canBookSelectedBallMillWindow = computed(() =>
    canBookBallMillForWindow(selectedBallMillWindow.value),
  )

  function directBookingDisabledText(window) {
    if (!canBookSelectedEquipment.value) return '你不在该设备的可预约用户范围内'
    if (window && isBlockedWindowForAction(window.start)) {
      return '当前仅支持直约窗口和下一整周排队窗口内的时段'
    }
    if (window && isQueueWindowForAction(window.start)) {
      return '该时段属于排队申请窗口，请使用上方"提交总排队申请"'
    }
    if (!ballMillForm.value.operation_type) return '请选择球磨用途'
    if (Number(ballMillForm.value.milling_minutes || 0) <= 0) return '请填写球磨时间'
    const rotationSpeedMessage = getBallMillRotationSpeedValidationMessage()
    if (rotationSpeedMessage) return rotationSpeedMessage
    return '先选择当前小时内的可预约工位'
  }

  const topDirectBookingButtonText = computed(() => {
    const window = selectedBallMillWindow.value
    if (!window) return '请选择小时和工位'
    if (canBookSelectedBallMillWindow.value) {
      return `预约 ${window.hour_label} 的 ${selectedBallMillPositionText.value}`
    }
    return directBookingDisabledText(window)
  })

  function isHourWindowUnavailable(window) {
    if (!window) return false
    if (isBlockedWindowForAction(window.start)) return true
    return ['full', 'past'].includes(window.card_status)
  }

  function hourWindowClass(window) {
    return {
      'hour-window-card--green': window.card_status === 'available',
      'hour-window-card--yellow': window.card_status === 'partial',
      'hour-window-card--red': window.card_status === 'full' || window.card_status === 'past',
      'hour-window-card--unavailable': isHourWindowUnavailable(window),
      'hour-window-card--queue-slot': isQueueWindowForDisplay(window.start),
      'hour-window-card--blocked-slot': isBlockedWindowForAction(window.start),
      'hour-window-card--direct-slot': !isQueueWindowForDisplay(window.start) && !isBlockedWindowForAction(window.start),
    }
  }

  function queueBadgeText(window) {
    return `排队${Number(window?.queue_pending_count || 0)}人`
  }

  function hourWindowSummary(window) {
    const pendingCount = Number(window?.queue_pending_count || 0)
    if (isQueueWindowForDisplay(window.start) || isQueueWindowForAction(window.start)) {
      return `排队${pendingCount}人`
    }
    return ''
  }

  function isBallMillPositionSelected(windowStart, positionNo) {
    return (
      selectedBallMillStartTime.value === windowStart &&
      selectedBallMillPositionNos.value.includes(positionNo)
    )
  }

  function hourPositionClass(window, position) {
    const isOccupied = position.status === 'occupied'
    return {
      'hour-position--selected': isBallMillPositionSelected(window.start, position.position_no),
      'hour-position--occupied': isOccupied,
      'hour-position--blocked': ['speed_locked', 'past', 'data_conflict'].includes(position.status),
      'hour-position--window-queue': !isOccupied && (isQueueWindowForDisplay(window.start) || isQueueWindowForAction(window.start)),
      'hour-position--window-blocked': !isOccupied && isBlockedWindowForAction(window.start),
    }
  }

  function isBallMillPositionSelectable(window, position) {
    if (!window || !position) return false
    if (window.card_status === 'past' || position.status === 'past') return false
    if (isQueueWindowForDisplay(window.start) || isQueueWindowForAction(window.start) || isBlockedWindowForAction(window.start)) return false
    return Boolean(position.allowed)
  }

  function disabledBallMillCalendarDate() {
    return false
  }

  return {
    ballMillMaxMillingMinutes,
    ballMillRotationSpeedMin,
    ballMillRotationSpeedMax,
    ballMillRotationSpeedInputMax,
    ballMillRotationSpeedRangeText,
    getBallMillRotationSpeedValidationMessage,
    isBallMillRotationSpeedValid,
    calculateBallMillActualMinutesByInput,
    calculateBallMillMaxMillingByActualLimit,
    selectedBallMillDynamicMaxActualMinutes,
    ballMillEffectiveMaxMillingMinutes,
    selectedBallMillLimitHint,
    ballMillCalculation,
    ballMillActualDurationMinutes,
    estimatedBallMillEndText,
    isWednesdayPublished,
    getBallMillDirectBookingWindowRange,
    getBallMillQueueApplyWindowRange,
    getBallMillActionRange,
    isDateInRange,
    isDateTimeInBallMillActionRange,
    ballMillRecentUsageAnchorLabel,
    selectedDateQueuePendingCount,
    isSelectedDateInQueueApplyRange,
    canSubmitBallMillQueueForDate,
    queueSubmitDisabledText,
    getBallMillWindowStage,
    shouldQueueForBallMillStart,
    isBlockedWindowForAction,
    isQueueWindowForAction,
    isQueueWindowForDisplay,
    selectedBallMillPositionText,
    ballMillMonthSummaryMap,
    ballMillCalendarPanelMonthText,
    syncBallMillCalendarValue,
    getCalendarDayMark,
    calendarDayClass,
    shiftMonth,
    canBookBallMill,
    selectedBallMillWindow,
    canBookBallMillForWindow,
    canBookSelectedBallMillWindow,
    directBookingDisabledText,
    topDirectBookingButtonText,
    isHourWindowUnavailable,
    hourWindowClass,
    queueBadgeText,
    hourWindowSummary,
    isBallMillPositionSelected,
    hourPositionClass,
    isBallMillPositionSelectable,
    disabledBallMillCalendarDate,
    normalizePositiveRank,
    compareOptionalRank,
    formatDateOnly,
    formatDateRange,
    formatDuration,
  }
}
