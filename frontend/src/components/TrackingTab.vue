<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import { useHabits } from '@/composables/useHabits'
import { useCategories } from '@/composables/useCategories'
import { useCategoryDrag } from '@/composables/useCategoryDrag'
import { useTags } from '@/composables/useTags'
import { useCookies } from '@/composables/useCookies'
import { toISODate, addDays, isSameDay } from '@/utils/dates'
import {
    ChevronLeft, ChevronRight, LayoutGrid, List, ListFilter, X, Sparkles, PenLine,
    CircleCheck, LoaderCircle, SearchX, Target, CalendarCheck,
} from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiSegmented from '@/components/ui/UiSegmented.vue'
import UiSpinner from '@/components/ui/UiSpinner.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import HabitIcon from '@/components/habits/HabitIcon.vue'
import HabitControl from '@/components/habits/HabitControl.vue'
import TagChip from '@/components/habits/TagChip.vue'
import CategoryHeader from '@/components/habits/CategoryHeader.vue'

const emit = defineEmits(['open-template-modal', 'open-habit-form'])

const { t, locale } = useLanguage()
const { habits, isLoadingHabits, fetchHabits, saveCompletion } = useHabits()
const { categories, fetchCategories, groupByCategory } = useCategories()
const { draggedId, dragOverId, onDragStart, onDragOver, onDrop, onDragEnd, moveGroup } = useCategoryDrag()
const { tags, fetchTags } = useTags()
const { setCookie, getCookie } = useCookies()

// --- Date navigation ---
const currentTrackingDate = ref(new Date())

const trackingDateString = computed(() => toISODate(currentTrackingDate.value))

const isToday = computed(() => isSameDay(currentTrackingDate.value, new Date()))
const isYesterday = computed(() => isSameDay(currentTrackingDate.value, addDays(new Date(), -1)))

const longDate = computed(() => currentTrackingDate.value.toLocaleDateString(locale.value, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
}))

const dayTitle = computed(() => {
    if (isToday.value) return t('today')
    if (isYesterday.value) return t('yesterday')
    return currentTrackingDate.value.toLocaleDateString(locale.value, { weekday: 'long' })
})

const goToDate = (date) => {
    currentTrackingDate.value = date
    fetchHabits(trackingDateString.value)
}

const goToPreviousDay = () => goToDate(addDays(currentTrackingDate.value, -1))
const goToNextDay = () => {
    if (!isToday.value) goToDate(addDays(currentTrackingDate.value, 1))
}
const goToToday = () => goToDate(new Date())

// --- View preference (cards / list), remembered in a cookie ---
const view = ref(getCookie('viewPreference') === 'row' ? 'row' : 'card')
watch(view, (value) => setCookie('viewPreference', value))

const viewOptions = computed(() => [
    { value: 'card', label: t('cardView'), icon: LayoutGrid },
    { value: 'row', label: t('rowView'), icon: List },
])

// --- Filters ---
const isFilterExpanded = ref(false)
const selectedCategories = ref([])
const selectedTags = ref([])

const activeFilterCount = computed(() => selectedCategories.value.length + selectedTags.value.length)
const hasActiveFilters = computed(() => activeFilterCount.value > 0)

const toggleIn = (list, id) => {
    const index = list.value.indexOf(id)
    if (index === -1) list.value.push(id)
    else list.value.splice(index, 1)
}

const clearFilters = () => {
    selectedCategories.value = []
    selectedTags.value = []
}

const filteredHabits = computed(() => {
    let result = habits.value

    if (selectedCategories.value.length > 0) {
        result = result.filter(h => selectedCategories.value.includes(h.category ? h.category.id : 'uncategorized'))
    }

    if (selectedTags.value.length > 0) {
        result = result.filter(h => h.tags?.some(tag => selectedTags.value.includes(tag.id)))
    }

    return result
})

const groupedHabits = computed(() =>
    groupByCategory(filteredHabits.value, h => h.category?.id ?? null, t('uncategorized'))
)

// --- Daily progress ---
const doneCount = computed(() => filteredHabits.value.filter(h => (h.today_value || 0) > 0).length)
const progress = computed(() =>
    filteredHabits.value.length ? Math.round((doneCount.value / filteredHabits.value.length) * 100) : 0
)

// --- Logging ---
const updateHabitValue = async (habit, value) => {
    habit.temp_value = value
    try {
        await saveCompletion(habit, value, trackingDateString.value)
    } catch (err) {
        // Resync with the server if the save failed
        notifyError(err, 'saveFailed')
        fetchHabits(trackingDateString.value)
    }
}

const filterChipClass = (active) => [
    'inline-flex h-8 items-center rounded-full border px-3 text-sm font-medium transition-colors',
    active
        ? 'border-primary-500 bg-primary-500/10 text-primary-700 dark:text-primary-300'
        : 'border-line bg-surface text-ink-soft hover:border-line-strong hover:text-ink',
]

