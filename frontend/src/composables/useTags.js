// composables/useTags.js
import { ref } from 'vue'
import api from '@/services/api'

export function useTags() {
    const tags = ref([])
    const isSavingTag = ref(false)
    const isDeletingTag = ref(null)

    const fetchTags = async () => {
        try {
            const res = await api.get('tags/')
            tags.value = res.data
        } catch (err) {
        }
    }

    const addTag = async (name, color = '#6B7280') => {
        isSavingTag.value = true
        try {
            await api.post('tags/', { name, color })
            await fetchTags()
        } catch (err) {
            throw err
        } finally {
            isSavingTag.value = false
        }
    }

    const deleteTag = async (tagId) => {
        isDeletingTag.value = tagId
        try {
            await api.delete(`tags/${tagId}/`)
            await fetchTags()
        } catch (err) {
            throw err
        } finally {
            isDeletingTag.value = null
        }
    }

    const updateTag = async (tagId, data) => {
        try {
            await api.patch(`tags/${tagId}/`, data)
            await fetchTags()
        } catch (err) {
            throw err
        }
    }

    return {
        tags,
        isSavingTag,
        isDeletingTag,
        fetchTags,
        addTag,
        deleteTag,
        updateTag
    }
}
