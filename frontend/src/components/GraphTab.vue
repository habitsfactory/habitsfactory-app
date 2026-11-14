<script setup>
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import api from '@/services/api'
import { useDarkMode } from '@/composables/useDarkMode'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import { toISODate, parseISODate, addDays, daysBetween, presetRange, recentYears } from '@/utils/dates'
import { Chart, registerables } from 'chart.js'
import 'chartjs-adapter-date-fns'
import { CalendarRange, ChartLine, LoaderCircle } from 'lucide-vue-next'
import CalendarHeatmap from '@/components/CalendarHeatmap.vue'
import UiSection from '@/components/ui/UiSection.vue'
import UiInput from '@/components/ui/UiInput.vue'
import { labelClass } from '@/components/ui/styles'

// Register Chart.js components
Chart.register(...registerables)

const { isDark } = useDarkMode()
const { t } = useLanguage()

const HABIT_TYPES = ['boolean', 'counter', 'value', 'rating', 'percentage']

// Graph state
const graphStartDate = ref('')
const graphEndDate = ref('')
const graphData = ref(Object.fromEntries(HABIT_TYPES.map(type => [type, []])))
const isLoading = ref(false)

// Chart instances and their canvases are kept out of Vue's reactivity on
// purpose: Chart.js objects must not be wrapped in proxies.
const chartInstances = {}
const canvases = {}

const chartSections = computed(() => HABIT_TYPES.map(type => ({
  type,
  title: t(`${type}Habits`),
  hasData: graphData.value[type]?.length > 0,
})))

// Date range quick select options
const dateRangeOptions = computed(() => [
  ...['thisWeek', 'thisMonth', 'last7Days', 'last30Days', 'allTime'].map(key => ({
    key,
    label: t(key),
    tooltip: t(`${key}Tooltip`),
  })),
  ...recentYears().map(year => ({ key: String(year), label: String(year), tooltip: String(year) })),
])

const setRange = (start, end) => {
  graphStartDate.value = start
  graphEndDate.value = end
}

// Set date range to all available data
const setAllDataRange = async () => {
  const today = toISODate()
  try {
    const response = await api.get('habits/date_range/')
    if (response.data.start_date && response.data.end_date) {
      setRange(response.data.start_date, response.data.end_date)
    } else {
      setRange(today, today)
    }
  } catch (err) {
    setRange('2020-01-01', today)
  }
}

// Set date range based on quick select option
const setDateRangeOption = (optionKey) => {
  if (optionKey === 'allTime') {
    setAllDataRange()
    return
  }
  const { start, end } = presetRange(optionKey)
  setRange(toISODate(start), toISODate(end))
}

// A day without an entry means "0" for yes/no and counter habits, but
// "not measured" for values and ratings (an unlogged night is not 0 h of sleep)
const EMPTY_DAY_VALUE = { boolean: 0, counter: 0, value: null, rating: null, percentage: null }

// Fill the gaps between a habit's first and last data point. Null points
// leave a gap in the line (see `spanGaps` below).
const fillMissingDates = (data, type) => {
  const empty = EMPTY_DAY_VALUE[type]
  return (data || []).map(habitData => {
    if (!habitData.data || habitData.data.length === 0) return habitData

    const dates = habitData.data.map(point => point.date).sort()
    const dataMap = new Map(habitData.data.map(point => [point.date, point.value]))

    const filledData = []
    const end = parseISODate(dates[dates.length - 1])
    for (let current = parseISODate(dates[0]); current <= end; current = addDays(current, 1)) {
      const dateStr = toISODate(current)
      filledData.push({ date: dateStr, value: dataMap.get(dateStr) ?? empty })
    }

    return { ...habitData, data: filledData }
  })
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

    graphData.value = Object.fromEntries(
      HABIT_TYPES.map(type => [type, fillMissingDates(response.data[type], type)])
    )

    await renderCharts()
  } catch (err) {
    notifyError(err, 'loadFailed')
  } finally {
    isLoading.value = false
  }
}

const destroyCharts = () => {
  HABIT_TYPES.forEach(type => {
    chartInstances[type]?.destroy()
    chartInstances[type] = null
  })
}

// Charts take their colors from the theme tokens defined in assets/main.css
const themeColor = (name) =>
  getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim()

