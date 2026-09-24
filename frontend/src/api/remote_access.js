// frontend/src/api/remote_access.js

import apiClient from './index';

// ===============================================
// === 主机管理 (Machine Management) - (管理员/通用) ===
// ===============================================

/**
 * @description 获取所有主机列表
 */
export const fetchRdpMachines = () => {
  return apiClient.get('/remote_access/machines/');
};

/**
 * @description 设备自动登录（kiosk 专用）
 * @param {Object} payload { machine_id, device_secret }
 */
export const deviceLogin = (payload) => {
  return apiClient.post('/remote_access/device_login/', payload);
};

/**
 * @description 获取某台主机的实时状态
 * 返回: { status: 'free'|'occupied', user: 'xxx', end_time: '...', booking_id: 123 }
 * @param {number} machineId 
 */
export const fetchMachineCurrentStatus = (machineId) => {
  return apiClient.get(`/remote_access/machines/${machineId}/current_status/`);
};

/**
 * @description 创建一个新主机
 */
export const createRdpMachine = (machineData) => {
  return apiClient.post('/remote_access/machines/', machineData);
};

/**
 * @description 更新一个主机
 */
export const updateRdpMachine = (machineId, machineData) => {
  return apiClient.put(`/remote_access/machines/${machineId}/`, machineData);
};

/**
 * @description 删除一个主机
 */
export const deleteRdpMachine = (machineId) => {
  return apiClient.delete(`/remote_access/machines/${machineId}/`);
};


// ===============================================
// === 预约 (Booking) - (普通用户) ===
// ===============================================

/**
 * @description [核心修改] 获取 "我" 的远程预约列表
 * @param {Object} params 包含筛选参数，例如 { date: '2026-01-18' }
 */
export const fetchMyRdpBookings = (params) => {
  // 允许传入 params 对象，axios 会将其转换为查询字符串
  return apiClient.get('/remote_access/bookings/my/', { params });
};

/**
 * @description 创建一个新的远程预约
 */
export const createRdpBooking = (bookingData) => {
  return apiClient.post('/remote_access/bookings/', bookingData);
};

/**
 * @description 使用服务器时间创建 30 分钟即时远程预约
 */
export const createInstantRdpBooking = (machineId) => {
  return apiClient.post('/remote_access/bookings/instant_connect/', { machine: machineId });
};

/**
 * @description 取消一个 "我" 的远程预约
 */
export const cancelRdpBooking = (bookingId) => {
  return apiClient.post(`/remote_access/bookings/${bookingId}/cancel/`);
};

// ===============================================
// === 核心连接逻辑 (Connect / Status / Takeover) ===
// ===============================================

/**
 * @description (核心) 发起连接请求
 * 后端会验证时间、生成 Token 并将状态置为 'active'
 * @param {number} bookingId 
 */
export const connectRdpBooking = (bookingId) => {
  return apiClient.post(`/remote_access/bookings/${bookingId}/connect/`);
};

/**
 * @description (核心) 主动登出
 * 记录实际结束时间，释放资源
 * @param {number} bookingId 
 */
export const disconnectRdpBooking = (bookingId) => {
  return apiClient.post(`/remote_access/bookings/${bookingId}/disconnect/`);
};

/**
 * @description (心跳) 检测预约状态
 * 返回：剩余时间、是否有人申请插队、是否被强制断开
 * @param {number} bookingId 
 */
export const checkBookingStatus = (bookingId) => {
  return apiClient.get(`/remote_access/bookings/${bookingId}/check_status/`);
};

/**
 * @description (插队) 申请紧急占用他人的预约
 * @param {number} bookingId 目标预约的 ID
 */
export const requestTakeover = (bookingId) => {
  return apiClient.post(`/remote_access/bookings/${bookingId}/request_takeover/`);
};

/**
 * @description (插队) 同意他人的插队申请 (自己将断开连接)
 * @param {number} bookingId 
 */
export const approveTakeover = (bookingId) => {
  return apiClient.post(`/remote_access/bookings/${bookingId}/approve_takeover/`);
};

/**
 * @description (插队) 拒绝他人的插队申请
 * @param {number} bookingId 
 */
export const rejectTakeover = (bookingId) => {
  return apiClient.post(`/remote_access/bookings/${bookingId}/reject_takeover/`);
};
