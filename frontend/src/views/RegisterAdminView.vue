<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import { AlertCircle, Shield } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'

const router = useRouter()
const { t } = useLanguage()

const username = ref('')
const email = ref('')
const password1 = ref('')
const password2 = ref('')
const errorMessage = ref('')
const isLoading = ref(false)
const isCheckingAdmin = ref(true)

// Check if a superuser already exists
const checkAdminExists = async () => {
    try {
        const res = await api.get('auth/register-admin/')
        if (res.data.superuser_exists) {
            // Redirect to register if admin already exists
            router.push('/register')
        }
    } catch (err) {
        console.error('Failed to check admin status:', err)
    } finally {
        isCheckingAdmin.value = false
    }
}

const handleRegisterAdmin = async () => {
    errorMessage.value = ''

    if (password1.value !== password2.value) {
        errorMessage.value = 'Passwords do not match'
        return
    }

    if (password1.value.length < 8) {
        errorMessage.value = 'Password must be at least 8 characters'
        return
    }

    isLoading.value = true

    try {
        await api.post('auth/register-admin/', {
            username: username.value,
            email: email.value,
            password1: password1.value,
            password2: password2.value
        })
        router.push('/login')
    } catch (err) {
        if (err.response?.data) {
            const errors = err.response.data
            if (errors.detail) {
                errorMessage.value = errors.detail
                // Check if we need to redirect
                if (errors.redirect_url) {
                    setTimeout(() => router.push(errors.redirect_url), 2000)
                }
            } else if (errors.username) {
                errorMessage.value = errors.username[0]
            } else if (errors.email) {
                errorMessage.value = errors.email[0]
            } else if (errors.password1) {
                errorMessage.value = errors.password1[0]
            } else if (errors.password2) {
                errorMessage.value = errors.password2[0]
            } else {
                errorMessage.value = 'Registration failed. Please try again.'
            }
        } else {
            errorMessage.value = 'Registration failed. Please try again.'
        }
    } finally {
        isLoading.value = false
    }
}

onMounted(() => {
    checkAdminExists()
})
</script>

<template>
    <div class="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center p-6">
        <div class="w-full max-w-md">
            <div
                class="bg-white dark:bg-neutral-800 rounded-4xl p-12 shadow-2xl border border-neutral-100 dark:border-neutral-700">
                <div class="text-center mb-8">
                    <div class="flex justify-center mb-4">
                        <div class="bg-primary-100 dark:bg-primary-900/30 p-4 rounded-2xl">
                            <Shield :size="48" class="text-primary-600 dark:text-primary-400" />
                        </div>
                    </div>
                    <h1
                        class="text-4xl font-black tracking-tighter text-neutral-900 dark:text-white uppercase italic mb-2">
                        Habits Factory
                    </h1>
                    <p class="text-neutral-500 dark:text-neutral-400 font-medium">Initial Setup</p>
                </div>

                <!-- Loading state while checking admin status -->
                <div v-if="isCheckingAdmin" class="text-center py-8">
                    <div
                        class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-neutral-300 border-t-primary-600">
                    </div>
                    <p class="mt-4 text-neutral-500 dark:text-neutral-400">Checking setup status...</p>
                </div>

                <!-- Admin registration form -->
                <form v-else @submit.prevent="handleRegisterAdmin" class="space-y-6">
                    <div
                        class="bg-primary-50 dark:bg-primary-900/20 border-2 border-primary-200 dark:border-primary-900/50 rounded-2xl p-4">
                        <p class="text-primary-700 dark:text-primary-300 font-medium text-sm">
                            Create your administrator account to get started. This account will have full access to
                            manage the application.
                        </p>
                    </div>

                    <div v-if="errorMessage"
                        class="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-900/50 rounded-2xl p-4">
                        <div class="flex items-center gap-2">
                            <AlertCircle :size="20" class="text-red-600 dark:text-red-400" />
                            <p class="text-red-600 dark:text-red-400 font-bold text-sm">{{ errorMessage }}</p>
                        </div>
                    </div>

                    <div class="space-y-2">
                        <label
                            class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">Username</label>
                        <input v-model="username" type="text" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Enter admin username" />
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">Email</label>
                        <input v-model="email" type="email" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Enter admin email" />
                    </div>

                    <div class="space-y-2">
                        <label
                            class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">Password</label>
                        <input v-model="password1" type="password" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Enter password (min 8 characters)" />
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">Confirm
                            Password</label>
                        <input v-model="password2" type="password" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Confirm password" />
                    </div>

                    <button type="submit" :disabled="isLoading"
                        class="w-full bg-primary-600 text-white py-4 rounded-2xl font-bold hover:bg-primary-700 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed">
                        {{ isLoading ? 'Creating Administrator...' : 'Create Administrator Account' }}
                    </button>

                    <div class="text-center">
                        <p class="text-sm text-neutral-500 dark:text-neutral-400">
                            Already have an account?
                            <router-link to="/login"
                                class="text-primary-600 dark:text-primary-400 font-bold hover:underline">
                                Login here
                            </router-link>
                        </p>
                    </div>
                </form>
            </div>
        </div>
    </div>
</template>
