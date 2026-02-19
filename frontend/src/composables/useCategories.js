// composables/useCategories.js
import { ref } from 'vue'
import api from '@/services/api'

export function useCategories() {
    const categories = ref([])
    const categoryOrder = ref([])
    const isSavingCategory = ref(false)
    const isDeletingCategory = ref(null)

    const fetchCategories = async () => {
        try {
            const res = await api.get('categories/')
            categories.value = res.data.sort((a, b) => {
                if (a.order === b.order) return a.id - b.id
                return (a.order || 0) - (b.order || 0)
            })
            categoryOrder.value = [...categories.value.map(c => c.id), 'uncategorized']
        } catch (err) {
        }
    }

    const addCategory = async (name) => {
        isSavingCategory.value = true
        try {
            await api.post('categories/', {
                name,
                order: categories.value.length
            })
            await fetchCategories()
        } catch (err) {
            throw err
        } finally {
            isSavingCategory.value = false
        }
    }

    const deleteCategory = async (categoryId) => {
        isDeletingCategory.value = categoryId
        try {
            await api.delete(`categories/${categoryId}/`)
            await fetchCategories()
        } catch (err) {
            throw err
        } finally {
            isDeletingCategory.value = null
        }
    }

    const updateCategory = async (categoryId, name) => {
        try {
            await api.patch(`categories/${categoryId}/`, { name })
        } catch (err) {
            throw err
        }
    }

    const saveLayoutToServer = async () => {
        try {
            localStorage.setItem('categoryOrder', JSON.stringify(categoryOrder.value))
            const layoutData = categoryOrder.value
                .filter(id => id !== 'uncategorized')
                .map((id, index) => ({ id, order: index }))
            await api.post('categories/update_layout/', { layout: layoutData })
        } catch (err) {
        }
    }

    return {
        categories,
        categoryOrder,
        isSavingCategory,
        isDeletingCategory,
        fetchCategories,
        addCategory,
        deleteCategory,
        updateCategory,
        saveLayoutToServer
    }
}
