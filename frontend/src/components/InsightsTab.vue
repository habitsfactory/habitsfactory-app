<script setup>
import { ref, onMounted } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import { Lightbulb, Link2, CalendarDays } from 'lucide-vue-next'
import api from '@/services/api'
import { parseISODate } from '@/utils/dates'
import UiSpinner from '@/components/ui/UiSpinner.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'
import HabitIcon from '@/components/habits/HabitIcon.vue'

const { t, locale } = useLanguage()

// Insights state
const insightsData = ref([])
const isFetchingInsights = ref(false)

// Fetch insights data
const fetchInsightsData = async () => {
    isFetchingInsights.value = true
    try {
        const response = await api.get('correlations/', {
            params: {
                limit: 10,
                min_correlation: 0.3
            }
        })
        insightsData.value = response.data.insights || []
    } catch (err) {
        insightsData.value = []
        notifyError(err, 'loadFailed')
    } finally {
        isFetchingInsights.value = false
    }
}

// Badge color + translation key per correlation strength
const strengths = {
    very_strong: { key: 'strengthVeryStrong', class: 'bg-violet-500/10 text-violet-700 dark:text-violet-300' },
    strong: { key: 'strengthStrong', class: 'bg-primary-500/10 text-primary-700 dark:text-primary-300' },
    moderate: { key: 'strengthModerate', class: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' },
    weak: { key: 'strengthWeak', class: 'bg-amber-500/10 text-amber-700 dark:text-amber-300' },
    very_weak: { key: 'strengthVeryWeak', class: 'bg-sunken text-ink-soft' },
}

const strengthOf = (insight) => strengths[insight.strength] || strengths.moderate

const formatDate = (value) => parseISODate(value).toLocaleDateString(locale.value, {
    year: 'numeric', month: 'short', day: 'numeric'
})

defineExpose({ fetchInsightsData })

onMounted(() => {
    fetchInsightsData()
})
</script>

<template>
    <div class="space-y-6">
        <!-- Header -->
        <section
            class="relative overflow-hidden rounded-2xl bg-linear-to-br from-primary-600 to-primary-950 p-5 text-white shadow-md sm:p-6">
            <Lightbulb :size="170" stroke-width="1.5"
                class="pointer-events-none absolute -right-6 -bottom-10 text-white/10" />
            <div class="relative">
                <h2 class="font-display text-3xl font-bold tracking-wide uppercase">{{ t('habitInsights') }}</h2>
                <p class="mt-1 text-sm text-primary-100">{{ t('discoverCorrelations') }}</p>
            </div>
        </section>

        <UiSpinner v-if="isFetchingInsights && insightsData.length === 0" :label="t('loading')" />

        <div v-else-if="insightsData.length > 0" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <article v-for="(insight, index) in insightsData" :key="index"
                class="flex flex-col rounded-2xl border border-line bg-surface p-5 shadow-xs">
                <div class="flex items-center justify-between gap-3">
                    <span
                        :class="['rounded-full px-2.5 py-1 text-xs font-semibold tracking-wider uppercase', strengthOf(insight).class]">
                        {{ t(strengthOf(insight).key) }}
                    </span>
                    <span class="font-display text-4xl leading-none font-semibold text-primary-600 tabular-nums dark:text-primary-400"
                        :title="t('correlation')">
                        {{ (insight.max_correlation * 100).toFixed(0) }}%
                    </span>
                </div>

                <!-- Habit pair -->
                <div class="my-4">
                    <template v-for="(habit, position) in [insight.habit1, insight.habit2]" :key="position">
                        <div v-if="position === 1" class="ml-8 flex h-6 items-center">
                            <span class="-ml-px h-full w-px bg-line-strong"></span>
                            <span
                                class="-ml-3 inline-flex size-6 items-center justify-center rounded-full border border-line-strong bg-surface text-ink-faint">
                                <Link2 :size="12" stroke-width="2.5" />
                            </span>
                        </div>
                        <div class="flex items-center gap-3 rounded-xl bg-sunken p-3">
                            <HabitIcon :icon="habit.icon" :color="habit.color" size="sm" />
                            <div class="min-w-0 flex-1">
                                <h4 class="truncate text-sm font-semibold text-ink">{{ habit.name }}</h4>
                                <p v-if="habit.category_name" class="truncate text-xs text-ink-faint">
                                    {{ habit.category_name }}
                                </p>
                            </div>
                        </div>
                    </template>
                </div>

                <p v-if="insight.description" class="mb-4 text-sm leading-relaxed text-ink-soft">
                    {{ insight.description }}
                </p>

                <div
                    class="mt-auto flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-line pt-3 text-xs font-medium text-ink-faint">
                    <span>{{ t('basedOnDays', { n: insight.sample_size }) }}</span>
                    <span class="inline-flex items-center gap-1.5">
                        <CalendarDays :size="13" stroke-width="2.25" />
                        {{ formatDate(insight.start_date) }} – {{ formatDate(insight.end_date) }}
                    </span>
                </div>
            </article>
        </div>

        <UiEmptyState v-else :icon="Lightbulb" :title="t('noInsightsYet')" :description="t('computeCorrelations')" />
    </div>
</template>
