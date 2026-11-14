<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

defineProps({
  // right | left — which edge of the trigger the panel aligns to
  align: { type: String, default: 'right' },
  // Tailwind width class for the panel
  width: { type: String, default: 'w-56' },
})

const emit = defineEmits(['open', 'close'])

const root = ref(null)
const isOpen = ref(false)

const open = () => {
  if (isOpen.value) return
  isOpen.value = true
  emit('open')
}

const close = () => {
  if (!isOpen.value) return
  isOpen.value = false
  emit('close')
}

const toggle = () => (isOpen.value ? close() : open())

const onPointerDown = (event) => {
  if (isOpen.value && root.value && !root.value.contains(event.target)) close()
}

const onKeydown = (event) => {
  if (event.key === 'Escape') close()
}

onMounted(() => {
  document.addEventListener('pointerdown', onPointerDown)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onPointerDown)
  document.removeEventListener('keydown', onKeydown)
})

defineExpose({ open, close, toggle })
</script>

<template>
  <div ref="root" class="relative">
    <slot name="trigger" :open="isOpen" :toggle="toggle" />

    <Transition enter-active-class="transition duration-150 ease-out"
      enter-from-class="-translate-y-1 scale-95 opacity-0" leave-active-class="transition duration-100 ease-in"
      leave-to-class="-translate-y-1 scale-95 opacity-0">
      <div v-if="isOpen" :class="[
        'absolute top-full z-40 mt-2 rounded-xl border border-line bg-surface p-1.5 shadow-xl',
        align === 'right' ? 'right-0 origin-top-right' : 'left-0 origin-top-left',
        width,
      ]">
        <slot :close="close" />
      </div>
    </Transition>
  </div>
</template>
