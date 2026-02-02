<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import { useHabits } from '@/composables/useHabits'
import { useCategories } from '@/composables/useCategories'
import { useTags } from '@/composables/useTags'
import { useCookies } from '@/composables/useCookies'
import * as LucideIcons from 'lucide-vue-next'
import { RefreshCw, ChevronLeft, ChevronRight, LayoutGrid, List, Star, Plus, Minus, Archive, Trash2, Pencil, CheckCircle2, GripVertical, Filter, ChevronDown, X, Sparkles } from 'lucide-vue-next'
import habitTemplatesData from '@/data/habitTemplates.json'

const { t } = useLanguage()
const { habits, isLoadingHabits, fetchHabits, archiveHabit, deleteActiveHabit, deleteArchivedHabit, saveCompletion, addHabit } = useHabits()
const { categories, categoryOrder, fetchCategories, saveLayoutToServer } = useCategories()
const { tags, fetchTags } = useTags()
const { setCookie, getCookie } = useCookies()

// Date navigation
const currentTrackingDate = ref(new Date())

// View preference
const isCardView = ref(true)

// Dragging for categories
const draggedCategoryId = ref(null)
const dragOverCategoryId = ref(null)

// Filter state
const isFilterExpanded = ref(false)
const selectedCategories = ref([])
const selectedTags = ref([])
const filterSectionRef = ref(null)

// Template modal state
const isTemplateModalOpen = ref(false)
const habitTemplates = habitTemplatesData.categories
const isAddingTemplate = ref(false)

const handleClickOutside = (event) => {
    if (isFilterExpanded.value && filterSectionRef.value && !filterSectionRef.value.contains(event.target)) {
        isFilterExpanded.value = false
    }
}

const hasActiveFilters = computed(() => {
    return selectedCategories.value.length > 0 || selectedTags.value.length > 0
})

const toggleCategoryFilter = (categoryId) => {
    const index = selectedCategories.value.indexOf(categoryId)
    if (index === -1) {
        selectedCategories.value.push(categoryId)
    } else {
        selectedCategories.value.splice(index, 1)
    }
}

const toggleTagFilter = (tagId) => {
    const index = selectedTags.value.indexOf(tagId)
    if (index === -1) {
        selectedTags.value.push(tagId)
    } else {
        selectedTags.value.splice(index, 1)
    }
}

const clearFilters = () => {
    selectedCategories.value = []
    selectedTags.value = []
}

// Load view preference from cookie
const loadViewPreference = () => {
    const saved = getCookie('viewPreference')
    if (saved !== null) {
        isCardView.value = saved === 'card'
    }
}

// Save view preference when it changes
watch(isCardView, (newValue) => {
    setCookie('viewPreference', newValue ? 'card' : 'row')
})

const trackingDateString = computed(() => {
    return currentTrackingDate.value.toISOString().split('T')[0]
})

const canGoToNextDay = computed(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const trackingDay = new Date(currentTrackingDate.value)
    trackingDay.setHours(0, 0, 0, 0)
    return trackingDay.getTime() < today.getTime()
})

const formattedTrackingDate = computed(() => {
    const date = currentTrackingDate.value
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const trackingDay = new Date(date)
    trackingDay.setHours(0, 0, 0, 0)

    if (trackingDay.getTime() === today.getTime()) {
        return t('today')
    }

    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    if (trackingDay.getTime() === yesterday.getTime()) {
        return t('yesterday')
    }

    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    if (trackingDay.getTime() === tomorrow.getTime()) {
        return t('tomorrow')
    }

    return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    })
})

// Filter habits based on selected categories and tags
const filteredHabits = computed(() => {
    let result = habits.value

    // Filter by categories
    if (selectedCategories.value.length > 0) {
        result = result.filter(h => {
            if (selectedCategories.value.includes('uncategorized')) {
                if (!h.category || h.category === null) return true
            }
            return h.category && selectedCategories.value.includes(h.category.id)
        })
    }

    // Filter by tags
    if (selectedTags.value.length > 0) {
        result = result.filter(h => {
            if (!h.tags || h.tags.length === 0) return false
            return h.tags.some(tag => selectedTags.value.includes(tag.id))
        })
    }

    return result
})

