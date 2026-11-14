<script setup>
import { LoaderCircle } from 'lucide-vue-next'

defineProps({
  size: { type: Number, default: 32 },
  label: { type: String, default: '' },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16 text-ink-soft" role="status">
    <LoaderCircle :size="size" class="animate-spin text-primary-500" />
    <p v-if="label" class="text-sm font-medium">{{ label }}</p>
  </div>
</template>
