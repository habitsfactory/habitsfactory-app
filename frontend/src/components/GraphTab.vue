<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import api from '@/services/api'
import { useDarkMode } from '@/composables/useDarkMode'
import { useLanguage } from '@/composables/useLanguage'
import { Chart, registerables } from 'chart.js'
import 'chartjs-adapter-date-fns'
import CalendarHeatmap from '@/components/CalendarHeatmap.vue'

// Register Chart.js components
Chart.register(...registerables)

const { isDark } = useDarkMode()
const { t } = useLanguage()

// Graph state
const graphStartDate = ref('')
const graphEndDate = ref('')
const chartInstances = ref({
  boolean: null,
  counter: null,
  value: null,
  rating: null
})
const graphData = ref({
  boolean: [],
  counter: [],
  value: [],
  rating: []
})
const isLoading = ref(false)

// Computed property for dynamic years
const quickSelectYears = computed(() => {
  const currentYear = new Date().getFullYear()
  return [
    currentYear,
    currentYear - 1,
    currentYear - 2
  ]
})

// Date range quick select options
const dateRangeOptions = [
  { key: 'thisWeek', label: t('thisWeek'), tooltip: t('thisWeekTooltip') },
  { key: 'thisMonth', label: t('thisMonth'), tooltip: t('thisMonthTooltip') },
  { key: 'last7Days', label: t('last7Days'), tooltip: t('last7DaysTooltip') },
  { key: 'last30Days', label: t('last30Days'), tooltip: t('last30DaysTooltip') },
  { key: 'allTime', label: t('allTime'), tooltip: t('allTimeTooltip') },
  { key: quickSelectYears.value[0], label: quickSelectYears.value[0], tooltip: quickSelectYears.value[0] },
  { key: quickSelectYears.value[1], label: quickSelectYears.value[1], tooltip: quickSelectYears.value[1] },
  { key: quickSelectYears.value[2], label: quickSelectYears.value[2], tooltip: quickSelectYears.value[2] },
]

// Set date range based on quick select option
const setDateRangeOption = (optionKey) => {
  // Handle allTime separately since it's async
  if (optionKey === 'allTime') {
    setAllDataRange()
    return
  }

  let endDate = new Date()
  let startDate = new Date()

  switch (optionKey) {
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
    case 'last30Days': {
      startDate.setDate(startDate.getDate() - 29) // -29 to include today
      break
    }
    default: {
      // Handle year selection
      const year = parseInt(optionKey)
      if (!isNaN(year)) {
        startDate = new Date(year, 0, 1)
        endDate = new Date(year, 11, 31)
      }
      break
    }
  }

  startDate.setHours(0, 0, 0, 0)

  graphStartDate.value = startDate.toISOString().split('T')[0]
  graphEndDate.value = endDate.toISOString().split('T')[0]
}

// Helper function to fill missing dates with 0 values
const fillMissingDates = (data) => {
  if (!data || data.length === 0) return data
  // Fill missing dates for each habit
  return data.map(habitData => {
    if (!habitData.data || habitData.data.length === 0) {
      return habitData
    }

    // Find the min and max dates where this habit has actual data
    const dates = habitData.data.map(point => point.date).sort()
    const minDataDate = dates[0]
    const maxDataDate = dates[dates.length - 1]

    // Create a map of existing data points
    const dataMap = new Map()
    habitData.data.forEach(point => {
      dataMap.set(point.date, point.value)
    })

    // Generate dates only between min and max data dates
    const filledData = []
    const current = new Date(minDataDate)
    const end = new Date(maxDataDate)

    while (current <= end) {
      const dateStr = current.toISOString().split('T')[0]
      filledData.push({
        date: dateStr,
        value: dataMap.get(dateStr) || 0
      })
      current.setDate(current.getDate() + 1)
    }

    return {
      ...habitData,
      data: filledData
    }
  })
}

// Initialize date range for graphs (default: current month)
const initializeDateRange = () => {
  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
  graphStartDate.value = startOfMonth.toISOString().split('T')[0]
  graphEndDate.value = now.toISOString().split('T')[0]
}

// Set date range to entire year
const setYearRange = (year) => {
  graphStartDate.value = `${year}-01-01`
  graphEndDate.value = `${year}-12-31`
}

// Set date range to all available data
const setAllDataRange = async () => {
  try {
    const response = await api.get('habits/date_range/')
    if (response.data.start_date && response.data.end_date) {
      graphStartDate.value = response.data.start_date
      graphEndDate.value = response.data.end_date
    } else {
      // Fallback if no data available
      graphStartDate.value = new Date().toISOString().split('T')[0]
      graphEndDate.value = new Date().toISOString().split('T')[0]
    }
  } catch (err) {
    // Fallback on error
    graphStartDate.value = '2020-01-01'
    graphEndDate.value = new Date().toISOString().split('T')[0]
  }
}