// Group habits by category
const groupedHabits = computed(() => {
    const groups = []

    if (filteredHabits.value.length === 0) {
        return groups
    }

    const categoryMap = new Map()
    categories.value.forEach(cat => {
        categoryMap.set(cat.id, cat)
    })

    const uncategorized = filteredHabits.value.filter(h => !h.category || h.category === null)
    const hasUncategorized = uncategorized.length > 0

    let orderedCategoryIds

    if (categoryOrder.value && categoryOrder.value.length > 0) {
        orderedCategoryIds = [...categoryOrder.value]
    } else {
        orderedCategoryIds = hasUncategorized
            ? ['uncategorized', ...categories.value.map(c => c.id)]
            : categories.value.map(c => c.id)
    }

    orderedCategoryIds.forEach(id => {
        if (id === 'uncategorized') {
            if (hasUncategorized) {
                groups.push({
                    id: 'uncategorized',
                    name: t('uncategorized'),
                    habits: uncategorized
                })
            }
        } else {
            const cat = categoryMap.get(id)
            if (cat) {
                const categoryHabits = filteredHabits.value.filter(h => h.category && h.category.id === cat.id)
                if (categoryHabits.length > 0) {
                    groups.push({
                        id: cat.id,
                        name: cat.name,
                        habits: categoryHabits
                    })
                }
            }
        }
    })

    return groups
})

// Navigation functions
const goToPreviousDay = () => {
    const newDate = new Date(currentTrackingDate.value)
    newDate.setDate(newDate.getDate() - 1)
    currentTrackingDate.value = newDate
    fetchHabits(trackingDateString.value)
}

const goToNextDay = () => {
    if (!canGoToNextDay.value) return
    const newDate = new Date(currentTrackingDate.value)
    newDate.setDate(newDate.getDate() + 1)
    currentTrackingDate.value = newDate
    fetchHabits(trackingDateString.value)
}

const goToToday = () => {
    currentTrackingDate.value = new Date()
    fetchHabits(trackingDateString.value)
}

// Get icon component from name
const getIcon = (iconName) => {
    if (!iconName) return LucideIcons.Calendar
    const pascalCase = iconName
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join('')
    return LucideIcons[pascalCase] || LucideIcons.Calendar
}

// Habit completion handlers
const toggleBoolean = (habit) => {
    const newValue = habit.is_completed_today ? 0 : 1
    saveCompletion(habit, newValue, trackingDateString.value)
}

const incrementCounter = (habit) => {
    const newValue = (habit.today_value || 0) + 1
    habit.temp_value = newValue
    saveCompletion(habit, newValue, trackingDateString.value)
}

const decrementCounter = (habit) => {
    const newValue = Math.max(0, (habit.today_value || 0) - 1)
    habit.temp_value = newValue
    saveCompletion(habit, newValue, trackingDateString.value)
}

const updateValue = (habit, value) => {
    const numValue = parseFloat(value) || 0
    habit.temp_value = numValue
    saveCompletion(habit, numValue, trackingDateString.value)
}

const setRating = (habit, rating) => {
    habit.temp_value = rating
    saveCompletion(habit, rating, trackingDateString.value)
}

const handleArchive = async (habitId) => {
    if (confirm(t('confirmArchive'))) {
        await archiveHabit(habitId)
    }
}

const handleDelete = async (habitId) => {
    if (confirm(t('confirmDeletePermanent'))) {
        await deleteActiveHabit(habitId)
    }
}

// Add habit from template
const addHabitFromTemplate = async (template) => {
    isAddingTemplate.value = true
    try {
        await addHabit({
            name: t(template.nameKey) || template.name,
            habit_type: template.habit_type,
            icon: template.icon,
            color: template.color,
            unit: template.unit || null,
            max_value: template.max_value || null
        })
        isTemplateModalOpen.value = false
        fetchHabits(trackingDateString.value)
    } catch (err) {
        console.error('Failed to add habit from template:', err)
    } finally {
        isAddingTemplate.value = false
    }
}

onMounted(() => {
    loadViewPreference()
    fetchCategories()
    fetchTags()
    fetchHabits(trackingDateString.value)
    document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
})

// Dragging of categories
const handleDragStart = (e, categoryId) => {
    draggedCategoryId.value = categoryId
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/html', e.target.innerHTML)
    e.target.style.opacity = '0.4'
}

const handleDragEnd = (e) => {
    e.target.style.opacity = '1'
    draggedCategoryId.value = null
    dragOverCategoryId.value = null
}

const handleDragOver = (e, categoryId) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    dragOverCategoryId.value = categoryId
    return false
}

