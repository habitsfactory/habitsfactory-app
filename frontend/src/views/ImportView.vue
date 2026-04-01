<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import { useDarkMode } from '@/composables/useDarkMode'
import { useLanguage } from '@/composables/useLanguage'
import { Upload, ArrowLeft, CheckCircle, AlertCircle, FileText } from 'lucide-vue-next'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const { isDark, toggleDarkMode } = useDarkMode()
const { t } = useLanguage()

// Import state
const selectedFile = ref(null)
const isImporting = ref(false)
const importResult = ref(null)
const importError = ref(null)
const fileInputRef = ref(null)

// Handle file selection
const handleFileSelect = (event) => {
    const file = event.target.files[0]
    if (file && file.type === 'text/csv') {
        selectedFile.value = file
        importResult.value = null
        importError.value = null
    } else {
        importError.value = 'Please select a valid CSV file'
        selectedFile.value = null
    }
}

// Trigger file input click
const triggerFileInput = () => {
    fileInputRef.value?.click()
}

// Import CSV file
const importCSV = async () => {
    if (!selectedFile.value) {
        importError.value = 'Please select a CSV file first'
        return
    }

    isImporting.value = true
    importError.value = null
    importResult.value = null

    try {
        // Read file content
        const fileContent = await readFileContent(selectedFile.value)

        // Send to backend
        const response = await api.post('habits/import_csv/', {
            csv_content: fileContent
        })

        importResult.value = response.data
        selectedFile.value = null
        if (fileInputRef.value) {
            fileInputRef.value.value = ''
        }
    } catch (err) {
        importError.value = err.response?.data?.error || 'Failed to import data. Please check your CSV format.'
    } finally {
        isImporting.value = false
    }
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

const goBack = () => {
    router.push('/dashboard')
}
</script>

<template>
    <div
        class="min-h-screen bg-neutral-50 dark:bg-neutral-900 p-6 md:p-12 font-sans text-neutral-900 dark:text-neutral-100 transition-colors duration-300">
        <div class="max-w-4xl mx-auto">
            <!-- Header -->
            <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
                <div>
                    <button @click="goBack"
                        class="flex items-center gap-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors mb-4 font-bold">
                        <ArrowLeft :size="20" stroke-width="2.5" />
                        {{ t('returnDashboard') }}
                    </button>
                    <h1 class="text-4xl font-black tracking-tighter text-neutral-900 dark:text-white uppercase italic">
                        Import Data
                    </h1>
                    <p class="text-neutral-400 dark:text-neutral-500 font-medium">Import your habit data from CSV</p>
                </div>
            </header>

            <!-- Main Content -->
            <div class="space-y-6">
                <!-- File Upload Section -->
                <div
                    class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                    <h2 class="text-2xl font-black text-neutral-900 dark:text-white mb-6">Select CSV File</h2>

                    <!-- File Input (Hidden) -->
                    <input ref="fileInputRef" type="file" accept=".csv" @change="handleFileSelect" class="hidden" />

                    <!-- File Drop Zone -->
                    <div @click="triggerFileInput"
                        class="border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded-3xl p-12 text-center cursor-pointer hover:border-primary-500 dark:hover:border-primary-400 transition-colors">
                        <Upload :size="48" class="mx-auto mb-4 text-neutral-400" stroke-width="2" />
                        <p class="text-lg font-bold text-neutral-900 dark:text-white mb-2">
                            {{ selectedFile ? selectedFile.name : 'Click to select CSV file' }}
                        </p>
                        <p class="text-sm text-neutral-500">
                            {{ selectedFile ? `${(selectedFile.size / 1024).toFixed(2)} KB` : 'Supported format: CSV' }}
                        </p>
                    </div>

                    <!-- Import Button -->
                    <button @click="importCSV" :disabled="!selectedFile || isImporting"
                        class="w-full mt-6 bg-primary-600 text-white py-4 rounded-2xl font-black hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                        <Upload :size="20" />
                        {{ isImporting ? 'Importing...' : 'Import Data' }}
                    </button>
                </div>

                <!-- Success Message -->
                <div v-if="importResult"
                    class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-3xl p-6">
                    <div class="flex items-start gap-3">
                        <CheckCircle :size="24" class="text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                        <div class="flex-1">
                            <h3 class="text-lg font-black text-green-900 dark:text-green-100 mb-2">Import Successful!
                            </h3>
                            <div class="space-y-1 text-sm text-green-800 dark:text-green-200">
                                <p><strong>Habits created:</strong> {{ importResult.habits_created }}</p>
                                <p><strong>Habits updated:</strong> {{ importResult.habits_updated }}</p>
                                <p><strong>Completions created:</strong> {{ importResult.completions_created }}</p>
                                <p><strong>Categories created:</strong> {{ importResult.categories_created || 0 }}</p>
                                <p><strong>Tags created:</strong> {{ importResult.tags_created || 0 }}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Error Message -->
                <div v-if="importError"
                    class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-3xl p-6">
                    <div class="flex items-start gap-3">
                        <AlertCircle :size="24" class="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                        <div class="flex-1">
                            <h3 class="text-lg font-black text-red-900 dark:text-red-100 mb-2">Import Failed</h3>
                            <p class="text-sm text-red-800 dark:text-red-200">{{ importError }}</p>
                        </div>
                    </div>
                </div>

                <!-- Instructions -->
                <div
                    class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-3xl p-8 shadow-lg">
                    <div class="flex items-start gap-3 mb-4">
                        <FileText :size="24" class="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                        <div class="flex-1">
                            <h3 class="text-xl font-black text-blue-900 dark:text-blue-100 mb-3">CSV Format Instructions
                            </h3>
                            <div class="space-y-2 text-sm text-blue-800 dark:text-blue-200">
                                <p>Your CSV file should follow this format:</p>
                                <ul class="list-disc list-inside space-y-1 ml-4">
                                    <li><strong>First row:</strong> Column headers</li>
                                    <li><strong>Columns 1-8:</strong> Habit Name, Type, Color, Icon, Category, Tags,
                                        Unit, Max Value</li>
                                    <li><strong>Remaining columns:</strong> Dates (YYYY-MM-DD format) with completion
                                        values</li>
                                    <li><strong>Tags:</strong> Multiple tags separated by colon (:)</li>
                                    <li><strong>Type:</strong> boolean, counter, value, or rating</li>
                                </ul>
                                <p class="mt-3 font-bold">Note: Export your data to see the correct format!</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <SiteFooter />
            </div>
        </div>
    </div>
</template>

<style scoped>
/* Add any component-specific styles here */
</style>
