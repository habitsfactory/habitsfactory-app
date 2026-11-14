<script setup>
import { ref } from 'vue'
import api from '@/services/api'
import { useLanguage } from '@/composables/useLanguage'
import { Upload, FileUp, FileCheck2, FileText } from 'lucide-vue-next'
import PageShell from '@/components/layout/PageShell.vue'
import UiSection from '@/components/ui/UiSection.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'

const { t } = useLanguage()

// Import state
const selectedFile = ref(null)
const isImporting = ref(false)
const importResult = ref(null)
const importError = ref(null)
const fileInputRef = ref(null)
const isDragging = ref(false)

// Browsers disagree on the MIME type of .csv files (Windows often reports
// "application/vnd.ms-excel" or nothing), so the extension is checked too.
const isCsvFile = (file) => file.type === 'text/csv' || /\.csv$/i.test(file.name)

const selectFile = (file) => {
    if (file && isCsvFile(file)) {
        selectedFile.value = file
        importResult.value = null
        importError.value = null
    } else {
        importError.value = t('invalidCsvFile')
        selectedFile.value = null
    }
}

// Handle file selection
const handleFileSelect = (event) => {
    selectFile(event.target.files[0])
}

const handleDrop = (event) => {
    isDragging.value = false
    selectFile(event.dataTransfer.files[0])
}

// Trigger file input click
const triggerFileInput = () => {
    fileInputRef.value?.click()
}

// Read file content as text
const readFileContent = (file) => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => resolve(e.target.result)
        reader.onerror = (e) => reject(e)
        reader.readAsText(file)
    })
}

// Import CSV file
const importCSV = async () => {
    if (!selectedFile.value) {
        importError.value = t('invalidCsvFile')
        return
    }

    isImporting.value = true
    importError.value = null
    importResult.value = null

    try {
        const fileContent = await readFileContent(selectedFile.value)

        const response = await api.post('habits/import_csv/', {
            csv_content: fileContent
        })

        importResult.value = response.data
        selectedFile.value = null
        if (fileInputRef.value) {
            fileInputRef.value.value = ''
        }
    } catch (err) {
        importError.value = err.response?.data?.error || t('importFailed')
    } finally {
        isImporting.value = false
    }
}

const resultRows = [
    { key: 'habits_created', label: 'habitsCreated' },
    { key: 'habits_updated', label: 'habitsUpdated' },
    { key: 'completions_created', label: 'completionsCreated' },
    { key: 'values_skipped', label: 'valuesSkipped' },
    { key: 'categories_created', label: 'categoriesCreated' },
    { key: 'tags_created', label: 'tagsCreated' },
]

const formatRules = ['csvFormatHeaders', 'csvFormatColumns', 'csvFormatDates', 'csvFormatTags', 'csvFormatTypes']
</script>

<template>
    <PageShell :title="t('importTitle')" :description="t('importSubtitle')">
        <UiSection :title="t('selectCsvFile')" :icon="FileUp">
            <input ref="fileInputRef" type="file" accept=".csv,text/csv" class="hidden" @change="handleFileSelect" />

            <!-- Drop zone -->
            <button type="button" :class="[
                'flex w-full flex-col items-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors',
                isDragging
                    ? 'border-primary-500 bg-primary-500/10'
                    : selectedFile
                        ? 'border-emerald-500/60 bg-emerald-500/5'
                        : 'border-line-strong hover:border-primary-500 hover:bg-sunken/60',
            ]" @click="triggerFileInput" @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false"
                @drop.prevent="handleDrop">
                <span :class="[
                    'inline-flex size-14 items-center justify-center rounded-2xl',
                    selectedFile ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-primary-500/10 text-primary-600 dark:text-primary-400',
                ]">
                    <component :is="selectedFile ? FileCheck2 : Upload" :size="28" stroke-width="2" />
                </span>
                <span class="mt-4 max-w-full truncate font-semibold text-ink">
                    {{ selectedFile ? selectedFile.name : t('clickToSelectCsv') }}
                </span>
                <span class="mt-1 text-sm text-ink-faint">
                    {{ selectedFile ? `${(selectedFile.size / 1024).toFixed(2)} KB` : t('supportedFormat') }}
                </span>
            </button>

            <UiButton class="mt-5" size="lg" block :icon="Upload" :loading="isImporting" :disabled="!selectedFile"
                @click="importCSV">
                {{ isImporting ? t('importing') : t('importButton') }}
            </UiButton>
        </UiSection>

        <UiAlert v-if="importResult" variant="success" :title="t('importSuccess')">
            <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5">
                <template v-for="row in resultRows" :key="row.key">
                    <dt>{{ t(row.label) }}</dt>
                    <dd class="font-semibold tabular-nums">{{ importResult[row.key] || 0 }}</dd>
                </template>
            </dl>
        </UiAlert>

        <UiAlert v-if="importError" :title="t('importFailedTitle')">{{ importError }}</UiAlert>

        <UiSection :title="t('csvFormatTitle')" :description="t('csvFormatIntro')" :icon="FileText">
            <ul class="list-disc space-y-1.5 pl-5 text-sm text-ink-soft marker:text-primary-500">
                <li v-for="rule in formatRules" :key="rule">{{ t(rule) }}</li>
            </ul>
            <UiAlert variant="info" class="mt-4">{{ t('csvFormatNote') }}</UiAlert>
        </UiSection>
    </PageShell>
</template>
