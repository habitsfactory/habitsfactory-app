<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import { useLanguage } from '@/composables/useLanguage'
import { useCategories } from '@/composables/useCategories'
import * as LucideIcons from 'lucide-vue-next'
import { RefreshCw, GripVertical } from 'lucide-vue-next'

const { t } = useLanguage()
const { categories, categoryOrder, fetchCategories, saveLayoutToServer } = useCategories()

// Cookie helpers
const COOKIE_NAME = 'summaryDateRange'

const getCookie = (name) => {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return match ? match[2] : null
}

const setCookie = (name, value, days = 365) => {
  const expires = new Date(Date.now() + days * 864e5).toUTCString()
  document.cookie = `${name}=${value}; expires=${expires}; path=/`
}

// Date range options
const dateRangeOptions = [
  { key: 'thisWeek', label: t('thisWeek'), tooltip: t('thisWeekTooltip') },
  { key: 'thisMonth', label: t('thisMonth'), tooltip: t('thisMonthTooltip') },
  { key: 'last7Days', label: t('last7Days'), tooltip: t('last7DaysTooltip') },
  { key: 'last30Days', label: t('last30Days'), tooltip: t('last30DaysTooltip') }
]

const validRangeKeys = dateRangeOptions.map(o => o.key)
const savedRange = getCookie(COOKIE_NAME)
const selectedRange = ref(validRangeKeys.includes(savedRange) ? savedRange : 'last30Days')

// Summary state
const summaryData = ref({
  boolean: [],
  counter: [],
  value: [],
  rating: []
})
const isFetchingSummary = ref(false)
const summaryDays = ref(30)

// Dragging for categories
const draggedCategoryId = ref(null)
const dragOverCategoryId = ref(null)

// Combine all habits and group by category
const groupedHabits = computed(() => {
  const allHabits = [
    ...summaryData.value.boolean.map(h => ({ ...h, habit_type: 'boolean' })),
    ...summaryData.value.counter.map(h => ({ ...h, habit_type: 'counter' })),
    ...summaryData.value.value.map(h => ({ ...h, habit_type: 'value' })),
    ...summaryData.value.rating.map(h => ({ ...h, habit_type: 'rating' }))
  ]

  if (allHabits.length === 0) return []

  const groups = []
  const categoryMap = new Map()
  categories.value.forEach(cat => {
    categoryMap.set(cat.id, cat)
  })

  const uncategorized = allHabits.filter(h => !h.category_id)
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
        const categoryHabits = allHabits.filter(h => h.category_id === cat.id)
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

// Check if there's any data
const hasAnyData = computed(() => {
  return summaryData.value.boolean.length > 0 ||
    summaryData.value.counter.length > 0 ||
    summaryData.value.value.length > 0 ||
    summaryData.value.rating.length > 0
})

// Get icon component from name
const getIcon = (iconName) => {
  if (!iconName) return LucideIcons.Calendar
  const pascalCase = iconName
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('')
  return LucideIcons[pascalCase] || LucideIcons.Calendar
}

// Drag handlers
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
  if (e.target.classList && e.target.classList.contains('category-group')) {
    dragOverCategoryId.value = null
  }
}

const handleDrop = (e, targetCategoryId) => {
  e.stopPropagation()
  e.preventDefault()

  if (!draggedCategoryId.value || draggedCategoryId.value === targetCategoryId) {
    dragOverCategoryId.value = null
    return
  }

  const newOrder = [...categoryOrder.value]
  const draggedIndex = newOrder.indexOf(draggedCategoryId.value)
  const targetIndex = newOrder.indexOf(targetCategoryId)

  if (draggedIndex !== -1 && targetIndex !== -1) {
    newOrder.splice(draggedIndex, 1)
    const insertIndex = draggedIndex < targetIndex ? targetIndex : targetIndex
    newOrder.splice(insertIndex, 0, draggedCategoryId.value)
    categoryOrder.value = newOrder
    saveLayoutToServer()
  }

  draggedCategoryId.value = null
  dragOverCategoryId.value = null
  return false
}

// Calculate date range based on selected option
const getDateRange = () => {
  const endDate = new Date()
  const startDate = new Date()

  switch (selectedRange.value) {
    case 'thisWeek': {
      // Start from Monday of current week
      const day = startDate.getDay()
      const diff = day === 0 ? 6 : day - 1 // Adjust for Sunday
      startDate.setDate(startDate.getDate() - diff)
      break
    }
    case 'thisMonth': {
      // Start from first day of current month
      startDate.setDate(1)
      break
    }
    case 'last7Days': {
      startDate.setDate(startDate.getDate() - 6) // -6 to include today
      break
    }
    case 'last30Days':
    default: {
      startDate.setDate(startDate.getDate() - 29) // -29 to include today
      break
    }
  }

  // Reset time to start of day for startDate
  startDate.setHours(0, 0, 0, 0)

  return { startDate, endDate }
}

// Fetch summary data from API
const fetchSummaryData = async () => {
  isFetchingSummary.value = true
  try {
    const { startDate, endDate } = getDateRange()

    // Calculate number of days in range
    summaryDays.value = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24))

    const response = await api.get('habits/summary/', {
      params: {
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0]
      }
    })
    summaryData.value = {
      boolean: response.data.boolean || [],
      counter: response.data.counter || [],
      value: response.data.value || [],
      rating: response.data.rating || []
    }
  } catch (err) {
  } finally {
    isFetchingSummary.value = false
  }
}