// Fetch graph data from API
const fetchGraphData = async () => {
  if (!graphStartDate.value || !graphEndDate.value) return

  isLoading.value = true
  try {
    const response = await api.get('habits/graph_data/', {
      params: {
        start_date: graphStartDate.value,
        end_date: graphEndDate.value
      }
    })

    // Fill missing dates with 0 for each habit type
    graphData.value = {
      boolean: fillMissingDates(response.data.boolean || []),
      counter: fillMissingDates(response.data.counter || []),
      value: fillMissingDates(response.data.value || []),
      rating: fillMissingDates(response.data.rating || [])
    }

    await renderCharts()
  } catch (err) {
  } finally {
    isLoading.value = false
  }
}

// Render all charts
const renderCharts = async () => {
  // Ensure DOM is fully updated before accessing canvas elements
  await nextTick()

  const habitTypes = ['boolean', 'counter', 'value', 'rating']

  habitTypes.forEach(type => {
    const data = graphData.value[type] || []

    // Destroy existing chart first
    if (chartInstances.value[type]) {
      try {
        chartInstances.value[type].destroy()
      } catch (e) {
        // Ignore destroy errors
      }
      chartInstances.value[type] = null
    }

    // Skip if no data
    if (data.length === 0) return

    const canvasId = `chart-${type}`
    const canvas = document.getElementById(canvasId)

    if (!canvas) {
      return
    }

    const ctx = canvas.getContext('2d')
    if (!ctx) {
      return
    }

    // Prepare datasets - one per habit
    const datasets = data.map(habitData => ({
      label: habitData.habit_name,
      data: habitData.data.map(d => ({ x: d.date, y: d.value })),
      borderColor: habitData.color,
      backgroundColor: habitData.color + '20',
      tension: 0.3,
      fill: type === 'boolean' ? false : true,
      pointRadius: 4,
      pointHoverRadius: 6,
      spanGaps: false
    }))

    try {
      chartInstances.value[type] = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'x',
            intersect: false,
          },
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                color: isDark.value ? '#a8a29e' : '#57534e',
                font: {
                  family: 'system-ui',
                  weight: 'bold'
                },
                padding: 15,
                usePointStyle: true,
                pointStyle: 'circle'
              }
            },
            tooltip: {
              backgroundColor: isDark.value ? '#292524' : '#ffffff',
              titleColor: isDark.value ? '#fafaf9' : '#1c1917',
              bodyColor: isDark.value ? '#a8a29e' : '#57534e',
              borderColor: isDark.value ? '#44403c' : '#d6d3d1',
              borderWidth: 1,
              padding: 12,
              displayColors: true,
              callbacks: {
                label: function (context) {
                  let label = context.dataset.label || '';
                  if (label) {
                    label += ': ';
                  }
                  if (context.parsed.y !== null) {
                    label += context.parsed.y;
                  }
                  return label;
                }
              }
            }
          },
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'day',
                displayFormats: {
                  day: 'MMM d'
                }
              },
              grid: {
                color: isDark.value ? '#44403c' : '#d6d3d1'
              },
              ticks: {
                color: isDark.value ? '#a8a29e' : '#57534e',
                font: {
                  weight: '600'
                }
              }
            },
            y: {
              beginAtZero: true,
              grace: '5%',
              grid: {
                color: isDark.value ? '#44403c' : '#d6d3d1'
              },
              ticks: {
                color: isDark.value ? '#a8a29e' : '#57534e',
                font: {
                  weight: '600'
                }
              }
            }
          }
        }
      })
    } catch (e) {
    }
  })
}

// Get user's timezone
const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone

// Helper to parse YYYY-MM-DD string as local date (not UTC)
const parseLocalDate = (dateStr) => {
  const [year, month, day] = dateStr.split('-').map(Number)
  // Create date at noon to avoid any DST edge cases
  return new Date(year, month - 1, day, 12, 0, 0)
}

// Helper to format date as YYYY-MM-DD from local date
const formatDateStr = (date) => {
  // Use Intl.DateTimeFormat with user's timezone for consistent formatting
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: userTimeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
  return formatter.format(date)
}

// Computed property to prepare heatmap data for boolean habits
// Fills all dates in the selected range (not just dates with data)
const booleanHeatmapData = computed(() => {
  if (!graphData.value.boolean || graphData.value.boolean.length === 0) {
    return []
  }

  if (!graphStartDate.value || !graphEndDate.value) {
    return []
  }

  return graphData.value.boolean.map(habit => {
    // Create a map of existing data points
    const dataMap = new Map()
    habit.data.forEach(point => {
      dataMap.set(point.date, point.value)
    })

    // Generate all dates in the selected range
    const filledData = []
    const current = parseLocalDate(graphStartDate.value)
    const end = parseLocalDate(graphEndDate.value)

    while (current <= end) {
      const dateStr = formatDateStr(current)
      filledData.push({
        date: dateStr,
        value: dataMap.get(dateStr) || 0
      })
      current.setDate(current.getDate() + 1)
    }

    return {
      habit_name: habit.habit_name,
      color: habit.color,
      data: filledData
    }
  })
})