// Render all charts
const renderCharts = async () => {
  // Ensure DOM is fully updated before accessing canvas elements
  await nextTick()
  destroyCharts()

  const colors = {
    ink: themeColor('ink'),
    soft: themeColor('ink-soft'),
    line: themeColor('line'),
    surface: themeColor('surface'),
  }
  const fontFamily = getComputedStyle(document.body).fontFamily

  HABIT_TYPES.forEach(type => {
    const data = graphData.value[type] || []
    const canvas = canvases[type]
    if (data.length === 0 || !canvas) return

    // One dataset per habit
    const datasets = data.map(habitData => ({
      label: habitData.habit_name,
      data: habitData.data.map(d => ({ x: d.date, y: d.value })),
      borderColor: habitData.color,
      backgroundColor: habitData.color + '20',
      borderWidth: 2,
      // Monotone curves never overshoot the data (no dipping below 0 / above 1)
      cubicInterpolationMode: 'monotone',
      fill: type !== 'boolean',
      pointRadius: 3,
      pointHoverRadius: 6,
      spanGaps: false
    }))

    chartInstances[type] = new Chart(canvas, {
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
              color: colors.soft,
              font: { family: fontFamily, weight: 600 },
              padding: 15,
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            backgroundColor: colors.surface,
            titleColor: colors.ink,
            bodyColor: colors.soft,
            borderColor: colors.line,
            borderWidth: 1,
            padding: 12,
            titleFont: { family: fontFamily },
            bodyFont: { family: fontFamily },
          }
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'day',
              displayFormats: { day: 'MMM d' }
            },
            grid: { color: colors.line },
            border: { color: colors.line },
            ticks: {
              color: colors.soft,
              font: { family: fontFamily, weight: 500 }
            }
          },
          y: {
            beginAtZero: true,
            // Scores always use the full 0-100 scale
            ...(type === 'percentage' ? { max: 100 } : { grace: '5%' }),
            grid: { color: colors.line },
            border: { color: colors.line },
            ticks: {
              color: colors.soft,
              font: { family: fontFamily, weight: 500 }
            }
          }
        }
      }
    })
  })
}

// Heatmap data for boolean habits: every day of the selected range
const booleanHeatmapData = computed(() => {
  if (!graphData.value.boolean?.length || !graphStartDate.value || !graphEndDate.value) return []

  const start = parseISODate(graphStartDate.value)
  const end = parseISODate(graphEndDate.value)

  return graphData.value.boolean.map(habit => {
    const dataMap = new Map(habit.data.map(point => [point.date, point.value]))

    const filledData = []
    for (let current = start; current <= end; current = addDays(current, 1)) {
      const dateStr = toISODate(current)
      filledData.push({ date: dateStr, value: dataMap.get(dateStr) || 0 })
    }

    return { habit_name: habit.habit_name, color: habit.color, data: filledData }
  })
})

// Long ranges need the full width; short ones fit several per row
const wideHeatmaps = computed(() => {
  if (!graphStartDate.value || !graphEndDate.value) return false
  return daysBetween(parseISODate(graphStartDate.value), parseISODate(graphEndDate.value)) > 120
})

// Refetch when the range changes
watch([graphStartDate, graphEndDate], () => {
  fetchGraphData()
})

// Redraw with the new palette when the theme changes
watch(isDark, () => renderCharts())

// Exposed so the parent can refresh when the tab becomes active
defineExpose({ fetchGraphData })

onMounted(() => {
  // Default range: current month (the watcher above triggers the fetch)
  setDateRangeOption('thisMonth')
})

onBeforeUnmount(destroyCharts)
</script>

<template>
  <div class="space-y-6">
    <!-- Date range -->
    <UiSection :title="t('dateRange')" :icon="CalendarRange">
      <template #actions>
        <LoaderCircle v-if="isLoading" :size="20" class="animate-spin text-primary-500" />
      </template>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <UiInput v-model="graphStartDate" type="date" :label="t('startDate')" :max="graphEndDate || undefined" />
        <UiInput v-model="graphEndDate" type="date" :label="t('endDate')" :min="graphStartDate || undefined" />
      </div>

      <div class="mt-5 border-t border-line pt-4">
        <span :class="labelClass">{{ t('quickSelect') }}</span>
        <div class="flex flex-wrap gap-2">
          <button v-for="option in dateRangeOptions" :key="option.key" type="button" :title="option.tooltip"
            class="inline-flex h-8 items-center rounded-full border border-line bg-surface px-3 text-sm font-medium text-ink-soft transition-colors hover:border-primary-500 hover:text-primary-700 dark:hover:text-primary-300"
            @click="setDateRangeOption(option.key)">
            {{ option.label }}
          </button>
        </div>
      </div>
    </UiSection>

    <!-- Boolean habits calendars -->
    <div v-if="booleanHeatmapData.length > 0"
      :class="['grid grid-cols-1 gap-4', !wideHeatmaps && 'md:grid-cols-2 lg:grid-cols-3']">
      <section v-for="habit in booleanHeatmapData" :key="habit.habit_name" :style="{ '--habit': habit.color }"
        class="rounded-2xl border border-line bg-surface p-4 shadow-xs">
        <div class="mb-3 flex items-center gap-2.5">
          <span class="size-3 shrink-0 rounded-full bg-(--habit)"></span>
          <h3 class="truncate font-semibold text-ink">{{ habit.habit_name }}</h3>
        </div>
        <div class="overflow-x-auto pb-1">
          <CalendarHeatmap :data="habit.data" :color="habit.color" />
        </div>
      </section>
    </div>

    <!-- One chart per habit type -->
    <UiSection v-for="section in chartSections" :key="section.type" :title="section.title" :icon="ChartLine">
      <!-- The canvas stays mounted so Chart.js can attach to it -->
      <div v-show="section.hasData" class="h-80">
        <canvas :ref="el => { canvases[section.type] = el }"></canvas>
      </div>
      <p v-if="!section.hasData" class="flex h-32 items-center justify-center text-sm font-medium text-ink-faint">
        {{ t('noData') }}
      </p>
    </UiSection>
  </div>
</template>
