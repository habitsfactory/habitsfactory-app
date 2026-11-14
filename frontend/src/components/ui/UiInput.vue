<script setup>
import { computed, useAttrs } from 'vue'
import { inputClass, labelClass, hintClass } from './styles'

defineOptions({ inheritAttrs: false })

defineProps({
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  type: { type: String, default: 'text' },
})

// Supports `v-model.number`
const [model, modifiers] = defineModel({
  type: [String, Number],
  set(value) {
    if (modifiers.number) return value === '' ? null : Number(value)
    return value
  },
})

// `class` goes on the wrapper, everything else (placeholder, required…) on the input
const attrs = useAttrs()
const inputAttrs = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})
</script>

<template>
  <label class="block" :class="attrs.class">
    <span v-if="label" :class="labelClass">{{ label }}</span>
    <input v-model="model" :type="type" v-bind="inputAttrs" :class="inputClass" />
    <span v-if="hint" :class="hintClass">{{ hint }}</span>
  </label>
</template>
