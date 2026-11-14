// Date helpers that work in the user's LOCAL timezone.
// (`toISOString()` is UTC and returns tomorrow's date in the evening for
// timezones west of Greenwich.)

const pad = (n) => String(n).padStart(2, '0')

/** Date -> "YYYY-MM-DD" in local time. */
export const toISODate = (date = new Date()) =>
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`

/** "YYYY-MM-DD" -> local Date (at noon, to stay clear of DST edges). */
export const parseISODate = (value) => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day, 12, 0, 0)
}

export const addDays = (date, amount) => {
  const next = new Date(date)
  next.setDate(next.getDate() + amount)
  return next
}

export const isSameDay = (a, b) => toISODate(a) === toISODate(b)

/** Number of calendar days between two dates, inclusive. */
export const daysBetween = (start, end) => {
  const a = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const b = new Date(end.getFullYear(), end.getMonth(), end.getDate())
  return Math.round((b - a) / 86400000) + 1
}

export const recentYears = (count = 3) => {
  const current = new Date().getFullYear()
  return Array.from({ length: count }, (_, i) => current - i)
}

/**
 * Resolve a quick-select preset to { start, end } Dates.
 * Keys: thisWeek | thisMonth | last7Days | last30Days | <year>
 */
export const presetRange = (key) => {
  const today = new Date()
  switch (key) {
    case 'thisWeek': {
      const day = today.getDay()
      return { start: addDays(today, -(day === 0 ? 6 : day - 1)), end: today }
    }
    case 'thisMonth':
      return { start: new Date(today.getFullYear(), today.getMonth(), 1), end: today }
    case 'last7Days':
      return { start: addDays(today, -6), end: today }
    case 'last30Days':
      return { start: addDays(today, -29), end: today }
    default: {
      const year = parseInt(key, 10)
      if (!Number.isNaN(year)) {
        return { start: new Date(year, 0, 1), end: new Date(year, 11, 31) }
      }
      return { start: addDays(today, -29), end: today }
    }
  }
}
