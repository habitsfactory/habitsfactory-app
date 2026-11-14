<script setup>
import { Check } from 'lucide-vue-next'
import { labelClass } from './styles'

defineProps({
  label: { type: String, default: '' },
})

const model = defineModel({ type: String, default: '#1490c9' })

const presets = [
  '#1490c9', '#6366f1', '#8b5cf6', '#ec4899', '#ef4444',
  '#f97316', '#f59e0b', '#22c55e', '#14b8a6', '#64748b',
]
</script>

<template>
  <div>
    <span v-if="label" :class="labelClass">{{ label }}</span>
    <div class="flex flex-wrap items-center gap-2">
      <button v-for="color in presets" :key="color" type="button" :title="color" :aria-label="color"
        :aria-pressed="model?.toLowerCase() === color" :style="{ '--swatch': color }"
        class="inline-flex size-8 items-center justify-center rounded-full bg-(--swatch) text-white ring-offset-2 ring-offset-surface transition hover:scale-110 aria-pressed:ring-2 aria-pressed:ring-(--swatch)"
        @click="model = color">
        <Check v-if="model?.toLowerCase() === color" :size="16" stroke-width="3" />
      </button>

      <label
        class="ml-auto flex h-9 items-center gap-2 rounded-lg border border-line bg-surface pr-3 pl-1 transition-colors hover:border-line-strong">
        <input v-model="model" type="color"
          class="size-7 cursor-pointer rounded-md border-0 bg-transparent p-0 [&::-moz-color-swatch]:rounded-md [&::-moz-color-swatch]:border-0 [&::-webkit-color-swatch]:rounded-md [&::-webkit-color-swatch]:border-0 [&::-webkit-color-swatch-wrapper]:p-0" />
        <span class="font-mono text-xs text-ink-soft uppercase">{{ model }}</span>
      </label>
    </div>
  </div>
</template>
