<script setup>
// Shell for the signed-out screens: animated backdrop + centered card.
import { Moon, Sun } from 'lucide-vue-next'
import { useDarkMode } from '@/composables/useDarkMode'
import { useLanguage } from '@/composables/useLanguage'
import BackgroundCards from '@/components/BackgroundCards.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'

defineProps({
  subtitle: { type: String, default: '' },
})

const { isDark, toggleDarkMode } = useDarkMode()
const { currentLanguage, setLanguage, languages, t } = useLanguage()
</script>

<template>
  <div class="relative flex min-h-dvh items-center justify-center overflow-hidden px-4 py-16 sm:px-6">
    <BackgroundCards />
    <!-- Veil that keeps the card readable over the moving backdrop -->
    <div class="pointer-events-none absolute inset-0 bg-canvas/50"></div>

    <div class="absolute top-4 right-4 z-20 flex items-center gap-1 rounded-xl border border-line bg-surface/90 p-1 shadow-xs backdrop-blur">
      <button v-for="lang in languages" :key="lang.code" type="button" :title="lang.name"
        :aria-pressed="currentLanguage === lang.code" :class="[
          'h-8 rounded-lg px-2.5 text-xs font-semibold uppercase transition-colors',
          currentLanguage === lang.code ? 'bg-sunken text-ink' : 'text-ink-faint hover:text-ink',
        ]" @click="setLanguage(lang.code)">
        {{ lang.code }}
      </button>
      <UiIconButton :icon="isDark ? Sun : Moon" :label="isDark ? t('lightMode') : t('darkMode')" size="sm"
        @click="toggleDarkMode" />
    </div>

    <main class="relative z-10 w-full max-w-md rounded-3xl border border-line bg-surface p-7 shadow-2xl sm:p-10">
      <div class="mb-8 text-center">
        <img src="/logo_edition.svg" alt="" class="mx-auto mb-3 size-16" />
        <h1 class="font-display text-4xl font-bold tracking-wide text-ink uppercase">{{ t('appName') }}</h1>
        <p v-if="subtitle" class="mt-1 text-ink-soft">{{ subtitle }}</p>
      </div>

      <slot />
    </main>
  </div>
</template>
