<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronDown, UserRound, ShieldCheck, Moon, Sun, Languages, Download, Upload, LogOut } from 'lucide-vue-next'
import authService from '@/services/auth'
import { useDarkMode } from '@/composables/useDarkMode'
import { useLanguage } from '@/composables/useLanguage'
import { useCurrentUser } from '@/composables/useCurrentUser'
import UiDropdown from '@/components/ui/UiDropdown.vue'
import UiMenuItem from '@/components/ui/UiMenuItem.vue'
import UiSegmented from '@/components/ui/UiSegmented.vue'

const router = useRouter()
const { isDark, toggleDarkMode } = useDarkMode()
const { currentLanguage, setLanguage, languages, t } = useLanguage()
const { user, isAdmin, fetchUser, clearUser } = useCurrentUser()

// Fall back to the profile stored at login until the API answers
const displayUser = computed(() => user.value || authService.getCurrentUser() || {})
const initial = computed(() => (displayUser.value.username || displayUser.value.email || '?').charAt(0).toUpperCase())

const languageOptions = languages.map((lang) => ({
  value: lang.code,
  label: lang.code.toUpperCase(),
  title: lang.name,
}))

const language = computed({
  get: () => currentLanguage.value,
  set: setLanguage,
})

const logout = async () => {
  await authService.logout()
  clearUser()
  router.push('/login')
}

onMounted(() => fetchUser())
</script>

<template>
  <UiDropdown width="w-64">
    <template #trigger="{ open, toggle }">
      <button type="button" :aria-expanded="open" :aria-label="t('account')"
        class="flex h-10 items-center gap-1.5 rounded-xl border border-line bg-surface pr-2 pl-1 transition-colors hover:border-line-strong hover:bg-sunken"
        @click="toggle">
        <span
          class="inline-flex size-8 items-center justify-center rounded-lg bg-primary-600 font-display text-lg font-semibold text-white">
          {{ initial }}
        </span>
        <ChevronDown :size="16" class="text-ink-faint transition-transform" :class="open && 'rotate-180'" />
      </button>
    </template>

    <template #default="{ close }">
      <div class="border-b border-line px-3 pt-1.5 pb-3">
        <p class="truncate text-sm font-semibold text-ink">{{ displayUser.username }}</p>
        <p class="truncate text-xs text-ink-faint">{{ displayUser.email }}</p>
      </div>

      <div class="py-1.5" @click="close">
        <UiMenuItem to="/profile" :icon="UserRound">{{ t('profile') }}</UiMenuItem>
        <UiMenuItem v-if="isAdmin" to="/admin-settings" :icon="ShieldCheck">{{ t('adminSettings') }}</UiMenuItem>
        <UiMenuItem to="/export" :icon="Download">{{ t('exportData') }}</UiMenuItem>
        <UiMenuItem to="/import" :icon="Upload">{{ t('importData') }}</UiMenuItem>
      </div>

      <div class="border-t border-line py-1.5">
        <UiMenuItem :icon="isDark ? Sun : Moon" @click="toggleDarkMode">
          {{ isDark ? t('lightMode') : t('darkMode') }}
        </UiMenuItem>
        <div class="flex items-center gap-3 px-3 py-1.5 text-sm font-medium text-ink">
          <Languages :size="18" stroke-width="2.25" class="shrink-0 text-ink-faint" />
          <span class="flex-1">{{ t('language') }}</span>
          <UiSegmented v-model="language" :options="languageOptions" />
        </div>
      </div>

      <div class="border-t border-line pt-1.5">
        <UiMenuItem :icon="LogOut" danger @click="logout">{{ t('logout') }}</UiMenuItem>
      </div>
    </template>
  </UiDropdown>
</template>
