<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import authService from '@/services/auth'
import { useDarkMode } from '@/composables/useDarkMode'
import { useLanguage } from '@/composables/useLanguage'
import { useHabits } from '@/composables/useHabits'
import { useCategories } from '@/composables/useCategories'
import * as LucideIcons from 'lucide-vue-next'
import { Plus, X, ChevronDown, Moon, Sun, BarChart3, FileText, Calendar, Languages, Check, Brain, LogOut, Sparkles, RefreshCw, PenLine } from 'lucide-vue-next'
import IconPicker from '@/components/IconPicker.vue'
import TrackingTab from '@/components/TrackingTab.vue'
import InsightsTab from '@/components/InsightsTab.vue'
import SummaryTab from '@/components/SummaryTab.vue'
import GraphTab from '@/components/GraphTab.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import habitTemplatesData from '@/data/habitTemplates.json'

const router = useRouter()
const { isDark, toggleDarkMode } = useDarkMode()
const { currentLanguage, setLanguage, languages, currentLanguageInfo, t } = useLanguage()
const { addHabit: addHabitApi } = useHabits()
const { categories, fetchCategories } = useCategories()

// Language dropdown state
const isLanguageDropdownOpen = ref(false)

// New habit dropdown state
const isNewHabitDropdownOpen = ref(false)

// --- STATE ---
const isModalOpen = ref(false)
const isTemplateModalOpen = ref(false)
const isAddingTemplate = ref(false)
const activeTab = ref('tracking')

// Template data
const habitTemplates = habitTemplatesData.categories

// Ref to TrackingTab for refreshing
const trackingTabRef = ref(null)

// Form Refs for New Habit
const newHabitName = ref('')
const newHabitType = ref('boolean')
const newHabitIcon = ref('calendar')
const newHabitColor = ref('#d97706')
const newHabitCategoryId = ref(null)
const newHabitMaxValue = ref(5)


// --- LOGIC ---
// --- LOGIC ---

const handleLogout = () => {
  authService.logout()
  router.push('/login')
}

const goToAdminSettings = () => {
  router.push('/admin-settings')
}

const goToExport = () => {
  router.push('/export')
}

// Handle new habit form submission
const addHabit = async () => {
  try {
    await addHabitApi({
      name: newHabitName.value,
      habit_type: newHabitType.value,
      icon: newHabitIcon.value,
      color: newHabitColor.value,
      category: newHabitCategoryId.value,
      max_value: newHabitType.value === 'rating' ? newHabitMaxValue.value : null
    })
    // Reset form and close modal
    newHabitName.value = ''
    newHabitType.value = 'boolean'
    newHabitIcon.value = 'calendar'
    newHabitColor.value = '#d97706'
    newHabitCategoryId.value = null
    newHabitMaxValue.value = 5
    isModalOpen.value = false
  } catch (err) {
    console.error('Failed to add habit:', err)
  }
}

const selectLanguage = (langCode) => {
  setLanguage(langCode)
  isLanguageDropdownOpen.value = false
}

// Get icon component from name
const getIcon = (iconName) => {
  if (!iconName) return LucideIcons.Calendar
  const pascalCase = iconName
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('')
  return LucideIcons[pascalCase] || LucideIcons.Calendar
}

// Add habit from template
const addHabitFromTemplate = async (template) => {
  isAddingTemplate.value = true
  try {
    await addHabitApi({
      name: t(template.nameKey) || template.name,
      habit_type: template.habit_type,
      icon: template.icon,
      color: template.color,
      unit: template.unit || null,
      max_value: template.max_value || null
    })
    isTemplateModalOpen.value = false
    // Refresh the tracking tab
    if (trackingTabRef.value?.refreshHabits) {
      trackingTabRef.value.refreshHabits()
    }
  } catch (err) {
    console.error('Failed to add habit from template:', err)
  } finally {
    isAddingTemplate.value = false
  }
}

