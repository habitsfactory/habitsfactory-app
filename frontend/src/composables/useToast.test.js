import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useToast, notifyError, notifySuccess } from './useToast'

const { toasts, dismiss } = useToast()

describe('useToast', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => {
    vi.runAllTimers()
    vi.useRealTimers()
  })

  it('shows an error and dismisses it after a delay', () => {
    notifyError(new Error('network'), 'loadFailed')

    expect(toasts.value).toMatchObject([{ type: 'error', key: 'loadFailed' }])
    vi.advanceTimersByTime(6000)
    expect(toasts.value).toEqual([])
  })

  it('defaults to the generic save message', () => {
    notifyError(new Error('boom'))
    expect(toasts.value[0].key).toBe('saveFailed')
  })

  it('collapses identical toasts and restarts their timer', () => {
    notifyError(null, 'loadFailed')
    vi.advanceTimersByTime(5000)
    notifyError(null, 'loadFailed')

    expect(toasts.value).toHaveLength(1)
    vi.advanceTimersByTime(5000) // 10 s after the first, 5 s after the second
    expect(toasts.value).toHaveLength(1)
    vi.advanceTimersByTime(1000)
    expect(toasts.value).toHaveLength(0)
  })

  it('keeps different messages apart', () => {
    notifyError(null, 'loadFailed')
    notifyError(null, 'deleteFailed')
    notifySuccess('saved')
    expect(toasts.value.map((toast) => toast.key)).toEqual(['loadFailed', 'deleteFailed', 'saved'])
  })

  it('stays quiet on an expired session (the app redirects to login)', () => {
    notifyError({ response: { status: 401 } }, 'loadFailed')
    expect(toasts.value).toEqual([])
  })

  it('can be dismissed by hand', () => {
    notifyError(null, 'loadFailed')
    dismiss(toasts.value[0].id)
    expect(toasts.value).toEqual([])
  })
})
