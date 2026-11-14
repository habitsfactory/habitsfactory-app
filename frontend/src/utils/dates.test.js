import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { toISODate, parseISODate, addDays, isSameDay, daysBetween, recentYears, presetRange } from './dates'

describe('toISODate', () => {
  it('formats in local time, not UTC', () => {
    // 23:30 local: toISOString() would give the next day west of Greenwich
    expect(toISODate(new Date(2026, 10, 14, 23, 30))).toBe('2026-11-14')
    expect(toISODate(new Date(2026, 10, 14, 0, 5))).toBe('2026-11-14')
  })

  it('pads months and days', () => {
    expect(toISODate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })
})

describe('parseISODate', () => {
  it('round-trips with toISODate', () => {
    for (const value of ['2026-01-01', '2026-03-29', '2026-10-25', '2024-02-29', '2026-12-31']) {
      expect(toISODate(parseISODate(value))).toBe(value)
    }
  })
})

describe('addDays', () => {
  it('crosses month and year boundaries', () => {
    expect(toISODate(addDays(new Date(2026, 0, 31), 1))).toBe('2026-02-01')
    expect(toISODate(addDays(new Date(2026, 0, 1), -1))).toBe('2025-12-31')
  })

  it('does not mutate its argument', () => {
    const date = new Date(2026, 5, 15)
    addDays(date, 10)
    expect(toISODate(date)).toBe('2026-06-15')
  })
})

describe('isSameDay', () => {
  it('ignores the time of day', () => {
    expect(isSameDay(new Date(2026, 5, 15, 0, 1), new Date(2026, 5, 15, 23, 59))).toBe(true)
    expect(isSameDay(new Date(2026, 5, 15, 23, 59), new Date(2026, 5, 16, 0, 1))).toBe(false)
  })
})

describe('daysBetween', () => {
  it('is inclusive', () => {
    expect(daysBetween(new Date(2026, 5, 15), new Date(2026, 5, 15))).toBe(1)
    expect(daysBetween(new Date(2026, 5, 1), new Date(2026, 5, 30))).toBe(30)
  })

  it('is not thrown off by daylight saving changes', () => {
    expect(daysBetween(new Date(2026, 2, 1), new Date(2026, 2, 31, 23))).toBe(31)
    expect(daysBetween(new Date(2026, 9, 1), new Date(2026, 10, 30))).toBe(61)
  })
})

describe('presets', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 10, 14, 15, 0)) // Saturday 14 November 2026
  })
  afterEach(() => vi.useRealTimers())

  const range = (key) => {
    const { start, end } = presetRange(key)
    return [toISODate(start), toISODate(end)]
  }

  it('thisWeek starts on Monday', () => {
    expect(range('thisWeek')).toEqual(['2026-11-09', '2026-11-14'])
  })

  it('thisWeek on a Sunday still starts the Monday before', () => {
    vi.setSystemTime(new Date(2026, 10, 15, 9, 0))
    expect(range('thisWeek')).toEqual(['2026-11-09', '2026-11-15'])
  })

  it('thisMonth, last7Days and last30Days end today', () => {
    expect(range('thisMonth')).toEqual(['2026-11-01', '2026-11-14'])
    expect(range('last7Days')).toEqual(['2026-11-08', '2026-11-14'])
    expect(range('last30Days')).toEqual(['2026-10-16', '2026-11-14'])
    expect(daysBetween(...Object.values(presetRange('last30Days')))).toBe(30)
  })

  it('a year covers the whole year', () => {
    expect(range('2025')).toEqual(['2025-01-01', '2025-12-31'])
  })

  it('unknown keys fall back to the last 30 days', () => {
    expect(range('nonsense')).toEqual(range('last30Days'))
  })

  it('recentYears lists the newest first', () => {
    expect(recentYears()).toEqual([2026, 2025, 2024])
  })
})
