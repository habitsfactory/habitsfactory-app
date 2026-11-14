<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import { useCategories } from '@/composables/useCategories'
import { useCategoryDrag } from '@/composables/useCategoryDrag'
import { useCookies } from '@/composables/useCookies'
import { toISODate, presetRange, daysBetween } from '@/utils/dates'
import { Flame, ChartNoAxesColumn, Star, Trophy } from 'lucide-vue-next'
import UiSegmented from '@/components/ui/UiSegmented.vue'
import UiSpinner from '@/components/ui/UiSpinner.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import UiStat from '@/components/ui/UiStat.vue'
import HabitIcon from '@/components/habits/HabitIcon.vue'
import TagChip from '@/components/habits/TagChip.vue'
import CategoryHeader from '@/components/habits/CategoryHeader.vue'

const { t } = useLanguage()
const { fetchCategories, groupByCategory } = useCategories()
const { draggedId, dragOverId, onDragStart, onDragOver, onDrop, onDragEnd, moveGroup } = useCategoryDrag()
const { setCookie, getCookie } = useCookies()

const COOKIE_NAME = 'summaryDateRange'
const RANGE_KEYS = ['thisWeek', 'thisMonth', 'last7Days', 'last30Days']

// Date range options (computed so labels follow the language)
const dateRangeOptions = computed(() => RANGE_KEYS.map(key => ({
  value: key,
  label: t(key),
  title: t(`${key}Tooltip`),
})))

const savedRange = getCookie(COOKIE_NAME)
const selectedRange = ref(RANGE_KEYS.includes(savedRange) ? savedRange : 'last30Days')

// Summary state
const HABIT_TYPES = ['boolean', 'counter', 'value', 'rating', 'percentage']

const summaryData = ref(Object.fromEntries(HABIT_TYPES.map(type => [type, []])))
const isFetchingSummary = ref(false)
const hasLoaded = ref(false)

const summaryDays = computed(() => {
  const { start, end } = presetRange(selectedRange.value)
  return daysBetween(start, end)
})

// Combine all habits and group by category
const allHabits = computed(() =>
  HABIT_TYPES.flatMap(type =>
    summaryData.value[type].map(h => ({ ...h, habit_type: type }))
  )
)

const groupedHabits = computed(() =>
  groupByCategory(allHabits.value, h => h.category_id ?? null, t('uncategorized'))
)

// Fetch summary data from API
const fetchSummaryData = async () => {
  isFetchingSummary.value = true
  try {
    const { start, end } = presetRange(selectedRange.value)
    const response = await api.get('habits/summary/', {
      params: {
        start_date: toISODate(start),
        end_date: toISODate(end)
      }
    })
    summaryData.value = Object.fromEntries(HABIT_TYPES.map(type => [type, response.data[type] || []]))
  } catch (err) {
    notifyError(err, 'loadFailed')
  } finally {
    isFetchingSummary.value = false
    hasLoaded.value = true
  }
}

// Caption under the headline figure of the non yes/no cards
const summaryLabels = { rating: 'averageRating', percentage: 'averageScore' }

// Averages and extremes mean nothing for a habit with no entry in the range
const measured = (habit, value) => (habit.metrics.days_tracked > 0 ? value : '–')

const range = computed({
  get: () => selectedRange.value,
  set: (key) => {
    selectedRange.value = key
    setCookie(COOKIE_NAME, key)
    fetchSummaryData()
  },
})

// Exposed so the parent can refresh when the tab becomes active
defineExpose({ fetchSummaryData })

