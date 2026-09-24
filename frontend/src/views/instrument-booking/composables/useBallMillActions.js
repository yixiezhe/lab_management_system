import { nextTick, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import apiClient from '@/api'
import {
  clearBallMillQueueAndBookings,
  createBallMillQueueRequest,
  deleteBallMillQueueRequest,
  dispatchBallMillQueue,
  cancelBallMillQueueRequest,
  getEquipmentCalendar,
  getEquipmentMonthSummary,
  listBallMillQueueRequests,
} from '@/api/equipment'
import { extractApiErrorMessage, toLocalDateString } from '../helpers'

const QUEUE_AUTO_REFRESH_INTERVAL_MS = 30000

export function useBallMillActions(ctx, logic, displays, deps) {
  const {
    selectedEquipmentId,
    selectedDate,
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
    rawAvailable,
    loading,
    requestSeq,
    isBallMillMode,
    isBallMillQueueMode,
    isSystemAdmin,
    canBookSelectedEquipment,
    equipmentInfo,
  } = ctx

  const {
    ballMillEffectiveMaxMillingMinutes,
    ballMillRotationSpeedMin,
    ballMillRotationSpeedMax,
    getBallMillRotationSpeedValidationMessage,
    shouldQueueForBallMillStart,
    isQueueWindowForAction,
    isSelectedDateInQueueApplyRange,
    canSubmitBallMillQueueForDate,
    queueSubmitDisabledText,
    shiftMonth,
    syncBallMillCalendarValue,
  } = logic

  const {
    shouldShowQueueDispatchPreview,
  } = displays

  const {
    fetchMyBookings,
  } = deps

  let queueAutoRefreshTimer = null

  function resetBallMillSelection() {
    selectedBallMillStartTime.value = ''
    selectedBallMillPositionNos.value = []
  }

  function clearQueueDispatchPreview() {
    ballMillQueueDispatchPreviewRows.value = []
    ballMillQueueDispatchPreviewMeta.value = {}
  }

  async function fetchBallMillMonthSummary(monthStr = ballMillCalendarPanelMonth.value) {
    if (!selectedEquipmentId.value || !monthStr) return
    const equipmentId = selectedEquipmentId.value
    const requestSeqNo = ++requestSeq.ballMillMonthSummary
    loading.monthSummary = true
    try {
      const { data } = await getEquipmentMonthSummary(equipmentId, monthStr)
      if (requestSeqNo !== requestSeq.ballMillMonthSummary || equipmentId !== selectedEquipmentId.value) return
      ballMillMonthSummaryDays.value = Array.isArray(data?.days) ? data.days : []
    } catch (error) {
      if (requestSeqNo !== requestSeq.ballMillMonthSummary || equipmentId !== selectedEquipmentId.value) return
      ballMillMonthSummaryDays.value = []
      ElMessage.error(extractApiErrorMessage(error, '获取日历概览失败'))
    } finally {
      if (requestSeqNo === requestSeq.ballMillMonthSummary) {
        loading.monthSummary = false
      }
    }
  }

  async function fetchBallMillDayBookings(dateStr = selectedDate.value) {
    if (!selectedEquipmentId.value || !dateStr) return
    const equipmentId = selectedEquipmentId.value
    const requestSeqNo = ++requestSeq.ballMillDayBookings
    loading.dayBookings = true
    try {
      const { data } = await getEquipmentCalendar(equipmentId, dateStr)
      if (
        requestSeqNo !== requestSeq.ballMillDayBookings ||
        equipmentId !== selectedEquipmentId.value ||
        dateStr !== selectedDate.value
      ) return
      ballMillDayBookings.value = Array.isArray(data) ? data : []
    } catch (error) {
      if (
        requestSeqNo !== requestSeq.ballMillDayBookings ||
        equipmentId !== selectedEquipmentId.value ||
        dateStr !== selectedDate.value
      ) return
      ballMillDayBookings.value = []
      ElMessage.error(extractApiErrorMessage(error, '获取当日预约详情失败'))
    } finally {
      if (requestSeqNo === requestSeq.ballMillDayBookings) {
        loading.dayBookings = false
      }
    }
  }

  async function fetchBallMillQueueRequests() {
    if (!selectedEquipmentId.value || !isBallMillMode.value) return
    if (!equipmentInfo.value?.ballMillQueueEnabled) {
      ballMillQueueRequests.value = []
      return
    }
    const equipmentId = selectedEquipmentId.value
    const requestSeqNo = ++requestSeq.ballMillQueueRequests
    loading.queue = true
    try {
      const { data } = await listBallMillQueueRequests(equipmentId, { all: 1 })
      if (requestSeqNo !== requestSeq.ballMillQueueRequests || equipmentId !== selectedEquipmentId.value) return
      ballMillQueueRequests.value = Array.isArray(data)
        ? data.filter((item) => item?.status !== 'cancelled')
        : []
    } catch (error) {
      if (requestSeqNo !== requestSeq.ballMillQueueRequests || equipmentId !== selectedEquipmentId.value) return
      ballMillQueueRequests.value = []
      ElMessage.error(extractApiErrorMessage(error, '获取排队申请失败'))
    } finally {
      if (requestSeqNo === requestSeq.ballMillQueueRequests) {
        loading.queue = false
      }
    }
  }

  async function fetchBallMillQueueDispatchPreview(options = {}) {
    const { silent = false } = options
    if (!selectedEquipmentId.value || !isBallMillQueueMode.value) return
    if (!shouldShowQueueDispatchPreview.value) {
      clearQueueDispatchPreview()
      return
    }

    const equipmentId = selectedEquipmentId.value
    const requestSeqNo = ++requestSeq.ballMillQueuePreview
    loading.queuePreview = true
    try {
      const { data } = await dispatchBallMillQueue(equipmentId, {
        force: true,
        preview: true,
      })
      if (requestSeqNo !== requestSeq.ballMillQueuePreview || equipmentId !== selectedEquipmentId.value) return
      ballMillQueueDispatchPreviewRows.value = Array.isArray(data?.results) ? data.results : []
      ballMillQueueDispatchPreviewMeta.value = {
        pending_count: Number(data?.pending_count || 0),
        allocated_count: Number(data?.allocated_count || 0),
        skipped_count: Number(data?.skipped_count || 0),
        detail: data?.detail || '',
        dispatch_window_start_date: data?.dispatch_window_start_date || '',
        dispatch_window_end_date: data?.dispatch_window_end_date || '',
      }
    } catch (error) {
      if (requestSeqNo !== requestSeq.ballMillQueuePreview || equipmentId !== selectedEquipmentId.value) return
      clearQueueDispatchPreview()
      if (!silent) {
        ElMessage.error(extractApiErrorMessage(error, '获取理论放榜预览失败'))
      }
    } finally {
      if (requestSeqNo === requestSeq.ballMillQueuePreview) {
        loading.queuePreview = false
      }
    }
  }

  async function fetchBallMillAvailability(options = {}) {
    if (!selectedEquipmentId.value || !selectedDate.value) return
    const { forcePreview = false } = options
    const equipmentId = selectedEquipmentId.value
    const currentDate = selectedDate.value
    const requestSeqNo = ++requestSeq.ballMillAvailability
    loading.available = true
    try {
      const normalizedMillingMinutes = Number(ballMillForm.value.milling_minutes || 0)
      const basePreviewMillingMinutes = Number(equipmentInfo.value?.ballMillCycleRunMinutes || 12)
      const queryMillingMinutes = (!forcePreview && selectedBallMillStartTime.value)
        ? normalizedMillingMinutes
        : Math.min(normalizedMillingMinutes || basePreviewMillingMinutes, basePreviewMillingMinutes)

      const params = { date: currentDate, _t: Date.now() }
      if (queryMillingMinutes > 0) {
        params.milling_minutes = queryMillingMinutes
      }
      if (
        ballMillForm.value.rotation_speed_rpm &&
        !getBallMillRotationSpeedValidationMessage(ballMillForm.value.rotation_speed_rpm)
      ) {
        params.rotation_speed_rpm = ballMillForm.value.rotation_speed_rpm
      }

      const res = await apiClient.get(`/equipment/equipments/${equipmentId}/available/`, { params })
      if (
        requestSeqNo !== requestSeq.ballMillAvailability ||
        equipmentId !== selectedEquipmentId.value ||
        currentDate !== selectedDate.value
      ) return

      rawAvailable.value = res.data || {}
      ballMillHourWindows.value = Array.isArray(res.data?.hour_windows) ? res.data.hour_windows : []

      if (selectedBallMillStartTime.value) {
        const selectedWindow = ballMillHourWindows.value.find(
          (window) => window.start === selectedBallMillStartTime.value,
        )
        if (!selectedWindow) {
          resetBallMillSelection()
        } else if (isQueueWindowForAction(selectedWindow.start)) {
          resetBallMillSelection()
        } else {
          selectedBallMillPositionNos.value = selectedBallMillPositionNos.value.filter((positionNo) =>
            selectedWindow.positions?.some(
              (position) => position.position_no === positionNo && Boolean(position.allowed),
            ),
          )
          if (!selectedBallMillPositionNos.value.length) {
            selectedBallMillStartTime.value = ''
          }
        }
      }
    } catch (error) {
      if (requestSeqNo !== requestSeq.ballMillAvailability) return
      ballMillHourWindows.value = []
      resetBallMillSelection()
      ElMessage.error(extractApiErrorMessage(error, '获取球磨机可预约信息失败'))
    } finally {
      if (requestSeqNo === requestSeq.ballMillAvailability) {
        loading.available = false
      }
    }
  }

  async function refreshQueueDynamicState() {
    if (!isBallMillQueueMode.value || !selectedEquipmentId.value || !selectedDate.value) return
    if (loading.booking) return
    if (!loading.queue) await fetchBallMillQueueRequests()
    if (!loading.available) await fetchBallMillAvailability()
    if (!loading.queuePreview) await fetchBallMillQueueDispatchPreview({ silent: true })
  }

  function stopQueueAutoRefresh() {
    if (queueAutoRefreshTimer) {
      clearInterval(queueAutoRefreshTimer)
      queueAutoRefreshTimer = null
    }
  }

  function startQueueAutoRefresh() {
    stopQueueAutoRefresh()
    queueAutoRefreshTimer = setInterval(async () => {
      await refreshQueueDynamicState()
    }, QUEUE_AUTO_REFRESH_INTERVAL_MS)
  }

  async function changeBallMillCalendarMonth(offset) {
    const targetMonth = shiftMonth(ballMillCalendarPanelMonth.value, offset)
    ballMillCalendarPanelMonth.value = targetMonth
    ballMillCalendarSwitchingMonth.value = true
    ballMillCalendarValue.value = new Date(`${targetMonth}-01T12:00:00`)
    await nextTick()
    ballMillCalendarSwitchingMonth.value = false
    await fetchBallMillMonthSummary(targetMonth)
  }

  async function handleBallMillCalendarChange(nextValue) {
    if (!nextValue) return
    if (ballMillCalendarSwitchingMonth.value) {
      ballMillCalendarPanelMonth.value = toLocalDateString(nextValue).slice(0, 7)
      return
    }

    const nextDate = toLocalDateString(nextValue)
    const previousMonth = selectedDate.value.slice(0, 7)
    selectedDate.value = nextDate
    ballMillCalendarPanelMonth.value = nextDate.slice(0, 7)
    resetBallMillSelection()
    syncBallMillCalendarValue(nextDate)
    await fetchBallMillAvailability()
    await fetchBallMillDayBookings(nextDate)
    await fetchBallMillQueueRequests()
    await fetchBallMillQueueDispatchPreview({ silent: true })
    if (nextDate.slice(0, 7) !== previousMonth) {
      await fetchBallMillMonthSummary(nextDate.slice(0, 7))
    }
  }

  function selectBallMillPosition(window, position) {
    if (!logic.isBallMillPositionSelectable(window, position)) return
    if (selectedBallMillStartTime.value !== window.start) {
      selectedBallMillStartTime.value = window.start
      selectedBallMillPositionNos.value = [position.position_no]
      return
    }

    if (selectedBallMillPositionNos.value.includes(position.position_no)) {
      selectedBallMillPositionNos.value = selectedBallMillPositionNos.value.filter(
        (positionNo) => positionNo !== position.position_no,
      )
      if (!selectedBallMillPositionNos.value.length) {
        selectedBallMillStartTime.value = ''
      }
      return
    }

    selectedBallMillPositionNos.value = [
      ...selectedBallMillPositionNos.value,
      position.position_no,
    ].sort((a, b) => a - b)
  }

  async function submitBallMillQueueForDate() {
    if (!selectedEquipmentId.value) return
    if (!canBookSelectedEquipment.value) {
      ElMessage.warning('你不在该设备的可预约用户范围内')
      return
    }
    if (!isSelectedDateInQueueApplyRange.value) {
      ElMessage.warning('仅支持当前排队申请周的日期提交排队申请')
      return
    }
    if (!canSubmitBallMillQueueForDate.value) {
      ElMessage.warning(queueSubmitDisabledText.value)
      return
    }
    loading.booking = true
    try {
      const { data } = await createBallMillQueueRequest(selectedEquipmentId.value, {
        target_date: selectedDate.value,
        position_count: Number(ballMillForm.value.queue_position_count),
        operation_type: ballMillForm.value.operation_type,
        rotation_speed_rpm: Number(ballMillForm.value.rotation_speed_rpm),
        milling_minutes: Number(ballMillForm.value.milling_minutes),
        remark: ballMillForm.value.remark || '',
      })
      const rank = Number(data?.queue_rank || 0)
      ElMessage.success(rank > 0 ? `排队申请已提交，当前预计排位第 ${rank}。` : '排队申请已提交，等待放榜分配。')
      resetBallMillSelection()
      await fetchBallMillAvailability({ forcePreview: true })
      await fetchBallMillQueueRequests()
      await fetchBallMillQueueDispatchPreview({ silent: true })
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '提交排队申请失败'))
    } finally {
      loading.booking = false
    }
  }

  async function dispatchQueueNow() {
    if (!selectedEquipmentId.value || !isBallMillQueueMode.value) return
    loading.queue = true
    try {
      const { data } = await dispatchBallMillQueue(selectedEquipmentId.value, { force: true })
      if (data?.executed) {
        ElMessage.success(
          `放榜完成：待分配 ${Number(data?.pending_count || 0)}，` +
          `已分配 ${Number(data?.allocated_count || 0)}，` +
          `顺延 ${Number(data?.rolled_over_count || 0)}，` +
          `未分配 ${Number(data?.skipped_count || 0)}`,
        )
      } else {
        ElMessage.warning(data?.detail || '当前条件下未执行放榜。')
      }
      await fetchBallMillAvailability({ forcePreview: true })
      await fetchBallMillQueueRequests()
      await fetchBallMillQueueDispatchPreview({ silent: true })
      await fetchBallMillDayBookings()
      await fetchMyBookings()
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '触发放榜失败'))
    } finally {
      loading.queue = false
    }
  }

  async function clearAllBallMillData() {
    if (!selectedEquipmentId.value || !isBallMillMode.value || !isSystemAdmin.value) return
    try {
      await ElMessageBox.confirm(
        '确定一键清除当前球磨机的全部排队和预约记录吗？该操作不可恢复。',
        '确认清空',
        {
          confirmButtonText: '确认清空',
          cancelButtonText: '取消',
          type: 'warning',
        },
      )
    } catch (error) {
      if (error === 'cancel' || error === 'close') return
      ElMessage.error(extractApiErrorMessage(error, '操作已中断'))
      return
    }

    loading.clearingAll = true
    try {
      const { data } = await clearBallMillQueueAndBookings(selectedEquipmentId.value)
      ElMessage.success(`已清空：排队 ${Number(data?.deleted_queue_requests || 0)} 条，预约 ${Number(data?.deleted_bookings || 0)} 条`)
      resetBallMillSelection()
      await fetchBallMillAvailability({ forcePreview: true })
      await fetchBallMillQueueRequests()
      await fetchBallMillQueueDispatchPreview({ silent: true })
      await fetchBallMillDayBookings()
      await fetchBallMillMonthSummary()
      await fetchMyBookings()
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '一键清空失败'))
    } finally {
      loading.clearingAll = false
    }
  }

  async function bookBallMill(startTime = selectedBallMillStartTime.value) {
    if (!startTime || !selectedBallMillPositionNos.value.length) return
    if (!canBookSelectedEquipment.value) {
      ElMessage.warning('你不在该设备的可预约用户范围内')
      return
    }
    if (shouldQueueForBallMillStart(startTime)) {
      ElMessage.warning('该时段属于排队申请窗口，请使用上方“提交总排队申请”。')
      return
    }
    loading.booking = true
    try {
      const positionNos = [...selectedBallMillPositionNos.value]
      const failedPositions = []
      let successCount = 0

      for (const positionNo of positionNos) {
        try {
          await apiClient.post(`/equipment/equipments/${selectedEquipmentId.value}/book/`, {
            date: selectedDate.value,
            start_time: startTime,
            position_no: positionNo,
            operation_type: ballMillForm.value.operation_type,
            rotation_speed_rpm: Number(ballMillForm.value.rotation_speed_rpm),
            milling_minutes: Number(ballMillForm.value.milling_minutes),
            remark: ballMillForm.value.remark || '',
          })
          successCount += 1
        } catch (error) {
          failedPositions.push({ positionNo, message: extractApiErrorMessage(error, '预约失败') })
        }
      }

      if (successCount && !failedPositions.length) {
        ElMessage.success(`预约成功，共 ${successCount} 个工位`)
      } else if (successCount && failedPositions.length) {
        ElMessage.warning(
          `已成功预约 ${successCount} 个工位；${failedPositions.map((item) => `${item.positionNo} 号位：${item.message}`).join('；')}`,
        )
      } else if (failedPositions.length) {
        ElMessage.error(failedPositions.map((item) => `${item.positionNo} 号位：${item.message}`).join('；'))
      }

      resetBallMillSelection()
      await fetchBallMillAvailability({ forcePreview: true })
      await fetchBallMillMonthSummary()
      await fetchBallMillDayBookings()
      await fetchMyBookings()
    } finally {
      resetBallMillSelection()
      loading.booking = false
    }
  }

  async function cancelQueueRequest(row) {
    if (!selectedEquipmentId.value || !row?.id) return
    try {
      await cancelBallMillQueueRequest(selectedEquipmentId.value, row.id)
      ElMessage.success('已取消排队申请')
      await fetchBallMillQueueRequests()
      await fetchBallMillQueueDispatchPreview({ silent: true })
      await fetchBallMillAvailability({ forcePreview: true })
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '取消排队申请失败'))
    }
  }

  async function deleteQueueRequest(row) {
    if (!selectedEquipmentId.value || !row?.id || !isSystemAdmin.value) return
    try {
      await deleteBallMillQueueRequest(selectedEquipmentId.value, row.id)
      ElMessage.success('已删除排队记录')
      await fetchBallMillQueueRequests()
      await fetchBallMillQueueDispatchPreview({ silent: true })
      await fetchBallMillAvailability({ forcePreview: true })
    } catch (error) {
      ElMessage.error(extractApiErrorMessage(error, '删除排队记录失败'))
    }
  }

  watch(
    () => [ballMillForm.value.milling_minutes, ballMillForm.value.rotation_speed_rpm],
    async () => {
      if (!isBallMillMode.value) return
      if (selectedBallMillStartTime.value || selectedBallMillPositionNos.value.length) {
        resetBallMillSelection()
      }
      await fetchBallMillAvailability()
    },
  )

  watch(
    () => [isBallMillMode.value, ballMillRotationSpeedMin.value, ballMillRotationSpeedMax.value],
    ([ballMillMode]) => {
      if (!ballMillMode) return
      const currentSpeed = Number(ballMillForm.value.rotation_speed_rpm || 0)
      if (!currentSpeed) {
        ballMillForm.value.rotation_speed_rpm = ballMillRotationSpeedMin.value
        return
      }
      if (currentSpeed < ballMillRotationSpeedMin.value) {
        ballMillForm.value.rotation_speed_rpm = ballMillRotationSpeedMin.value
        ElMessage.warning(`当前设备最小转速为 ${ballMillRotationSpeedMin.value} r/min，已自动调整。`)
        return
      }
      if (ballMillRotationSpeedMax.value != null && currentSpeed > ballMillRotationSpeedMax.value) {
        ballMillForm.value.rotation_speed_rpm = ballMillRotationSpeedMax.value
        ElMessage.warning(`当前设备最大转速为 ${ballMillRotationSpeedMax.value} r/min，已自动调整。`)
      }
    },
    { immediate: true },
  )

  watch(
    () => [ballMillEffectiveMaxMillingMinutes.value, selectedBallMillStartTime.value, selectedBallMillPositionNos.value.join(',')],
    ([maxMilling, startTime, positionNos]) => {
      if (!isBallMillMode.value || !startTime || !positionNos) return
      if (isQueueWindowForAction(startTime)) return
      const safeMax = Math.max(Number(maxMilling || 0), 1)
      if (Number(ballMillForm.value.milling_minutes || 0) > safeMax) {
        ballMillForm.value.milling_minutes = safeMax
        ElMessage.warning(`该开始时间与工位组合最多可输入 ${safeMax} 分钟球磨时间，已自动调整。`)
      }
    },
  )

  watch(
    () => [isBallMillQueueMode.value, selectedEquipmentId.value, selectedDate.value],
    async ([queueModeEnabled]) => {
      if (queueModeEnabled) {
        startQueueAutoRefresh()
        await refreshQueueDynamicState()
        return
      }
      stopQueueAutoRefresh()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    stopQueueAutoRefresh()
  })

  return {
    resetBallMillSelection,
    clearQueueDispatchPreview,
    fetchBallMillMonthSummary,
    fetchBallMillDayBookings,
    fetchBallMillQueueRequests,
    fetchBallMillQueueDispatchPreview,
    fetchBallMillAvailability,
    refreshQueueDynamicState,
    stopQueueAutoRefresh,
    startQueueAutoRefresh,
    changeBallMillCalendarMonth,
    handleBallMillCalendarChange,
    selectBallMillPosition,
    submitBallMillQueueForDate,
    dispatchQueueNow,
    clearAllBallMillData,
    bookBallMill,
    cancelQueueRequest,
    deleteQueueRequest,
  }
}
