<script setup>
import { Sparkles, LoaderCircle } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import UiModal from '@/components/ui/UiModal.vue'
import HabitIcon from '@/components/habits/HabitIcon.vue'
import habitTemplatesData from '@/data/habitTemplates.json'

defineProps({
  open: Boolean,
  // A template is being added
  busy: Boolean,
})

const emit = defineEmits(['close', 'select'])

const { t } = useLanguage()

const templateCategories = habitTemplatesData.categories

const typeBadges = {
  boolean: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  counter: 'bg-sky-500/10 text-sky-700 dark:text-sky-300',
  value: 'bg-violet-500/10 text-violet-700 dark:text-violet-300',
  rating: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
  percentage: 'bg-violet-500/10 text-violet-700 dark:text-violet-300',
}
</script>

<template>
  <UiModal :open="open" :title="t('habitTemplates')" :description="t('selectHabitTemplate')" :icon="Sparkles"
    size="xl" :busy="busy" @close="emit('close')">
    <div class="space-y-7">
      <section v-for="category in templateCategories" :key="category.id">
        <div class="mb-3 flex items-center gap-2.5">
          <HabitIcon :icon="category.icon" :color="category.color" size="sm" />
          <h3 class="font-display text-lg font-semibold tracking-wide text-ink uppercase">
            {{ t(category.nameKey) }}
          </h3>
          <span class="h-px flex-1 bg-line"></span>
        </div>

        <div class="grid grid-cols-1 gap-2 min-[420px]:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          <button v-for="habit in category.habits" :key="habit.nameKey" type="button" :disabled="busy"
            class="group flex items-center gap-3 rounded-xl border border-line bg-surface p-3 text-left transition hover:border-primary-500 hover:shadow-md active:scale-[.98] disabled:pointer-events-none disabled:opacity-50"
            @click="emit('select', habit)">
            <HabitIcon :icon="habit.icon" :color="habit.color" size="sm" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold text-ink">{{ t(habit.nameKey) }}</span>
              <span class="mt-1 flex items-center gap-1.5">
                <span
                  :class="['rounded-md px-1.5 py-0.5 text-[10px] font-semibold tracking-wider uppercase', typeBadges[habit.habit_type]]">
                  {{ t(habit.habit_type) }}
                </span>
                <span v-if="habit.unit" class="truncate text-[11px] text-ink-faint">{{ habit.unit }}</span>
              </span>
            </span>
          </button>
        </div>
      </section>
    </div>

    <!-- Busy overlay -->
    <div v-if="busy" class="absolute inset-0 flex items-center justify-center bg-surface/70">
      <LoaderCircle :size="36" class="animate-spin text-primary-500" />
    </div>
  </UiModal>
</template>
