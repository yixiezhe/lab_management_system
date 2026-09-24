// frontend/src/api/equipment.js
import apiClient from '@/api'

/** ===== 工具函数：前后端字段映射 ===== */

// 后端 → 前端（列表展示用）
const mapEquipmentFromApi = (item) => {
  if (!item) return item
  return {
    // 原本就有的基础字段
    id: item.id,
    name: item.name,
    location: item.location,
    description: item.description,
    is_active: item.is_active,
    booking_mode: item.booking_mode || 'standard',

    // 时间配置映射
    time_slot_minutes: item.time_unit_minutes, // 后端 time_unit_minutes
    open_time: item.open_time_start,           // 'HH:MM:SS' 或 'HH:MM'
    close_time: item.open_time_end,
    advance_days: item.max_advance_days,
    ball_mill_duration_unit_minutes: item.ball_mill_duration_unit_minutes ?? 12,
    ball_mill_position_count: item.ball_mill_position_count ?? 4,
    ball_mill_min_rotation_speed_rpm: item.ball_mill_min_rotation_speed_rpm ?? 1,
    ball_mill_max_rotation_speed_rpm: item.ball_mill_max_rotation_speed_rpm ?? null,
    ball_mill_max_actual_minutes: item.ball_mill_max_actual_minutes ?? 2880,
    ball_mill_monthly_max_actual_minutes: item.ball_mill_monthly_max_actual_minutes ?? null,
    ball_mill_queue_enabled: item.ball_mill_queue_enabled ?? false,
    ball_mill_queue_publish_time: item.ball_mill_queue_publish_time ?? '00:00:00',
    ball_mill_queue_request_window_days: item.ball_mill_queue_request_window_days ?? 18,
    ball_mill_queue_allocate_window_days: item.ball_mill_queue_allocate_window_days ?? 7,
    ball_mill_queue_dispatch_cursor_date: item.ball_mill_queue_dispatch_cursor_date ?? null,
    ball_mill_queue_publish_lead_days: item.ball_mill_queue_publish_lead_days ?? 5,
    ball_mill_queue_day_start_time: item.ball_mill_queue_day_start_time ?? '07:00:00',
    ball_mill_queue_day_end_time: item.ball_mill_queue_day_end_time ?? '22:00:00',
    ball_mill_queue_heavy_user_threshold_minutes:
      item.ball_mill_queue_heavy_user_threshold_minutes ?? 4320,
    ball_mill_direct_booking_window_days: item.ball_mill_direct_booking_window_days ?? 14,
    ball_mill_direct_booking_cutoff_time: item.ball_mill_direct_booking_cutoff_time ?? '00:00:00',
    ball_mill_max_milling_minutes: item.ball_mill_max_milling_minutes ?? 1920,
    ball_mill_cycle_run_minutes: item.ball_mill_cycle_run_minutes ?? 12,
    ball_mill_cycle_pause_minutes: item.ball_mill_cycle_pause_minutes ?? 6,
    electrochemical_channel_count: item.electrochemical_channel_count ?? 8,
    electrochemical_offline_channels: item.electrochemical_offline_channels || [],
    xrd_remote_machine: item.xrd_remote_machine ?? null,
    xrd_remote_machine_name: item.xrd_remote_machine_name || '',
    xrd_tutorial_html: item.xrd_tutorial_html || 'The quick brown fox jumps over the lazy dog',
    effective_max_advance_days: item.effective_max_advance_days,

    // 早鸟配置映射
    early_bird_advance_days: item.early_bird_max_advance_days,
    early_bird_users: item.early_bird_users || [],
    booking_allowed_users: item.booking_allowed_users || [],

    // 也保留一份原始字段，防止别的地方要用
    _raw: item,
  }
}

