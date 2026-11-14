<script setup>
// One line of a habit list (profile page): icon, name, a short description
// and its tags on the left, actions on the right. On narrow screens the
// actions wrap onto their own line instead of squeezing the name.
import { computed } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import HabitIcon from './HabitIcon.vue'

const props = defineProps({
  habit: { type: Object, required: true },
  // Greyed out (archived habits)
  muted: Boolean,
})

const { t } = useLanguage()

// "Value · hr", "Rating · 5", "Percentage · 0–100", "Counter · glasses"
const details = computed(() => {
  const { habit_type: type, unit, max_value: max } = props.habit
  const parts = [t(type)]
  if (type === 'rating') parts.push(`1–${max || 5}`)
  else if (type === 'percentage') parts.push('0–100')
  else if (unit) parts.push(unit)
  return parts.join(' · ')
})
</script>

<template>
  <li class="flex flex-wrap items-center gap-x-3 gap-y-1 py-3">
    <HabitIcon :icon="habit.icon" :color="habit.color" :class="muted && 'opacity-60'" />

    <div class="min-w-0 flex-1 basis-56">
      <div class="flex items-baseline gap-2">
        <p :class="['truncate font-semibold', muted ? 'text-ink-soft' : 'text-ink']" :title="habit.name">
          {{ habit.name }}
        </p>
        <span class="shrink-0 text-xs font-medium text-ink-faint">{{ details }}</span>
      </div>
      <div class="mt-1 flex flex-wrap items-center gap-1.5">
        <span v-if="habit.category"
          class="rounded-full bg-primary-500/10 px-2 py-0.5 text-xs font-semibold text-primary-700 dark:text-primary-300">
          {{ habit.category.name }}
        </span>
        <span v-else class="rounded-full bg-sunken px-2 py-0.5 text-xs font-semibold text-ink-faint">
          {{ t('uncategorized') }}
        </span>
        <!-- Tags -->
        <slot />
      </div>
    </div>

    <div class="ml-auto flex shrink-0 items-center">
      <slot name="actions" />
    </div>
  </li>
</template>