// Handle date range change
const onRangeChange = (rangeKey) => {
  selectedRange.value = rangeKey
  setCookie(COOKIE_NAME, rangeKey)
  fetchSummaryData()
}

// Expose fetchSummaryData so parent can trigger it when tab becomes active
defineExpose({ fetchSummaryData })

onMounted(() => {
  fetchCategories()
  fetchSummaryData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-linear-to-r from-primary-600 to-neutral-950 rounded-4xl p-6 shadow-xl">
      <div class="flex justify-between items-center mb-2">
        <div>
          <h2 class="text-3xl font-black text-white mb-2">{{ t('summaryView') }}</h2>
          <p class="text-primary-100 font-medium">{{ t('retrospectiveAnalysis') }}</p>
          <!-- Date Range Selector -->
          <div class="pt-2 flex flex-wrap gap-2">
            <button v-for="option in dateRangeOptions" :key="option.key" @click="onRangeChange(option.key)"
              :title="option.tooltip" :class="[
                'rounded-xl font-bold text-sm transition-all',
                selectedRange === option.key
                  ? 'bg-white text-primary-600 shadow-lg'
                  : 'bg-primary-700/50 text-primary-100 hover:bg-primary-700'
              ]">
              {{ option.label }}
            </button>
          </div>
        </div>


        <div class="text-right">
          <p class="text-5xl font-black text-white">{{ summaryDays }}</p>
          <p class="text-primary-100 font-bold uppercase tracking-wide">{{ t('days') }}</p>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isFetchingSummary" class="flex items-center justify-center py-20">
      <RefreshCw :size="40" class="animate-spin text-primary-500" />
    </div>

    <!-- Summary Content -->
    <div v-else class="space-y-6">
      <!-- Category Groups -->
      <div v-for="group in groupedHabits" :key="group.id" class="space-y-4 category-group"
        :class="{ 'opacity-50': draggedCategoryId === group.id, 'ring-2 ring-primary-500 ring-offset-2 rounded-2xl': dragOverCategoryId === group.id && draggedCategoryId !== group.id }"
        @dragover="handleDragOver($event, group.id)" @dragenter="handleDragEnter($event, group.id)"
        @dragleave="handleDragLeave" @drop="handleDrop($event, group.id)">

        <!-- Group Header -->
        <div class="flex items-center gap-3 px-2 cursor-grab active:cursor-grabbing" draggable="true"
          @dragstart="handleDragStart($event, group.id)" @dragend="handleDragEnd">
          <GripVertical :size="20"
            class="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 shrink-0" />
          <div class="w-2 h-6 bg-primary-500 rounded-full shrink-0"></div>
          <h3 class="text-xl font-black text-neutral-900 dark:text-white uppercase tracking-tight shrink-0">
            {{ group.name }}
          </h3>
          <div class="flex-1 h-px bg-linear-to-r from-neutral-300 dark:from-neutral-600 to-transparent"></div>
          <span class="text-sm font-medium text-neutral-400 dark:text-neutral-500 shrink-0">
            {{ group.habits.length }} {{ group.habits.length === 1 ? t('habit') : t('habits') }}
          </span>
        </div>

        <!-- Habits Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="habit in group.habits" :key="habit.habit_id"
            class="bg-white dark:bg-neutral-800 rounded-4xl p-6 shadow-lg border border-neutral-100 dark:border-neutral-700 hover:shadow-xl transition-all">

            <!-- Habit Header -->
            <div class="flex items-center gap-3 mb-4">
              <div class="p-3 rounded-2xl" :style="{ backgroundColor: habit.color + '20' }">
                <component :is="getIcon(habit.icon)" :size="24" :style="{ color: habit.color }" stroke-width="2.5" />
              </div>
              <div class="flex-1">
                <h4 class="font-black text-neutral-900 dark:text-white text-lg">{{ habit.habit_name }}</h4>
                <div v-if="habit.tags && habit.tags.length > 0" class="flex flex-wrap gap-1 mt-1">
                  <span v-for="tag in habit.tags" :key="tag.id"
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold"
                    :style="{ backgroundColor: tag.color + '20', color: tag.color }">
                    {{ tag.name }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Boolean Habit Metrics -->
            <div v-if="habit.habit_type === 'boolean'" class="space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-neutral-500 dark:text-neutral-400 text-sm font-bold">Completion Rate</span>
                <span class="text-2xl font-black" :style="{ color: habit.color }">
                  {{ habit.metrics.completion_rate }}%
                </span>
              </div>
              <div class="h-2 bg-neutral-100 dark:bg-neutral-700 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all" :style="{
                  width: habit.metrics.completion_rate + '%',
                  backgroundColor: habit.color
                }"></div>
              </div>
              <div class="grid grid-cols-2 gap-3 pt-2">
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-2xl font-black text-neutral-900 dark:text-white">
                    {{ habit.metrics.total_completions }}
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">{{ t('completed') }}</div>
                </div>
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-2xl font-black text-neutral-900 dark:text-white">
                    {{ habit.metrics.streak }}
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">Day Streak</div>
                </div>
              </div>
              <div class="text-center text-xs text-neutral-400 font-bold">
                Last {{ habit.metrics.days_in_range }} days
              </div>
            </div>

            <!-- Counter Habit Metrics -->
            <div v-else-if="habit.habit_type === 'counter'" class="space-y-3">
              <div class="text-center p-4 rounded-2xl" :style="{ backgroundColor: habit.color + '10' }">
                <div class="text-4xl font-black" :style="{ color: habit.color }">
                  {{ habit.metrics.total }}
                </div>
                <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide mt-1">Total Count</div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-xl font-black text-neutral-900 dark:text-white">
                    {{ habit.metrics.average }}
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">Avg/Day</div>
                </div>
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-xl font-black text-neutral-900 dark:text-white">
                    {{ habit.metrics.max }}
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">Best Day</div>
                </div>
              </div>
              <div class="text-center text-xs text-neutral-400 font-bold">
                Tracked {{ habit.metrics.days_tracked }}/{{ habit.metrics.days_in_range }} days
              </div>
            </div>

            <!-- Value Habit Metrics -->
            <div v-else-if="habit.habit_type === 'value'" class="space-y-3">
              <div class="text-center p-4 rounded-2xl" :style="{ backgroundColor: habit.color + '10' }">
                <div class="text-4xl font-black" :style="{ color: habit.color }">
                  {{ habit.metrics.total }} {{ habit.metrics.unit || '' }}
                </div>
                <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide mt-1">Total</div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-xl font-black text-neutral-900 dark:text-white">
                    {{ habit.metrics.average }} {{ habit.metrics.unit || '' }}
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">Avg/Day</div>
                </div>
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-xl font-black text-neutral-900 dark:text-white">
                    {{ habit.metrics.max_value }} {{ habit.metrics.unit || '' }}
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">Longest</div>
                </div>
              </div>
              <div class="text-center text-xs text-neutral-400 font-bold">
                Tracked {{ habit.metrics.days_tracked }}/{{ habit.metrics.days_in_range }} days
              </div>
            </div>

            <!-- Rating Habit Metrics -->
            <div v-else-if="habit.habit_type === 'rating'" class="space-y-3">
              <div class="text-center p-4 rounded-2xl" :style="{ backgroundColor: habit.color + '10' }">
                <div class="text-4xl font-black" :style="{ color: habit.color }">
                  {{ habit.metrics.average }}/{{ habit.metrics.max_value }}
                </div>
                <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide mt-1">Average Rating</div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-xl font-black text-green-600 dark:text-green-400">
                    {{ habit.metrics.max }}★
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">Best</div>
                </div>
                <div class="text-center p-3 bg-neutral-50 dark:bg-neutral-700 rounded-xl">
                  <div class="text-xl font-black text-red-600 dark:text-red-400">
                    {{ habit.metrics.min }}★
                  </div>
                  <div class="text-xs font-bold text-neutral-400 uppercase tracking-wide">Lowest</div>
                </div>
              </div>
              <div class="text-center text-xs text-neutral-400 font-bold">
                Tracked {{ habit.metrics.days_tracked }}/{{ habit.metrics.days_in_range }} days
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="!hasAnyData"
        class="bg-white dark:bg-neutral-800 rounded-4xl p-16 shadow-lg border border-neutral-100 dark:border-neutral-700 text-center">
        <div class="text-6xl mb-4">📊</div>
        <h3 class="text-2xl font-black text-neutral-900 dark:text-white mb-2">{{ t('noHabitsYet') }}</h3>
        <p class="text-neutral-500 dark:text-neutral-400">{{ t('startTracking') }}</p>
      </div>
    </div>
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
</style>
