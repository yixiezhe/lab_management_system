export function getTodayStr() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function toLocalDateString(dateLike) {
  const d = new Date(dateLike)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function toMonthString(dateLike) {
  return toLocalDateString(dateLike).slice(0, 7)
}

export function parseDateString(dateStr) {
  return new Date(`${dateStr}T12:00:00`)
}

export function toMinutes(tStr) {
  if (!tStr) return 0
  const [h, m] = tStr.slice(0, 5).split(':').map(Number)
  return h * 60 + (m || 0)
}

export function formatClock(value) {
  return (value || '').slice(0, 5)
}

export function formatInclusiveEndTime(value) {
  const clock = formatClock(value)
  const [hour, minute] = clock.split(':').map(Number)
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return clock
  if (minute !== 0) return clock

  const total = (hour * 60 + minute + 24 * 60 - 1) % (24 * 60)
  const nextHour = String(Math.floor(total / 60)).padStart(2, '0')
  const nextMinute = String(total % 60).padStart(2, '0')
  return `${nextHour}:${nextMinute}`
}

export function formatElectrochemicalTimeRange(start, end) {
  return `${formatClock(start)} - ${formatInclusiveEndTime(end)}`
}

export function startOfDay(dateValue) {
  const d = new Date(dateValue)
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0)
}

export function addDays(dateValue, days) {
  return new Date(
    dateValue.getFullYear(),
    dateValue.getMonth(),
    dateValue.getDate() + days,
    dateValue.getHours(),
    dateValue.getMinutes(),
    dateValue.getSeconds(),
    dateValue.getMilliseconds(),
  )
}

export function getMondayBasedWeekday(dateValue) {
  return (new Date(dateValue).getDay() + 6) % 7
}

export function getWeekMonday(dateValue) {
  const dayStart = startOfDay(dateValue)
  return addDays(dayStart, -getMondayBasedWeekday(dayStart))
}

export function formatDuration(minutes) {
  if (!minutes) return '0 分钟'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (hours && mins) return `${hours} 小时 ${mins} 分钟`
  if (hours) return `${hours} 小时`
  return `${mins} 分钟`
}

export function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

export function formatDateOnly(dateValue) {
  if (!dateValue) return '-'
  const y = dateValue.getFullYear()
  const m = String(dateValue.getMonth() + 1).padStart(2, '0')
  const d = String(dateValue.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function formatDateRange(startDate, endDate) {
  return `${formatDateOnly(startDate)} 至 ${formatDateOnly(endDate)}`
}

export function normalizePositiveRank(value) {
  const rank = Number(value || 0)
  return Number.isFinite(rank) && rank > 0 ? rank : null
}

export function compareOptionalRank(rankA, rankB) {
  const normalizedA = normalizePositiveRank(rankA)
  const normalizedB = normalizePositiveRank(rankB)
  if (normalizedA !== null && normalizedB !== null) {
    return normalizedA - normalizedB
  }
  if (normalizedA !== null) return -1
  if (normalizedB !== null) return 1
  return 0
}

export function extractApiErrorMessage(error, fallback = '操作失败') {
  const data = error?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') {
    const text = data.trim()
    const looksLikeHtml = /<!doctype html>|<html[\s>]|<body[\s>]/i.test(text)
    const looksLikeTraceback = /traceback \(most recent call last\)|django version|exception type:/i.test(text)
    if (looksLikeHtml || looksLikeTraceback || text.length > 300) {
      return `${fallback}（服务端异常，请查看后端日志）`
    }
    return text
  }
  if (Array.isArray(data) && data.length) {
    return typeof data[0] === 'string' ? data[0] : fallback
  }
  if (typeof data.detail === 'string') return data.detail

  const values = Object.values(data)
  for (const value of values) {
    if (typeof value === 'string' && value) return value
    if (Array.isArray(value) && value.length) {
      return typeof value[0] === 'string' ? value[0] : fallback
    }
  }
  return fallback
}
