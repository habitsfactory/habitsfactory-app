// composables/useCategories.js
import { ref } from 'vue'
import api from '@/services/api'
import { notifyError } from '@/composables/useToast'

// Module-level state: every tab/view shares the same categories and the same
// ordering, so reordering in one tab is reflected in the others.
const categories = ref([])
const categoryOrder = ref([])
const isSavingCategory = ref(false)
const isDeletingCategory = ref(null)

const ORDER_STORAGE_KEY = 'categoryOrder'

// The server only stores the order of real categories; the position of the
// "uncategorized" group is remembered locally.
const savedUncategorizedIndex = (max) => {
    try {
        const saved = JSON.parse(localStorage.getItem(ORDER_STORAGE_KEY) || 'null')
        if (Array.isArray(saved)) {
            const index = saved.indexOf('uncategorized')
            if (index !== -1) return Math.min(index, max)
        }
    } catch {
        // ignore malformed storage
    }
    return max
}

const fetchCategories = async () => {
    try {
        const res = await api.get('categories/')
        categories.value = res.data.sort((a, b) => {
            if (a.order === b.order) return a.id - b.id
            return (a.order || 0) - (b.order || 0)
        })
        const order = categories.value.map(c => c.id)
        order.splice(savedUncategorizedIndex(order.length), 0, 'uncategorized')
        categoryOrder.value = order
    } catch (err) {
        notifyError(err, 'loadFailed')
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
    } finally {
        isSavingCategory.value = false
    }
}

const deleteCategory = async (categoryId) => {
    isDeletingCategory.value = categoryId
    try {
        await api.delete(`categories/${categoryId}/`)
        await fetchCategories()
    } finally {
        isDeletingCategory.value = null
    }
}

const updateCategory = async (categoryId, name) => {
    await api.patch(`categories/${categoryId}/`, { name })
}

const saveLayoutToServer = async () => {
    try {
        localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(categoryOrder.value))
        const layoutData = categoryOrder.value
            .filter(id => id !== 'uncategorized')
            .map((id, index) => ({ id, order: index }))
        await api.post('categories/update_layout/', { layout: layoutData })
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

/**
 * Group a list of habits by category, following the user's category order.
 * `getCategoryId` extracts the category id from a habit (the tracking and
 * summary endpoints shape habits differently).
 */
const groupByCategory = (habitList, getCategoryId, uncategorizedLabel) => {
    if (habitList.length === 0) return []

    const byId = new Map(categories.value.map(cat => [cat.id, cat]))
    const order = categoryOrder.value.length > 0
        ? categoryOrder.value
        : [...categories.value.map(c => c.id), 'uncategorized']

    const groups = []
    order.forEach(id => {
        if (id === 'uncategorized') {
            // Also catches habits whose category is not loaded (yet)
            const items = habitList.filter(h => !byId.has(getCategoryId(h)))
            if (items.length > 0) {
                groups.push({ id, name: uncategorizedLabel, habits: items })
            }
        } else if (byId.has(id)) {
            const items = habitList.filter(h => getCategoryId(h) === id)
            if (items.length > 0) {
                groups.push({ id, name: byId.get(id).name, habits: items })
            }
        }
    })
    return groups
}

export function useCategories() {
    return {
        categories,
        categoryOrder,
        isSavingCategory,
        isDeletingCategory,
        fetchCategories,
        addCategory,
        deleteCategory,
        updateCategory,
        saveLayoutToServer,
        groupByCategory
    }
}
