<script setup>
import { LoaderCircle } from 'lucide-vue-next'

defineProps({
  // primary | secondary | soft | ghost | danger | danger-soft | inverse
  variant: { type: String, default: 'primary' },
  // sm | md | lg | field (same height as a text input)
  size: { type: String, default: 'md' },
  // Lucide icon component shown before the label
  icon: { type: [Object, Function], default: null },
  type: { type: String, default: 'button' },
  loading: Boolean,
  disabled: Boolean,
  block: Boolean,
})

const variants = {
  primary: 'bg-primary-600 text-white shadow-xs hover:bg-primary-700 dark:hover:bg-primary-500',
  secondary: 'border border-line bg-surface text-ink shadow-xs hover:border-line-strong hover:bg-sunken',
  soft: 'bg-sunken text-ink hover:bg-line',
  ghost: 'text-ink-soft hover:bg-sunken hover:text-ink',
  danger: 'bg-red-600 text-white shadow-xs hover:bg-red-700',
  'danger-soft': 'text-red-600 hover:bg-red-500/10 dark:text-red-400',
  inverse: 'bg-white text-primary-700 shadow-xs hover:bg-primary-50',
}

const sizes = {
  sm: 'h-8 gap-1.5 rounded-lg px-3 text-sm',
  md: 'h-10 gap-2 rounded-xl px-4 text-sm',
  lg: 'h-12 gap-2.5 rounded-xl px-6 text-base',
  field: 'h-11 gap-2 rounded-xl px-4 text-sm',
}

const iconSizes = { sm: 16, md: 18, lg: 20, field: 18 }
</script>

<template>
  <button :type="type" :disabled="disabled || loading" :class="[
    'inline-flex shrink-0 items-center justify-center font-semibold whitespace-nowrap transition active:scale-[.98] disabled:pointer-events-none disabled:opacity-50',
    variants[variant],
    sizes[size],
    block && 'w-full',
  ]">
    <LoaderCircle v-if="loading" :size="iconSizes[size]" class="animate-spin" />
    <component :is="icon" v-else-if="icon" :size="iconSizes[size]" stroke-width="2.25" />
    <slot />
  </button>
</template>
