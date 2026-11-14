<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import { ShieldCheck } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import AuthShell from '@/components/layout/AuthShell.vue'
import UiInput from '@/components/ui/UiInput.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSpinner from '@/components/ui/UiSpinner.vue'

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
        notifyError(err, 'loadFailed')
    } finally {
        isCheckingAdmin.value = false
    }
}

const handleRegisterAdmin = async () => {
    errorMessage.value = ''

    if (password1.value !== password2.value) {
        errorMessage.value = t('passwordMismatch')
        return
    }

    if (password1.value.length < 8) {
        errorMessage.value = t('passwordTooShort')
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
        const errors = err.response?.data || {}
        if (errors.detail && errors.redirect_url) {
            setTimeout(() => router.push(errors.redirect_url), 2000)
        }
        errorMessage.value = errors.detail
            || errors.username?.[0]
            || errors.email?.[0]
            || errors.password1?.[0]
            || errors.password2?.[0]
            || t('registrationFailed')
    } finally {
        isLoading.value = false
    }
}

onMounted(() => {
    checkAdminExists()
})
</script>

<template>
    <AuthShell :subtitle="t('initialSetup')">
        <UiSpinner v-if="isCheckingAdmin" :label="t('checkingSetup')" />

        <form v-else class="space-y-5" @submit.prevent="handleRegisterAdmin">
            <UiAlert variant="info">{{ t('adminSetupInfo') }}</UiAlert>

            <UiAlert v-if="errorMessage">{{ errorMessage }}</UiAlert>

            <UiInput v-model="username" :label="t('username')" :placeholder="t('usernamePlaceholder')" required
                autocomplete="username" />

            <UiInput v-model="email" type="email" :label="t('email')" :placeholder="t('emailPlaceholder')" required
                autocomplete="email" />

            <UiInput v-model="password1" type="password" :label="t('password')" :hint="t('passwordMinHint')" required
                minlength="8" autocomplete="new-password" />

            <UiInput v-model="password2" type="password" :label="t('confirmPassword')" required
                autocomplete="new-password" />

            <UiButton type="submit" size="lg" block :icon="ShieldCheck" :loading="isLoading">
                {{ isLoading ? t('creatingAdmin') : t('createAdminAccount') }}
            </UiButton>

            <p class="text-center text-sm text-ink-soft">
                {{ t('signupMessage') }}
                <router-link to="/login" class="font-semibold text-primary-600 hover:underline dark:text-primary-400">
                    {{ t('loginHere') }}
                </router-link>
            </p>
        </form>
    </AuthShell>
</template>
