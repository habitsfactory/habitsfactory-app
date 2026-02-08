<script setup>
import { useRouter } from 'vue-router'
import { useLanguage } from '@/composables/useLanguage'
import { useDarkMode } from '@/composables/useDarkMode'

const { isDark, toggleDarkMode } = useDarkMode()

const router = useRouter()
const { t } = useLanguage()

const goToAdminSettings = () => {
    router.push('/admin-settings')
}

const goToProfile = () => {
    router.push('/profile')
}

const goToExport = () => {
    router.push('/export')
}
</script>

<template>
    <!-- Footer -->
    <footer class="py-12 px-6">
        <div class="dark:text-white max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div class="flex flex-col gap-4">
                <a href="https://habitsfactory.io" target="_blank" rel="noopener noreferrer">
                    <img src="/logo_edition.svg" alt="Habits Factory Logo" class="h-32 w-32 object-contain center" />
                </a>
                <span class="text-xl font-bold tracking-tight">Habits Factory</span>
                <p class="text-sm text-gray-400">Building better routines, one day at a time.</p>
                <a href="https://habitsfactory.io" target="_blank" rel="noopener noreferrer">
                    <span
                        class="text-sm text-gray-500 hover:text-primary-400 transition-colors">https://habitsfactory.io</span>
                </a>
            </div>
            <div>
                <h3 class="font-semibold mb-4 uppercase text-xs tracking-wider">Management</h3>
                <ul class="space-y-2 text-sm">
                    <li>
                        <button @click="goToAdminSettings"
                            class="hover:text-primary-400 transition-colors flex items-center pl-0">
                            <span>{{ t('adminSettings') }}</span>
                        </button>
                    </li>
                    <li>
                        <button @click="goToProfile"
                            class="hover:text-primary-400 transition-colors flex items-center pl-0">
                            <span>{{ t('profile') }}</span>
                        </button>
                    </li>
                </ul>
            </div>
            <div>
                <h3 class="font-semibold mb-4 uppercase text-xs tracking-wider">Data</h3>
                <ul class="space-y-2 text-sm">
                    <li>
                        <button @click="goToExport"
                            class="hover:text-primary-400 transition-colors flex items-center pl-0">
                            <span>{{ t('importData') }}</span>
                        </button>
                    </li>
                    <li>
                        <button @click="goToExport"
                            class="hover:text-primary-400 transition-colors flex items-center pl-0">
                            <span>{{ t('exportData') }}</span>
                        </button>
                    </li>
                </ul>
            </div>
            <div>
                <h3 class="font-semibold mb-4 uppercase text-xs tracking-wider">Support</h3>
                <ul class="space-y-4 text-sm">
                    <li>
                        <a href="https://github.com/habitsfactory/habitsfactory-app" target="_blank"
                            rel="noopener noreferrer"
                            class="text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors font-medium flex items-center gap-2 group">
                            <svg class="w-5 h-5 group-hover:scale-110 transition-transform" fill="currentColor"
                                viewBox="0 0 24 24">
                                <path fill-rule="evenodd"
                                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                                    clip-rule="evenodd" />
                            </svg>
                            <span class="text-sm font-bold">{{ t('viewOnGithub') }}</span>
                        </a>
                    </li>
                    <li>
                        <a href="https://ko-fi.com/joeydev" target="_blank"><img src="/support_me_on_kofi_dark.png"
                                alt="Support me on Ko-Fi" style="width: 160px;"></img></a>
                    </li>
                    <li>
                        <a href="mailto:contact@habitsfactory.io">
                            <span
                                class="text-sm text-gray-500 hover:text-primary-400 transition-colors">contact@habitsfactory.io</span>
                        </a>
                    </li>
                </ul>
            </div>
        </div>
        <div class="max-w-7xl mx-auto mt-12 pt-8 border-t border-gray-300 text-center text-xs text-gray-500">
            © {{ new Date().getFullYear() }} {{ t('appName') }}. {{ t('license') }}
        </div>
    </footer>
</template>