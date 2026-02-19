<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import authService from '@/services/auth'
import { useDarkMode } from '@/composables/useDarkMode'
import { useLanguage } from '@/composables/useLanguage'
import {
    ArrowLeft, Plus, Trash2, Copy, Check,
    Link, Clock, AlertCircle, CheckCircle2, RefreshCw
} from 'lucide-vue-next'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const { isDark, toggleDarkMode } = useDarkMode()
const { t } = useLanguage()

// State
const userInfo = ref({
    username: '',
    email: '',
    is_staff: false,
    is_superuser: false
})

// Invite links state
const inviteLinks = ref([])
const isLoadingLinks = ref(false)
const isCreatingLink = ref(false)
const copiedToken = ref(null)

// Fetch user info
const fetchUserInfo = async () => {
    try {
        const res = await api.get('auth/user/')
        userInfo.value = res.data
    } catch (err) {
        console.error('Failed to fetch user info:', err)
    }
}

// Fetch invite links
const fetchInviteLinks = async () => {
    isLoadingLinks.value = true
    try {
        const res = await api.get('invite-links/')
        inviteLinks.value = res.data
    } catch (err) {
        console.error('Failed to fetch invite links:', err)
    } finally {
        isLoadingLinks.value = false
    }
}

// Create invite link
const createInviteLink = async () => {
    isCreatingLink.value = true
    try {
        await api.post('invite-links/')
        await fetchInviteLinks()
    } catch (err) {
        console.error('Failed to create invite link:', err)
    } finally {
        isCreatingLink.value = false
    }
}

// Delete invite link
const deleteInviteLink = async (id) => {
    try {
        await api.delete(`invite-links/${id}/`)
        await fetchInviteLinks()
    } catch (err) {
        console.error('Failed to delete invite link:', err)
    }
}

// Copy invite link to clipboard
const copyInviteLink = async (token) => {
    const url = `${window.location.origin}/register?invite=${token}`
    await navigator.clipboard.writeText(url)
    copiedToken.value = token
    setTimeout(() => {
        copiedToken.value = null
    }, 2000)
}

// Computed: separate active and expired/used links
const activeLinks = computed(() =>
    inviteLinks.value.filter(link => link.is_valid)
)
const inactiveLinks = computed(() =>
    inviteLinks.value.filter(link => !link.is_valid)
)

// Time remaining helper
const timeRemaining = (expiresAt) => {
    const now = new Date()
    const expires = new Date(expiresAt)
    const diff = expires - now
    if (diff <= 0) return t('expired')
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
    return `${hours}h ${minutes}m`
}

// Build invite URL for display
const inviteUrl = (token) => {
    return `${window.location.origin}/register?invite=${token}`
}

const goBack = () => {
    router.push('/dashboard')
}

const handleLogout = () => {
    authService.logout()
    router.push('/login')
}

onMounted(() => {
    fetchUserInfo()
    fetchInviteLinks()
})
</script>

