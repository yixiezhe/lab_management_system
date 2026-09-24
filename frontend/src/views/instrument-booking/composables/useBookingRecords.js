import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '@/api'
import {
  cancelBooking as cancelBookingApi,
  deleteBooking as deleteBookingApi,
  endBookingEarly as endBookingEarlyApi,
} from '@/api/equipment'
import { extractApiErrorMessage, formatElectrochemicalTimeRange } from '../helpers'

export function useBookingRecords(ctx, deps = {}) {
  const {
    myBookings,
    historyVisible,
    historyDateRange,
    historyBookings,
    loading,
    getEffectiveNow,
    testClockEnabled,
    isBallMillMode,
    isElectrochemicalMode,
    selectedEquipmentId,
    selectedElectrochemicalChannelNo,
  } = ctx

  const {
    fetchCurrentAvailability,
    fetchBallMillMonthSummary,
    fetchBallMillDayBookings,
    fetchElectrochemicalMonthSummary,
  } = deps

  const bookingClockTick = ref(0)
  let bookingClockTimerId = null

  onMounted(() => {
    bookingClockTimerId = window.setInterval(() => {
      bookingClockTick.value += 1
    }, 10_000)
  })

  onBeforeUnmount(() => {
    if (bookingClockTimerId !== null) {
      window.clearInterval(bookingClockTimerId)
    }
  })

  const myBookingsDisplay = computed(() => {
    const source = Array.isArray(myBookings.value) ? myBookings.value : []
    const groupedRows = []
    const ballMillGroupedMap = new Map()

    for (const row of source) {
      if (row?.booking_mode !== 'planetary_ball_mill') {
        groupedRows.push(row)
        continue
      }

      const key = [
        row.equipment || '',
        row.date || '',
        row.end_date || '',
        row.start_time || '',
        row.end_time || '',
        row.start_at || '',
        row.end_at || '',
        row.operation_type || '',
        row.rotation_speed_rpm || '',
        row.milling_minutes || '',
        row.actual_duration_minutes || '',
        row.status || '',
        row.remark || '',
      ].join('|')

      if (!ballMillGroupedMap.has(key)) {
        const initialRow = {
          ...row,
          booking_ids: row.id ? [row.id] : [],
          position_nos: row.position_no ? [row.position_no] : [],
        }
        ballMillGroupedMap.set(key, initialRow)
        groupedRows.push(initialRow)
        continue
      }

      const existing = ballMillGroupedMap.get(key)
      if (row.id && !existing.booking_ids.includes(row.id)) {
        existing.booking_ids.push(row.id)
      }
      if (row.position_no && !existing.position_nos.includes(row.position_no)) {
        existing.position_nos.push(row.position_no)
      }
    }

    return groupedRows.map((row) => {
      if (row?.booking_mode !== 'planetary_ball_mill') return row
      return {
        ...row,
        booking_ids: (row.booking_ids || []).slice().sort((a, b) => a - b),
        position_nos: (row.position_nos || []).slice().sort((a, b) => a - b),
      }
    })
  })

  const currentElectrochemicalChannelBookingsDisplay = computed(() => {
    if (!isElectrochemicalMode.value) return []
    const equipmentId = Number(selectedEquipmentId.value || 0)
    const channelNo = Number(selectedElectrochemicalChannelNo.value || 0)
    return myBookingsDisplay.value.filter((row) => (
      row?.booking_mode === 'electrochemical_workstation' &&
      Number(row?.equipment || 0) === equipmentId &&
      Number(row?.position_no || 0) === channelNo
    ))
  })

  function formatBookingDate(row) {
    if (!row?.date) return '-'
    if (row.end_date && row.end_date !== row.date) {
      return `${row.date} 至 ${row.end_date}`
    }
    return row.date
  }

  function formatBookingTime(row) {
    if (row?.booking_mode === 'electrochemical_workstation') {
      return formatElectrochemicalTimeRange(row?.start_time, row?.end_time)
    }
    return `${(row?.start_time || '').slice(0, 5)} - ${(row?.end_time || '').slice(0, 5)}`
  }

  function formatBookingDetails(row) {
    if (!row) return '-'
    if (row.booking_mode === 'electrochemical_workstation') {
      const parts = []
      if (row.position_no) parts.push(`通道 ${row.position_no}`)
      if (row.remark) parts.push(row.remark)
      return parts.join(' / ') || '-'
    }
    if (row.booking_mode === 'xrd') {
      const parts = []
      if (row.actual_duration_minutes) parts.push(`时长 ${row.actual_duration_minutes} 分钟`)
      if (row.remark) parts.push(row.remark)
      return parts.join(' / ') || '-'
    }
    if (row.booking_mode !== 'planetary_ball_mill') return row.remark || '-'

    const parts = []
    const positions = Array.isArray(row.position_nos) && row.position_nos.length
      ? row.position_nos
      : (row.position_no ? [row.position_no] : [])

    if (positions.length) {
      parts.push(positions.map((positionNo) => `${positionNo} 号位`).join('、'))
    }
    if (row.operation_type_display) parts.push(row.operation_type_display)
    if (row.rotation_speed_rpm) parts.push(`${row.rotation_speed_rpm} r/min`)
    if (row.milling_minutes) parts.push(`球磨 ${row.milling_minutes} 分钟`)
    if (row.actual_duration_minutes) parts.push(`真实 ${row.actual_duration_minutes} 分钟`)
    if (row.remark) parts.push(row.remark)
    return parts.join(' / ') || '-'
  }

  function getBookingStartMs(row) {
    if (row?.start_at) return new Date(row.start_at).getTime()
    return new Date(`${row?.date}T${row?.start_time}`).getTime()
  }

  function getBookingEndMs(row) {
    if (row?.end_at) return new Date(row.end_at).getTime()
    return new Date(`${row?.date}T${row?.end_time}`).getTime()
  }

  function getBookingNowMs() {
    void bookingClockTick.value
    return testClockEnabled.value ? getEffectiveNow().getTime() : Date.now()
  }

  function canModifyBooking(row) {
    const startMs = getBookingStartMs(row)
    return Number.isFinite(startMs) && startMs > getBookingNowMs()
  }

  function canCancelBooking(row) {
    return canModifyBooking(row)
  }

  function canEndBookingEarly(row) {
    if (row?.booking_mode !== 'electrochemical_workstation' || row?.status !== 'active') {
      return false
    }
    const nowMs = getBookingNowMs()
    const startMs = getBookingStartMs(row)
    const endMs = getBookingEndMs(row)
    return Number.isFinite(startMs) && Number.isFinite(endMs) && startMs < nowMs && nowMs < endMs
  }

  async function fetchMyBookings() {
    loading.myBookings = true
    try {
      const res = await apiClient.get('/equipment/bookings/mine/')
      myBookings.value = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      myBookings.value = []
    } finally {
      loading.myBookings = false
    }
  }

  function getBookingStatusLabel(row) {
    if (row?.booking_mode === 'xrd' && row?.xrd_test_ended) return '已结束测试'
    const nowMs = getBookingNowMs()
    const startMs = getBookingStartMs(row)
    const endMs = getBookingEndMs(row)
    if (startMs <= nowMs && nowMs < endMs) return '使用中'
    return '已预约'
  }

  function getBookingStatusType(row) {
    if (row?.booking_mode === 'xrd' && row?.xrd_test_ended) return 'info'
    return getBookingStatusLabel(row) === '使用中' ? 'warning' : 'success'
  }

  function getCancelBookingConfirmText(row) {
    const bookingIds = Array.isArray(row?.booking_ids) ? row.booking_ids : []
    if (bookingIds.length > 1) {
      return `确定取消该条预约下的 ${bookingIds.length} 个工位吗？`
    }
    return '确定取消该预约吗？'
  }

  async function refreshAfterBookingMutation() {
    try {
      if (typeof fetchMyBookings === 'function') {
        await fetchMyBookings()
      }
      if (typeof fetchCurrentAvailability === 'function') {
        await fetchCurrentAvailability()
      }
      if (isBallMillMode.value) {
        if (typeof fetchBallMillMonthSummary === 'function') {
          await fetchBallMillMonthSummary()
        }
        if (typeof fetchBallMillDayBookings === 'function') {
          await fetchBallMillDayBookings()
        }
      } else if (typeof fetchElectrochemicalMonthSummary === 'function') {
        await fetchElectrochemicalMonthSummary()
      }
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '刷新预约信息失败'))
    }
  }

  async function cancelBooking(row) {
    if (!canCancelBooking(row)) {
      ElMessage.warning('已开始或已过去的预约不能取消')
      return
    }

    const bookingIds = Array.isArray(row?.booking_ids) && row.booking_ids.length
      ? row.booking_ids
      : (row?.id ? [row.id] : [])
    if (!bookingIds.length) return

    const failed = []
    let successCount = 0

    for (const bookingId of bookingIds) {
      try {
        await cancelBookingApi(bookingId)
        successCount += 1
      } catch (error) {
        failed.push(extractApiErrorMessage(error, `ID ${bookingId} 取消失败`))
      }
    }

    if (successCount > 0 && failed.length === 0) {
      ElMessage.success(successCount > 1 ? `已取消 ${successCount} 条预约` : '已取消')
    } else if (successCount > 0 && failed.length > 0) {
      ElMessage.warning(`已取消 ${successCount} 条；${failed.join('；')}`)
    } else {
      ElMessage.error(failed[0] || '取消失败')
    }

    await refreshAfterBookingMutation()
  }

  async function endBookingEarly(row) {
    if (!canEndBookingEarly(row)) {
      ElMessage.warning('只能提前结束正在使用的输力强预约')
      return
    }

    try {
      await ElMessageBox.confirm(
        '确定提前结束该预约吗？结束后，后续可预约时段将被释放，且无法恢复。',
        '确认提前结束',
        {
          confirmButtonText: '确认结束',
          cancelButtonText: '取消',
          type: 'warning',
        },
      )
    } catch (error) {
      if (error === 'cancel' || error === 'close') return
      throw error
    }

    try {
      await endBookingEarlyApi(row.id)
      ElMessage.success('预约已提前结束')
      await refreshAfterBookingMutation()
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '提前结束预约失败'))
    }
  }

  async function forceDeleteBooking(row) {
    if (!canModifyBooking(row)) {
      ElMessage.warning('已开始或已过去的预约不能删除')
      return
    }

    const bookingIds = Array.isArray(row?.booking_ids) && row.booking_ids.length
      ? row.booking_ids
      : (row?.id ? [row.id] : [])
    if (!bookingIds.length) return

    const failed = []
    let successCount = 0

    for (const bookingId of bookingIds) {
      try {
        await deleteBookingApi(bookingId)
        successCount += 1
      } catch (error) {
        failed.push(extractApiErrorMessage(error, `ID ${bookingId} 删除失败`))
      }
    }

    if (successCount > 0 && failed.length === 0) {
      ElMessage.success(successCount > 1 ? `已删除 ${successCount} 条预约` : '已删除')
    } else if (successCount > 0 && failed.length > 0) {
      ElMessage.warning(`已删除 ${successCount} 条；${failed.join('；')}`)
    } else {
      ElMessage.error(failed[0] || '删除失败')
    }

    await refreshAfterBookingMutation()
  }

  function openHistoryDialog() {
    historyVisible.value = true
    fetchHistoryBookings()
  }

  function clearHistoryFilter() {
    historyDateRange.value = []
    fetchHistoryBookings()
  }

  async function fetchHistoryBookings() {
    loading.history = true
    try {
      const params = {}
      if (historyDateRange.value && historyDateRange.value.length === 2) {
        params.start_date = historyDateRange.value[0]
        params.end_date = historyDateRange.value[1]
      }
      const res = await apiClient.get('/equipment/bookings/history/', { params })
      historyBookings.value = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      historyBookings.value = []
    } finally {
      loading.history = false
    }
  }

  return {
    myBookingsDisplay,
    currentElectrochemicalChannelBookingsDisplay,
    formatBookingDate,
    formatBookingTime,
    formatBookingDetails,
    getBookingStartMs,
    getBookingEndMs,
    canModifyBooking,
    canCancelBooking,
    canEndBookingEarly,
    fetchMyBookings,
    getBookingStatusLabel,
    getBookingStatusType,
    getCancelBookingConfirmText,
    cancelBooking,
    endBookingEarly,
    forceDeleteBooking,
    openHistoryDialog,
    clearHistoryFilter,
    fetchHistoryBookings,
  }
}
