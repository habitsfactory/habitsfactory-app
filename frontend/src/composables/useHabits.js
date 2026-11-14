// composables/useHabits.js
import { ref } from 'vue'
import api from '@/services/api'
import { notifyError } from '@/composables/useToast'

// Module-level state shared by every consumer (dashboard, tracking tab,
// profile): a habit created or edited in one place shows up in the others.
const habits = ref([])
const archivedHabits = ref([])
const isLoadingHabits = ref(false)

// Extra client-side fields used by the tracking controls
const withTrackingState = (habit) => ({
    ...habit,
    temp_value: habit.today_value || 0,
    is_completed_today: habit.today_value > 0,
    is_saving: false
})

// Only the latest request may update the list (fast day-to-day navigation)
let latestFetch = 0

const fetchHabits = async (trackingDateString) => {
    const requestId = ++latestFetch
    isLoadingHabits.value = true
    try {
        const res = await api.get('habits/', {
            params: { date: trackingDateString }
        })
        if (requestId === latestFetch) habits.value = res.data.map(withTrackingState)
    } catch (err) {
        notifyError(err, 'loadFailed')
    } finally {
        if (requestId === latestFetch) isLoadingHabits.value = false
    }
}

const fetchArchivedHabits = async () => {
    try {
        const res = await api.get('habits/', {
            params: { archived_only: 'true' }
        })
        archivedHabits.value = res.data
    } catch (err) {
        notifyError(err, 'loadFailed')
    }
}

const addHabit = async (habitData) => {
    const res = await api.post('habits/', habitData)
    habits.value.push(withTrackingState(res.data))
    return res.data
}

const archiveHabit = async (habitId) => {
    await api.post(`habits/${habitId}/archive/`)
    habits.value = habits.value.filter(h => h.id !== habitId)
    await fetchArchivedHabits()
}

const unarchiveHabit = async (habitId) => {
    await api.post(`habits/${habitId}/unarchive/`)
    archivedHabits.value = archivedHabits.value.filter(h => h.id !== habitId)
}

const updateHabit = async (habitId, payload) => {
    await api.patch(`habits/${habitId}/`, payload)
    const habitIndex = habits.value.findIndex(h => h.id === habitId)
    if (habitIndex !== -1) {
        habits.value[habitIndex] = { ...habits.value[habitIndex], ...payload }
    }
}

const deleteActiveHabit = async (habitId) => {
    await api.delete(`habits/${habitId}/`)
    habits.value = habits.value.filter(h => h.id !== habitId)
}

const deleteArchivedHabit = async (habitId) => {
    await api.delete(`habits/${habitId}/`)
    archivedHabits.value = archivedHabits.value.filter(h => h.id !== habitId)
}

/**
 * Move a habit one position up (-1) or down (+1) in the user's list and
 * save the new order. The list is restored if the save fails.
 */
const moveHabit = async (habitId, direction) => {
    const from = habits.value.findIndex(h => h.id === habitId)
    const to = from + direction
    if (from === -1 || to < 0 || to >= habits.value.length) return

    const previous = habits.value
    const next = [...previous]
    next.splice(to, 0, ...next.splice(from, 1))
    habits.value = next
    try {
        await api.post('habits/reorder/', { order: next.map(h => h.id) })
    } catch (err) {
        habits.value = previous
        throw err
    }
}

const saveCompletion = async (habit, value, trackingDateString) => {
    habit.is_saving = true
    try {
        await api.post(`habits/${habit.id}/complete/`, {
            value,
            date: trackingDateString
        })
        habit.today_value = value
        habit.is_completed_today = value > 0
    } finally {
        setTimeout(() => { habit.is_saving = false }, 500)
    }
}

export function useHabits() {
    return {
        habits,
        archivedHabits,
        isLoadingHabits,
        fetchHabits,
        fetchArchivedHabits,
        addHabit,
        archiveHabit,
        unarchiveHabit,
        deleteActiveHabit,
        deleteArchivedHabit,
        updateHabit,
        moveHabit,
        saveCompletion
    }
}
