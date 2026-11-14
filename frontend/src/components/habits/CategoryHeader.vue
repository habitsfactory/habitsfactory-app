<script setup>
import { GripVertical, ChevronUp, ChevronDown } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'

defineProps({
  name: { type: String, required: true },
  count: { type: Number, default: 0 },
  canMoveUp: Boolean,
  canMoveDown: Boolean,
})

defineEmits(['dragstart', 'dragend', 'move-up', 'move-down'])

const { t } = useLanguage()

const moveButtonClass =
  'inline-flex size-8 items-center justify-center rounded-lg text-ink-faint transition hover:bg-sunken hover:text-ink active:scale-95 disabled:pointer-events-none disabled:opacity-30'
</script>

<template>
  <div class="flex items-center gap-2.5">
    <!-- Mouse: drag the title. Touch / keyboard: the arrows on the right. -->
    <div class="group flex min-w-0 cursor-grab items-center gap-2.5 select-none active:cursor-grabbing" draggable="true"
      :title="t('dragToReorder')" @dragstart="$emit('dragstart', $event)" @dragend="$emit('dragend', $event)">
      <GripVertical :size="16"
        class="hidden shrink-0 text-ink-faint transition-colors group-hover:text-ink-soft pointer-fine:block" />
      <span class="h-5 w-1 shrink-0 rounded-full bg-primary-500"></span>
      <h3 class="truncate font-display text-xl font-semibold tracking-wide text-ink uppercase">{{ name }}</h3>
      <span class="shrink-0 rounded-full bg-sunken px-2 py-0.5 text-xs font-semibold text-ink-soft tabular-nums"
        :title="`${count} ${count === 1 ? t('habit') : t('habits')}`">
        {{ count }}
      </span>
    </div>
    <span class="h-px flex-1 bg-line"></span>
    <div v-if="canMoveUp || canMoveDown" class="flex shrink-0">
      <button type="button" :class="moveButtonClass" :title="t('moveUp')" :aria-label="`${t('moveUp')}: ${name}`"
        :disabled="!canMoveUp" @click="$emit('move-up')">
        <ChevronUp :size="18" stroke-width="2.25" />
      </button>
      <button type="button" :class="moveButtonClass" :title="t('moveDown')" :aria-label="`${t('moveDown')}: ${name}`"
        :disabled="!canMoveDown" @click="$emit('move-down')">
        <ChevronDown :size="18" stroke-width="2.25" />
      </button>
    </div>
  </div>
</template>