// Watch for date changes
watch([graphStartDate, graphEndDate], () => {
  fetchGraphData()
})

// Watch for dark mode changes to update charts
watch(isDark, async () => {
  await renderCharts()
})

// Expose fetchGraphData so parent can trigger it when tab becomes active
defineExpose({ fetchGraphData })

onMounted(() => {
  initializeDateRange()
  fetchGraphData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Date Range Selector -->
    <div
      class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
      <h2 class="text-2xl font-black text-neutral-900 dark:text-white mb-6">{{ t('dateRange') }}</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div class="space-y-2">
          <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{ t('startDate') }}</label>
          <input v-model="graphStartDate" type="date"
            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white" />
        </div>
        <div class="space-y-2">
          <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{ t('endDate') }}</label>
          <input v-model="graphEndDate" type="date"
            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white" />
        </div>
      </div>

      <!-- Quick Select Buttons -->
      <div class="pt-4 border-t border-neutral-100 dark:border-neutral-700">
        <p class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2 mb-3">Quick Select</p>
        <div class="flex gap-3 flex-wrap">
          <button v-for="option in dateRangeOptions" :key="option.key" @click="setDateRangeOption(option.key)"
            :title="option.tooltip"
            class="px-6 py-2.5 bg-neutral-100 dark:bg-neutral-700 text-neutral-900 dark:text-white rounded-xl font-bold text-sm hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all shadow-sm active:scale-95">
            {{ option.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Loading Indicator -->
    <div v-if="isLoading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-10 w-10 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none"
        viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
        </path>
      </svg>
    </div>

    <!-- Boolean Habits Heatmaps -->
    <div v-if="booleanHeatmapData.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="habit in booleanHeatmapData" :key="habit.habit_name"
        class="bg-white dark:bg-neutral-800 rounded-4xl p-6 shadow-lg border border-neutral-100 dark:border-neutral-700">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-4 h-4 rounded-full" :style="{ backgroundColor: habit.color }">
          </div>
          <h3 class="text-lg font-black text-neutral-900 dark:text-white uppercase tracking-tight">
            {{ habit.habit_name }}
          </h3>
        </div>
        <div class="overflow-x-auto">
          <CalendarHeatmap :data="habit.data" :color="habit.color" :square-size="14" :gap="3" :border-radius="3" />
        </div>
      </div>
    </div>

    <!-- Boolean Habits Chart -->
    <div
      class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
      <h3 class="text-xl font-black text-neutral-900 dark:text-white mb-6 uppercase tracking-tight">{{
        t('booleanHabits') }}
      </h3>
      <div class="h-80 flex items-center justify-center" v-if="!graphData.boolean || graphData.boolean.length === 0">
        <p class="text-neutral-400 dark:text-neutral-500 font-medium text-lg">{{ t('noData') }}</p>
      </div>
      <div class="h-80" v-else>
        <canvas id="chart-boolean"></canvas>
      </div>
    </div>

    <!-- Counter Habits Chart -->
    <div
      class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
      <h3 class="text-xl font-black text-neutral-900 dark:text-white mb-6 uppercase tracking-tight">{{
        t('counterHabits') }}
      </h3>
      <div class="h-80 flex items-center justify-center" v-if="!graphData.counter || graphData.counter.length === 0">
        <p class="text-neutral-400 dark:text-neutral-500 font-medium text-lg">{{ t('noData') }}</p>
      </div>
      <div class="h-80" v-else>
        <canvas id="chart-counter"></canvas>
      </div>
    </div>

    <!-- Value Habits Chart -->
    <div
      class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
      <h3 class="text-xl font-black text-neutral-900 dark:text-white mb-6 uppercase tracking-tight">{{
        t('valueHabits') }}</h3>
      <div class="h-80 flex items-center justify-center" v-if="!graphData.value || graphData.value.length === 0">
        <p class="text-neutral-400 dark:text-neutral-500 font-medium text-lg">{{ t('noData') }}</p>
      </div>
      <div class="h-80" v-else>
        <canvas id="chart-value"></canvas>
      </div>
    </div>

    <!-- Rating Habits Chart -->
    <div
      class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
      <h3 class="text-xl font-black text-neutral-900 dark:text-white mb-6 uppercase tracking-tight">{{
        t('ratingHabits') }}</h3>
      <div class="h-80 flex items-center justify-center" v-if="!graphData.rating || graphData.rating.length === 0">
        <p class="text-neutral-400 dark:text-neutral-500 font-medium text-lg">{{ t('noData') }}</p>
      </div>
      <div class="h-80" v-else>
        <canvas id="chart-rating"></canvas>
      </div>
    </div>
  </div>
</template>
