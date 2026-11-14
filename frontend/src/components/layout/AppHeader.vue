<script setup>
import { RouterLink } from 'vue-router'
import { useLanguage } from '@/composables/useLanguage'
import UserMenu from '@/components/layout/UserMenu.vue'

const { t } = useLanguage()
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur-md">
    <div class="mx-auto flex h-16 w-full max-w-6xl items-center gap-3 px-4 sm:px-6">
      <RouterLink to="/dashboard" class="flex shrink-0 items-center gap-2.5 rounded-lg" :title="t('tagline')">
        <img src="/logo_edition.svg" alt="" class="size-9" />
        <span class="hidden font-display text-2xl leading-none font-bold tracking-wide text-ink uppercase sm:block">
          {{ t('appName') }}
        </span>
      </RouterLink>

      <div class="flex min-w-0 flex-1 justify-center">
        <slot name="nav" />
      </div>

      <div class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
        <UserMenu />
      </div>
    </div>
  </header>
</template>
