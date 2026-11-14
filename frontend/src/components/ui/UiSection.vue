<script setup>
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  // default | danger
  tone: { type: String, default: 'default' },
})
</script>

<template>
  <section :class="[
    'rounded-2xl border bg-surface p-5 shadow-xs sm:p-6',
    tone === 'danger' ? 'border-red-500/40' : 'border-line',
  ]">
    <header v-if="title || $slots.actions" class="mb-5 flex flex-wrap items-center gap-3">
      <span v-if="icon" :class="[
        'inline-flex size-10 shrink-0 items-center justify-center rounded-xl',
        tone === 'danger' ? 'bg-red-500/10 text-red-600 dark:text-red-400' : 'bg-primary-500/10 text-primary-600 dark:text-primary-400',
      ]">
        <component :is="icon" :size="20" stroke-width="2.25" />
      </span>
      <div class="min-w-0 flex-1">
        <h2 :class="[
          'font-display text-xl leading-tight font-semibold tracking-wide uppercase',
          tone === 'danger' ? 'text-red-700 dark:text-red-300' : 'text-ink',
        ]">
          {{ title }}
        </h2>
        <p v-if="description" class="mt-0.5 text-sm text-ink-soft">{{ description }}</p>
      </div>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>