const handleDragEnter = (e, categoryId) => {
    e.preventDefault()
    dragOverCategoryId.value = categoryId
}

const handleDragLeave = (e) => {
    // Only set to null if we're leaving the category group itself
    // Check if we're moving to a non-category element
    if (e.target.classList && e.target.classList.contains('category-group')) {
        dragOverCategoryId.value = null
    }
}

const handleDrop = (e, targetCategoryId) => {
    e.stopPropagation()
    e.preventDefault()

    console.log('Drop detected:', { draggedCategoryId: draggedCategoryId.value, targetCategoryId })

    if (!draggedCategoryId.value) {
        dragOverCategoryId.value = null
        return
    }

    if (draggedCategoryId.value === targetCategoryId) {
        dragOverCategoryId.value = null
        return
    }

    const newOrder = [...categoryOrder.value]
    const draggedIndex = newOrder.indexOf(draggedCategoryId.value)
    const targetIndex = newOrder.indexOf(targetCategoryId)

    console.log('Indices:', { draggedIndex, targetIndex, newOrderLength: newOrder.length })

    if (draggedIndex !== -1 && targetIndex !== -1) {
        // Remove dragged item
        newOrder.splice(draggedIndex, 1)

        // Calculate insertion index based on direction
        let insertIndex
        if (draggedIndex < targetIndex) {
            // Dragging forward (from earlier to later)
            // After removal, target index shifts down by 1, but we want to insert AFTER it
            insertIndex = targetIndex
        } else {
            // Dragging backward (from later to earlier)
            // Target index doesn't shift, insert before it
            insertIndex = targetIndex
        }

        // Insert at calculated position
        newOrder.splice(insertIndex, 0, draggedCategoryId.value)

        console.log('New order:', newOrder)

        categoryOrder.value = newOrder
        saveLayoutToServer()
    }

    draggedCategoryId.value = null
    dragOverCategoryId.value = null
    return false
}
</script>

