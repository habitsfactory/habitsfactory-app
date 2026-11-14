<script setup>
import { ref, computed, watch, onMounted, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import { useHabits } from '@/composables/useHabits'
import { useCategories } from '@/composables/useCategories'
import { Plus, ChevronDown, PenLine, Sparkles, CalendarCheck, ClipboardList, ChartLine, Lightbulb } from 'lucide-vue-next'
import AppHeader from '@/components/layout/AppHeader.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import UiDropdown from '@/components/ui/UiDropdown.vue'
import UiMenuItem from '@/components/ui/UiMenuItem.vue'
import TrackingTab from '@/components/TrackingTab.vue'
import SummaryTab from '@/components/SummaryTab.vue'
import InsightsTab from '@/components/InsightsTab.vue'
import HabitFormModal from '@/components/habits/HabitFormModal.vue'
import HabitTemplatesModal from '@/components/habits/HabitTemplatesModal.vue'

// Chart.js is heavy: only load it when the Graph tab is opened
const GraphTab = defineAsyncComponent(() => import('@/components/GraphTab.vue'))

const route = useRoute()
const router = useRouter()
const { t } = useLanguage()
const { addHabit } = useHabits()
const { fetchCategories } = useCategories()

// --- Tabs ---
const tabs = computed(() => [
  { value: 'tracking', label: t('tracking'), icon: CalendarCheck },
  { value: 'summary', label: t('summary'), icon: ClipboardList },
  { value: 'graph', label: t('graph'), icon: ChartLine },
  { value: 'insights', label: t('insights'), icon: Lightbulb },
])

const TAB_VALUES = ['tracking', 'summary', 'graph', 'insights']
const activeTab = ref(TAB_VALUES.includes(route.query.tab) ? route.query.tab : 'tracking')

// Tabs are mounted on first visit, then kept alive (hidden) to preserve state
const visitedTabs = ref(new Set([activeTab.value]))

const trackingTabRef = ref(null)
const summaryTabRef = ref(null)
const graphTabRef = ref(null)
const insightsTabRef = ref(null)

watch(activeTab, (tab) => {
  // Keep the tab in the URL so reload / back work as expected
  router.replace({ query: tab === 'tracking' ? {} : { tab } })

  // Refresh data when coming back to an already-mounted tab
  if (visitedTabs.value.has(tab)) {
    if (tab === 'summary') summaryTabRef.value?.fetchSummaryData()
    if (tab === 'graph') graphTabRef.value?.fetchGraphData()
    if (tab === 'insights') insightsTabRef.value?.fetchInsightsData()
  }
  visitedTabs.value.add(tab)
  window.scrollTo({ top: 0 })
})

// --- New habit ---
const isFormOpen = ref(false)
const isSavingHabit = ref(false)
const formError = ref('')

const isTemplateModalOpen = ref(false)
const isAddingTemplate = ref(false)

const openHabitForm = () => {
  formError.value = ''
  isFormOpen.value = true
}

const createHabit = async (payload) => {
  isSavingHabit.value = true
  formError.value = ''
  try {
    await addHabit(payload)
    isFormOpen.value = false
    activeTab.value = 'tracking'
    trackingTabRef.value?.refreshHabits()
  } catch (err) {
    formError.value = t('saveFailed')
  } finally {
    isSavingHabit.value = false
  }
}

const addHabitFromTemplate = async (template) => {
  isAddingTemplate.value = true
  try {
    await addHabit({
      name: t(template.nameKey) || template.name,
      habit_type: template.habit_type,
      icon: template.icon,
      color: template.color,
      unit: template.unit || null,
      max_value: template.max_value || null
    })
    isTemplateModalOpen.value = false
    activeTab.value = 'tracking'
    trackingTabRef.value?.refreshHabits()
  } catch (err) {
    notifyError(err, 'saveFailed')
  } finally {
    isAddingTemplate.value = false
  }
}

onMounted(() => {
  fetchCategories()
})
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <AppHeader>
      <!-- Desktop tabs -->
      <template #nav>
        <nav class="hidden items-center gap-1 md:flex" :aria-label="t('appName')">
          <button v-for="tab in tabs" :key="tab.value" type="button"
            :aria-current="activeTab === tab.value ? 'page' : undefined" :class="[
              'inline-flex h-10 items-center gap-2 rounded-xl px-3.5 text-sm font-semibold transition-colors',
              activeTab === tab.value
                ? 'bg-primary-500/10 text-primary-700 dark:text-primary-300'
                : 'text-ink-soft hover:bg-sunken hover:text-ink',
            ]" @click="activeTab = tab.value">
            <component :is="tab.icon" :size="18" stroke-width="2.25" />
            {{ tab.label }}
          </button>
        </nav>
      </template>

      <template #actions>
        <UiDropdown width="w-72">
          <template #trigger="{ open, toggle }">
            <button type="button" :aria-expanded="open"
              class="inline-flex h-10 items-center gap-2 rounded-xl bg-primary-600 px-3 text-sm font-semibold text-white shadow-xs transition hover:bg-primary-700 active:scale-[.98] sm:px-4 dark:hover:bg-primary-500"
              @click="toggle">
              <Plus :size="18" stroke-width="2.5" />
              <span class="hidden sm:inline">{{ t('newHabit') }}</span>
              <ChevronDown :size="16" class="transition-transform" :class="open && 'rotate-180'" />
            </button>
          </template>

          <template #default="{ close }">
            <div @click="close">
              <UiMenuItem :icon="PenLine" :description="t('createCustomDesc')" @click="openHabitForm">
                {{ t('createCustom') }}
              </UiMenuItem>
              <UiMenuItem :icon="Sparkles" :description="t('fromTemplatesDesc')" @click="isTemplateModalOpen = true">
                {{ t('fromTemplates') }}
              </UiMenuItem>
            </div>
          </template>
        </UiDropdown>
      </template>
    </AppHeader>

    <main class="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
      <TrackingTab v-if="visitedTabs.has('tracking')" v-show="activeTab === 'tracking'" ref="trackingTabRef"
        @open-template-modal="isTemplateModalOpen = true" @open-habit-form="openHabitForm" />
      <SummaryTab v-if="visitedTabs.has('summary')" v-show="activeTab === 'summary'" ref="summaryTabRef" />
      <GraphTab v-if="visitedTabs.has('graph')" v-show="activeTab === 'graph'" ref="graphTabRef" />
      <InsightsTab v-if="visitedTabs.has('insights')" v-show="activeTab === 'insights'" ref="insightsTabRef" />
    </main>

    <!-- Bottom padding leaves room for the mobile tab bar -->
    <SiteFooter class="pb-20 md:pb-0" />

    <!-- Mobile tabs -->
    <nav
      class="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden"
      :aria-label="t('appName')">
      <div class="mx-auto grid max-w-md grid-cols-4">
        <button v-for="tab in tabs" :key="tab.value" type="button"
          :aria-current="activeTab === tab.value ? 'page' : undefined" :class="[
            'relative flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold transition-colors',
            activeTab === tab.value ? 'text-primary-600 dark:text-primary-400' : 'text-ink-faint hover:text-ink',
          ]" @click="activeTab = tab.value">
          <span v-if="activeTab === tab.value" class="absolute inset-x-6 top-0 h-0.5 rounded-full bg-primary-500"></span>
          <component :is="tab.icon" :size="22" stroke-width="2.25" />
          {{ tab.label }}
        </button>
      </div>
    </nav>

    <HabitFormModal :open="isFormOpen" :saving="isSavingHabit" :error="formError" @close="isFormOpen = false"
      @save="createHabit" />

    <HabitTemplatesModal :open="isTemplateModalOpen" :busy="isAddingTemplate" @close="isTemplateModalOpen = false"
      @select="addHabitFromTemplate" />
  </div>
</template>
