<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import { useLanguage } from '@/composables/useLanguage'
import { toISODate, addDays, recentYears } from '@/utils/dates'
import { Download, CalendarRange, FileSpreadsheet } from 'lucide-vue-next'
import PageShell from '@/components/layout/PageShell.vue'
import UiSection from '@/components/ui/UiSection.vue'
import UiInput from '@/components/ui/UiInput.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import { labelClass } from '@/components/ui/styles'

const { t } = useLanguage()

// Export state
const exportStartDate = ref('')
const exportEndDate = ref('')
const isExporting = ref(false)
const exportError = ref('')

const quickSelectYears = recentYears()

const isRangeValid = computed(() =>
    !!exportStartDate.value && !!exportEndDate.value && exportStartDate.value <= exportEndDate.value
)

// Set export date range for a specific year
const setExportYearRange = (year) => {
    exportStartDate.value = `${year}-01-01`
    exportEndDate.value = `${year}-12-31`
}

// Set export date range for all available data
const setAllExportDataRange = async () => {
    try {
        const response = await api.get('habits/date_range/')
        if (response.data.start_date && response.data.end_date) {
            exportStartDate.value = response.data.start_date
            exportEndDate.value = response.data.end_date
        }
    } catch (err) {
        // Fallback: set to a wide range
        exportStartDate.value = '2020-01-01'
        exportEndDate.value = toISODate()
    }
}

// Export data to CSV
const exportToCSV = async () => {
    exportError.value = ''

    if (!isRangeValid.value) {
        exportError.value = t('invalidDateRange')
        return
    }

    isExporting.value = true

    try {
        const response = await api.get('habits/export_csv/', {
            params: {
                start_date: exportStartDate.value,
                end_date: exportEndDate.value
            }
        })

        // Create a blob and download
        const blob = new Blob([response.data.csv_content], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')

        link.href = url
        link.download = `habit_data_${exportStartDate.value}_to_${exportEndDate.value}.csv`

        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
    } catch (err) {
        exportError.value = t('exportFailed')
    } finally {
        isExporting.value = false
    }
}

const quickChipClass =
    'inline-flex h-8 items-center rounded-full border border-line bg-surface px-3 text-sm font-medium text-ink-soft transition-colors hover:border-primary-500 hover:text-primary-700 dark:hover:text-primary-300'

onMounted(() => {
    // Default: the last 30 days
    exportEndDate.value = toISODate()
    exportStartDate.value = toISODate(addDays(new Date(), -30))
})
</script>

<template>
    <PageShell :title="t('exportTitle')" :description="t('exportSubtitle')">
        <UiSection :title="t('dateRange')" :icon="CalendarRange">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <UiInput v-model="exportStartDate" type="date" :label="t('startDate')"
                    :max="exportEndDate || undefined" />
                <UiInput v-model="exportEndDate" type="date" :label="t('endDate')"
                    :min="exportStartDate || undefined" />
            </div>

            <div class="mt-5 border-t border-line pt-4">
                <span :class="labelClass">{{ t('quickSelect') }}</span>
                <div class="flex flex-wrap gap-2">
                    <button type="button" :class="quickChipClass" @click="setAllExportDataRange">
                        {{ t('allData') }}
                    </button>
                    <button v-for="year in quickSelectYears" :key="year" type="button" :class="quickChipClass"
                        @click="setExportYearRange(year)">
                        {{ year }}
                    </button>
                </div>
            </div>
        </UiSection>

        <UiAlert v-if="exportError">{{ exportError }}</UiAlert>

        <section
            class="relative overflow-hidden rounded-2xl bg-linear-to-br from-primary-600 to-primary-950 p-5 text-white shadow-md sm:p-6">
            <FileSpreadsheet :size="150" stroke-width="1.5"
                class="pointer-events-none absolute -right-4 -bottom-8 text-white/10" />
            <div class="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 class="font-display text-2xl font-bold tracking-wide uppercase">{{ t('readyToExport') }}</h2>
                    <p class="mt-1 max-w-md text-sm text-primary-100">{{ t('exportDescription') }}</p>
                </div>
                <UiButton variant="inverse" size="lg" :icon="Download" :loading="isExporting" :disabled="!isRangeValid"
                    @click="exportToCSV">
                    {{ isExporting ? t('exporting') : t('exportCsv') }}
                </UiButton>
            </div>
        </section>
    </PageShell>
</template>