// 前端 → 后端（新建 / 更新用）
const mapEquipmentToApi = (payload) => {
  if (!payload) return payload
  const isBallMill = payload.booking_mode === 'planetary_ball_mill'
  const isElectrochemical = payload.booking_mode === 'electrochemical_workstation'
  // 如果早鸟天数没填，就默认等于普通提前天数
  const earlyBirdDays =
    typeof payload.early_bird_advance_days === 'number'
      ? payload.early_bird_advance_days
      : payload.advance_days

  return {
    name: payload.name,
    location: payload.location,
    description: payload.description,
    booking_mode: payload.booking_mode || 'standard',

    time_unit_minutes: isBallMill ? 60 : payload.time_slot_minutes,
    open_time_start: (isBallMill || isElectrochemical) ? '00:00' : payload.open_time,
    open_time_end: (isBallMill || isElectrochemical) ? '23:59' : payload.close_time,
    max_advance_days: payload.advance_days,
    ball_mill_duration_unit_minutes: payload.ball_mill_duration_unit_minutes ?? 12,
    ball_mill_min_rotation_speed_rpm: payload.ball_mill_min_rotation_speed_rpm ?? 1,
    ball_mill_max_rotation_speed_rpm: payload.ball_mill_max_rotation_speed_rpm ?? null,
    ball_mill_max_actual_minutes: payload.ball_mill_max_actual_minutes ?? 2880,
    ball_mill_monthly_max_actual_minutes:
      payload.ball_mill_monthly_max_actual_minutes ?? null,
    ball_mill_queue_enabled: Boolean(payload.ball_mill_queue_enabled),
    ball_mill_queue_publish_time: payload.ball_mill_queue_publish_time ?? '00:00',
    ball_mill_queue_request_window_days: payload.ball_mill_queue_request_window_days ?? 18,
    ball_mill_queue_allocate_window_days: payload.ball_mill_queue_allocate_window_days ?? 7,
    ball_mill_queue_dispatch_cursor_date: payload.ball_mill_queue_dispatch_cursor_date || null,
    ball_mill_queue_publish_lead_days: payload.ball_mill_queue_publish_lead_days ?? 5,
    ball_mill_queue_day_start_time: payload.ball_mill_queue_day_start_time ?? '07:00',
    ball_mill_queue_day_end_time: payload.ball_mill_queue_day_end_time ?? '22:00',
    ball_mill_queue_heavy_user_threshold_minutes:
      payload.ball_mill_queue_heavy_user_threshold_minutes ?? 4320,
    ball_mill_direct_booking_window_days: payload.ball_mill_direct_booking_window_days ?? 14,
    ball_mill_direct_booking_cutoff_time: payload.ball_mill_direct_booking_cutoff_time ?? '00:00',
    electrochemical_offline_channels: payload.electrochemical_offline_channels || [],
    xrd_remote_machine: payload.booking_mode === 'xrd'
      ? (payload.xrd_remote_machine || null)
      : null,

    early_bird_max_advance_days: earlyBirdDays,
    early_bird_users: payload.early_bird_users || [],
    booking_allowed_users: payload.booking_allowed_users || [],

    is_active: payload.is_active,
  }
}

/** 仪器（管理员可写，登录用户可读） */
export const listEquipments = (params = {}) =>
  apiClient.get('/equipment/equipments/', { params }).then((res) => {
    const raw = res.data || []
    const mapped = Array.isArray(raw) ? raw.map(mapEquipmentFromApi) : []
    // 保持调用方式不变：外面仍然可以 `const { data } = await listEquipments()`
    return { ...res, data: mapped }
  })

export const getEquipment = (id) =>
  apiClient.get(`/equipment/equipments/${id}/`)

export const createEquipment = (payload) => {
  const body = mapEquipmentToApi(payload)
  return apiClient.post('/equipment/equipments/', body)
}

export const updateEquipment = (id, payload) => {
  const body = mapEquipmentToApi(payload)
  return apiClient.patch(`/equipment/equipments/${id}/`, body)
}

export const deleteEquipment = (id) =>
  apiClient.delete(`/equipment/equipments/${id}/`)

