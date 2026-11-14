<script setup>
import { computed } from 'vue'
import { resolveIcon, loadIcons } from '@/utils/icons'

const props = defineProps({
  icon: { type: String, default: '' },
  color: { type: String, default: '#1490c9' },
  // sm | md | lg
  size: { type: String, default: 'md' },
})

const sizes = {
  sm: { box: 'size-9 rounded-lg', icon: 18 },
  md: { box: 'size-11 rounded-xl', icon: 22 },
  lg: { box: 'size-12 rounded-xl', icon: 24 },
}

loadIcons()

// null while the icon set is loading: the coloured tile is shown empty
const component = computed(() => resolveIcon(props.icon))
</script>

<template>
  <span :style="{ '--habit': color }"
    :class="['inline-flex shrink-0 items-center justify-center bg-(--habit)/15 text-(--habit)', sizes[size].box]">
    <component :is="component" v-if="component" :size="sizes[size].icon" stroke-width="2.25" />
  </span>
</template>
