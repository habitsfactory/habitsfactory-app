<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { X } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import UiIconButton from './UiIconButton.vue'

const props = defineProps({
  open: Boolean,
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  // Lucide icon shown next to the title
  icon: { type: [Object, Function], default: null },
  // sm | md | lg | xl
  size: { type: String, default: 'md' },
  // default | danger
  tone: { type: String, default: 'default' },
  // Block closing (backdrop / Esc / X) while an action is running
  busy: Boolean,
})

const emit = defineEmits(['close'])

const { t } = useLanguage()

const sizes = {
  sm: 'sm:max-w-md',
  md: 'sm:max-w-lg',
  lg: 'sm:max-w-2xl',
  xl: 'sm:max-w-4xl',
}

const close = () => {
  if (!props.busy) emit('close')
}

const panel = ref(null)

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

const focusableElements = () =>
  [...(panel.value?.querySelectorAll(FOCUSABLE) || [])].filter((el) => el.getClientRects().length > 0)

// Only the dialog opened last reacts to the keyboard (a confirm dialog can
// sit on top of another modal).
const isTopmost = () => {
  const dialogs = document.querySelectorAll('[role="dialog"]')
  return dialogs[dialogs.length - 1] === panel.value?.parentElement
}

const onKeydown = (event) => {
  if (!isTopmost()) return
  if (event.key === 'Escape') {
    close()
    return
  }
  if (event.key !== 'Tab') return

  // Keep Tab / Shift+Tab inside the dialog
  const items = focusableElements()
  if (items.length === 0) {
    event.preventDefault()
    panel.value?.focus()
    return
  }
  const first = items[0]
  const last = items[items.length - 1]
  const current = document.activeElement
  if (!panel.value.contains(current)) {
    event.preventDefault()
    first.focus()
  } else if (event.shiftKey && (current === first || current === panel.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && current === last) {
    event.preventDefault()
    first.focus()
  }
}

// Move focus into the dialog on open, and back to where it was on close
let returnFocusTo = null

const focusDialog = async () => {
  returnFocusTo = document.activeElement
  await nextTick()
  if (!panel.value || panel.value.contains(document.activeElement)) return
  const target = panel.value.querySelector('[autofocus]')
    // Prefer the first field over the header's close button
    || focusableElements().find((el) => el.matches('input, select, textarea'))
    || panel.value
  target.focus({ preventScroll: true })
}

const restoreFocus = () => {
  if (returnFocusTo?.isConnected) returnFocusTo.focus({ preventScroll: true })
  returnFocusTo = null
}

// Lock page scroll while open (counted, so stacked dialogs behave)
const setLocked = (locked) => {
  const root = document.documentElement
  const count = Math.max(0, Number(root.dataset.modalCount || 0) + (locked ? 1 : -1))
  root.dataset.modalCount = String(count)
  root.classList.toggle('overflow-hidden', count > 0)
}

let active = false
const sync = (open) => {
  if (open === active) return
  active = open
  setLocked(open)
  if (open) {
    document.addEventListener('keydown', onKeydown)
    focusDialog()
  } else {
    document.removeEventListener('keydown', onKeydown)
    restoreFocus()
  }
}

watch(() => props.open, sync, { immediate: true })
onBeforeUnmount(() => sync(false))
</script>

<template>
  <Teleport to="body">
    <Transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in" leave-to-class="opacity-0">
      <div v-if="open" class="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4" role="dialog"
        aria-modal="true" :aria-label="title">
        <div class="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" @click="close"></div>

        <div ref="panel" tabindex="-1" :class="[
          'relative flex max-h-[92dvh] outline-none w-full flex-col overflow-hidden rounded-t-3xl border border-line bg-surface shadow-2xl sm:rounded-2xl',
          sizes[size],
        ]">
          <header class="flex shrink-0 items-start gap-3 border-b border-line px-5 py-4 sm:px-6">
            <span v-if="icon" :class="[
              'inline-flex size-10 shrink-0 items-center justify-center rounded-xl',
              tone === 'danger' ? 'bg-red-500/10 text-red-600 dark:text-red-400' : 'bg-primary-500/10 text-primary-600 dark:text-primary-400',
            ]">
              <component :is="icon" :size="20" stroke-width="2.25" />
            </span>
            <div class="min-w-0 flex-1 self-center">
              <h2 class="font-display text-2xl leading-tight font-semibold tracking-wide text-ink uppercase">
                {{ title }}
              </h2>
              <p v-if="description" class="mt-0.5 text-sm text-ink-soft">{{ description }}</p>
            </div>
            <UiIconButton :icon="X" :label="t('close')" :disabled="busy" @click="close" />
          </header>

          <div class="relative flex-1 overflow-y-auto px-5 py-5 sm:px-6">
            <slot />
          </div>

          <footer v-if="$slots.footer"
            class="flex shrink-0 flex-col-reverse gap-2 border-t border-line bg-sunken/50 px-5 py-4 sm:flex-row sm:justify-end sm:px-6">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
