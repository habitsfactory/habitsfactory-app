<script setup>
import { X } from 'lucide-vue-next'

defineProps({
  tag: { type: Object, required: true },
  removable: Boolean,
  removeLabel: { type: String, default: 'Remove' },
})

defineEmits(['remove'])
</script>

<template>
  <span :style="{ '--tag': tag.color }"
    class="inline-flex max-w-full items-center gap-1.5 rounded-full bg-(--tag)/15 px-2 py-0.5 text-xs font-semibold text-(--tag)">
    <span class="size-1.5 shrink-0 rounded-full bg-(--tag)"></span>
    <span class="truncate">{{ tag.name }}</span>
    <button v-if="removable" type="button" :title="removeLabel" :aria-label="`${removeLabel}: ${tag.name}`"
      class="-mr-1 inline-flex size-4 items-center justify-center rounded-full transition-colors hover:bg-(--tag)/25"
      @click.stop="$emit('remove')">
      <X :size="12" stroke-width="2.5" />
    </button>
  </span>
</template>
