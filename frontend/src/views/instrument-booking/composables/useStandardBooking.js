import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '@/api'
import {
  connectXrdRemoteBooking,
  endXrdTestBooking,
  getEquipmentMonthSummary,
  getXrdTutorStats,
  setElectrochemicalChannelStatus,
  updateXrdTutorial,
} from '@/api/equipment'
import {
  extractApiErrorMessage,
  parseDateString,
  startOfDay,
  toLocalDateString,
} from '../helpers'

export function useStandardBooking(ctx) {
  const {
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
    selectedEquipment,
    myBookings,
    xrdTutorStatsVisible,
    xrdTutorStatsRows,
    xrdTutorStatsMonth,
    selectedXrdStudentStats,
    xrdTutorialVisible,
    xrdTutorialDraftHtml,
    loading,
    requestSeq,
    equipmentInfo,
    isElectrochemicalMode,
    isXrdMode,
    isSelectedElectrochemicalChannelOffline,
    canBookSelectedEquipment,
    canViewXrdTutorStats,
    isSystemAdmin,
    getEffectiveNow,
    todayStr,
  } = ctx

  const xrdRemoteNow = ref(Date.now())
  let xrdRemoteTimer = null
  let xrdRemoteRefreshing = false

  async function refreshXrdRemoteBookings() {
    if (!isXrdMode.value || !selectedEquipmentId.value || xrdRemoteRefreshing) return
    xrdRemoteRefreshing = true
    try {
      const res = await apiClient.get('/equipment/bookings/mine/')
      myBookings.value = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      // 保持静默，避免 XRD 远程状态轮询打断用户当前操作。
    } finally {
      xrdRemoteRefreshing = false
    }
  }

  onMounted(() => {
    xrdRemoteTimer = setInterval(() => {
      xrdRemoteNow.value = Date.now()
      refreshXrdRemoteBookings()
    }, 15000)
  })

  onUnmounted(() => {
    if (xrdRemoteTimer) {
      clearInterval(xrdRemoteTimer)
      xrdRemoteTimer = null
    }
  })

  function timeTextToMinutes(value) {
    const [hour, minute] = String(value || '').split(':').map((item) => Number(item || 0))
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) return null
    return hour * 60 + minute
  }

  const xrdSelectedDurationMinutes = computed(() => {
    const start = timeTextToMinutes(xrdForm.value.start_time)
    const end = timeTextToMinutes(xrdForm.value.end_time)
    if (start == null || end == null || end <= start) return 0
    return end - start
  })

  const xrdEffectiveDurationMinutes = computed(() => xrdSelectedDurationMinutes.value)

  function getBookingBoundaryMs(row, field) {
    const directValue = row?.[`${field}_at`]
    if (directValue) {
      const directMs = new Date(directValue).getTime()
      if (Number.isFinite(directMs)) return directMs
    }

    const date = row?.date
    const time = row?.[`${field}_time`]
    if (!date || !time) return NaN
    return new Date(`${date}T${String(time).slice(0, 5)}`).getTime()
  }

  const selectedXrdRemoteMachine = computed(() => {
    const apiEquipment = rawAvailable.value?.equipment || {}
    const selected = selectedEquipment.value || {}
    const id = apiEquipment.xrd_remote_machine ?? selected.xrd_remote_machine ?? null
    if (!id) return null
    return {
      id,
      name: apiEquipment.xrd_remote_machine_name || selected.xrd_remote_machine_name || '',
    }
  })

  const currentEquipmentXrdBookings = computed(() => {
    xrdRemoteNow.value
    if (!isXrdMode.value || !selectedEquipmentId.value) return []

    const nowMs = getEffectiveNow().getTime()
    const equipmentId = Number(selectedEquipmentId.value || 0)
    return (Array.isArray(myBookings.value) ? myBookings.value : [])
      .filter((row) => {
        if (row?.booking_mode !== 'xrd') return false
        if (Number(row?.equipment || 0) !== equipmentId) return false
        const endMs = getBookingBoundaryMs(row, 'end')
        return Number.isFinite(endMs) && nowMs < endMs
      })
      .sort((a, b) => getBookingBoundaryMs(a, 'start') - getBookingBoundaryMs(b, 'start'))
  })

  const activeXrdRemoteBooking = computed(() => {
    xrdRemoteNow.value
    const rows = currentEquipmentXrdBookings.value
    if (!rows.length) return null

    const serverAllowed = rows.find((row) => (
      row?.xrd_remote_connect_available === true &&
      !row?.xrd_test_ended
    ))
    if (serverAllowed) return serverAllowed

    const nowMs = getEffectiveNow().getTime()
    return rows.find((row) => {
      if (row?.xrd_remote_connect_available === false || row?.xrd_test_ended) return false
      const startMs = getBookingBoundaryMs(row, 'start')
      const endMs = getBookingBoundaryMs(row, 'end')
      return Number.isFinite(startMs) && Number.isFinite(endMs) && startMs <= nowMs && nowMs < endMs
    }) || null
  })

  const xrdRemoteConnectAvailable = computed(() =>
    Boolean(selectedXrdRemoteMachine.value && activeXrdRemoteBooking.value),
  )

  const xrdRemoteConnectDisabledReason = computed(() => {
    if (!selectedXrdRemoteMachine.value) return '该 XRD 尚未配置远程主机'
    if (!activeXrdRemoteBooking.value) {
      const nextBooking = currentEquipmentXrdBookings.value.find((row) => !row?.xrd_test_ended)
      return nextBooking?.xrd_remote_connect_disabled_reason || '仅在自己的 XRD 预约时段内可连接'
    }
    return ''
  })

  const xrdEndTestAvailable = computed(() =>
    Boolean(activeXrdRemoteBooking.value && !activeXrdRemoteBooking.value?.xrd_test_ended),
  )

  const xrdEndTestDisabledReason = computed(() => {
    if (activeXrdRemoteBooking.value?.xrd_test_ended) return '该 XRD 测试已结束'
    const nextBooking = currentEquipmentXrdBookings.value.find((row) => !row?.xrd_test_ended)
    if (nextBooking?.xrd_remote_connect_disabled_reason) {
      return nextBooking.xrd_remote_connect_disabled_reason
    }
    if (!activeXrdRemoteBooking.value) return '当前没有可结束的 XRD 测试'
    return ''
  })

  const xrdTutorialHtml = computed(() => {
    const apiEquipment = rawAvailable.value?.equipment || {}
    const selected = selectedEquipment.value || {}
    return (
      apiEquipment.xrd_tutorial_html ||
      selected.xrd_tutorial_html ||
      'The quick brown fox jumps over the lazy dog'
    )
  })

  const electrochemicalMonthSummaryMap = computed(() =>
    Object.fromEntries((electrochemicalMonthSummaryDays.value || []).map((item) => [item.date, item])),
  )

  const electrochemicalCalendarPanelMonthText = computed(() => {
    const [year, month] = (electrochemicalCalendarPanelMonth.value || todayStr.value.slice(0, 7)).split('-')
    return `${year} 年 ${Number(month)} 月`
  })

  function shiftMonth(monthStr, offset) {
    const [year, month] = monthStr.split('-').map(Number)
    const date = new Date(year, month - 1 + offset, 1)
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
  }

  function syncElectrochemicalCalendarValue(dateStr = selectedDate.value) {
    if (!dateStr) return
    const current = toLocalDateString(electrochemicalCalendarValue.value)
    if (current === dateStr) return
    electrochemicalCalendarValue.value = parseDateString(dateStr)
  }

  function getElectrochemicalCalendarDayMark(dayStr) {
    const summary = electrochemicalMonthSummaryMap.value[dayStr]
    return summary?.has_booking ? '已约' : ''
  }

  function electrochemicalCalendarDayClass(data) {
    const summary = electrochemicalMonthSummaryMap.value[data.day]
    const isPast = startOfDay(data.date).getTime() < startOfDay(getEffectiveNow()).getTime()
    return {
      'ball-mill-date-cell--booked': Boolean(summary?.has_booking),
      'ball-mill-date-cell--free': !summary?.has_booking,
      'ball-mill-date-cell--past': isPast,
      'ball-mill-date-cell--selected': data.isSelected,
      'ball-mill-date-cell--adjacent': data.type !== 'current-month',
      'ball-mill-date-cell--disabled': disabledDate(data.date),
    }
  }

  function sameSlot(a, b) {
    return a.start === b.start && a.end === b.end
  }

  function slotIndex(slot) {
    return slots.value.findIndex((item) => sameSlot(item, slot))
  }

  function isSelected(slot) {
    return selectedSlots.value.some((item) => sameSlot(item, slot))
  }

  function getSelectedSlotsSorted() {
    return selectedSlots.value
      .map((slot) => ({ slot, idx: slotIndex(slot) }))
      .filter((item) => item.idx >= 0)
      .sort((a, b) => a.idx - b.idx)
      .map((item) => item.slot)
  }

  const isSelectedDateToday = computed(() => selectedDate.value === todayStr.value)

  const isSelectedDatePast = computed(() => {
    if (!selectedDate.value) return false
    const sel = new Date(selectedDate.value)
    const today = getEffectiveNow()
    const selDate = new Date(sel.getFullYear(), sel.getMonth(), sel.getDate())
    const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate())
    return selDate < todayDate
  })

  function isPastSlotForSelectedDate(slot) {
    if (!selectedDate.value) return false
    if (isSelectedDatePast.value) return true
    if (!isSelectedDateToday.value) return false

    const now = getEffectiveNow()
    const nowMinutes = now.getHours() * 60 + now.getMinutes()
    const [hour, minute] = String(slot.end || '0:0').split(':').map((value) => Number(value || 0))
    const slotEndMinutes = hour * 60 + minute
    return slotEndMinutes <= nowMinutes
  }

  function isSlotDisabled(slot) {
    return isSelectedElectrochemicalChannelOffline.value || slot.occupied || isPastSlotForSelectedDate(slot)
  }

  function buttonType(slot) {
    if (isElectrochemicalMode.value && isSelectedElectrochemicalChannelOffline.value) return 'info'
    if (slot.occupied) return 'danger'
    if (isSelected(slot)) return 'primary'
    return 'default'
  }

  function disabledDate(date) {
    if (!date) return false
    const d = new Date(date)
    const today = getEffectiveNow()
    d.setHours(0, 0, 0, 0)
    today.setHours(0, 0, 0, 0)

    const maxAdvance = equipmentInfo.value?.maxAdvance
    if (typeof maxAdvance === 'number') {
      const last = new Date(today)
      last.setDate(last.getDate() + maxAdvance)
      if (d > last) return true
    }
    return false
  }

  function getSelectedRangeBounds() {
    if (!selectedSlots.value.length) return null
    const indexes = selectedSlots.value
      .map((slot) => slotIndex(slot))
      .filter((idx) => idx >= 0)
      .sort((a, b) => a - b)

    if (!indexes.length) return null

    return {
      start: indexes[0],
      end: indexes[indexes.length - 1],
      set: new Set(indexes),
    }
  }

  function buildSelectableRange(startIndex, endIndex) {
    const from = Math.min(startIndex, endIndex)
    const to = Math.max(startIndex, endIndex)
    const range = slots.value.slice(from, to + 1)
    if (!range.length) return null
    if (range.some((slot) => isSlotDisabled(slot))) {
      return null
    }
    return range
  }

  function syncXrdSelectedWindow() {
    const sortedSlots = getSelectedSlotsSorted()
    if (!sortedSlots.length) {
      xrdForm.value.start_time = ''
      xrdForm.value.end_time = ''
      return
    }
    xrdForm.value.start_time = sortedSlots[0].start
    xrdForm.value.end_time = sortedSlots[sortedSlots.length - 1].end
  }

  function selectXrdSlot(slot) {
    if (!isXrdMode.value || isSlotDisabled(slot)) return

    const clickedIndex = slotIndex(slot)
    if (clickedIndex < 0) return

    const rangeBounds = getSelectedRangeBounds()
    if (!rangeBounds) {
      selectedSlots.value = [slots.value[clickedIndex]]
      syncXrdSelectedWindow()
      return
    }

    const { start, end, set } = rangeBounds

    if (set.has(clickedIndex)) {
      const nextSlots = clickedIndex <= start
        ? []
        : slots.value.slice(start, clickedIndex)
      selectedSlots.value = nextSlots
      syncXrdSelectedWindow()
      return
    }

    const targetStart = clickedIndex < start ? clickedIndex : start
    const targetEnd = clickedIndex > end ? clickedIndex : end
    const nextRange = buildSelectableRange(targetStart, targetEnd)

    if (!nextRange) {
      ElMessage.warning('所选范围包含不可预约时段，请重新选择连续可预约时段')
      return
    }

    selectedSlots.value = nextRange
    syncXrdSelectedWindow()
  }

  function toggleSlot(slot) {
    if (isSlotDisabled(slot)) return

    const clickedIndex = slotIndex(slot)
    if (clickedIndex < 0) return

    const rangeBounds = getSelectedRangeBounds()
    if (!rangeBounds) {
      selectedSlots.value = [slots.value[clickedIndex]]
      return
    }

    const { start, end, set } = rangeBounds

    if (set.has(clickedIndex)) {
      selectedSlots.value = []
      return
    }

    const targetStart = clickedIndex < start ? clickedIndex : start
    const targetEnd = clickedIndex > end ? clickedIndex : end
    const nextRange = buildSelectableRange(targetStart, targetEnd)

    if (!nextRange) {
      ElMessage.warning('所选范围包含不可预约时段，请重新选择连续可预约时段')
      return
    }

    selectedSlots.value = nextRange
  }

  async function fetchStandardAvailability() {
    if (!selectedEquipmentId.value || !selectedDate.value) return
    const equipmentId = selectedEquipmentId.value
    const requestSeqNo = ++requestSeq.standardAvailability
    loading.available = true
    selectedSlots.value = []
    try {
      const params = { date: selectedDate.value, _t: Date.now() }
      if (isElectrochemicalMode.value) {
        params.channel_no = Number(selectedElectrochemicalChannelNo.value || 1)
      }
      const res = await apiClient.get(`/equipment/equipments/${equipmentId}/available/`, { params })
      if (requestSeqNo !== requestSeq.standardAvailability || equipmentId !== selectedEquipmentId.value) return
      rawAvailable.value = res.data || {}
      slots.value = Array.isArray(res.data?.slots) ? res.data.slots : []
      if (isXrdMode.value) {
        xrdForm.value.start_time = ''
        xrdForm.value.end_time = ''
      }

      if (isElectrochemicalMode.value) {
        const channelRows = Array.isArray(res.data?.channels)
          ? res.data.channels
          : Array.from({ length: Number(equipmentInfo.value?.electrochemicalChannelCount || 8) }, (_, idx) => ({
              channel_no: idx + 1,
              name: `通道${idx + 1}`,
              offline: false,
            }))
        electrochemicalChannels.value = channelRows
        const fromApi = Number(res.data?.selected_channel_no || selectedElectrochemicalChannelNo.value || 1)
        selectedElectrochemicalChannelNo.value = Number.isFinite(fromApi) ? fromApi : 1
      } else {
        electrochemicalChannels.value = []
        selectedElectrochemicalChannelNo.value = 1
      }
    } catch (error) {
      if (requestSeqNo !== requestSeq.standardAvailability || equipmentId !== selectedEquipmentId.value) return
      slots.value = []
      if (isElectrochemicalMode.value) {
        electrochemicalChannels.value = []
      }
      ElMessage.error(extractApiErrorMessage(error, '获取可预约时段失败'))
    } finally {
      if (requestSeqNo === requestSeq.standardAvailability) {
        loading.available = false
      }
    }
  }

  async function fetchElectrochemicalMonthSummary(monthStr = electrochemicalCalendarPanelMonth.value) {
    if (!selectedEquipmentId.value || !monthStr || (!isElectrochemicalMode.value && !isXrdMode.value)) return
    const equipmentId = selectedEquipmentId.value
    const channelNo = Number(selectedElectrochemicalChannelNo.value || 1)
    const requestSeqNo = ++requestSeq.electrochemicalMonthSummary
    loading.monthSummary = true
    electrochemicalMonthSummaryDays.value = []
    try {
      const params = isElectrochemicalMode.value ? { channel_no: channelNo } : {}
      const { data } = await getEquipmentMonthSummary(equipmentId, monthStr, params)
      if (
        requestSeqNo !== requestSeq.electrochemicalMonthSummary ||
        equipmentId !== selectedEquipmentId.value ||
        channelNo !== Number(selectedElectrochemicalChannelNo.value || 1)
      ) return
      electrochemicalMonthSummaryDays.value = Array.isArray(data?.days) ? data.days : []
    } catch (error) {
      if (
        requestSeqNo !== requestSeq.electrochemicalMonthSummary ||
        equipmentId !== selectedEquipmentId.value ||
        channelNo !== Number(selectedElectrochemicalChannelNo.value || 1)
      ) return
      electrochemicalMonthSummaryDays.value = []
      ElMessage.error(extractApiErrorMessage(error, '获取日历概览失败'))
    } finally {
      if (requestSeqNo === requestSeq.electrochemicalMonthSummary) {
        loading.monthSummary = false
      }
    }
  }

  async function changeElectrochemicalCalendarMonth(offset) {
    const targetMonth = shiftMonth(electrochemicalCalendarPanelMonth.value, offset)
    electrochemicalCalendarPanelMonth.value = targetMonth
    electrochemicalCalendarSwitchingMonth.value = true
    electrochemicalCalendarValue.value = new Date(`${targetMonth}-01T12:00:00`)
    await nextTick()
    electrochemicalCalendarSwitchingMonth.value = false
    await fetchElectrochemicalMonthSummary(targetMonth)
  }

  async function handleElectrochemicalCalendarChange(nextValue) {
    if (!nextValue) return
    if (electrochemicalCalendarSwitchingMonth.value) {
      electrochemicalCalendarPanelMonth.value = toLocalDateString(nextValue).slice(0, 7)
      return
    }

    if (disabledDate(nextValue)) {
      syncElectrochemicalCalendarValue(selectedDate.value)
      return
    }

    const nextDate = toLocalDateString(nextValue)
    const previousMonth = selectedDate.value.slice(0, 7)
    selectedDate.value = nextDate
    electrochemicalCalendarPanelMonth.value = nextDate.slice(0, 7)
    syncElectrochemicalCalendarValue(nextDate)
    await fetchStandardAvailability()
    if (nextDate.slice(0, 7) !== previousMonth) {
      await fetchElectrochemicalMonthSummary(nextDate.slice(0, 7))
    }
  }

  async function handleElectrochemicalChannelChange() {
    if (!isElectrochemicalMode.value) return
    await fetchStandardAvailability()
    await fetchElectrochemicalMonthSummary()
  }

  async function toggleElectrochemicalChannelStatus() {
    if (!selectedEquipmentId.value || !isElectrochemicalMode.value) return
    const channelNo = Number(selectedElectrochemicalChannelNo.value || 0)
    if (!channelNo) return

    loading.channelToggle = true
    try {
      const targetOffline = !isSelectedElectrochemicalChannelOffline.value
      const { data } = await setElectrochemicalChannelStatus(
        selectedEquipmentId.value,
        channelNo,
        targetOffline,
      )
      const channelRows = Array.isArray(data?.channels) ? data.channels : []
      if (channelRows.length) {
        electrochemicalChannels.value = channelRows
      }
      ElMessage.success(targetOffline ? `通道 ${channelNo} 已下线` : `通道 ${channelNo} 已上线`)
      await fetchStandardAvailability()
      await fetchElectrochemicalMonthSummary()
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '通道状态更新失败'))
    } finally {
      loading.channelToggle = false
    }
  }

  async function loadXrdTutorStats() {
    if (!selectedEquipmentId.value || !isXrdMode.value || !canViewXrdTutorStats.value) return
    loading.xrdTutorStats = true
    try {
      const { data } = await getXrdTutorStats(selectedEquipmentId.value, {
        month: xrdTutorStatsMonth.value,
      })
      xrdTutorStatsRows.value = Array.isArray(data?.rows) ? data.rows : []
    } catch (error) {
      xrdTutorStatsRows.value = []
      ElMessage.error(extractApiErrorMessage(error, '加载 XRD 导师统计失败'))
    } finally {
      loading.xrdTutorStats = false
    }
  }

  async function openXrdTutorStats() {
    if (!selectedEquipmentId.value || !isXrdMode.value || !canViewXrdTutorStats.value) return
    selectedXrdStudentStats.value = null
    xrdTutorStatsVisible.value = true
    await loadXrdTutorStats()
  }

  function openXrdStudentStats(student) {
    selectedXrdStudentStats.value = student || null
  }

  function closeXrdStudentStats() {
    selectedXrdStudentStats.value = null
  }

  function openXrdTutorial() {
    if (!isXrdMode.value) return
    xrdTutorialDraftHtml.value = xrdTutorialHtml.value
    xrdTutorialVisible.value = true
  }

  async function saveXrdTutorial() {
    if (!selectedEquipmentId.value || !isXrdMode.value || !isSystemAdmin.value) return
    loading.xrdTutorialSaving = true
    try {
      const { data } = await updateXrdTutorial(selectedEquipmentId.value, xrdTutorialDraftHtml.value)
      const nextHtml = data?.xrd_tutorial_html || ''
      if (rawAvailable.value?.equipment) {
        rawAvailable.value.equipment.xrd_tutorial_html = nextHtml
      }
      if (selectedEquipment.value) {
        selectedEquipment.value.xrd_tutorial_html = nextHtml
      }
      xrdTutorialDraftHtml.value = nextHtml
      ElMessage.success('XRD 使用教程已更新')
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '保存 XRD 使用教程失败'))
    } finally {
      loading.xrdTutorialSaving = false
    }
  }

  async function bookXrd() {
    if (!selectedEquipmentId.value || !isXrdMode.value) return
    if (!canBookSelectedEquipment.value) {
      ElMessage.warning('你不在该设备的可预约用户范围内')
      return
    }
    if (!xrdForm.value.start_time || !xrdForm.value.end_time) {
      ElMessage.warning('请选择预约占用时段')
      return
    }
    const duration = Number(xrdEffectiveDurationMinutes.value || 0)
    if (duration <= 0 || !Number.isInteger(duration)) {
      ElMessage.warning('请选择有效的预约占用时段')
      return
    }

    const payload = {
      date: selectedDate.value,
      start_time: xrdForm.value.start_time,
      end_time: xrdForm.value.end_time,
      remark: xrdForm.value.remark || '',
    }

    loading.booking = true
    try {
      await apiClient.post(`/equipment/equipments/${selectedEquipmentId.value}/book/`, payload)
      ElMessage.success('预约成功')
      await fetchStandardAvailability()
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '预约失败'))
    } finally {
      loading.booking = false
    }
  }

  async function connectXrdRemote() {
    const booking = activeXrdRemoteBooking.value
    if (!selectedXrdRemoteMachine.value) {
      ElMessage.warning('该 XRD 尚未配置远程主机')
      return
    }
    if (!booking?.id) {
      ElMessage.warning('仅在自己的 XRD 预约时段内可连接')
      return
    }

    const remoteWindow = window.open('about:blank', '_blank')
    if (remoteWindow) {
      remoteWindow.opener = null
      remoteWindow.document.title = '正在准备远程连接'
      remoteWindow.document.body.innerHTML = '<p style="font-family: sans-serif; padding: 24px;">正在准备远程连接...</p>'
    }

    loading.xrdRemoteConnect = true
    try {
      const { data } = await connectXrdRemoteBooking(booking.id)
      const url = data?.connection_url
      if (!url) {
        remoteWindow?.close()
        ElMessage.error('远程连接地址为空')
        return
      }
      if (data?.xrd_shutdown_notice_required) {
        try {
          await ElMessageBox.alert('请注意关闭软件和仪器', '提示', {
            type: 'warning',
            confirmButtonText: '我知道了',
          })
        } catch {
          // 提示关闭不应阻断远程连接。
        }
      }
      if (remoteWindow) {
        remoteWindow.location.href = url
      } else {
        window.open(url, '_blank', 'noopener')
      }
    } catch (error) {
      remoteWindow?.close()
      ElMessage.error(extractApiErrorMessage(error, '远程连接失败'))
    } finally {
      loading.xrdRemoteConnect = false
    }
  }

  async function endXrdTest() {
    const booking = activeXrdRemoteBooking.value
    if (!booking?.id) {
      ElMessage.warning('当前没有可结束的 XRD 测试')
      return
    }

    try {
      await ElMessageBox.confirm(
        '点击此按钮代表当前测试已结束，下一个预约者可以提前开始测试，请确保所有数据已经保存和拷贝。如果你的测试尚未结束，请点击取消',
        '确认结束测试',
        {
          type: 'warning',
          confirmButtonText: '确认结束测试',
          cancelButtonText: '取消',
        },
      )
    } catch {
      return
    }

    loading.xrdEndTest = true
    try {
      await endXrdTestBooking(booking.id)
      ElMessage.success('已结束测试')
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '结束测试失败'))
    } finally {
      loading.xrdEndTest = false
    }
  }

  async function bookSelected() {
    if (!selectedEquipmentId.value || selectedSlots.value.length === 0) return
    if (!canBookSelectedEquipment.value) {
      ElMessage.warning('你不在该设备的可预约用户范围内')
      return
    }

    const sortedSlots = getSelectedSlotsSorted()
    if (!sortedSlots.length) return
    const firstSlot = sortedSlots[0]
    const lastSlot = sortedSlots[sortedSlots.length - 1]

    loading.booking = true
    try {
      const payload = {
        date: selectedDate.value,
        start_time: firstSlot.start,
        end_time: lastSlot.end,
      }
      if (isElectrochemicalMode.value) {
        payload.position_no = Number(selectedElectrochemicalChannelNo.value || 0)
      }
      await apiClient.post(`/equipment/equipments/${selectedEquipmentId.value}/book/`, payload)
      ElMessage.success('预约成功')
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '预约失败'))
    } finally {
      loading.booking = false
      selectedSlots.value = []
    }
  }

  return {
    sameSlot,
    isSelected,
    isSelectedDateToday,
    isSelectedDatePast,
    isPastSlotForSelectedDate,
    isSlotDisabled,
    buttonType,
    disabledDate,
    xrdSelectedDurationMinutes,
    xrdEffectiveDurationMinutes,
    selectedXrdRemoteMachine,
    activeXrdRemoteBooking,
    xrdRemoteConnectAvailable,
    xrdRemoteConnectDisabledReason,
    xrdEndTestAvailable,
    xrdEndTestDisabledReason,
    xrdTutorialHtml,
    electrochemicalMonthSummaryMap,
    electrochemicalCalendarPanelMonthText,
    syncElectrochemicalCalendarValue,
    getElectrochemicalCalendarDayMark,
    electrochemicalCalendarDayClass,
    fetchElectrochemicalMonthSummary,
    changeElectrochemicalCalendarMonth,
    handleElectrochemicalCalendarChange,
    toggleSlot,
    selectXrdSlot,
    fetchStandardAvailability,
    handleElectrochemicalChannelChange,
    toggleElectrochemicalChannelStatus,
    loadXrdTutorStats,
    openXrdTutorStats,
    openXrdStudentStats,
    closeXrdStudentStats,
    openXrdTutorial,
    saveXrdTutorial,
    bookSelected,
    bookXrd,
    connectXrdRemote,
    endXrdTest,
  }
}
