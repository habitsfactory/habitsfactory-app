<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/services/api'
import { UserPlus, ArrowLeft } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import AuthShell from '@/components/layout/AuthShell.vue'
import UiInput from '@/components/ui/UiInput.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiSpinner from '@/components/ui/UiSpinner.vue'

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
        const res = await api.get('invite-links/validate/', { params: { token } })
        inviteValid.value = res.data.valid
        if (!res.data.valid) {
            inviteError.value = res.data.detail || t('invalidInviteLink')
        }
    } catch (err) {
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
        errorMessage.value = t('passwordMismatch')
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
        const errors = err.response?.data || {}
        errorMessage.value = errors.detail
            || errors.username?.[0]
            || errors.email?.[0]
            || errors.password1?.[0]
            || errors.password2?.[0]
            || errors.non_field_errors?.[0]
            || t('registrationFailed')
    } finally {
        isLoading.value = false
    }
}

onMounted(() => {
    validateInvite()
})
</script>

<template>
    <AuthShell :subtitle="t('createAccount')">
        <!-- Validating the invite -->
        <UiSpinner v-if="isValidatingInvite" :label="t('validatingInvite')" />

        <!-- Invalid invite -->
        <div v-else-if="!inviteValid" class="space-y-5">
            <UiAlert :title="t('invalidInvite')">{{ inviteError }}</UiAlert>
            <UiButton variant="secondary" size="lg" block :icon="ArrowLeft" @click="router.push('/login')">
                {{ t('backToLogin') }}
            </UiButton>
        </div>

        <!-- Registration form -->
        <form v-else class="space-y-5" @submit.prevent="handleRegister">
            <UiAlert v-if="errorMessage">{{ errorMessage }}</UiAlert>

            <UiInput v-model="username" :label="t('username')" :placeholder="t('usernamePlaceholder')" required
                autocomplete="username" />

            <UiInput v-model="email" type="email" :label="t('email')" :placeholder="t('emailPlaceholder')" required
                autocomplete="email" />

            <UiInput v-model="password1" type="password" :label="t('password')" :hint="t('passwordMinHint')" required
                minlength="8" autocomplete="new-password" />

            <UiInput v-model="password2" type="password" :label="t('confirmPassword')" required
                autocomplete="new-password" />

            <UiButton type="submit" size="lg" block :icon="UserPlus" :loading="isLoading">
                {{ isLoading ? t('creatingAccount') : t('register') }}
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
