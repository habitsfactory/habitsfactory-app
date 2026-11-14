<script setup>
// The input used to log a habit for the day. Emits `update` with the new value.
// Colors come from the `--habit` CSS variable set on an ancestor.
import { computed, ref, watch } from 'vue'
import { Check, Circle, Minus, Plus, Star } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'

const props = defineProps({
  habit: { type: Object, required: true },
  // Compact layout for the list view
  compact: Boolean,
})

const emit = defineEmits(['update'])

const { t } = useLanguage()

const value = computed(() => props.habit.today_value || 0)
const done = computed(() => value.value > 0)
const stars = computed(() => props.habit.max_value || 5)

// Percentage: the slider moves a local draft and saves once, on release
const draft = ref(value.value)
watch(value, (next) => { draft.value = next })

const commitPercentage = (raw) => {
  const next = Math.min(100, Math.max(0, Math.round(Number(raw) || 0)))
  draft.value = next
  if (next !== value.value) emit('update', next)
}

const stepClass =
  'inline-flex shrink-0 items-center justify-center rounded-xl bg-sunken text-ink-soft transition hover:bg-line hover:text-ink active:scale-95 disabled:pointer-events-none disabled:opacity-40'
</script>

<template>
  <!-- Boolean -->
  <button v-if="habit.habit_type === 'boolean'" type="button" :aria-pressed="done" :class="[
    'inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition active:scale-[.98]',
    compact ? 'h-9 px-3' : 'h-11 w-full',
    done
      ? 'bg-emerald-600 text-white hover:bg-emerald-700'
      : 'border border-line bg-sunken/60 text-ink-soft hover:border-line-strong hover:text-ink',
  ]" @click="emit('update', done ? 0 : 1)">
    <Check v-if="done" :size="18" stroke-width="3" />
    <Circle v-else :size="16" stroke-width="2.25" />
    <span>{{ done ? t('completed') : compact ? t('done') : t('markComplete') }}</span>
  </button>

  <!-- Counter -->
  <div v-else-if="habit.habit_type === 'counter'"
    :class="['flex items-center', compact ? 'gap-2' : 'justify-between gap-3']">
    <button type="button" :class="[stepClass, compact ? 'size-9' : 'size-11']" :disabled="value <= 0"
      :aria-label="t('decrease')" @click="emit('update', Math.max(0, value - 1))">
      <Minus :size="18" stroke-width="2.5" />
    </button>
    <div :class="['flex items-baseline justify-center gap-1.5', compact ? 'min-w-12' : 'min-w-16']">
      <span :class="['font-display font-semibold text-(--habit) tabular-nums', compact ? 'text-2xl' : 'text-4xl leading-none']">
        {{ value }}
      </span>
      <span v-if="habit.unit" class="text-sm font-medium text-ink-soft">{{ habit.unit }}</span>
    </div>
    <button type="button" :class="[stepClass, compact ? 'size-9' : 'size-11']" :aria-label="t('increase')"
      @click="emit('update', value + 1)">
      <Plus :size="18" stroke-width="2.5" />
    </button>
  </div>

  <!-- Value -->
  <label v-else-if="habit.habit_type === 'value'" :class="[
    'flex items-center gap-2 rounded-xl border border-line bg-surface px-3 transition-colors hover:border-line-strong focus-within:border-primary-500 focus-within:ring-3 focus-within:ring-primary-500/20',
    compact ? 'h-9 w-32' : 'h-11',
  ]">
    <input type="number" step="any" inputmode="decimal" placeholder="0" :value="value || ''" :aria-label="habit.name"
      :class="[
        'w-full min-w-0 [appearance:textfield] bg-transparent text-center font-display font-semibold text-(--habit) tabular-nums placeholder:text-ink-faint focus:outline-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none',
        compact ? 'text-xl' : 'text-2xl',
      ]" @change="emit('update', parseFloat($event.target.value) || 0)" />
    <span v-if="habit.unit" class="shrink-0 text-sm font-medium text-ink-soft">{{ habit.unit }}</span>
  </label>

  <!-- Rating (click the current rating again to clear it) -->
  <div v-else-if="habit.habit_type === 'rating'"
    :class="['flex flex-wrap items-center', compact ? 'justify-end' : 'h-11 justify-center gap-0.5']">
    <button v-for="star in stars" :key="star" type="button" :aria-label="`${star} / ${stars}`"
      :aria-pressed="star <= value" class="rounded-md p-0.5 text-(--habit) transition hover:scale-115 active:scale-95"
      @click="emit('update', star === value ? 0 : star)">
      <Star :size="compact ? 20 : 26" stroke-width="2"
        :class="star <= value ? 'fill-(--habit)' : 'fill-transparent opacity-50'" />
    </button>
  </div>

  <!-- Percentage (0-100 score): slider + exact number -->
  <div v-else-if="habit.habit_type === 'percentage'" :class="['flex items-center gap-3', compact ? '' : 'h-11']">
    <input v-if="!compact" type="range" min="0" max="100" step="1" :value="draft" :aria-label="habit.name"
      class="h-2 min-w-0 flex-1 cursor-pointer accent-(--habit)" @input="draft = Number($event.target.value)"
      @change="commitPercentage($event.target.value)" />
    <label :class="[
      'flex shrink-0 items-center gap-1 rounded-xl border border-line bg-surface px-3 transition-colors hover:border-line-strong focus-within:border-primary-500 focus-within:ring-3 focus-within:ring-primary-500/20',
      compact ? 'h-9 w-24' : 'h-11 w-24',
    ]">
      <input type="number" min="0" max="100" step="1" inputmode="numeric" placeholder="0" :value="draft || ''"
        :aria-label="habit.name" :class="[
          'w-full min-w-0 [appearance:textfield] bg-transparent text-center font-display font-semibold text-(--habit) tabular-nums placeholder:text-ink-faint focus:outline-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none',
          compact ? 'text-xl' : 'text-2xl',
        ]" @change="commitPercentage($event.target.value)" />
      <span class="shrink-0 text-sm font-medium text-ink-soft">%</span>
    </label>
  </div>
</template>
