<script setup>
// Shell for secondary pages (profile, admin, import, export):
// app header, back link, page title, content, footer.
import { RouterLink } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import AppHeader from '@/components/layout/AppHeader.vue'
import SiteFooter from '@/components/SiteFooter.vue'

defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  // Tailwind max-width class for the content column
  width: { type: String, default: 'max-w-3xl' },
})

const { t } = useLanguage()
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <AppHeader />

    <main :class="['mx-auto w-full flex-1 px-4 py-8 sm:px-6', width]">
      <RouterLink to="/dashboard"
        class="inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-ink-soft transition-colors hover:text-ink">
        <ArrowLeft :size="16" stroke-width="2.25" />
        {{ t('returnDashboard') }}
      </RouterLink>

      <div class="mt-3 mb-8">
        <h1 class="font-display text-4xl font-bold tracking-wide text-ink uppercase">{{ title }}</h1>
        <p v-if="description" class="mt-1 text-ink-soft">{{ description }}</p>
      </div>

      <div class="space-y-6">
        <slot />
      </div>
    </main>

    <SiteFooter />
  </div>
</template>
