<template>
    <div
        class="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center p-6 relative overflow-hidden">
        <!-- Animated Background Cards -->
        <BackgroundCards />

        <div class="bg-white dark:bg-neutral-800 rounded-4xl p-12 shadow-2xl w-full max-w-md relative z-10">
            <div class="text-center mb-10">
                <h1 class="text-4xl font-black tracking-tighter text-neutral-900 dark:text-white uppercase italic mb-2">
                    {{ t('appName')
                    }}</h1>
                <p class="text-neutral-400 dark:text-neutral-500 font-medium">{{ t('signInToContinue') }}</p>
            </div>

            <form @submit.prevent="handleLogin" class="space-y-6">
                <div v-if="errorMessage"
                    class="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-2xl p-4">
                    <p class="text-red-600 dark:text-red-400 text-sm font-semibold">{{ errorMessage }}</p>
                </div>

                <div class="space-y-2">
                    <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{ t('email')
                    }}</label>
                    <input v-model="email" type="email" required :placeholder="t('emailPlaceholder')"
                        class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white" />
                </div>

                <div class="space-y-2">
                    <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                        t('password') }}</label>
                    <input v-model="password" type="password" required placeholder="••••••••"
                        class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white" />
                </div>

                <button type="submit" :disabled="loading"
                    class="w-full bg-neutral-900 dark:bg-primary-600 text-white py-6 rounded-4xl font-black text-xl hover:bg-primary-600 dark:hover:bg-primary-500 transition-all shadow-xl shadow-primary-100 dark:shadow-none disabled:opacity-50">
                    {{ loading ? t('signingIn') : t('signIn') }}
                </button>

            </form>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import authService from '../services/auth'
import { useLanguage } from '@/composables/useLanguage'
import BackgroundCards from '@/components/BackgroundCards.vue'

const router = useRouter()
const { t } = useLanguage()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
    loading.value = true
    errorMessage.value = ''

    try {
        await authService.login(email.value, password.value)
        router.push('/dashboard')
    } catch (error) {
        console.error('Login error:', error)
        errorMessage.value = error.response?.data?.non_field_errors?.[0] || t('invalidCredentials')
    } finally {
        loading.value = false
    }
}
</script>