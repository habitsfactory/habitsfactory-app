<script setup>
defineProps({
  label: { type: String, required: true },
  icon: { type: [Object, Function], default: null },
})
</script>

<template>
  <div class="rounded-xl bg-sunken px-3 py-2.5 text-center">
    <div class="flex items-center justify-center gap-1.5 font-display text-2xl leading-tight font-semibold text-ink tabular-nums">
      <component :is="icon" v-if="icon" :size="18" stroke-width="2.25" class="text-ink-faint" />
      <slot />
    </div>
    <div class="mt-0.5 text-[11px] font-semibold tracking-wider text-ink-faint uppercase">{{ label }}</div>
  </div>
</template>
