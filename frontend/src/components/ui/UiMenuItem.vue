<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  icon: { type: [Object, Function], default: null },
  // Renders a router link instead of a button
  to: { type: [String, Object], default: null },
  description: { type: String, default: '' },
  danger: Boolean,
})
</script>

<template>
  <component :is="to ? RouterLink : 'button'" :to="to || undefined" :type="to ? undefined : 'button'" :class="[
    'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors',
    danger ? 'text-red-600 hover:bg-red-500/10 dark:text-red-400' : 'text-ink hover:bg-sunken',
  ]">
    <component :is="icon" v-if="icon" :size="18" stroke-width="2.25"
      :class="['shrink-0', danger ? '' : 'text-ink-faint']" />
    <span class="min-w-0 flex-1">
      <span class="block truncate">
        <slot />
      </span>
      <span v-if="description" class="block truncate text-xs font-normal text-ink-faint">{{ description }}</span>
    </span>
    <slot name="trailing" />
  </component>
</template>