// Expose refresh method for parent component
const refreshHabits = () => {
    fetchCategories()
    return fetchHabits(trackingDateString.value)
}

defineExpose({ refreshHabits })

onMounted(() => {
    fetchCategories()
    fetchTags()
    fetchHabits(trackingDateString.value)
})
</script>

<template>
    <!-- flex + gap (not space-y): the groups use negative margins for their drop highlight -->
    <div class="flex flex-col gap-6">
        <!-- Day navigation + progress -->
        <section class="rounded-2xl border border-line bg-surface p-3 shadow-xs sm:p-4">
            <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
                <div class="flex items-center gap-1">
                    <UiIconButton :icon="ChevronLeft" variant="soft" size="lg" :label="t('previous')"
                        @click="goToPreviousDay" />
                    <UiIconButton :icon="ChevronRight" variant="soft" size="lg" :label="t('next')" :disabled="isToday"
                        @click="goToNextDay" />
                </div>

                <div class="min-w-0 flex-1">
                    <h2 class="truncate font-display text-2xl leading-tight font-semibold tracking-wide text-ink uppercase">
                        {{ dayTitle }}
                    </h2>
                    <p class="truncate text-xs font-medium text-ink-faint first-letter:uppercase">{{ longDate }}</p>
                </div>

                <div class="flex items-center gap-2">
                    <UiButton v-if="!isToday" variant="soft" size="sm" :icon="CalendarCheck" @click="goToToday">
                        {{ t('today') }}
                    </UiButton>

                    <button type="button" :aria-expanded="isFilterExpanded" :class="[
                        'inline-flex h-10 items-center gap-2 rounded-xl border px-3 text-sm font-semibold transition-colors',
                        hasActiveFilters || isFilterExpanded
                            ? 'border-primary-500 bg-primary-500/10 text-primary-700 dark:text-primary-300'
                            : 'border-line bg-surface text-ink-soft hover:border-line-strong hover:text-ink',
                    ]" @click="isFilterExpanded = !isFilterExpanded">
                        <ListFilter :size="18" stroke-width="2.25" />
                        <span class="hidden sm:inline">{{ t('filters') }}</span>
                        <span v-if="hasActiveFilters"
                            class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-600 px-1.5 text-xs font-semibold text-white tabular-nums">
                            {{ activeFilterCount }}
                        </span>
                    </button>

                    <UiSegmented v-model="view" :options="viewOptions" icon-only />
                </div>
            </div>

            <!-- Filters -->
            <div v-if="isFilterExpanded" class="mt-3 space-y-4 border-t border-line pt-4">
                <div>
                    <div class="mb-2 flex items-center justify-between gap-3">
                        <h3 class="text-xs font-semibold tracking-wider text-ink-faint uppercase">{{ t('categories') }}</h3>
                        <button v-if="hasActiveFilters" type="button"
                            class="inline-flex items-center gap-1 rounded-md text-xs font-semibold text-red-600 hover:underline dark:text-red-400"
                            @click="clearFilters">
                            <X :size="14" stroke-width="2.5" />
                            {{ t('clearFilters') }}
                        </button>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button v-for="category in categories" :key="category.id" type="button"
                            :aria-pressed="selectedCategories.includes(category.id)"
                            :class="filterChipClass(selectedCategories.includes(category.id))"
                            @click="toggleIn(selectedCategories, category.id)">
                            {{ category.name }}
                        </button>
                        <button type="button" :aria-pressed="selectedCategories.includes('uncategorized')"
                            :class="filterChipClass(selectedCategories.includes('uncategorized'))"
                            @click="toggleIn(selectedCategories, 'uncategorized')">
                            {{ t('uncategorized') }}
                        </button>
                    </div>
                </div>

                <div>
                    <h3 class="mb-2 text-xs font-semibold tracking-wider text-ink-faint uppercase">{{ t('tags') }}</h3>
                    <div class="flex flex-wrap gap-2">
                        <button v-for="tag in tags" :key="tag.id" type="button" :style="{ '--tag': tag.color }"
                            :aria-pressed="selectedTags.includes(tag.id)" :class="[
                                'inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-sm font-medium text-(--tag) transition-colors',
                                selectedTags.includes(tag.id)
                                    ? 'border-(--tag) bg-(--tag)/15'
                                    : 'border-line bg-surface hover:border-(--tag)/60',
                            ]" @click="toggleIn(selectedTags, tag.id)">
                            <span class="size-2 rounded-full bg-(--tag)"></span>
                            {{ tag.name }}
                        </button>
                        <p v-if="tags.length === 0" class="text-sm text-ink-faint">{{ t('noTags') }}</p>
                    </div>
                </div>
            </div>

            <!-- Progress -->
            <div v-if="filteredHabits.length > 0" class="mt-3 flex items-center gap-3 border-t border-line pt-3">
                <div class="h-2 flex-1 overflow-hidden rounded-full bg-sunken" role="progressbar" :aria-valuenow="progress"
                    aria-valuemin="0" aria-valuemax="100" :aria-label="t('dailyProgress')">
                    <div :class="[
                        'h-full rounded-full transition-all duration-500',
                        progress === 100 ? 'bg-emerald-500' : 'bg-primary-500',
                    ]" :style="{ width: `${progress}%` }"></div>
                </div>
                <span class="shrink-0 text-xs font-semibold text-ink-soft tabular-nums">
                    {{ t('progressToday', { done: doneCount, total: filteredHabits.length }) }}
                </span>
            </div>
        </section>

        <!-- Loading (first load only, so logging doesn't flash the grid) -->
        <UiSpinner v-if="isLoadingHabits && habits.length === 0" />

        <template v-else>
            <!-- Habit groups -->
            <section v-for="(group, index) in groupedHabits" :key="group.id" :class="[
                '-m-2 space-y-3 rounded-2xl p-2 transition',
                draggedId === group.id && 'opacity-40',
                dragOverId === group.id && draggedId !== group.id && 'bg-primary-500/5 ring-2 ring-primary-500',
                isLoadingHabits && 'opacity-60',
            ]" @dragover="onDragOver($event, group.id)" @drop="onDrop($event, group.id)">
                <CategoryHeader :name="group.name" :count="group.habits.length" :can-move-up="index > 0"
                    :can-move-down="index < groupedHabits.length - 1" @dragstart="onDragStart($event, group.id)"
                    @dragend="onDragEnd" @move-up="moveGroup(group.id, groupedHabits[index - 1].id)"
                    @move-down="moveGroup(group.id, groupedHabits[index + 1].id)" />

                <!-- Card view -->
                <div v-if="view === 'card'" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <article v-for="habit in group.habits" :key="habit.id" :style="{ '--habit': habit.color }"
                        class="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-4 shadow-xs transition hover:border-line-strong hover:shadow-md">
                        <div class="flex items-start gap-3">
                            <HabitIcon :icon="habit.icon" :color="habit.color" />
                            <div class="min-w-0 flex-1">
                                <h4 class="truncate leading-snug font-semibold text-ink" :title="habit.name">{{ habit.name }}</h4>
                                <div v-if="habit.tags?.length" class="mt-1 flex flex-wrap gap-1">
                                    <TagChip v-for="tag in habit.tags" :key="tag.id" :tag="tag" />
                                </div>
                            </div>
                            <LoaderCircle v-if="habit.is_saving" :size="18" class="shrink-0 animate-spin text-primary-500" />
                            <CircleCheck v-else-if="habit.today_value > 0" :size="18" stroke-width="2.25"
                                class="shrink-0 text-emerald-500" />
                        </div>

                        <div class="mt-auto">
                            <HabitControl :habit="habit" @update="updateHabitValue(habit, $event)" />
                        </div>
                    </article>
                </div>

                <!-- List view -->
                <div v-else class="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-xs">
                    <div v-for="habit in group.habits" :key="habit.id" :style="{ '--habit': habit.color }"
                        class="flex flex-wrap items-center justify-end gap-x-3 gap-y-2 px-3 py-2.5 sm:px-4">
                        <div class="flex min-w-40 flex-1 items-center gap-3">
                            <HabitIcon :icon="habit.icon" :color="habit.color" size="sm" />
                            <div class="min-w-0 flex-1">
                                <h4 class="truncate text-sm font-semibold text-ink" :title="habit.name">{{ habit.name }}</h4>
                                <div v-if="habit.tags?.length" class="mt-0.5 flex flex-wrap gap-1">
                                    <TagChip v-for="tag in habit.tags" :key="tag.id" :tag="tag" />
                                </div>
                            </div>
                        </div>
                        <LoaderCircle v-if="habit.is_saving" :size="16" class="shrink-0 animate-spin text-primary-500" />
                        <HabitControl :habit="habit" compact @update="updateHabitValue(habit, $event)" />
                    </div>
                </div>
            </section>

            <!-- Empty states -->
            <UiEmptyState v-if="groupedHabits.length === 0 && hasActiveFilters" :icon="SearchX"
                :title="t('noMatchingHabits')" :description="t('noHabitsMatchFilters')">
                <UiButton variant="secondary" :icon="X" @click="clearFilters">{{ t('clearFilters') }}</UiButton>
            </UiEmptyState>

            <UiEmptyState v-else-if="groupedHabits.length === 0" :icon="Target" :title="t('noHabitsYet')"
                :description="t('createFirstHabit')">
                <UiButton :icon="Sparkles" @click="emit('open-template-modal')">{{ t('addFromTemplates') }}</UiButton>
                <UiButton variant="secondary" :icon="PenLine" @click="emit('open-habit-form')">
                    {{ t('createCustom') }}
                </UiButton>
            </UiEmptyState>
        </template>
    </div>
</template>
