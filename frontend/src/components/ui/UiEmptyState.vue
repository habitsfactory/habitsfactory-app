<script setup>
defineProps({
  icon: { type: [Object, Function], required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  // Drop the card chrome when nested inside another card
  plain: Boolean,
})
</script>

<template>
  <div :class="[
    'flex flex-col items-center px-6 text-center',
    plain ? 'py-8' : 'rounded-2xl border border-dashed border-line-strong bg-surface/60 py-14',
  ]">
    <span class="inline-flex size-14 items-center justify-center rounded-2xl bg-primary-500/10 text-primary-600 dark:text-primary-400">
      <component :is="icon" :size="28" stroke-width="2" />
    </span>
    <h3 class="mt-4 font-display text-2xl font-semibold tracking-wide text-ink uppercase">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-sm text-sm text-ink-soft">{{ description }}</p>
    <div v-if="$slots.default" class="mt-5 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </div>
</template>
