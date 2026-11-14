// composables/useConfirm.js
// Promise-based replacement for window.confirm(), rendered by
// components/ui/ConfirmDialog.vue (mounted once in App.vue).
//
//   const { confirm } = useConfirm()
//   if (await confirm({ title: '…', message: '…', danger: true })) { … }
import { reactive } from 'vue'

const state = reactive({
    open: false,
    title: '',
    message: '',
    confirmLabel: '',
    danger: false,
})

let resolver = null

const settle = (result) => {
    state.open = false
    resolver?.(result)
    resolver = null
}

const confirm = (options = {}) => {
    // A second request while one is open cancels the first
    resolver?.(false)
    Object.assign(state, {
        title: '',
        message: '',
        confirmLabel: '',
        danger: false,
        ...options,
        open: true,
    })
    return new Promise((resolve) => { resolver = resolve })
}

export function useConfirm() {
    return { state, confirm, settle }
}
