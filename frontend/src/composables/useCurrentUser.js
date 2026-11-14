// composables/useCurrentUser.js
import { ref, computed } from 'vue'
import api from '@/services/api'

// Shared state: the profile is fetched once and reused by the header,
// footer and views.
const user = ref(null)
let pending = null

const fetchUser = (force = false) => {
    if (user.value && !force) return Promise.resolve(user.value)
    if (!pending) {
        pending = api.get('auth/user/')
            .then((res) => {
                user.value = res.data
                return res.data
            })
            .catch(() => null)
            .finally(() => { pending = null })
    }
    return pending
}

const clearUser = () => {
    user.value = null
}

const isAdmin = computed(() => !!(user.value?.is_staff || user.value?.is_superuser))

export function useCurrentUser() {
    return { user, isAdmin, fetchUser, clearUser }
}
