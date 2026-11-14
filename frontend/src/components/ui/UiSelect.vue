<script setup>
import { computed, useAttrs } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { inputClass, labelClass } from './styles'

defineOptions({ inheritAttrs: false })

defineProps({
  label: { type: String, default: '' },
})

const model = defineModel({ type: [String, Number] })

const attrs = useAttrs()
const selectAttrs = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <label class="block" :class="attrs.class">
    <span v-if="label" :class="labelClass">{{ label }}</span>
    <span class="relative block">
      <select v-model="model" v-bind="selectAttrs" :class="[inputClass, 'appearance-none pr-10']">
        <slot />
      </select>
      <ChevronDown :size="18"
        class="pointer-events-none absolute top-1/2 right-3.5 -translate-y-1/2 text-ink-faint" />
    </span>
  </label>
</template>
