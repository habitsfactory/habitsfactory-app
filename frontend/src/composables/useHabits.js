// composables/useHabits.js
import { ref } from 'vue'
import api from '@/services/api'

export function useHabits() {
    const habits = ref([])
    const archivedHabits = ref([])
    const isLoadingHabits = ref(false)

    const fetchHabits = async (trackingDateString) => {
        isLoadingHabits.value = true
        try {
            const res = await api.get('habits/', {
                params: { date: trackingDateString }
            })
            habits.value = res.data.map(h => ({
                ...h,
                temp_value: h.today_value || 0,
                is_completed_today: h.today_value > 0,
                is_saving: false
            }))
        } catch (err) {
        } finally {
            isLoadingHabits.value = false
        }
    }

    const fetchArchivedHabits = async () => {
        try {
            const res = await api.get('habits/', {
                params: { archived_only: 'true' }
            })
            archivedHabits.value = res.data
        } catch (err) {
        }
    }

    const addHabit = async (habitData) => {
        try {
            const res = await api.post('habits/', habitData)
            habits.value.push({
                ...res.data,
                temp_value: 0,
                is_completed_today: false,
                is_saving: false
            })
            return res.data
        } catch (err) {
            throw err
        }
    }

    const archiveHabit = async (habitId) => {
        try {
            await api.post(`habits/${habitId}/archive/`)
            habits.value = habits.value.filter(h => h.id !== habitId)
            await fetchArchivedHabits()
        } catch (err) {
            throw err
        }
    }

    const unarchiveHabit = async (habitId) => {
        try {
            await api.post(`habits/${habitId}/unarchive/`)
            archivedHabits.value = archivedHabits.value.filter(h => h.id !== habitId)
        } catch (err) {
            throw err
        }
    }

    const updateHabit = async (habitId, payload) => {
        try {
            await api.patch(`habits/${habitId}/`, payload)
            const habitIndex = habits.value.findIndex(h => h.id === habitId)
            if (habitIndex !== -1) {
                habits.value[habitIndex] = { ...habits.value[habitIndex], ...payload }
            }
        } catch (err) {
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
        } catch (err) {
            throw err
        } finally {
            setTimeout(() => { habit.is_saving = false }, 500)
        }
    }

    return {
        habits,
        archivedHabits,
        isLoadingHabits,
        fetchHabits,
        fetchArchivedHabits,
        addHabit,
        archiveHabit,
        unarchiveHabit,
        deleteActiveHabit: async (habitId) => {
            try {
                await api.delete(`habits/${habitId}/`)
                habits.value = habits.value.filter(h => h.id !== habitId)
            } catch (err) {
                throw err
            }
        },
        deleteArchivedHabit: async (habitId) => {
            try {
                await api.delete(`habits/${habitId}/`)
                archivedHabits.value = archivedHabits.value.filter(h => h.id !== habitId)
            } catch (err) {
                throw err
            }
        },
        updateHabit,
        saveCompletion
    }
}
