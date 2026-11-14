<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Github, Mail, Globe } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import { useCurrentUser } from '@/composables/useCurrentUser'

const { t } = useLanguage()
const { isAdmin, fetchUser } = useCurrentUser()

const linkClass = 'inline-flex items-center gap-2 rounded-md text-ink-soft transition-colors hover:text-primary-600 dark:hover:text-primary-400'
const headingClass = 'mb-3 text-xs font-semibold tracking-wider text-ink-faint uppercase'

onMounted(() => fetchUser())
</script>

<template>
  <footer class="mt-12 border-t border-line bg-surface/60">
    <div class="mx-auto grid w-full max-w-6xl grid-cols-2 gap-8 px-4 py-10 text-sm sm:px-6 md:grid-cols-4">
      <div class="col-span-2 md:col-span-1">
        <a href="https://habitsfactory.io" target="_blank" rel="noopener noreferrer"
          class="inline-flex items-center gap-2.5 rounded-lg">
          <img src="/logo_edition.svg" alt="" class="size-10" />
          <span class="font-display text-xl font-bold tracking-wide text-ink uppercase">{{ t('appName') }}</span>
        </a>
        <p class="mt-3 max-w-xs text-ink-soft">{{ t('footerTagline') }}</p>
      </div>

      <nav :aria-label="t('management')">
        <h3 :class="headingClass">{{ t('management') }}</h3>
        <ul class="space-y-2">
          <li>
            <RouterLink to="/profile" :class="linkClass">{{ t('profile') }}</RouterLink>
          </li>
          <li v-if="isAdmin">
            <RouterLink to="/admin-settings" :class="linkClass">{{ t('adminSettings') }}</RouterLink>
          </li>
        </ul>
      </nav>

      <nav :aria-label="t('data')">
        <h3 :class="headingClass">{{ t('data') }}</h3>
        <ul class="space-y-2">
          <li>
            <RouterLink to="/import" :class="linkClass">{{ t('importData') }}</RouterLink>
          </li>
          <li>
            <RouterLink to="/export" :class="linkClass">{{ t('exportData') }}</RouterLink>
          </li>
        </ul>
      </nav>

      <div class="col-span-2 md:col-span-1">
        <h3 :class="headingClass">{{ t('support') }}</h3>
        <ul class="space-y-2">
          <li>
            <a href="https://github.com/habitsfactory/habitsfactory-app" target="_blank" rel="noopener noreferrer"
              :class="linkClass">
              <Github :size="16" stroke-width="2.25" />
              {{ t('viewOnGithub') }}
            </a>
          </li>
          <li>
            <a href="https://habitsfactory.io" target="_blank" rel="noopener noreferrer" :class="linkClass">
              <Globe :size="16" stroke-width="2.25" />
              habitsfactory.io
            </a>
          </li>
          <li>
            <a href="mailto:contact@habitsfactory.io" :class="linkClass">
              <Mail :size="16" stroke-width="2.25" />
              contact@habitsfactory.io
            </a>
          </li>
          <li class="pt-1">
            <a href="https://ko-fi.com/joeydev" target="_blank" rel="noopener noreferrer" class="inline-block rounded-lg">
              <img src="/support_me_on_kofi_dark.png" alt="Support me on Ko-fi" class="h-9 w-auto" />
            </a>
          </li>
        </ul>
      </div>
    </div>

    <div class="border-t border-line">
      <p class="mx-auto w-full max-w-6xl px-4 py-4 text-center text-xs text-ink-faint sm:px-6">
        © {{ new Date().getFullYear() }} {{ t('appName') }} · {{ t('license') }}
      </p>
    </div>
  </footer>
</template>
