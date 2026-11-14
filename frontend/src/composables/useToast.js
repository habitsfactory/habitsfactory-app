import { ref } from 'vue'

// Module-level state: one toast stack for the whole app, rendered by
// components/ui/ToastHost.vue. Toasts hold a translation key rather than a
// string so they follow the language and can be raised from composables.
const toasts = ref([])
const timers = new Map()
let nextId = 0

const DURATION = { error: 6000, success: 3000 }

const dismiss = (id) => {
    clearTimeout(timers.get(id))
    timers.delete(id)
    toasts.value = toasts.value.filter(toast => toast.id !== id)
}

const show = (type, key) => {
    // Several requests failing at once (e.g. offline) show a single toast
    let toast = toasts.value.find(item => item.type === type && item.key === key)
    if (toast) {
        clearTimeout(timers.get(toast.id))
    } else {
        toast = { id: ++nextId, type, key }
        toasts.value = [...toasts.value, toast]
    }
    const { id } = toast
    timers.set(id, setTimeout(() => dismiss(id), DURATION[type]))
}

/**
 * Report a failed request to the user.
 * `key` is a translation key: loadFailed | saveFailed | deleteFailed.
 */
export const notifyError = (err, key = 'saveFailed') => {
    // An expired session redirects to the login page (see services/api.js)
    if (err?.response?.status === 401) return
    show('error', key)
}

export const notifySuccess = (key) => show('success', key)

export function useToast() {
    return { toasts, dismiss, notifyError, notifySuccess }
}