onMounted(() => {
  fetchCategories()
  fetchSummaryData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <section
      class="relative overflow-hidden rounded-2xl bg-linear-to-br from-primary-600 to-primary-950 p-5 text-white shadow-md sm:p-6">
      <ChartNoAxesColumn :size="180" stroke-width="1.5"
        class="pointer-events-none absolute -right-6 -bottom-10 text-white/10" />
      <div class="relative flex flex-wrap items-end justify-between gap-4">
        <div class="min-w-0">
          <h2 class="font-display text-3xl font-bold tracking-wide uppercase">{{ t('summaryView') }}</h2>
          <p class="mt-1 text-sm text-primary-100">{{ t('retrospectiveAnalysis') }}</p>
          <UiSegmented v-model="range" :options="dateRangeOptions" tone="inverse" class="mt-4" />
        </div>
        <div class="text-right">
          <p class="font-display text-6xl leading-none font-bold tabular-nums">{{ summaryDays }}</p>
          <p class="text-xs font-semibold tracking-wider text-primary-100 uppercase">{{ t('days') }}</p>
        </div>
      </div>
    </section>

    <UiSpinner v-if="isFetchingSummary && !hasLoaded" />

    <div v-else :class="['flex flex-col gap-6 transition-opacity', isFetchingSummary && 'opacity-60']">
      <section v-for="(group, index) in groupedHabits" :key="group.id" :class="[
        '-m-2 space-y-3 rounded-2xl p-2 transition',
        draggedId === group.id && 'opacity-40',
        dragOverId === group.id && draggedId !== group.id && 'bg-primary-500/5 ring-2 ring-primary-500',
      ]" @dragover="onDragOver($event, group.id)" @drop="onDrop($event, group.id)">
        <CategoryHeader :name="group.name" :count="group.habits.length" :can-move-up="index > 0"
            :can-move-down="index < groupedHabits.length - 1" @dragstart="onDragStart($event, group.id)"
            @dragend="onDragEnd" @move-up="moveGroup(group.id, groupedHabits[index - 1].id)"
            @move-down="moveGroup(group.id, groupedHabits[index + 1].id)" />

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <article v-for="habit in group.habits" :key="habit.habit_id" :style="{ '--habit': habit.color }"
            class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-4 shadow-xs">
            <div class="flex items-start gap-3">
              <HabitIcon :icon="habit.icon" :color="habit.color" />
              <div class="min-w-0 flex-1">
                <h4 class="truncate leading-snug font-semibold text-ink" :title="habit.habit_name">
                  {{ habit.habit_name }}
                </h4>
                <p class="text-xs font-medium text-ink-faint">{{ t(habit.habit_type) }}</p>
                <div v-if="habit.tags?.length" class="mt-1 flex flex-wrap gap-1">
                  <TagChip v-for="tag in habit.tags" :key="tag.id" :tag="tag" />
                </div>
              </div>
            </div>

            <!-- Boolean -->
            <template v-if="habit.habit_type === 'boolean'">
              <div>
                <div class="flex items-end justify-between gap-3">
                  <span class="text-xs font-semibold tracking-wider text-ink-faint uppercase">
                    {{ t('completionRate') }}
                  </span>
                  <span class="font-display text-4xl leading-none font-semibold text-(--habit) tabular-nums">
                    {{ habit.metrics.completion_rate }}%
                  </span>
                </div>
                <div class="mt-2 h-2 overflow-hidden rounded-full bg-sunken">
                  <div class="h-full rounded-full bg-(--habit) transition-all duration-500"
                    :style="{ width: `${Math.min(100, habit.metrics.completion_rate)}%` }"></div>
                </div>
              </div>
              <div class="mt-auto grid grid-cols-3 gap-2">
                <UiStat :label="t('completed')">{{ habit.metrics.total_completions }}</UiStat>
                <UiStat :label="t('currentStreak')" :icon="Flame" :title="t('currentStreakHint')">{{ habit.metrics.current_streak }}</UiStat>
                <UiStat :label="t('bestStreak')" :icon="Trophy" :title="t('bestStreakHint')">{{ habit.metrics.best_streak }}</UiStat>
              </div>
              <p class="text-center text-xs font-medium text-ink-faint">
                {{ t('overDays', { n: habit.metrics.days_in_range }) }}
              </p>
            </template>

            <!-- Counter / Value / Rating -->
            <template v-else>
              <div class="rounded-xl bg-(--habit)/10 px-3 py-4 text-center">
                <div class="font-display text-4xl leading-none font-semibold text-(--habit) tabular-nums">
                  <template v-if="habit.habit_type === 'rating'">
                    {{ measured(habit, habit.metrics.average) }}<span class="text-2xl opacity-70">/{{ habit.metrics.max_value || 5 }}</span>
                  </template>
                  <template v-else-if="habit.habit_type === 'percentage'">
                    {{ measured(habit, habit.metrics.average) }}<span class="text-2xl opacity-70">%</span>
                  </template>
                  <template v-else>
                    {{ habit.metrics.total }}
                    <span v-if="habit.metrics.unit" class="text-xl">{{ habit.metrics.unit }}</span>
                  </template>
                </div>
                <div class="mt-1.5 text-xs font-semibold tracking-wider text-ink-faint uppercase">
                  {{ t(summaryLabels[habit.habit_type] || 'total') }}
                </div>
              </div>

              <div class="mt-auto grid grid-cols-2 gap-2">
                <template v-if="habit.habit_type === 'counter'">
                  <UiStat :label="t('avgPerDay')">{{ habit.metrics.average }}</UiStat>
                  <UiStat :label="t('bestDay')">{{ habit.metrics.max }}</UiStat>
                </template>
                <template v-else-if="habit.habit_type === 'value'">
                  <UiStat :label="t('average')">{{ measured(habit, habit.metrics.average) }}</UiStat>
                  <UiStat :label="t('highest')">{{ measured(habit, habit.metrics.max_value) }}</UiStat>
                </template>
                <template v-else-if="habit.habit_type === 'percentage'">
                  <UiStat :label="t('highest')">{{ measured(habit, habit.metrics.max) }}</UiStat>
                  <UiStat :label="t('lowest')">{{ measured(habit, habit.metrics.min) }}</UiStat>
                </template>
                <template v-else>
                  <UiStat :label="t('best')" :icon="Star">{{ measured(habit, habit.metrics.max) }}</UiStat>
                  <UiStat :label="t('lowest')" :icon="Star">{{ measured(habit, habit.metrics.min) }}</UiStat>
                </template>
              </div>
              <p class="text-center text-xs font-medium text-ink-faint">
                {{ t('trackedDays', { tracked: habit.metrics.days_tracked, total: habit.metrics.days_in_range }) }}
              </p>
            </template>
          </article>
        </div>
      </section>

      <UiEmptyState v-if="allHabits.length === 0" :icon="ChartNoAxesColumn" :title="t('noHabitsYet')"
        :description="t('startTracking')" />
    </div>
  </div>
</template>
