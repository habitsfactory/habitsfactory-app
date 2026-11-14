<script setup>
import { LoaderCircle } from 'lucide-vue-next'

defineProps({
  icon: { type: [Object, Function], required: true },
  // Accessible name, also used as tooltip
  label: { type: String, required: true },
  // ghost | soft | danger | success
  variant: { type: String, default: 'ghost' },
  // sm | md | lg
  size: { type: String, default: 'md' },
  loading: Boolean,
  disabled: Boolean,
})

const variants = {
  ghost: 'text-ink-soft hover:bg-sunken hover:text-ink',
  soft: 'bg-sunken text-ink-soft hover:bg-line hover:text-ink',
  danger: 'text-ink-soft hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400',
  success: 'bg-emerald-600 text-white hover:bg-emerald-700',
}

const sizes = { sm: 'size-8 rounded-lg', md: 'size-9 rounded-lg', lg: 'size-10 rounded-xl' }
const iconSizes = { sm: 16, md: 18, lg: 20 }
</script>

<template>
  <button type="button" :title="label" :aria-label="label" :disabled="disabled || loading" :class="[
    'inline-flex shrink-0 items-center justify-center transition active:scale-95 disabled:pointer-events-none disabled:opacity-40',
    variants[variant],
    sizes[size],
  ]">
    <LoaderCircle v-if="loading" :size="iconSizes[size]" class="animate-spin" />
    <component :is="icon" v-else :size="iconSizes[size]" stroke-width="2.25" />
  </button>
</template>
