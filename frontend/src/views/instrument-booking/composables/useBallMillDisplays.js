import { computed } from 'vue'
import {
  addDays,
  compareOptionalRank,
  formatDateOnly,
  formatDateRange,
  formatDateTime,
  getWeekMonday,
  parseDateString,
} from '../helpers'

export function useBallMillDisplays(ctx, logic) {
  const {
    ballMillQueueRequests,
    ballMillQueueDispatchPreviewRows,
    ballMillHourWindows,
    ballMillDayBookings,
    selectedDate,
    currentUserId,
    isSystemAdmin,
  } = ctx

  const {
    normalizePositiveRank,
    isSelectedDateInQueueApplyRange,
    isQueueWindowForDisplay,
    isQueueWindowForAction,
  } = logic

  const selectedQueueWeekMonday = computed(() => {
    if (!selectedDate.value) return ''
    return formatDateOnly(getWeekMonday(parseDateString(selectedDate.value)))
  })

  function formatQueueBatchRange(requestedDate) {
    if (!requestedDate) return '-'
    const start = getWeekMonday(parseDateString(requestedDate))
    if (Number.isNaN(start.getTime())) return requestedDate
    return formatDateRange(start, addDays(start, 6))
  }

  const selectedQueueWeekRows = computed(() => {
    const rows = Array.isArray(ballMillQueueRequests.value) ? ballMillQueueRequests.value : []
    const weekMonday = selectedQueueWeekMonday.value
    return rows.filter((row) => {
      if (!weekMonday) return true
      const requestedDate = row?.requested_date
      if (!requestedDate) return false
      const currentWeekMonday = getWeekMonday(parseDateString(requestedDate))
      return formatDateOnly(currentWeekMonday) === weekMonday
    })
  })

  function getQueueDisplayRank(row) {
    if (!row) return null
    return normalizePositiveRank(row.queue_display_rank ?? row.dispatch_rank ?? row.queue_rank)
  }

  function compareQueueRowsByDisplayRank(a, b) {
    const rankCompare = compareOptionalRank(getQueueDisplayRank(a), getQueueDisplayRank(b))
    if (rankCompare !== 0) return rankCompare
    const tsA = new Date(a?.created_at || 0).getTime()
    const tsB = new Date(b?.created_at || 0).getTime()
    if (tsA !== tsB) return tsA - tsB
    return Number(a?.id || 0) - Number(b?.id || 0)
  }

  const queueBoardRows = computed(() =>
    selectedQueueWeekRows.value.slice().sort(compareQueueRowsByDisplayRank),
  )

  const queuePublishedRows = computed(() =>
    selectedQueueWeekRows.value
      .filter((row) => row?.status && row.status !== 'pending')
      .slice()
      .sort(compareQueueRowsByDisplayRank),
  )

  const hasQueuePublishedResults = computed(() => queuePublishedRows.value.length > 0)

  const shouldShowQueueDispatchPreview = computed(() => Boolean(
    isSelectedDateInQueueApplyRange.value && !hasQueuePublishedResults.value,
  ))

  const queueAllocatedBookingRankMap = computed(() => {
    const map = {}
    for (const row of queuePublishedRows.value || []) {
      const rank = getQueueDisplayRank(row)
      if (!rank) continue
      const bookingIds = Array.isArray(row?.allocated_booking_ids) ? row.allocated_booking_ids : []
      for (const bookingId of bookingIds) {
        const normalizedBookingId = Number(bookingId || 0)
        if (!normalizedBookingId) continue
        const currentRank = Number(map[normalizedBookingId] || 0)
        if (!currentRank || rank < currentRank) {
          map[normalizedBookingId] = rank
        }
      }
    }
    return map
  })

  function getQueueDisplayRankByBookingId(bookingId) {
    const normalizedBookingId = Number(bookingId || 0)
    if (!normalizedBookingId) return null
    return normalizePositiveRank(queueAllocatedBookingRankMap.value[normalizedBookingId])
  }

  function compareBallMillDayBookingRows(a, b) {
    const rankCompare = compareOptionalRank(a?.queue_display_rank, b?.queue_display_rank)
    if (rankCompare !== 0) return rankCompare
    const startA = new Date(a?.start_at || 0).getTime()
    const startB = new Date(b?.start_at || 0).getTime()
    if (startA !== startB) return startA - startB
    const positionA = Array.isArray(a?.position_nos) && a.position_nos.length
      ? Number(a.position_nos[0] || 0)
      : Number(a?.position_no || 0)
    const positionB = Array.isArray(b?.position_nos) && b.position_nos.length
      ? Number(b.position_nos[0] || 0)
      : Number(b?.position_no || 0)
    if (positionA !== positionB) return positionA - positionB
    return Number(a?.id || 0) - Number(b?.id || 0)
  }

  const ballMillDayBookingsDisplay = computed(() => {
    const grouped = new Map()
    for (const row of ballMillDayBookings.value || []) {
      const key = [
        row.user_name || '',
        row.operation_type || '',
        row.rotation_speed_rpm || '',
        row.milling_minutes || '',
        row.actual_duration_minutes || '',
        row.start_at || '',
        row.end_at || '',
      ].join('|')
      if (!grouped.has(key)) {
        grouped.set(key, {
          ...row,
          booking_ids: row.id ? [row.id] : [],
          position_nos: row.position_no ? [row.position_no] : [],
          queue_display_rank: getQueueDisplayRankByBookingId(row.id),
        })
        continue
      }
      const current = grouped.get(key)
      if (row.id && !current.booking_ids.includes(row.id)) {
        current.booking_ids.push(row.id)
      }
      if (row.position_no && !current.position_nos.includes(row.position_no)) {
        current.position_nos.push(row.position_no)
      }
      const rowRank = getQueueDisplayRankByBookingId(row.id)
      if (rowRank && (!current.queue_display_rank || rowRank < current.queue_display_rank)) {
        current.queue_display_rank = rowRank
      }
    }
    return Array.from(grouped.values())
      .map((row) => ({
        ...row,
        position_nos: (row.position_nos || []).slice().sort((a, b) => a - b),
      }))
      .sort(compareBallMillDayBookingRows)
  })

  function buildMergedPreviewRows(rows, keyPrefix) {
    const merged = []
    const seenUsers = new Set()
    for (const row of rows || []) {
      const userName = String(row?.user_name || '').trim() || '-'
      if (seenUsers.has(userName)) continue
      seenUsers.add(userName)
      merged.push({
        ...row,
        user_name: userName,
        preview_key: `${keyPrefix}-${userName}-${merged.length + 1}`,
      })
    }
    return merged
  }

  const windowQueueDispatchPreviewMap = computed(() => {
    const map = {}
    for (const window of ballMillHourWindows.value || []) {
      if (window?.start) map[window.start] = []
    }

    for (const row of ballMillQueueDispatchPreviewRows.value || []) {
      if (row?.status !== 'allocated' || !row?.allocated_start_at) continue
      const dt = new Date(row.allocated_start_at)
      if (Number.isNaN(dt.getTime())) continue

      const dateStr = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
      const hourKey = `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`

      if (dateStr !== selectedDate.value) continue
      if (!Object.prototype.hasOwnProperty.call(map, hourKey)) {
        map[hourKey] = []
      }
      map[hourKey].push(row)
    }

    for (const key of Object.keys(map)) {
      map[key].sort((a, b) => {
        const rankCompare = compareOptionalRank(a?.theoretical_rank, b?.theoretical_rank)
        if (rankCompare !== 0) return rankCompare
        return Number(a?.id || 0) - Number(b?.id || 0)
      })
    }

    return map
  })

  function windowQueueDispatchPreviewRows(window) {
    if (!window?.start) return []
    return buildMergedPreviewRows(windowQueueDispatchPreviewMap.value[window.start] || [], `queue-${window.start}`)
  }

  function windowQueueDispatchPreviewTopRows(window) {
    return windowQueueDispatchPreviewRows(window).slice(0, 4)
  }

  function windowQueueDispatchPreviewMoreCount(window) {
    return Math.max(windowQueueDispatchPreviewRows(window).length - 4, 0)
  }

  const windowBookingPreviewMap = computed(() => {
    const map = {}
    for (const window of ballMillHourWindows.value || []) {
      const rows = []
      for (const position of window?.positions || []) {
        const booking = position?.booking
        if (!booking) continue
        const bookingId = Number(booking?.id || 0)
        rows.push({
          id: bookingId,
          user_name: booking.booked_by || '-',
          position_no: Number(position?.position_no || booking?.position_no || 0),
          operation_type_display: booking.operation_type_display || '',
          rotation_speed_rpm: Number(booking.rotation_speed_rpm || 0),
          start_at: booking.start_at || '',
          end_at: booking.end_at || '',
          queue_display_rank: bookingId ? queueAllocatedBookingRankMap.value[bookingId] || null : null,
        })
      }
      rows.sort((a, b) => {
        const rankCompare = compareOptionalRank(a?.queue_display_rank, b?.queue_display_rank)
        if (rankCompare !== 0) return rankCompare
        if (a.position_no !== b.position_no) return a.position_no - b.position_no
        const tsA = new Date(a.start_at || 0).getTime()
        const tsB = new Date(b.start_at || 0).getTime()
        if (tsA !== tsB) return tsA - tsB
        return Number(a.id || 0) - Number(b.id || 0)
      })
      map[window.start] = rows
    }
    return map
  })

  function windowBookingPreviewRows(window) {
    if (!window?.start) return []
    return buildMergedPreviewRows(windowBookingPreviewMap.value[window.start] || [], `booking-${window.start}`)
  }

  function windowBookingPreviewTopRows(window) {
    return windowBookingPreviewRows(window).slice(0, 4)
  }

  function windowBookingPreviewMoreCount(window) {
    return Math.max(windowBookingPreviewRows(window).length - 4, 0)
  }

  const queueBoardEmptyDescription = computed(() => '暂无排队申请')

  const queueWindowPreviewEmptyText = computed(() => (
    queuePublishedRows.value.length ? '当前小时暂无放榜预约' : '暂无排队申请'
  ))

  function windowPreviewEmptyText(window) {
    if (isSelectedDateInQueueApplyRange.value && isQueueWindowForDisplay(window?.start)) {
      return queueWindowPreviewEmptyText.value
    }
    return '当前小时暂无预约'
  }

  function formatBallMillPositions(row) {
    const positions = Array.isArray(row?.position_nos) && row.position_nos.length
      ? row.position_nos
      : (row?.position_no ? [row.position_no] : [])
    if (!positions.length) return '-'
    return positions.map((no) => `${no} 号位`).join('、')
  }

  function queueStatusLabel(status) {
    if (status === 'pending') return '排队中'
    if (status === 'allocated') return '已分配'
    if (status === 'rejected') return '未分配'
    if (status === 'cancelled') return '已取消'
    return status || '-'
  }

  function queueStatusType(status) {
    if (status === 'allocated') return 'success'
    if (status === 'pending') return 'warning'
    if (status === 'rejected') return 'danger'
    return 'info'
  }

  function queueAllocationText(row) {
    if (row.status === 'allocated') {
      const start = formatDateTime(row.allocated_start_at)
      const end = formatDateTime(row.allocated_end_at)
      const positions = Array.isArray(row.allocated_position_nos)
        ? row.allocated_position_nos.map((p) => `${p} 号位`).join('、')
        : '-'
      return `${start} - ${end} / ${positions}`
    }
    return row.fail_reason || '-'
  }

  function queueDispatchCompactText(row) {
    if (!row) return '-'
    if (row.status === 'allocated') {
      const positions = Array.isArray(row.allocated_position_nos)
        ? row.allocated_position_nos.join('、')
        : '-'
      const startText = formatDateTime(row.allocated_start_at)
      const endText = formatDateTime(row.allocated_end_at)
      const startHm = startText !== '-' ? startText.slice(11, 16) : '-'
      const endHm = endText !== '-' ? endText.slice(11, 16) : '-'
      return `${startHm}-${endHm} / ${positions}`
    }
    if (row.status === 'rejected') return '未分配'
    if (row.status === 'pending') return '排队中'
    return row.fail_reason || '-'
  }

  function canCancelQueueRequest(row) {
    if (!row) return false
    return Number(row.user || 0) === Number(currentUserId.value || 0)
  }

  function canDeleteQueueRequest(row) {
    return Boolean(row?.id && isSystemAdmin.value)
  }

  return {
    selectedQueueWeekMonday,
    formatQueueBatchRange,
    selectedQueueWeekRows,
    getQueueDisplayRank,
    compareQueueRowsByDisplayRank,
    queueBoardRows,
    queuePublishedRows,
    hasQueuePublishedResults,
    shouldShowQueueDispatchPreview,
    queueAllocatedBookingRankMap,
    getQueueDisplayRankByBookingId,
    compareBallMillDayBookingRows,
    ballMillDayBookingsDisplay,
    windowQueueDispatchPreviewRows,
    windowQueueDispatchPreviewTopRows,
    windowQueueDispatchPreviewMoreCount,
    windowBookingPreviewRows,
    windowBookingPreviewTopRows,
    windowBookingPreviewMoreCount,
    queueBoardEmptyDescription,
    queueWindowPreviewEmptyText,
    windowPreviewEmptyText,
    formatBallMillPositions,
    queueStatusLabel,
    queueStatusType,
    queueAllocationText,
    queueDispatchCompactText,
    canCancelQueueRequest,
    canDeleteQueueRequest,
    isQueueWindowForAction,
  }
}
