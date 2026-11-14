<script setup>
import { CircleAlert, CircleCheck, Info, TriangleAlert } from 'lucide-vue-next'

defineProps({
  // error | success | info | warning
  variant: { type: String, default: 'error' },
  title: { type: String, default: '' },
})

const variants = {
  error: { icon: CircleAlert, class: 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300' },
  success: { icon: CircleCheck, class: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' },
  info: { icon: Info, class: 'border-primary-500/30 bg-primary-500/10 text-primary-800 dark:text-primary-200' },
  warning: { icon: TriangleAlert, class: 'border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-200' },
}
</script>

<template>
  <div role="alert" :class="['flex items-start gap-3 rounded-xl border px-4 py-3 text-sm', variants[variant].class]">
    <component :is="variants[variant].icon" :size="18" stroke-width="2.25" class="mt-0.5 shrink-0" />
    <div class="min-w-0 flex-1">
      <p v-if="title" class="font-semibold">{{ title }}</p>
      <div :class="title ? 'mt-1 opacity-90' : 'font-medium'">
        <slot />
      </div>
    </div>
  </div>
</template>
