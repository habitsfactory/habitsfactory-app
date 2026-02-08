<script setup>
import { ref, onMounted } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import * as LucideIcons from 'lucide-vue-next'
import { RefreshCw } from 'lucide-vue-next'
import api from '@/services/api'

const { t } = useLanguage()

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
        console.error('Failed to fetch insights:', err)
        insightsData.value = []
    } finally {
        isFetchingInsights.value = false
    }
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

// Helper function to get correlation badge color
const getCorrelationBadgeColor = (strength) => {
    const colors = {
        'very_strong': 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300',
        'strong': 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300',
        'moderate': 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300',
        'weak': 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300',
        'very_weak': 'bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-300'
    }
    return colors[strength] || colors['moderate']
}

// Helper function to get strength label
const getStrengthLabel = (strength) => {
    const labels = {
        'very_strong': 'Very Strong',
        'strong': 'Strong',
        'moderate': 'Moderate',
        'weak': 'Weak',
        'very_weak': 'Very Weak'
    }
    return labels[strength] || 'Moderate'
}

onMounted(() => {
    fetchInsightsData()
})
</script>

<template>
    <div class="space-y-6">
        <!-- Insights Header -->
        <div class="bg-linear-to-r from-primary-600 to-neutral-950 rounded-4xl p-6 shadow-xl">
            <h2 class="text-3xl font-black text-white mb-2">{{ t('insights') }}</h2>
            <p class="text-primary-100 font-medium">{{ t('discoverCorrelations') }}</p>
        </div>

        <!-- Loading State for Insights -->
        <div v-if="isFetchingInsights" class="flex items-center justify-center py-20">
            <div class="text-center">
                <RefreshCw :size="40" class="animate-spin text-primary-500 mx-auto mb-4" />
                <p class="text-neutral-600 dark:text-neutral-400 font-bold">{{ t('loading') }}</p>
            </div>
        </div>

        <!-- Insights Content -->
        <div v-else-if="insightsData.length > 0" class="space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div v-for="(insight, index) in insightsData" :key="index"
                    class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700 hover:shadow-xl transition-all">

                    <!-- Correlation Badge -->
                    <div class="flex items-center justify-between mb-6">
                        <span :class="getCorrelationBadgeColor(insight.strength)"
                            class="px-4 py-2 rounded-full text-xs font-black uppercase tracking-wider">
                            {{ getStrengthLabel(insight.strength) }}
                        </span>
                        <span class="text-3xl font-black text-primary-600 dark:text-primary-400">
                            {{ (insight.max_correlation * 100).toFixed(0) }}%
                        </span>
                    </div>

                    <!-- Habit Pair Display -->
                    <div class="space-y-4 mb-6">
                        <!-- Habit 1 -->
                        <div class="flex items-center gap-4 p-4 bg-neutral-50 dark:bg-neutral-700 rounded-2xl">
                            <div class="p-3 rounded-xl" :style="{ backgroundColor: insight.habit1.color + '20' }">
                                <component :is="getIcon(insight.habit1.icon)" :size="24"
                                    :style="{ color: insight.habit1.color }" stroke-width="2.5" />
                            </div>
                            <div class="flex-1">
                                <h4 class="font-black text-neutral-900 dark:text-white text-lg">
                                    {{ insight.habit1.name }}
                                </h4>
                                <p v-if="insight.habit1.category"
                                    class="text-xs font-bold text-neutral-400 uppercase tracking-wide">
                                    {{ insight.habit1.category }}
                                </p>
                            </div>
                        </div>

                        <!-- Connection Arrow -->
                        <div class="flex justify-center">
                            <div class="bg-linear-to-r from-primary-600 to-primary-950 text-white p-3 rounded-full">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                                    fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"
                                    stroke-linejoin="round">
                                    <line x1="12" y1="5" x2="12" y2="19"></line>
                                    <polyline points="19 12 12 19 5 12"></polyline>
                                </svg>
                            </div>
                        </div>

                        <!-- Habit 2 -->
                        <div class="flex items-center gap-4 p-4 bg-neutral-50 dark:bg-neutral-700 rounded-2xl">
                            <div class="p-3 rounded-xl" :style="{ backgroundColor: insight.habit2.color + '20' }">
                                <component :is="getIcon(insight.habit2.icon)" :size="24"
                                    :style="{ color: insight.habit2.color }" stroke-width="2.5" />
                            </div>
                            <div class="flex-1">
                                <h4 class="font-black text-neutral-900 dark:text-white text-lg">
                                    {{ insight.habit2.name }}
                                </h4>
                                <p v-if="insight.habit2.category"
                                    class="text-xs font-bold text-neutral-400 uppercase tracking-wide">
                                    {{ insight.habit2.category }}
                                </p>
                            </div>
                        </div>
                    </div>

                    <!-- Description -->
                    <div
                        class="p-4 bg-linear-to-r from-primary-50 to-purple-50 dark:from-primary-950 dark:to-purple-950 rounded-2xl">
                        <p class="text-sm font-bold text-neutral-700 dark:text-neutral-300 leading-relaxed">
                            {{ insight.description }}
                        </p>
                    </div>

                    <!-- Stats Footer -->
                    <div
                        class="mt-4 pt-4 border-t border-neutral-100 dark:border-neutral-700 flex justify-between items-center">
                        <span class="text-xs font-bold text-neutral-400">
                            Based on {{ insight.sample_size }} days
                        </span>
                        <span class="text-xs font-bold text-neutral-400">
                            {{ new Date(insight.start_date).toLocaleDateString() }} -
                            {{ new Date(insight.end_date).toLocaleDateString() }}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- No Insights State -->
        <div v-else
            class="bg-white dark:bg-neutral-800 rounded-4xl p-16 shadow-lg border border-neutral-100 dark:border-neutral-700 text-center">
            <div class="text-6xl mb-4">🔍</div>
            <h3 class="text-2xl font-black text-neutral-900 dark:text-white mb-2">
                {{ t('noInsightsYet') }}
            </h3>
            <p class="text-neutral-500 dark:text-neutral-400">
                {{ t('computeCorrelations') }}
            </p>
        </div>
    </div>
</template>
