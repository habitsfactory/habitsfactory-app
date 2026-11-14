<script setup>
defineProps({
  // [{ value, label, icon?, title? }]
  options: { type: Array, required: true },
  // Hide labels (they remain as tooltips / accessible names)
  iconOnly: Boolean,
  // default: sits on a surface · inverse: sits on a brand-colored banner
  tone: { type: String, default: 'default' },
})

const model = defineModel({ type: [String, Number] })

const tones = {
  default: {
    track: 'bg-sunken',
    active: 'bg-surface text-ink shadow-xs',
    idle: 'text-ink-soft hover:text-ink',
  },
  inverse: {
    track: 'bg-white/10',
    active: 'bg-white text-primary-700 shadow-xs',
    idle: 'text-white/80 hover:text-white',
  },
}
</script>

<template>
  <div :class="['inline-flex max-w-full flex-wrap gap-1 rounded-xl p-1', tones[tone].track]" role="radiogroup">
    <button v-for="option in options" :key="option.value" type="button" role="radio"
      :aria-checked="model === option.value" :title="option.title || option.label"
      :aria-label="iconOnly ? option.label : undefined" :class="[
        'inline-flex h-8 items-center justify-center gap-1.5 rounded-lg text-sm font-semibold whitespace-nowrap transition',
        iconOnly ? 'w-9' : 'px-3',
        model === option.value ? tones[tone].active : tones[tone].idle,
      ]" @click="model = option.value">
      <component :is="option.icon" v-if="option.icon" :size="16" stroke-width="2.25" />
      <span v-if="!iconOnly">{{ option.label }}</span>
    </button>
  </div>
</template>
