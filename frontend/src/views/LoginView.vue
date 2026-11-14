<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { LogIn } from 'lucide-vue-next'
import authService from '../services/auth'
import { useLanguage } from '@/composables/useLanguage'
import { useCurrentUser } from '@/composables/useCurrentUser'
import AuthShell from '@/components/layout/AuthShell.vue'
import UiInput from '@/components/ui/UiInput.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'

const router = useRouter()
const { t } = useLanguage()
const { clearUser } = useCurrentUser()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
    loading.value = true
    errorMessage.value = ''

    try {
        await authService.login(email.value, password.value)
        clearUser()
        router.push('/dashboard')
    } catch (error) {
        errorMessage.value = error.response?.data?.non_field_errors?.[0] || t('invalidCredentials')
    } finally {
        loading.value = false
    }
}
</script>

<template>
    <AuthShell :subtitle="t('signInToContinue')">
        <form class="space-y-5" @submit.prevent="handleLogin">
            <UiAlert v-if="errorMessage">{{ errorMessage }}</UiAlert>

            <UiInput v-model="email" type="email" :label="t('email')" :placeholder="t('emailPlaceholder')" required
                autocomplete="email" autofocus />

            <UiInput v-model="password" type="password" :label="t('password')" placeholder="••••••••" required
                autocomplete="current-password" />

            <UiButton type="submit" size="lg" block :icon="LogIn" :loading="loading">
                {{ loading ? t('signingIn') : t('signIn') }}
            </UiButton>
        </form>
    </AuthShell>
</template>