/** 可用时段（登录用户） */
export const getAvailableSlots = (id, dateStr) =>
  apiClient.get(`/equipment/equipments/${id}/available/`, { params: { date: dateStr } })

/** 仪器日历（管理页） */
export const getEquipmentCalendar = (id, dateStr) =>
  apiClient.get(`/equipment/equipments/${id}/calendar/`, { params: { date: dateStr } })

/** 导出单台仪器已完成的使用记录（系统管理员） */
export const exportEquipmentUsageRecords = (id) =>
  apiClient.get(`/equipment/equipments/${id}/usage-records-export/`, {
    responseType: 'blob',
  })

/** 仪器按月预约概览 */
export const getEquipmentMonthSummary = (id, monthStr, params = {}) =>
  apiClient.get(`/equipment/equipments/${id}/month-summary/`, {
    params: { month: monthStr, ...params },
  })

/** 预约（登录用户） */
export const bookOneSlot = (id, payload /* {date:'YYYY-MM-DD', start_time:'HH:MM'} */) =>
  apiClient.post(`/equipment/equipments/${id}/book/`, payload)

/** 球磨排队申请 */
export const createBallMillQueueRequest = (id, payload) =>
  apiClient.post(`/equipment/equipments/${id}/queue/`, payload)

export const listBallMillQueueRequests = (id, params = {}) =>
  apiClient.get(`/equipment/equipments/${id}/queue/`, { params })

export const dispatchBallMillQueue = (id, payload = {}) =>
  apiClient.post(`/equipment/equipments/${id}/dispatch-queue/`, payload)

export const cancelBallMillQueueRequest = (id, queueId) =>
  apiClient.post(`/equipment/equipments/${id}/queue/${queueId}/cancel/`)

export const deleteBallMillQueueRequest = (id, queueId) =>
  apiClient.post(`/equipment/equipments/${id}/queue/${queueId}/delete/`)

export const clearBallMillQueueAndBookings = (id) =>
  apiClient.post(`/equipment/equipments/${id}/clear-all/`)

export const setElectrochemicalChannelStatus = (id, channelNo, offline) =>
  apiClient.post(`/equipment/equipments/${id}/electrochemical-channel/${channelNo}/status/`, { offline })

export const getEquipmentTestClock = () =>
  apiClient.get("/equipment/equipments/test-clock/")

export const setEquipmentTestClock = (datetimeText) =>
  apiClient.post("/equipment/equipments/test-clock/", { datetime: datetimeText })

export const clearEquipmentTestClock = () =>
  apiClient.delete("/equipment/equipments/test-clock/")

/** 预约列表（目前通用接口；你的预约页面我们已经单独用 /mine /history 了） */
export const listBookings = (params = {}) =>
  apiClient.get('/equipment/bookings/', { params })

/** 取消预约（本人或管理员） */
export const cancelBooking = (id) =>
  apiClient.post(`/equipment/bookings/${id}/cancel/`)

/** 提前结束本人正在使用的输力强预约 */
export const endBookingEarly = (id) =>
  apiClient.post(`/equipment/bookings/${id}/end-early/`)

export const connectXrdRemoteBooking = (id) =>
  apiClient.post(`/equipment/bookings/${id}/xrd-remote-connect/`)

export const endXrdTestBooking = (id) =>
  apiClient.post(`/equipment/bookings/${id}/xrd-end-test/`)

export const updateXrdTutorial = (id, html) =>
  apiClient.post(`/equipment/equipments/${id}/xrd-tutorial/`, { html })

/** 彻底删除预约（后端已有默认 destroy 路由；普通用户仅能删除自己的预约） */
export const deleteBooking = (id) =>
  apiClient.delete(`/equipment/bookings/${id}/`)

export const getXrdTutorStats = (id, params = {}) =>
  apiClient.get(`/equipment/equipments/${id}/xrd-tutor-stats/`, { params })
