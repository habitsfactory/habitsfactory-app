<script setup>
import { CircleAlert, CircleCheck, X } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import { useToast } from '@/composables/useToast'

const { t } = useLanguage()
const { toasts, dismiss } = useToast()

const types = {
  error: { icon: CircleAlert, class: 'text-red-600 dark:text-red-400' },
  success: { icon: CircleCheck, class: 'text-emerald-600 dark:text-emerald-400' },
}
</script>

<template>
  <Teleport to="body">
    <TransitionGroup tag="div" aria-live="assertive"
      class="pointer-events-none fixed inset-x-0 top-4 z-100 flex flex-col items-center gap-2 px-4"
      enter-active-class="transition duration-200 ease-out" enter-from-class="-translate-y-3 opacity-0"
      leave-active-class="transition duration-150 ease-in" leave-to-class="-translate-y-3 opacity-0"
      move-class="transition duration-200">
      <div v-for="toast in toasts" :key="toast.id" role="alert"
        class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-line bg-surface py-3 pr-2 pl-4 shadow-lg">
        <component :is="types[toast.type].icon" :size="20" stroke-width="2.25"
          :class="['mt-0.5 shrink-0', types[toast.type].class]" />
        <p class="min-w-0 flex-1 py-0.5 text-sm font-medium text-ink">{{ t(toast.key) }}</p>
        <button type="button" :aria-label="t('close')"
          class="inline-flex size-7 shrink-0 items-center justify-center rounded-lg text-ink-faint transition-colors hover:bg-sunken hover:text-ink"
          @click="dismiss(toast.id)">
          <X :size="16" />
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>