<template>
    <div
        class="min-h-screen bg-neutral-50 dark:bg-neutral-900 p-6 md:p-12 font-sans text-neutral-900 dark:text-neutral-100 transition-colors duration-300">
        <div class="max-w-5xl mx-auto">
            <!-- Header -->
            <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
                <div>
                    <button @click="goBack"
                        class="flex items-center gap-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors mb-4 font-bold">
                        <ArrowLeft :size="20" stroke-width="2.5" />
                        {{ t('returnDashboard') }}
                    </button>
                    <h1 class="text-4xl font-black tracking-tighter text-neutral-900 dark:text-white uppercase italic">
                        {{ t('adminSettings') }}
                    </h1>
                    <p class="text-neutral-400 dark:text-neutral-500 font-medium">{{ t('adminSettingsMessage') }}</p>
                </div>
            </header>

            <div class="space-y-6">

                <!-- Invite Links Management (Admin Only) -->
                <div v-if="userInfo.is_staff || userInfo.is_superuser"
                    class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                    <div class="flex items-center justify-between mb-6">
                        <div class="flex items-center gap-3">
                            <div class="p-3 bg-emerald-100 dark:bg-emerald-900/30 rounded-2xl">
                                <Link :size="24" class="text-emerald-600 dark:text-emerald-400" stroke-width="2.5" />
                            </div>
                            <div>
                                <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ t('inviteLinks') }}
                                </h2>
                                <p class="text-sm text-neutral-500 dark:text-neutral-400 font-medium">
                                    {{ t('inviteLinksDescription') }}</p>
                            </div>
                        </div>
                        <button @click="createInviteLink" :disabled="isCreatingLink"
                            class="flex items-center gap-2 px-6 py-3 bg-emerald-600 text-white rounded-2xl font-bold hover:bg-emerald-700 transition-all shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">
                            <RefreshCw v-if="isCreatingLink" :size="18" class="animate-spin" />
                            <Plus v-else :size="18" stroke-width="2.5" />
                            {{ t('generateLink') }}
                        </button>
                    </div>

                    <!-- Active Invite Links -->
                    <div v-if="activeLinks.length > 0" class="space-y-3 mb-6">
                        <h3 class="text-sm font-black uppercase tracking-widest text-neutral-400 ml-1">
                            {{ t('activeLinks') }}</h3>
                        <div v-for="link in activeLinks" :key="link.id"
                            class="flex items-center justify-between p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-900/50 rounded-2xl">
                            <div class="flex-1 min-w-0">
                                <p class="text-sm font-mono font-bold text-neutral-700 dark:text-neutral-300 truncate">
                                    {{ inviteUrl(link.token) }}
                                </p>
                                <div class="flex items-center gap-3 mt-1">
                                    <span
                                        class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                                        <Clock :size="12" /> {{ timeRemaining(link.expires_at) }}
                                    </span>
                                    <span class="text-xs text-neutral-400">
                                        {{ t('createdAt') }} {{ new Date(link.created_at).toLocaleString() }}
                                    </span>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 ml-4">
                                <button @click="copyInviteLink(link.token)"
                                    class="p-2 rounded-xl hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors"
                                    :title="t('copyLink')">
                                    <Check v-if="copiedToken === link.token" :size="18" class="text-emerald-600" />
                                    <Copy v-else :size="18" class="text-neutral-500 dark:text-neutral-400" />
                                </button>
                                <button @click="deleteInviteLink(link.id)"
                                    class="p-2 rounded-xl hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                                    :title="t('deleteLink')">
                                    <Trash2 :size="18" class="text-red-500" />
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Empty state for active links -->
                    <div v-else-if="!isLoadingLinks"
                        class="p-6 bg-neutral-50 dark:bg-neutral-700 rounded-2xl text-center mb-6">
                        <p class="text-neutral-500 dark:text-neutral-400 font-medium">{{ t('noActiveLinks') }}</p>
                    </div>

                    <!-- Expired/Used Links -->
                    <div v-if="inactiveLinks.length > 0" class="space-y-3">
                        <h3 class="text-sm font-black uppercase tracking-widest text-neutral-400 ml-1">
                            {{ t('expiredUsedLinks') }}</h3>
                        <div v-for="link in inactiveLinks" :key="link.id"
                            class="flex items-center justify-between p-4 bg-neutral-50 dark:bg-neutral-700 rounded-2xl opacity-60">
                            <div class="flex-1 min-w-0">
                                <p class="text-sm font-mono text-neutral-500 dark:text-neutral-400 truncate">
                                    {{ link.token }}
                                </p>
                                <div class="flex items-center gap-3 mt-1">
                                    <span v-if="link.is_used" class="flex items-center gap-1 text-xs text-blue-500">
                                        <CheckCircle2 :size="12" /> {{ t('usedBy') }} {{ link.used_by_username }}
                                    </span>
                                    <span v-else class="flex items-center gap-1 text-xs text-red-500">
                                        <AlertCircle :size="12" /> {{ t('expired') }}
                                    </span>
                                </div>
                            </div>
                            <button @click="deleteInviteLink(link.id)"
                                class="p-2 rounded-xl hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors ml-4"
                                :title="t('deleteLink')">
                                <Trash2 :size="18" class="text-red-500" />
                            </button>
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
/* Custom styles if needed */
</style>
