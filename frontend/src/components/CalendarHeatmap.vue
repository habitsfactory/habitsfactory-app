<script setup>
// GitHub-style activity calendar: one column per week (Monday first).
// Ranges of a week or less are shown as a single labelled row instead.
import { computed } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import { parseISODate } from '@/utils/dates'

const props = defineProps({
  // Array of { date: 'YYYY-MM-DD', value: number }, one entry per day, in order
  data: {
    type: Array,
    required: true,
    validator: (value) => value.every(item => 'date' in item && 'value' in item)
  },
  // Main color for the heatmap (any CSS color)
  color: {
    type: String,
    default: '#22c55e'
  },
  // Show tooltips on hover
  showTooltips: {
    type: Boolean,
    default: true
  }
})

const { locale } = useLanguage()

// 0 = Monday … 6 = Sunday
const dayIndex = (date) => (date.getDay() + 6) % 7

const isRow = computed(() => props.data.length <= 7)

const maxValue = computed(() => Math.max(1, ...props.data.map(d => d.value)))

const days = computed(() => {
  const fullFormat = new Intl.DateTimeFormat(locale.value, {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
  })
  const weekdayFormat = new Intl.DateTimeFormat(locale.value, { weekday: 'short' })

  return props.data.map(item => {
    const date = parseISODate(item.date)
    return {
      key: item.date,
      date,
      weekday: weekdayFormat.format(date),
      // 0 = empty, otherwise 0.25 → 1 depending on the value
      opacity: item.value > 0 ? 0.25 + 0.75 * (item.value / maxValue.value) : 0,
      tooltip: `${fullFormat.format(date)}: ${item.value}`,
    }
  })
})

// Blank cells so the first day lands on its weekday row
const leadingBlanks = computed(() => (days.value.length ? dayIndex(days.value[0].date) : 0))

// One label slot per week column; filled when a new month starts in that week
const monthLabels = computed(() => {
  if (!days.value.length) return []
  const monthFormat = new Intl.DateTimeFormat(locale.value, { month: 'short' })
  const weeks = Math.ceil((days.value.length + leadingBlanks.value) / 7)
  const labels = Array(weeks).fill('')
  let lastMonth = -1
  let lastLabelWeek = -4
  days.value.forEach((day, index) => {
    const month = day.date.getMonth()
    if (month === lastMonth) return
    lastMonth = month
    const week = Math.floor((index + leadingBlanks.value) / 7)
    // Skip labels that would overlap the previous one
    if (week - lastLabelWeek >= 3) {
      labels[week] = monthFormat.format(day.date)
      lastLabelWeek = week
    }
  })
  return labels
})

// Mon / Wed / Fri labels (2024-01-01 is a Monday)
const weekdayLabels = computed(() => {
  const format = new Intl.DateTimeFormat(locale.value, { weekday: 'short' })
  return Array.from({ length: 7 }, (_, i) => (i % 2 === 0 ? format.format(new Date(2024, 0, 1 + i, 12)) : ''))
})
</script>

<template>
  <div class="inline-block" :style="{ '--heat': color }">
    <!-- A week or less: one row of labelled days -->
    <div v-if="isRow" class="flex gap-1.5">
      <div v-for="day in days" :key="day.key" class="flex flex-col items-center gap-1.5">
        <span class="text-[10px] font-semibold text-ink-faint uppercase">{{ day.weekday }}</span>
        <span class="relative block size-7 overflow-hidden rounded-md bg-ink/10 transition hover:ring-2 hover:ring-ink-faint"
          :title="showTooltips ? day.tooltip : undefined">
          <span class="absolute inset-0 bg-(--heat)" :style="{ opacity: day.opacity }"></span>
        </span>
      </div>
    </div>

    <!-- Longer ranges: weeks as columns -->
    <div v-else class="flex gap-2">
      <div class="grid grid-rows-7 gap-[3px] pt-5 text-[10px] leading-[14px] font-semibold text-ink-faint">
        <span v-for="(label, index) in weekdayLabels" :key="index" class="h-3.5">{{ label }}</span>
      </div>

      <div>
        <div class="mb-1 grid h-4 auto-cols-[14px] grid-flow-col gap-[3px] text-[10px] leading-4 font-semibold text-ink-faint">
          <span v-for="(label, index) in monthLabels" :key="index" class="whitespace-nowrap">{{ label }}</span>
        </div>

        <div class="grid auto-cols-[14px] grid-flow-col grid-rows-7 gap-[3px]">
          <span v-for="blank in leadingBlanks" :key="`blank-${blank}`" class="size-3.5"></span>
          <span v-for="day in days" :key="day.key"
            class="relative block size-3.5 overflow-hidden rounded-[3px] bg-ink/10 transition hover:ring-2 hover:ring-ink-faint"
            :title="showTooltips ? day.tooltip : undefined">
            <span class="absolute inset-0 bg-(--heat)" :style="{ opacity: day.opacity }"></span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
