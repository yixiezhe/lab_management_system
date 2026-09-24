const ENTRY_ENABLED_KEY = 'instrumentBookingEntryEnabled'

export function getInstrumentBookingEntryPreferenceKey(user) {
  const userKey = user?.id ?? user?.username ?? user?.name ?? 'anonymous'
  return `${ENTRY_ENABLED_KEY}:${userKey}`
}

export function isInstrumentBookingEntryEnabled(user) {
  if (typeof window === 'undefined') return true
  return window.localStorage.getItem(getInstrumentBookingEntryPreferenceKey(user)) !== 'false'
}

export function setInstrumentBookingEntryEnabled(user, enabled) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(
    getInstrumentBookingEntryPreferenceKey(user),
    enabled ? 'true' : 'false',
  )
}
