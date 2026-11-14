// src/composables/useDarkMode.js
import { ref, watch } from 'vue'

// Shared across the whole app so every component (header toggle, charts,
// heatmaps…) reacts to the same state.
const readInitial = () => {
    try {
        const stored = localStorage.getItem('darkMode')
        if (stored !== null) return stored === 'true'
    } catch {
        // localStorage unavailable — fall back to the system preference
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const isDark = ref(readInitial())

const applyDarkMode = () => {
    document.documentElement.classList.toggle('dark', isDark.value)
}

applyDarkMode()

watch(isDark, (value) => {
    try {
        localStorage.setItem('darkMode', String(value))
    } catch {
        // ignore
    }
    applyDarkMode()
}, { flush: 'sync' })

const toggleDarkMode = () => {
    isDark.value = !isDark.value
}

export function useDarkMode() {
    return {
        isDark,
        toggleDarkMode
    }
}
