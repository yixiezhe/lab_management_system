import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  clearEquipmentTestClock,
  dispatchBallMillQueue,
  listEquipments,
  setEquipmentTestClock,
} from '@/api/equipment'
import { extractApiErrorMessage } from '../helpers'
import { useBallMillActions } from './useBallMillActions'
import { useBallMillDisplays } from './useBallMillDisplays'
import { useBallMillLogic } from './useBallMillLogic'
import { useBookingCore } from './useBookingCore'
import { useBookingRecords } from './useBookingRecords'
import { useStandardBooking } from './useStandardBooking'
import {
  isInstrumentBookingEntryEnabled,
  setInstrumentBookingEntryEnabled,
} from '../entryPreference'

export function useInstrumentBookingPage() {
  const route = useRoute()
  const router = useRouter()
  const ctx = useBookingCore()
  const logic = useBallMillLogic(ctx)
  const bookingEntryEnabled = ref(isInstrumentBookingEntryEnabled(ctx.authStore.user))

  let ballMillActionsRef = null
  let standardRef = null
  let pageReady = false

  function fetchBallMillMonthSummaryProxy(...args) {
    return ballMillActionsRef?.fetchBallMillMonthSummary?.(...args)
  }

  function fetchBallMillDayBookingsProxy(...args) {
    return ballMillActionsRef?.fetchBallMillDayBookings?.(...args)
  }

  function fetchElectrochemicalMonthSummaryProxy(...args) {
    return standardRef?.fetchElectrochemicalMonthSummary?.(...args)
  }

  const records = useBookingRecords(ctx, {
    fetchCurrentAvailability,
    fetchBallMillMonthSummary: fetchBallMillMonthSummaryProxy,
    fetchBallMillDayBookings: fetchBallMillDayBookingsProxy,
    fetchElectrochemicalMonthSummary: fetchElectrochemicalMonthSummaryProxy,
  })
  const displays = useBallMillDisplays(ctx, logic)
  const standard = useStandardBooking(ctx)
  standardRef = standard
  const ballMillActions = useBallMillActions(ctx, logic, displays, {
    fetchMyBookings: records.fetchMyBookings,
  })
  ballMillActionsRef = ballMillActions

  function resetStandardSelection() {
    ctx.selectedSlots.value = []
  }

  function resetAllSelections() {
    resetStandardSelection()
    ballMillActions.resetBallMillSelection()
  }

  function isCurrentModeDateDisabled(date) {
    return ctx.isBallMillMode.value
      ? logic.disabledBallMillCalendarDate(date)
      : standard.disabledDate(date)
  }

  function getPreferredEquipment(rows) {
    return rows.find((item) => item.booking_mode === 'planetary_ball_mill') || rows[0] || null
  }

  function readReservationPrefill() {
    if (route.query?.assistant_prefill !== '1') return null
    const equipmentId = Number(route.query?.equipment_id || 0)
    const positionNo = Number(route.query?.position_no || 0)
    const targetDate = String(route.query?.date || '')
    const startTime = String(route.query?.start_time || '')
    const endTime = String(route.query?.end_time || '')
    if (
      !equipmentId ||
      !/^\d{4}-\d{2}-\d{2}$/.test(targetDate) ||
      !/^\d{2}:\d{2}$/.test(startTime) ||
      !/^\d{2}:\d{2}$/.test(endTime)
    ) return null
    return { equipmentId, positionNo, targetDate, startTime, endTime }
  }

  function configureReservationPrefill(prefill) {
    const equipment = ctx.equipments.value.find(
      item => Number(item.id) === prefill.equipmentId,
    )
    if (!equipment) {
      ElMessage.warning('预填仪器不存在或当前账号无权预约')
      return false
    }
    ctx.selectedEquipmentId.value = equipment.id
    ctx.selectedDate.value = prefill.targetDate
    if (equipment.booking_mode === 'electrochemical_workstation') {
      ctx.selectedElectrochemicalChannelNo.value = prefill.positionNo || 1
    }
    ctx.electrochemicalCalendarValue.value = ctx.parseDateString(prefill.targetDate)
    ctx.electrochemicalCalendarPanelMonth.value = prefill.targetDate.slice(0, 7)
    return true
  }

  function applyReservationPrefillSelection(prefill) {
    const selected = ctx.slots.value.filter((slot) => (
      String(slot.start).slice(0, 5) >= prefill.startTime &&
      String(slot.end).slice(0, 5) <= prefill.endTime
    ))
    const aligned = (
      selected.length > 0 &&
      String(selected[0].start).slice(0, 5) === prefill.startTime &&
      String(selected[selected.length - 1].end).slice(0, 5) === prefill.endTime
    )
    if (!aligned || selected.some(slot => standard.isSlotDisabled(slot))) {
      ctx.selectedSlots.value = []
      ElMessage.warning('预填时段已不可预约，请重新选择')
      return false
    }
    ctx.selectedSlots.value = selected
    if (ctx.isXrdMode.value) {
      ctx.xrdForm.value.start_time = prefill.startTime
      ctx.xrdForm.value.end_time = prefill.endTime
    }
    ElMessage.success(`已预选 ${prefill.startTime}–${prefill.endTime}，请核对后手动提交`)
    return true
  }

  function consumeReservationPrefill() {
    router.replace({
      name: 'instruments-book',
      query: { equipment_id: ctx.selectedEquipmentId.value },
    })
  }

  async function reloadReservationPrefill(prefill) {
    if (!configureReservationPrefill(prefill)) return
    await fetchCurrentAvailability()
    if (ctx.isElectrochemicalMode.value || ctx.isXrdMode.value) {
      await standard.fetchElectrochemicalMonthSummary()
    }
    applyReservationPrefillSelection(prefill)
    consumeReservationPrefill()
  }

  function syncSelectedEquipmentRoute() {
    if (route.name !== 'instruments-book' || !ctx.selectedEquipmentId.value) return
    router.replace({
      name: 'instruments-book',
      query: {
        ...route.query,
        equipment_id: ctx.selectedEquipmentId.value,
      },
    })
  }

  function goToBookingEntry() {
    router.push({
      name: 'instruments-book-entry',
      query: { force: '1' },
    })
  }

  function toggleBookingEntryEnabled() {
    const nextEnabled = !bookingEntryEnabled.value
    bookingEntryEnabled.value = nextEnabled
    setInstrumentBookingEntryEnabled(ctx.authStore.user, nextEnabled)
    ElMessage.success(nextEnabled ? '已开启入口界面' : '已关闭入口界面')
  }

  async function fetchEquipments() {
    ctx.loading.equipments = true
    try {
      const { data } = await listEquipments()
      const availableEquipments = Array.isArray(data)
        ? data.filter((item) => ctx.canCurrentUserUseEquipment(item))
        : []
      ctx.equipments.value = availableEquipments

      const requestedEquipmentId = Number(route.query?.equipment_id || 0)
      const requestedEquipment = availableEquipments.find(
        (item) => Number(item.id) === requestedEquipmentId,
      )
      if (requestedEquipment) {
        ctx.selectedEquipmentId.value = requestedEquipment.id
      } else {
        const hasSelectedEquipment = availableEquipments.some(
          (item) => item.id === ctx.selectedEquipmentId.value,
        )
        if (!hasSelectedEquipment && availableEquipments.length > 0) {
          ctx.selectedEquipmentId.value = getPreferredEquipment(availableEquipments).id
        }
      }

      if (ctx.isElectrochemicalMode.value && !ctx.selectedElectrochemicalChannelNo.value) {
        ctx.selectedElectrochemicalChannelNo.value = 1
      }
    } catch (error) {
      ElMessage.error('获取仪器列表失败')
    } finally {
      ctx.loading.equipments = false
    }
  }

  async function fetchCurrentAvailability() {
    resetAllSelections()
    if (ctx.isBallMillMode.value) {
      ctx.ballMillCalendarPanelMonth.value = ctx.selectedDate.value.slice(0, 7)
      logic.syncBallMillCalendarValue(ctx.selectedDate.value)
      await ballMillActions.fetchBallMillAvailability()
      return
    }
    if (ctx.isElectrochemicalMode.value || ctx.isXrdMode.value) {
      ctx.electrochemicalCalendarPanelMonth.value = ctx.selectedDate.value.slice(0, 7)
      standard.syncElectrochemicalCalendarValue(ctx.selectedDate.value)
    }
    await standard.fetchStandardAvailability()
  }

  async function handleEquipmentChange() {
    syncSelectedEquipmentRoute()
    ctx.rawAvailable.value = null
    ctx.slots.value = []
    ctx.ballMillHourWindows.value = []
    ctx.ballMillMonthSummaryDays.value = []
    ctx.electrochemicalMonthSummaryDays.value = []
    ctx.ballMillDayBookings.value = []
    ctx.ballMillQueueRequests.value = []
    ctx.electrochemicalChannels.value = []
    ctx.selectedElectrochemicalChannelNo.value = 1
    ballMillActions.clearQueueDispatchPreview()

    if (isCurrentModeDateDisabled(ctx.parseDateString(ctx.selectedDate.value))) {
      ctx.selectedDate.value = ctx.todayStr.value
    }

    resetAllSelections()
    ctx.ballMillCalendarPanelMonth.value = ctx.selectedDate.value.slice(0, 7)
    ctx.electrochemicalCalendarPanelMonth.value = ctx.selectedDate.value.slice(0, 7)
    await fetchCurrentAvailability()

    if (ctx.isBallMillMode.value) {
      await ballMillActions.fetchBallMillMonthSummary()
      await ballMillActions.fetchBallMillDayBookings()
      await ballMillActions.fetchBallMillQueueRequests()
      await ballMillActions.fetchBallMillQueueDispatchPreview({ silent: true })
    } else if (ctx.isElectrochemicalMode.value || ctx.isXrdMode.value) {
      await standard.fetchElectrochemicalMonthSummary()
    }

    await records.fetchMyBookings()
  }

  async function autoDispatchQueueIfDue(options = {}) {
    const { silent = true, announce = false } = options
    if (!ctx.selectedEquipmentId.value || !ctx.isBallMillQueueMode.value) return false

    try {
      const { data } = await dispatchBallMillQueue(ctx.selectedEquipmentId.value, { force: false })
      if (data?.executed) {
        if (announce) {
          ElMessage.success(
            `已按当前系统日期自动放榜：已分配 ${Number(data?.allocated_count || 0)}，顺延 ${Number(data?.rolled_over_count || 0)}`,
          )
        }
        return true
      }
      return false
    } catch (error) {
      if (!silent) {
        ElMessage.error(extractApiErrorMessage(error, '自动放榜失败'))
      }
      return false
    }
  }

  async function reloadAfterTestClockChanged(options = {}) {
    const { announceAutoDispatch = false } = options
    if (!ctx.selectedEquipmentId.value) return

    if (isCurrentModeDateDisabled(ctx.parseDateString(ctx.selectedDate.value))) {
      ctx.selectedDate.value = ctx.todayStr.value
    }

    resetAllSelections()
    ctx.ballMillCalendarPanelMonth.value = ctx.selectedDate.value.slice(0, 7)
    ctx.electrochemicalCalendarPanelMonth.value = ctx.selectedDate.value.slice(0, 7)
    logic.syncBallMillCalendarValue(ctx.selectedDate.value)
    standard.syncElectrochemicalCalendarValue(ctx.selectedDate.value)

    await fetchCurrentAvailability()
    if (ctx.isBallMillMode.value) {
      const autoDispatched = await autoDispatchQueueIfDue({
        silent: !announceAutoDispatch,
        announce: announceAutoDispatch,
      })
      if (autoDispatched) {
        await fetchCurrentAvailability()
      }
      await ballMillActions.fetchBallMillMonthSummary()
      await ballMillActions.fetchBallMillDayBookings()
      await ballMillActions.fetchBallMillQueueRequests()
      await ballMillActions.fetchBallMillQueueDispatchPreview({ silent: true })
    } else if (ctx.isElectrochemicalMode.value || ctx.isXrdMode.value) {
      await standard.fetchElectrochemicalMonthSummary()
    }
    await records.fetchMyBookings()
  }

  async function setTestClockByPrompt() {
    try {
      const { value } = await ElMessageBox.prompt(
        '请输入测试系统日期时间（例如：2026-04-12 10:30:00）',
        '手动系统日期（测试）',
        {
          confirmButtonText: '应用',
          cancelButtonText: '取消',
          inputValue: ctx.testClockDisplayText.value,
        },
      )
      const text = String(value || '').trim()
      if (!text) {
        ElMessage.warning('请输入有效日期时间')
        return
      }
      const { data } = await setEquipmentTestClock(text)
      ctx.applyTestClockState(data || {})
      ElMessage.success('测试系统日期已更新')
      await reloadAfterTestClockChanged({ announceAutoDispatch: true })
    } catch (error) {
      if (error === 'cancel' || error === 'close') return
      ElMessage.error(extractApiErrorMessage(error, '设置测试系统日期失败'))
    }
  }

  async function resetTestClock() {
    try {
      await ElMessageBox.confirm('确定恢复真实系统日期吗？', '提示', {
        type: 'warning',
        confirmButtonText: '恢复',
        cancelButtonText: '取消',
      })
      const { data } = await clearEquipmentTestClock()
      ctx.applyTestClockState(data || {})
      ElMessage.success('已恢复真实系统日期')
      await reloadAfterTestClockChanged()
    } catch (error) {
      if (error === 'cancel' || error === 'close') return
      ElMessage.error(extractApiErrorMessage(error, '恢复真实系统日期失败'))
    }
  }

  async function bookXrd() {
    await standard.bookXrd()
    await records.fetchMyBookings()
  }

  async function endXrdTest() {
    await standard.endXrdTest()
    await records.fetchMyBookings()
  }

  async function bookSelected() {
    if (!ctx.selectedEquipmentId.value || ctx.selectedSlots.value.length === 0) return
    await standard.bookSelected()
    await standard.fetchStandardAvailability()
    if (ctx.isElectrochemicalMode.value || ctx.isXrdMode.value) {
      await standard.fetchElectrochemicalMonthSummary()
    }
    await records.fetchMyBookings()
  }

  onMounted(async () => {
    await ctx.refreshTestClockState({ silent: true })
    if (!ctx.authStore.user && ctx.authStore.accessToken) {
      await ctx.authStore.fetchUser()
    }
    bookingEntryEnabled.value = isInstrumentBookingEntryEnabled(ctx.authStore.user)
    ctx.selectedDate.value = ctx.todayStr.value
    ctx.ballMillCalendarValue.value = ctx.parseDateString(ctx.todayStr.value)
    ctx.electrochemicalCalendarValue.value = ctx.parseDateString(ctx.todayStr.value)
    ctx.ballMillCalendarPanelMonth.value = ctx.todayStr.value.slice(0, 7)
    ctx.electrochemicalCalendarPanelMonth.value = ctx.todayStr.value.slice(0, 7)

    await fetchEquipments()
    const reservationPrefill = readReservationPrefill()
    const hasReservationPrefill = reservationPrefill
      ? configureReservationPrefill(reservationPrefill)
      : false
    await fetchCurrentAvailability()
    if (ctx.isBallMillMode.value) {
      const autoDispatched = await autoDispatchQueueIfDue({ silent: true })
      if (autoDispatched) {
        await fetchCurrentAvailability()
      }
      await ballMillActions.fetchBallMillMonthSummary()
      await ballMillActions.fetchBallMillDayBookings()
      await ballMillActions.fetchBallMillQueueRequests()
      await ballMillActions.fetchBallMillQueueDispatchPreview({ silent: true })
    } else if (ctx.isElectrochemicalMode.value || ctx.isXrdMode.value) {
      await standard.fetchElectrochemicalMonthSummary()
    }
    await records.fetchMyBookings()
    if (hasReservationPrefill) {
      applyReservationPrefillSelection(reservationPrefill)
      consumeReservationPrefill()
    }
    pageReady = true
  })

  watch(
    () => route.fullPath,
    async () => {
      if (!pageReady) return
      const reservationPrefill = readReservationPrefill()
      if (reservationPrefill) await reloadReservationPrefill(reservationPrefill)
    },
  )

  return {
    ...ctx,
    ...logic,
    ...displays,
    ...standard,
    ...ballMillActions,
    ...records,
    resetStandardSelection,
    resetAllSelections,
    isCurrentModeDateDisabled,
    fetchEquipments,
    fetchCurrentAvailability,
    handleEquipmentChange,
    bookingEntryEnabled,
    goToBookingEntry,
    toggleBookingEntryEnabled,
    autoDispatchQueueIfDue,
    reloadAfterTestClockChanged,
    setTestClockByPrompt,
    resetTestClock,
    bookSelected,
    bookXrd,
    endXrdTest,
  }
}
