<script setup>
// Decorative wall of drifting habit cards behind the auth screens.
import { Star, Check } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import HabitIcon from '@/components/habits/HabitIcon.vue'
import backgroundHabits from '@/data/backgroundHabits.json'

const { t } = useLanguage()

const shuffle = (array) => {
  const copy = [...array]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

// Each row holds the list twice so the -50% marquee loops seamlessly
const rows = Array.from({ length: 6 }, () => {
  const shuffled = shuffle(backgroundHabits)
  return [...shuffled, ...shuffled]
})

// Negative delays start every row mid-animation, at a different offset
const delays = ['[animation-delay:0s]', '[animation-delay:-9s]', '[animation-delay:-18s]', '[animation-delay:-27s]', '[animation-delay:-36s]', '[animation-delay:-45s]']
</script>

<template>
  <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
    <div class="absolute top-1/2 left-1/2 flex size-[200vmax] -translate-1/2 -rotate-45 flex-col justify-center gap-6">
      <div v-for="(row, rowIndex) in rows" :key="rowIndex" :class="[
        'flex shrink-0 gap-6 motion-reduce:animate-none',
        rowIndex % 2 === 0 ? 'animate-marquee-left' : 'animate-marquee-right',
        delays[rowIndex],
      ]">
        <div v-for="(habit, cardIndex) in row" :key="cardIndex" :style="{ '--habit': habit.color }"
          class="w-44 shrink-0 rounded-2xl border border-line bg-surface p-4 opacity-70 shadow-sm">
          <div class="mb-3 flex items-center gap-2.5">
            <HabitIcon :icon="habit.icon" :color="habit.color" size="sm" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-semibold text-ink">{{ habit.name }}</p>
              <p v-if="habit.unit" class="text-[10px] font-semibold tracking-wider text-ink-faint uppercase">
                {{ habit.unit }}
              </p>
            </div>
          </div>

          <div v-if="habit.habit_type === 'boolean'" :class="[
            'flex h-9 items-center justify-center rounded-lg text-xs font-semibold',
            habit.is_completed ? 'bg-emerald-600 text-white' : 'bg-sunken text-ink-soft',
          ]">
            <Check v-if="habit.is_completed" :size="18" stroke-width="3" />
            <span v-else>{{ t('notDone') }}</span>
          </div>

          <div v-else-if="habit.habit_type === 'rating'" class="flex h-9 items-center justify-center gap-0.5">
            <Star v-for="star in (habit.max_value || 5)" :key="star" :size="18" stroke-width="2"
              :class="['text-(--habit)', star <= habit.value ? 'fill-(--habit)' : 'fill-transparent']" />
          </div>

          <div v-else class="flex h-9 items-baseline justify-center gap-1.5">
            <span class="font-display text-3xl leading-9 font-semibold text-(--habit) tabular-nums">
              {{ habit.value }}
            </span>
            <span v-if="habit.habit_type === 'value' && habit.unit" class="text-xs font-medium text-ink-faint">
              {{ habit.unit }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