// Handle opening template modal from TrackingTab empty state
const openTemplateModal = () => {
  isTemplateModalOpen.value = true
}

// Close dropdowns when clicking outside
const closeDropdowns = (event) => {
  if (!event.target.closest('.language-dropdown-container')) {
    isLanguageDropdownOpen.value = false
  }
  if (!event.target.closest('.new-habit-dropdown-container')) {
    isNewHabitDropdownOpen.value = false
  }
}

onMounted(() => {
  fetchCategories()
  document.addEventListener('click', closeDropdowns)
})

onUnmounted(() => {
  document.removeEventListener('click', closeDropdowns)
})

</script>

<template>
  <div
    class="min-h-screen bg-neutral-50 dark:bg-neutral-900 p-6 md:p-12 text-neutral-900 dark:text-neutral-100 transition-colors duration-300">
    <div class="max-w-7xl mx-auto">
      <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8">
        <div class="flex items-center gap-4">
          <a href="https://habitsfactory.io" target="_blank" rel="noopener noreferrer">
            <img src="/logo_edition.svg" alt="App Logo" class="h-22 w-22" />
          </a>
          <div>
            <h1 class="text-4xl font-black tracking-tighter text-neutral-900 dark:text-white uppercase italic">
              {{ t('appName') }}
            </h1>
            <p class="text-neutral-400 dark:text-neutral-500 font-medium">{{ t('tagline') }}</p>
          </div>
        </div>
        <div class="flex gap-4">
          <!-- New Habit Dropdown -->
          <div class="relative new-habit-dropdown-container">
            <button @click="isNewHabitDropdownOpen = !isNewHabitDropdownOpen"
              class="bg-primary-600 text-white px-8 py-4 rounded-2xl font-bold flex items-center gap-3 hover:bg-primary-800 transition-all shadow-md active:scale-95">
              <Plus :size="20" stroke-width="3" />
              <span>{{ t('newHabit') }}</span>
              <ChevronDown :size="16" stroke-width="2.5" :class="{ 'rotate-180': isNewHabitDropdownOpen }"
                class="transition-transform" />
            </button>

            <!-- Dropdown Menu -->
            <Transition name="dropdown">
              <div v-if="isNewHabitDropdownOpen"
                class="absolute top-full mt-2 right-0 bg-white dark:bg-neutral-800 rounded-2xl shadow-2xl border border-neutral-200 dark:border-neutral-700 py-2 min-w-56 z-50">
                <button @click="isModalOpen = true; isNewHabitDropdownOpen = false"
                  class="w-full px-4 py-3 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors flex items-center gap-3 text-left">
                  <PenLine :size="20" class="text-primary-600" stroke-width="2.5" />
                  <div>
                    <span class="font-bold text-neutral-900 dark:text-white block">{{ t('createCustom') }}</span>
                    <span class="text-xs text-neutral-500">{{ t('createCustomDesc') }}</span>
                  </div>
                </button>
                <button @click="isTemplateModalOpen = true; isNewHabitDropdownOpen = false"
                  class="w-full px-4 py-3 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors flex items-center gap-3 text-left">
                  <Sparkles :size="20" class="text-primary-500" stroke-width="2.5" />
                  <div>
                    <span class="font-bold text-neutral-900 dark:text-white block">{{ t('fromTemplates') }}</span>
                    <span class="text-xs text-neutral-500">{{ t('fromTemplatesDesc') }}</span>
                  </div>
                </button>
              </div>
            </Transition>
          </div>

          <!-- Language Selector -->
          <div class="relative language-dropdown-container">
            <button @click="isLanguageDropdownOpen = !isLanguageDropdownOpen"
              class="bg-neutral-200 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 px-6 py-4 rounded-2xl font-bold flex items-center gap-3 hover:bg-neutral-300 dark:hover:bg-neutral-700 transition-all shadow-md active:scale-95">
              <Languages :size="20" stroke-width="2.5" />
              <span class="text-xl">{{ currentLanguageInfo.flag }}</span>
              <ChevronDown :size="16" stroke-width="2.5" :class="{ 'rotate-180': isLanguageDropdownOpen }"
                class="transition-transform" />
            </button>

            <!-- Language Dropdown -->
            <Transition name="dropdown">
              <div v-if="isLanguageDropdownOpen"
                class="absolute top-full mt-2 right-0 bg-white dark:bg-neutral-800 rounded-2xl shadow-2xl border border-neutral-200 dark:border-neutral-700 py-2 min-w-50 z-50">
                <button v-for="lang in languages" :key="lang.code" @click="selectLanguage(lang.code)"
                  class="w-full px-4 py-3 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors flex items-center gap-3 text-left">
                  <span class="text-xl">{{ lang.flag }}</span>
                  <span class="font-bold text-neutral-900 dark:text-white">{{ lang.name }}</span>
                  <Check v-if="currentLanguage === lang.code" :size="16"
                    class="ml-auto text-primary-600 dark:text-primary-400" stroke-width="3" />
                </button>
              </div>
            </Transition>
          </div>

          <!-- Dark Mode Toggle -->
          <button @click="toggleDarkMode"
            class="bg-neutral-200 dark:bg-neutral-800 text-yellow-500 dark:text-yellow-700 dark:text-primary-400 px-6 py-4 rounded-2xl font-bold flex items-center gap-3 hover:bg-neutral-300 dark:hover:bg-neutral-700 transition-all shadow-md active:scale-95">
            <Moon v-if="!isDark" :size="20" stroke-width="2.5" />
            <Sun v-else :size="20" stroke-width="2.5" />
          </button>

          <button @click="handleLogout"
            class="bg-neutral-200 text-red-600 px-6 py-4 rounded-2xl font-bold hover:bg-neutral-300 transition-all shadow-md active:scale-95 dark:bg-neutral-800 dark:hover:bg-neutral-700">
            <LogOut :size="20" stroke-width="2.5" />
          </button>
        </div>
      </header>

      <!-- Tabs Navigation -->
      <div class="mb-6">
        <div
          class="flex gap-2 p-2 bg-white dark:bg-neutral-800 rounded-3xl shadow-md border border-neutral-100 dark:border-neutral-700">
          <button @click="activeTab = 'tracking'" :class="[
            'flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-2xl font-bold transition-all',
            activeTab === 'tracking'
              ? 'bg-primary-600 text-white shadow-lg'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700'
          ]">
            <Calendar :size="20" stroke-width="2.5" />
            <span>{{ t('tracking') }}</span>
          </button>

          <button @click="activeTab = 'summary'" :class="[
            'flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-2xl font-bold transition-all',
            activeTab === 'summary'
              ? 'bg-primary-600 text-white shadow-lg'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700'
          ]">
            <FileText :size="20" stroke-width="2.5" />
            <span>{{ t('summary') }}</span>
          </button>

          <button @click="activeTab = 'graph'" :class="[
            'flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-2xl font-bold transition-all',
            activeTab === 'graph'
              ? 'bg-primary-600 text-white shadow-lg'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700'
          ]">
            <BarChart3 :size="20" stroke-width="2.5" />
            <span>{{ t('graph') }}</span>
          </button>

          <button @click="activeTab = 'insights'" :class="[
            'flex-1 flex items-center justify-center gap-2 px-6 py-4 rounded-2xl font-bold transition-all',
            activeTab === 'insights'
              ? 'bg-primary-600 text-white shadow-lg'
              : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700'
          ]">
            <Brain :size="20" stroke-width="2.5" />
            <span>{{ t('insights') }}</span>
          </button>
        </div>
      </div>

      <!-- Tab Content -->

      <!-- Tracking Tab -->
      <TrackingTab ref="trackingTabRef" v-show="activeTab === 'tracking'" @open-template-modal="openTemplateModal" />

      <!-- Summary Tab -->
      <SummaryTab v-show="activeTab === 'summary'" />

      <!-- Graph Tab -->
      <GraphTab v-show="activeTab === 'graph'" />

      <!-- Insights Tab -->
      <InsightsTab v-show="activeTab === 'insights'" />
    </div>

    <SiteFooter />

    <!-- Modal for New Habit -->
    <Transition name="fade">
      <div v-if="isModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-neutral-900/60 backdrop-blur-md" @click="isModalOpen = false"></div>
        <div
          class="relative z-10 bg-white dark:bg-neutral-800 w-full max-w-lg rounded-4xl p-12 shadow-2xl overflow-hidden">
          <div class="absolute top-0 left-0 right-0 h-2 bg-primary-600"></div>

          <div class="flex justify-between items-center mb-10">
            <h2 class="text-3xl font-black text-neutral-900 dark:text-white">{{ t('newHabit') }}</h2>
            <button @click="isModalOpen = false"
              class="text-neutral-300 hover:text-neutral-900 dark:hover:text-white transition">
              <X :size="32" />
            </button>
          </div>

          <form @submit.prevent="addHabit" class="space-y-8">
            <div class="space-y-2">
              <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                t('objectiveName')
              }}</label>
              <input v-model="newHabitName" type="text" :placeholder="t('habitNamePlaceholder')" required
                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-lg text-neutral-900 dark:text-white">
            </div>

            <div class="space-y-2">
              <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{ t('metricType')
              }}</label>
              <select v-model="newHabitType"
                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 font-bold outline-none appearance-none text-neutral-900 dark:text-white">
                <option value="boolean">{{ t('boolean') }}</option>
                <option value="counter">{{ t('counter') }}</option>
                <option value="value">{{ t('value') }}</option>
                <option value="rating">{{ t('rating') }}</option>
              </select>
            </div>

            <IconPicker v-model="newHabitIcon" :label="t('visualIcon')" />

            <!-- Max Value for Rating -->
            <div v-if="newHabitType === 'rating'" class="space-y-2">
              <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">
                {{ t('numberOfStars') }}
              </label>
              <input v-model.number="newHabitMaxValue" type="number" min="1" max="10" placeholder="5"
                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-lg text-neutral-900 dark:text-white">
              <p class="text-xs text-neutral-400 ml-2">
                Between 1-10 stars
              </p>
            </div>

            <div class="space-y-2">
              <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{ t('category')
              }}</label>
              <select v-model="newHabitCategoryId"
                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 font-bold outline-none appearance-none text-neutral-900 dark:text-white">
                <option :value="null">{{ t('uncategorized') }}</option>
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
              </select>
            </div>

            <div class="space-y-2">
              <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                t('identityColor')
              }}</label>
              <div class="flex items-center gap-4 bg-neutral-50 dark:bg-neutral-700 p-4 rounded-3xl">
                <input v-model="newHabitColor" type="color"
                  class="w-16 h-12 rounded-xl border-none bg-transparent cursor-pointer">
                <span class="font-mono font-bold text-neutral-400">{{ newHabitColor }}</span>
              </div>
            </div>

            <button type="submit"
              class="w-full bg-primary-600 text-white py-6 rounded-4xl font-black text-xl hover:bg-primary-700 transition-all shadow-xl">
              {{ t('initiateHabit') }}
            </button>
          </form>
        </div>
      </div>
    </Transition>

    <!-- Template Modal -->
    <Transition name="fade">
      <div v-if="isTemplateModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-neutral-900/60 backdrop-blur-md" @click="isTemplateModalOpen = false"></div>
        <div
          class="relative z-10 bg-white dark:bg-neutral-800 w-full max-w-4xl max-h-[85vh] rounded-4xl shadow-2xl overflow-hidden flex flex-col">
          <!-- Modal Header -->
          <div class="shrink-0 p-8 pb-4 border-b border-neutral-100 dark:border-neutral-700">
            <div class="absolute top-0 left-0 right-0 h-2 bg-primary-600"></div>
            <div class="flex justify-between items-center">
              <div>
                <h2 class="text-3xl font-black text-neutral-900 dark:text-white">{{ t('habitTemplates') }}</h2>
                <p class="text-neutral-500 dark:text-neutral-400 mt-1">{{ t('selectHabitTemplate') }}</p>
              </div>
              <button @click="isTemplateModalOpen = false"
                class="text-neutral-300 hover:text-neutral-900 dark:hover:text-white transition p-2">
                <X :size="28" />
              </button>
            </div>
          </div>

          <!-- Modal Content - Scrollable -->
          <div class="flex-1 overflow-y-auto p-8 space-y-8">
            <!-- Loading Overlay -->
            <div v-if="isAddingTemplate"
              class="absolute inset-0 bg-white/80 dark:bg-neutral-800/80 flex items-center justify-center z-10">
              <RefreshCw :size="40" class="animate-spin text-primary-600" />
            </div>

            <!-- Category Groups -->
            <div v-for="category in habitTemplates" :key="category.id" class="space-y-4">
              <!-- Category Header -->
              <div class="flex items-center gap-3">
                <div class="p-2 rounded-xl" :style="{ backgroundColor: category.color + '20' }">
                  <component :is="getIcon(category.icon)" :size="20" :style="{ color: category.color }"
                    stroke-width="2.5" />
                </div>
                <h3 class="text-lg font-black text-neutral-900 dark:text-white uppercase tracking-tight">
                  {{ t(category.nameKey) || category.name }}
                </h3>
                <div class="flex-1 h-px bg-linear-to-r from-neutral-200 dark:from-neutral-700 to-transparent"></div>
              </div>

              <!-- Habit Cards Grid -->
              <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                <button v-for="habit in category.habits" :key="habit.nameKey" @click="addHabitFromTemplate(habit)"
                  :disabled="isAddingTemplate"
                  class="bg-neutral-50 dark:bg-neutral-700/50 hover:bg-white dark:hover:bg-neutral-700 border border-neutral-100 dark:border-neutral-600 hover:border-neutral-200 dark:hover:border-neutral-500 rounded-2xl p-4 text-left transition-all hover:shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed group">
                  <!-- Habit Icon & Name -->
                  <div class="flex items-center gap-3 mb-2">
                    <div class="p-2 rounded-xl transition-colors" :style="{ backgroundColor: habit.color + '20' }">
                      <component :is="getIcon(habit.icon)" :size="18" :style="{ color: habit.color }"
                        stroke-width="2.5" />
                    </div>
                    <span class="font-bold text-neutral-900 dark:text-white text-sm truncate">
                      {{ t(habit.nameKey) || habit.name }}
                    </span>
                  </div>
                  <!-- Habit Type Badge -->
                  <div class="flex items-center gap-2">
                    <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-lg" :class="{
                      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400': habit.habit_type === 'boolean',
                      'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400': habit.habit_type === 'counter',
                      'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400': habit.habit_type === 'value',
                      'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400': habit.habit_type === 'rating'
                    }">
                      {{ t(habit.habit_type) }}
                    </span>
                    <span v-if="habit.unit" class="text-[10px] text-neutral-400 dark:text-neutral-500 font-medium">
                      {{ habit.unit }}
                    </span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.dropdown-enter-active {
  transition: all 0.2s ease;
}

.dropdown-leave-active {
  transition: all 0.15s ease;
}

.dropdown-enter-from {
  opacity: 0;
  transform: tranneutralY(-10px);
}

.dropdown-leave-to {
  opacity: 0;
  transform: tranneutralY(-5px);
}

input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.category-group {
  user-select: none;
}
</style>