<template>
    <div class="space-y-8">
        <!-- Date Navigation -->
        <div
            class="bg-white dark:bg-neutral-800 rounded-4xl py-2 px-6 shadow-lg border border-neutral-100 dark:border-neutral-700 flex items-center justify-between">
            <button @click="goToPreviousDay"
                class="p-2 rounded-xl bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all active:scale-95">
                <ChevronLeft :size="24" class="text-neutral-600 dark:text-neutral-300" stroke-width="2.5" />
            </button>

            <div class="text-center flex-1">
                <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ formattedTrackingDate }}</h2>
                <p class="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5 font-bold">
                    {{ currentTrackingDate.toLocaleDateString('fr', {
                        day: '2-digit', month: '2-digit', year: 'numeric'
                    }) }}
                </p>
                <!-- Today Button (only show if not on today) -->
                <button v-if="formattedTrackingDate !== t('today')" @click="goToToday"
                    class="shrink-0 px-3 py-1 mt-1 bg-primary-600 text-white rounded-xl font-bold text-xs md:text-sm hover:bg-primary-800 transition-all active:scale-95 whitespace-nowrap self-center">
                    {{ t('today') }}
                </button>
            </div>

            <div class="flex items-center gap-3">
                <!-- View Toggle -->
                <button @click="isCardView = !isCardView"
                    class="p-2 rounded-xl bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all active:scale-95">
                    <LayoutGrid v-if="!isCardView" :size="24" class="text-neutral-600 dark:text-neutral-300"
                        stroke-width="2.5" />
                    <List v-else :size="24" class="text-neutral-600 dark:text-neutral-300" stroke-width="2.5" />
                </button>

                <button @click="goToNextDay" :disabled="!canGoToNextDay" :class="[
                    'p-2 rounded-xl transition-all active:scale-95',
                    canGoToNextDay
                        ? 'bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600'
                        : 'bg-neutral-50 dark:bg-neutral-800 cursor-not-allowed opacity-50'
                ]">
                    <ChevronRight :size="24" class="text-neutral-600 dark:text-neutral-300" stroke-width="2.5" />
                </button>
            </div>
        </div>

        <!-- Filter Section -->
        <div ref="filterSectionRef" class="space-y-2">
            <!-- Filter Toggle Button -->
            <button @click="isFilterExpanded = !isFilterExpanded" :class="[
                'w-full flex items-center justify-between px-6 py-2 rounded-2xl font-bold transition-all',
                hasActiveFilters
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border-2 border-primary-300 dark:border-primary-700'
                    : 'bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 border border-neutral-100 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700'
            ]">
                <div class="flex items-center gap-3">
                    <Filter :size="20" stroke-width="2.5" />
                    <span>{{ t('filters') }}</span>
                    <span v-if="hasActiveFilters"
                        class="px-2 py-0.5 text-xs rounded-full bg-primary-600 text-white font-bold">
                        {{ selectedCategories.length + selectedTags.length }}
                    </span>
                </div>
                <ChevronDown :size="20" :class="['transition-transform', isFilterExpanded ? 'rotate-180' : '']" />
            </button>

            <!-- Expanded Filter Panel -->
            <Transition name="slide">
                <div v-if="isFilterExpanded"
                    class="bg-white dark:bg-neutral-800 rounded-3xl p-6 shadow-lg border border-neutral-100 dark:border-neutral-700 space-y-6">

                    <!-- Clear Filters Button -->
                    <div v-if="hasActiveFilters" class="flex justify-end">
                        <button @click="clearFilters"
                            class="flex items-center gap-2 px-4 py-2 text-sm font-bold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors">
                            <X :size="16" />
                            {{ t('clearFilters') }}
                        </button>
                    </div>

                    <!-- Categories Filter -->
                    <div class="space-y-3">
                        <h4 class="text-xs font-black uppercase tracking-widest text-neutral-400">
                            {{ t('categories') }}
                        </h4>
                        <div class="flex flex-wrap gap-2">
                            <!-- Uncategorized option -->
                            <button @click="toggleCategoryFilter('uncategorized')" :class="[
                                'px-4 py-2 rounded-xl font-bold text-sm transition-all',
                                selectedCategories.includes('uncategorized')
                                    ? 'bg-primary-600 text-white'
                                    : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600'
                            ]">
                                {{ t('uncategorized') }}
                            </button>
                            <button v-for="category in categories" :key="category.id"
                                @click="toggleCategoryFilter(category.id)" :class="[
                                    'px-4 py-2 rounded-xl font-bold text-sm transition-all',
                                    selectedCategories.includes(category.id)
                                        ? 'bg-primary-600 text-white'
                                        : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600'
                                ]">
                                {{ category.name }}
                            </button>
                        </div>
                    </div>

                    <!-- Tags Filter -->
                    <div class="space-y-3">
                        <h4 class="text-xs font-black uppercase tracking-widest text-neutral-400">
                            {{ t('tags') }}
                        </h4>
                        <div class="flex flex-wrap gap-2">
                            <button v-for="tag in tags" :key="tag.id" @click="toggleTagFilter(tag.id)" :class="[
                                'px-4 py-2 rounded-xl font-bold text-sm transition-all flex items-center gap-2',
                                selectedTags.includes(tag.id)
                                    ? 'ring-2 ring-offset-2 ring-primary-500'
                                    : 'hover:opacity-80'
                            ]" :style="{
                                    backgroundColor: tag.color + '20',
                                    color: tag.color
                                }">
                                <span class="w-2 h-2 rounded-full" :style="{ backgroundColor: tag.color }"></span>
                                {{ tag.name }}
                            </button>
                            <p v-if="tags.length === 0" class="text-sm text-neutral-400 dark:text-neutral-500">
                                {{ t('noTags') }}
                            </p>
                        </div>
                    </div>
                </div>
            </Transition>
        </div>

        <!-- Loading State -->
        <div v-if="isLoadingHabits" class="flex items-center justify-center py-20">
            <RefreshCw :size="40" class="animate-spin text-yellow-500" />
        </div>

        <!-- Habit Groups -->
        <template v-else>
            <div v-for="group in groupedHabits" :key="group.id" class="space-y-4 category-group"
                :class="{ 'opacity-50': draggedCategoryId === group.id, 'ring-2 ring-yellow-500 ring-offset-2 rounded-2xl': dragOverCategoryId === group.id && draggedCategoryId !== group.id }"
                @dragover="handleDragOver($event, group.id)" @dragenter="handleDragEnter($event, group.id)"
                @dragleave="handleDragLeave" @drop="handleDrop($event, group.id)">
                <!-- Group Header -->
                <div class="flex items-center gap-3 px-2 cursor-grab active:cursor-grabbing"
                    draggable="true" @dragstart="handleDragStart($event, group.id)" @dragend="handleDragEnd">
                    <GripVertical :size="20"
                        class="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 shrink-0" />
                    <div class="w-2 h-6 bg-yellow-500 rounded-full shrink-0"></div>
                    <h3 class="text-xl font-black text-neutral-900 dark:text-white uppercase tracking-tight shrink-0">
                        {{ group.name }}
                    </h3>
                    <div class="flex-1 h-px bg-linear-to-r from-neutral-300 dark:from-neutral-600 to-transparent"></div>
                    <span class="text-sm font-medium text-neutral-400 dark:text-neutral-500 shrink-0">
                        {{ group.habits.length }} {{ group.habits.length === 1 ? (t('habit')) : (t('habits')) }}
                    </span>
                </div>

                <!-- Card View -->
                <div v-if="isCardView" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div v-for="habit in group.habits" :key="habit.id"
                        class="bg-white dark:bg-neutral-800 rounded-4xl p-6 shadow-lg border border-neutral-100 dark:border-neutral-700 hover:shadow-xl transition-all">
                        <!-- Habit Header -->
                        <div class="flex items-center gap-3 mb-4">
                            <div class="p-3 rounded-2xl" :style="{ backgroundColor: habit.color + '20' }">
                                <component :is="getIcon(habit.icon)" :size="24" :style="{ color: habit.color }"
                                    stroke-width="2.5" />
                            </div>
                            <div class="flex-1">
                                <h4 class="font-black text-neutral-900 dark:text-white text-lg">{{ habit.name }}</h4>
                                <p v-if="habit.unit" class="text-xs font-bold text-neutral-400 uppercase tracking-wide">
                                    {{ habit.unit }}
                                </p>
                            </div>
                            <div v-if="habit.is_saving">
                                <RefreshCw :size="20" class="animate-spin text-yellow-500" />
                            </div>
                        </div>

                        <!-- Boolean Habit -->
                        <div v-if="habit.habit_type === 'boolean'" class="flex justify-center">
                            <button @click="toggleBoolean(habit)" :class="[
                                'w-full py-4 rounded-2xl font-black text-lg transition-all active:scale-95',
                                habit.is_completed_today
                                    ? 'bg-green-500 text-white'
                                    : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300'
                            ]">
                                <CheckCircle2 v-if="habit.is_completed_today" :size="24" class="mx-auto" />
                                <span v-else>{{ t('markComplete') }}</span>
                            </button>
                        </div>

                        <!-- Counter Habit -->
                        <div v-else-if="habit.habit_type === 'counter'" class="flex items-center justify-center gap-4">
                            <button @click="decrementCounter(habit)"
                                class="p-3 rounded-xl bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all active:scale-95">
                                <Minus :size="20" class="text-neutral-600 dark:text-neutral-300" />
                            </button>
                            <span class="text-4xl font-black" :style="{ color: habit.color }">
                                {{ habit.today_value || 0 }}
                            </span>
                            <button @click="incrementCounter(habit)"
                                class="p-3 rounded-xl bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all active:scale-95">
                                <Plus :size="20" class="text-neutral-600 dark:text-neutral-300" />
                            </button>
                        </div>

                        <!-- Value Habit -->
                        <div v-else-if="habit.habit_type === 'value'" class="space-y-2">
                            <input :value="habit.today_value || ''" @change="updateValue(habit, $event.target.value)"
                                type="number" step="1" placeholder="0"
                                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-100 dark:border-neutral-600 rounded-2xl px-4 py-3 text-center text-2xl font-black outline-none focus:border-yellow-500 transition text-neutral-900 dark:text-white"
                                :style="{ color: habit.color }" />
                            <p v-if="habit.unit" class="text-center text-sm font-bold text-neutral-400">{{ habit.unit }}
                            </p>
                        </div>

                        <!-- Rating Habit -->
                        <div v-else-if="habit.habit_type === 'rating'" class="flex justify-center gap-1">
                            <button v-for="star in (habit.max_value || 5)" :key="star" @click="setRating(habit, star)"
                                class="p-1 transition-transform hover:scale-110 active:scale-95">
                                <Star :size="28" :fill="star <= (habit.today_value || 0) ? habit.color : 'transparent'"
                                    :style="{ color: habit.color }" stroke-width="2" />
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Row View -->
                <div v-else class="space-y-3">
                    <div v-for="habit in group.habits" :key="habit.id"
                        class="bg-white dark:bg-neutral-800 rounded-2xl p-4 shadow-md border border-neutral-100 dark:border-neutral-700 flex items-center gap-4">
                        <!-- Icon -->
                        <div class="p-2 rounded-xl" :style="{ backgroundColor: habit.color + '20' }">
                            <component :is="getIcon(habit.icon)" :size="20" :style="{ color: habit.color }"
                                stroke-width="2.5" />
                        </div>

                        <!-- Name -->
                        <div class="flex-1">
                            <h4 class="font-bold text-neutral-900 dark:text-white">{{ habit.name }}</h4>
                        </div>

                        <!-- Compact Controls -->
                        <div class="flex items-center gap-3">
                            <!-- Loading -->
                            <RefreshCw v-if="habit.is_saving" :size="16" class="animate-spin text-yellow-500" />

                            <!-- Boolean -->
                            <button v-if="habit.habit_type === 'boolean'" @click="toggleBoolean(habit)" :class="[
                                'px-4 py-2 rounded-xl font-bold transition-all active:scale-95',
                                habit.is_completed_today
                                    ? 'bg-green-500 text-white'
                                    : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300'
                            ]">
                                <CheckCircle2 v-if="habit.is_completed_today" :size="20" />
                                <span v-else>{{ t('done') }}</span>
                            </button>

                            <!-- Counter -->
                            <template v-else-if="habit.habit_type === 'counter'">
                                <button @click="decrementCounter(habit)"
                                    class="p-2 rounded-lg bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all">
                                    <Minus :size="16" />
                                </button>
                                <span class="text-xl font-black min-w-12 text-center" :style="{ color: habit.color }">
                                    {{ habit.today_value || 0 }}
                                </span>
                                <button @click="incrementCounter(habit)"
                                    class="p-2 rounded-lg bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all">
                                    <Plus :size="16" />
                                </button>
                            </template>

                            <!-- Value -->
                            <input v-else-if="habit.habit_type === 'value'" :value="habit.today_value || ''"
                                @change="updateValue(habit, $event.target.value)" type="number" step="1"
                                placeholder="0"
                                class="w-24 bg-neutral-50 dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 rounded-xl px-3 py-2 text-center font-bold outline-none focus:border-yellow-500 transition text-neutral-900 dark:text-white" />

                            <!-- Rating -->
                            <div v-else-if="habit.habit_type === 'rating'" class="flex gap-0.5">
                                <button v-for="star in (habit.max_value || 5)" :key="star"
                                    @click="setRating(habit, star)" class="p-0.5 transition-transform hover:scale-110">
                                    <Star :size="20"
                                        :fill="star <= (habit.today_value || 0) ? habit.color : 'transparent'"
                                        :style="{ color: habit.color }" stroke-width="2" />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Empty State -->
            <div v-if="groupedHabits.length === 0"
                class="bg-white dark:bg-neutral-800 rounded-4xl p-16 shadow-lg border border-neutral-100 dark:border-neutral-700 text-center">
                <template v-if="hasActiveFilters">
                    <div class="text-6xl mb-4">🔍</div>
                    <h3 class="text-2xl font-black text-neutral-900 dark:text-white mb-2">
                        {{ t('noMatchingHabits') }}
                    </h3>
                    <p class="text-neutral-500 dark:text-neutral-400 mb-4">
                        {{ t('noHabitsMatchFilters') }}
                    </p>
                    <button @click="clearFilters"
                        class="px-6 py-3 bg-red-500 text-white rounded-2xl font-bold hover:bg-red-400 transition-all">
                        {{ t('clearFilters') }}
                    </button>
                </template>
                <template v-else>
                    <div class="text-6xl mb-4">🎯</div>
                    <h3 class="text-2xl font-black text-neutral-900 dark:text-white mb-2">{{ t('noHabitsYet') }}
                    </h3>
                    <p class="text-neutral-500 dark:text-neutral-400 mb-6">{{ t('createFirstHabit') }}</p>
                    <button @click="isTemplateModalOpen = true"
                        class="inline-flex items-center gap-3 px-8 py-4 bg-primary-600 text-white rounded-2xl font-bold hover:bg-primary-700 transition-all shadow-lg active:scale-95">
                        <Sparkles :size="20" stroke-width="2.5" />
                        {{ t('addFromTemplates') }}
                    </button>
                </template>
            </div>
        </template>

        <!-- Template Modal -->
        <Teleport to="body">
            <Transition name="fade">
                <div v-if="isTemplateModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div class="absolute inset-0 bg-neutral-900/60 backdrop-blur-md" @click="isTemplateModalOpen = false"></div>
                    <div class="relative z-10 bg-white dark:bg-neutral-800 w-full max-w-4xl max-h-[85vh] rounded-4xl shadow-2xl overflow-hidden flex flex-col">
                        <!-- Modal Header -->
                        <div class="shrink-0 p-8 pb-4 border-b border-neutral-100 dark:border-neutral-700">
                            <div class="absolute top-0 left-0 right-0 h-2 bg-primary-600"></div>
                            <div class="flex justify-between items-center">
                                <div>
                                    <h2 class="text-3xl font-black text-neutral-900 dark:text-white">{{ t('habitTemplates') }}</h2>
                                    <p class="text-neutral-500 dark:text-neutral-400 mt-1">{{ t('selectHabitTemplate') }}</p>
                                </div>
                                <button @click="isTemplateModalOpen = false"
                                    class="text-neutral-300 hover:text-neutral-900 dark:hover:text-white transition p-2">
                                    <X :size="28" />
                                </button>
                            </div>
                        </div>

                        <!-- Modal Content - Scrollable -->
                        <div class="flex-1 overflow-y-auto p-8 space-y-8">
                            <!-- Loading Overlay -->
                            <div v-if="isAddingTemplate" class="absolute inset-0 bg-white/80 dark:bg-neutral-800/80 flex items-center justify-center z-10">
                                <RefreshCw :size="40" class="animate-spin text-primary-600" />
                            </div>

                            <!-- Category Groups -->
                            <div v-for="category in habitTemplates" :key="category.id" class="space-y-4">
                                <!-- Category Header -->
                                <div class="flex items-center gap-3">
                                    <div class="p-2 rounded-xl" :style="{ backgroundColor: category.color + '20' }">
                                        <component :is="getIcon(category.icon)" :size="20" :style="{ color: category.color }" stroke-width="2.5" />
                                    </div>
                                    <h3 class="text-lg font-black text-neutral-900 dark:text-white uppercase tracking-tight">
                                        {{ t(category.nameKey) || category.name }}
                                    </h3>
                                    <div class="flex-1 h-px bg-linear-to-r from-neutral-200 dark:from-neutral-700 to-transparent"></div>
                                </div>

                                <!-- Habit Cards Grid -->
                                <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                    <button v-for="habit in category.habits" :key="habit.nameKey"
                                        @click="addHabitFromTemplate(habit)"
                                        :disabled="isAddingTemplate"
                                        class="bg-neutral-50 dark:bg-neutral-700/50 hover:bg-white dark:hover:bg-neutral-700 border border-neutral-100 dark:border-neutral-600 hover:border-neutral-200 dark:hover:border-neutral-500 rounded-2xl p-4 text-left transition-all hover:shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed group">
                                        <!-- Habit Icon & Name -->
                                        <div class="flex items-center gap-3 mb-2">
                                            <div class="p-2 rounded-xl transition-colors" :style="{ backgroundColor: habit.color + '20' }">
                                                <component :is="getIcon(habit.icon)" :size="18" :style="{ color: habit.color }" stroke-width="2.5" />
                                            </div>
                                            <span class="font-bold text-neutral-900 dark:text-white text-sm truncate">
                                                {{ t(habit.nameKey) || habit.name }}
                                            </span>
                                        </div>
                                        <!-- Habit Type Badge -->
                                        <div class="flex items-center gap-2">
                                            <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-lg"
                                                :class="{
                                                    'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400': habit.habit_type === 'boolean',
                                                    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400': habit.habit_type === 'counter',
                                                    'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400': habit.habit_type === 'value',
                                                    'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400': habit.habit_type === 'rating'
                                                }">
                                                {{ t(habit.habit_type) }}
                                            </span>
                                            <span v-if="habit.unit" class="text-[10px] text-neutral-400 dark:text-neutral-500 font-medium">
                                                {{ habit.unit }}
                                            </span>
                                        </div>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </Transition>
        </Teleport>
    </div>
</template>

<style scoped>
.category-group {
    transition: all 0.2s ease;
    user-select: none;
}

.category-group[draggable="true"] {
    touch-action: none;
}

/* Filter panel slide transition */
.slide-enter-active,
.slide-leave-active {
    transition: all 0.3s ease;
    overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}

/* Modal fade transition */
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
