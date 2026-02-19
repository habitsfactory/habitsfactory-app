<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/services/api'
import { AlertCircle } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'

const router = useRouter()
const route = useRoute()
const { t } = useLanguage()

const username = ref('')
const email = ref('')
const password1 = ref('')
const password2 = ref('')
const errorMessage = ref('')
const isLoading = ref(false)
const inviteToken = ref('')
const inviteValid = ref(false)
const isValidatingInvite = ref(true)
const inviteError = ref('')

// Validate the invite token from URL query parameter
const validateInvite = async () => {
    const token = route.query.invite
    if (!token) {
        inviteValid.value = false
        inviteError.value = t('noInviteToken')
        isValidatingInvite.value = false
        return
    }

    inviteToken.value = token

    try {
        const res = await api.get(`invite-links/validate/?token=${token}`)
        inviteValid.value = res.data.valid
        if (!res.data.valid) {
            inviteError.value = res.data.detail || t('invalidInviteLink')
        }
    } catch (err) {
        console.error('Failed to validate invite:', err)
        inviteValid.value = false
        inviteError.value = t('invalidInviteLink')
    } finally {
        isValidatingInvite.value = false
    }
}

const handleRegister = async () => {
    errorMessage.value = ''

    if (!inviteValid.value) {
        errorMessage.value = t('invalidInviteLink')
        return
    }

    if (password1.value !== password2.value) {
        errorMessage.value = 'Passwords do not match'
        return
    }

    isLoading.value = true

    try {
        await api.post('auth/registration/', {
            username: username.value,
            email: email.value,
            password1: password1.value,
            password2: password2.value,
            invite_token: inviteToken.value
        })
        router.push('/login')
    } catch (err) {
        if (err.response?.data) {
            const errors = err.response.data
            if (errors.detail) {
                errorMessage.value = errors.detail
            } else if (errors.username) {
                errorMessage.value = errors.username[0]
            } else if (errors.email) {
                errorMessage.value = errors.email[0]
            } else if (errors.password1) {
                errorMessage.value = errors.password1[0]
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
    validateInvite()
})
</script>

<template>
    <div class="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center p-6">
        <div class="w-full max-w-md">
            <div
                class="bg-white dark:bg-neutral-800 rounded-4xl p-12 shadow-2xl border border-neutral-100 dark:border-neutral-700">
                <div class="text-center mb-8">
                    <h1
                        class="text-4xl font-black tracking-tighter text-neutral-900 dark:text-white uppercase italic mb-2">
                        Habits Factory
                    </h1>
                    <p class="text-neutral-500 dark:text-neutral-400 font-medium">{{ t('createAccount') }}</p>
                </div>

                <!-- Loading state while validating invite -->
                <div v-if="isValidatingInvite" class="text-center py-8">
                    <div
                        class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-neutral-300 border-t-primary-600">
                    </div>
                    <p class="mt-4 text-neutral-500 dark:text-neutral-400">{{ t('validatingInvite') }}</p>
                </div>

                <!-- Invalid invite message -->
                <div v-else-if="!inviteValid" class="space-y-6">
                    <div
                        class="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-900/50 rounded-2xl p-6">
                        <div class="flex items-center gap-3 mb-3">
                            <AlertCircle :size="24" class="text-red-600 dark:text-red-400" />
                            <h3 class="font-black text-red-900 dark:text-red-400 text-lg">{{ t('invalidInvite') }}
                            </h3>
                        </div>
                        <p class="text-red-700 dark:text-red-300 font-medium">
                            {{ inviteError }}
                        </p>
                    </div>

                    <button @click="router.push('/login')"
                        class="w-full bg-neutral-600 text-white py-4 rounded-2xl font-bold hover:bg-neutral-700 transition-all shadow-lg">
                        {{ t('backToLogin') }}
                    </button>
                </div>

                <!-- Registration form -->
                <form v-else @submit.prevent="handleRegister" class="space-y-6">
                    <div v-if="errorMessage"
                        class="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-900/50 rounded-2xl p-4">
                        <p class="text-red-600 dark:text-red-400 font-bold text-sm">{{ errorMessage }}</p>
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                            t('username') }}</label>
                        <input v-model="username" type="text" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Enter username" />
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{ t('email')
                            }}</label>
                        <input v-model="email" type="email" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Enter email" />
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                            t('password') }}</label>
                        <input v-model="password1" type="password" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Enter password" />
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                            t('confirmPassword') }}</label>
                        <input v-model="password2" type="password" required
                            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white"
                            placeholder="Confirm password" />
                    </div>

                    <button type="submit" :disabled="isLoading"
                        class="w-full bg-primary-600 text-white py-4 rounded-2xl font-bold hover:bg-primary-700 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed">
                        {{ isLoading ? 'Creating Account...' : 'Register' }}
                    </button>

                    <div class="text-center">
                        <p class="text-sm text-neutral-500 dark:text-neutral-400">
                            {{ t('signupMessage') }}
                            <router-link to="/login"
                                class="text-primary-600 dark:text-primary-400 font-bold hover:underline">
                                {{ t('loginHere') }}
                            </router-link>
                        </p>
                    </div>
                </form>
            </div>
        </div>
    </div>
</template>
