<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { Plus, Trash2, Copy, Check, Link2, Clock, CircleAlert, CircleCheck, ShieldAlert } from 'lucide-vue-next'
import PageShell from '@/components/layout/PageShell.vue'
import UiSection from '@/components/ui/UiSection.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiSpinner from '@/components/ui/UiSpinner.vue'
import UiEmptyState from '@/components/ui/UiEmptyState.vue'

const { t, locale } = useLanguage()
const { isAdmin, fetchUser } = useCurrentUser()

// Invite links state
const inviteLinks = ref([])
const isLoadingLinks = ref(false)
const isCreatingLink = ref(false)
const copiedToken = ref(null)
const isReady = ref(false)

// Fetch invite links
const fetchInviteLinks = async () => {
    isLoadingLinks.value = true
    try {
        const res = await api.get('invite-links/')
        inviteLinks.value = res.data
    } catch (err) {
        notifyError(err, 'loadFailed')
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
        notifyError(err, 'saveFailed')
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
        notifyError(err, 'deleteFailed')
    }
}

// Build invite URL for display
const inviteUrl = (token) => `${window.location.origin}/register?invite=${token}`

// Copy invite link to clipboard
const copyInviteLink = async (token) => {
    try {
        await navigator.clipboard.writeText(inviteUrl(token))
        copiedToken.value = token
        setTimeout(() => {
            copiedToken.value = null
        }, 2000)
    } catch (err) {
        // Clipboard unavailable (insecure context) — the URL stays selectable
    }
}

// Separate active and expired/used links
const activeLinks = computed(() => inviteLinks.value.filter(link => link.is_valid))
const inactiveLinks = computed(() => inviteLinks.value.filter(link => !link.is_valid))

// Time remaining helper
const timeRemaining = (expiresAt) => {
    const diff = new Date(expiresAt) - new Date()
    if (diff <= 0) return t('expired')
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
    return `${hours}h ${minutes}m`
}

onMounted(async () => {
    await fetchUser()
    isReady.value = true
    if (isAdmin.value) fetchInviteLinks()
})
</script>

<template>
    <PageShell :title="t('adminSettings')" :description="t('adminSettingsMessage')">
        <UiSpinner v-if="!isReady" />

        <UiEmptyState v-else-if="!isAdmin" :icon="ShieldAlert" :title="t('adminOnlyTitle')"
            :description="t('adminOnly')" />

        <UiSection v-else :title="t('inviteLinks')" :description="t('inviteLinksDescription')" :icon="Link2">
            <template #actions>
                <UiButton :icon="Plus" :loading="isCreatingLink" @click="createInviteLink">
                    {{ t('generateLink') }}
                </UiButton>
            </template>

            <!-- Active links -->
            <h3 class="mb-2 text-xs font-semibold tracking-wider text-ink-faint uppercase">{{ t('activeLinks') }}</h3>

            <ul v-if="activeLinks.length > 0" class="space-y-2">
                <li v-for="link in activeLinks" :key="link.id"
                    class="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3">
                    <div class="min-w-0 flex-1">
                        <p class="truncate font-mono text-sm text-ink select-all">{{ inviteUrl(link.token) }}</p>
                        <p class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-ink-faint">
                            <span class="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400">
                                <Clock :size="12" stroke-width="2.5" /> {{ timeRemaining(link.expires_at) }}
                            </span>
                            <span>{{ t('createdAt') }} {{ new Date(link.created_at).toLocaleString(locale) }}</span>
                        </p>
                    </div>
                    <UiIconButton :icon="copiedToken === link.token ? Check : Copy"
                        :label="copiedToken === link.token ? t('linkCopied') : t('copyLink')"
                        :class="copiedToken === link.token && 'text-emerald-600 dark:text-emerald-400'"
                        @click="copyInviteLink(link.token)" />
                    <UiIconButton :icon="Trash2" variant="danger" :label="t('deleteLink')"
                        @click="deleteInviteLink(link.id)" />
                </li>
            </ul>

            <UiSpinner v-else-if="isLoadingLinks" :size="24" />

            <p v-else class="rounded-xl bg-sunken px-4 py-6 text-center text-sm text-ink-soft">
                {{ t('noActiveLinks') }}
            </p>

            <!-- Expired / used links -->
            <template v-if="inactiveLinks.length > 0">
                <h3 class="mt-6 mb-2 text-xs font-semibold tracking-wider text-ink-faint uppercase">
                    {{ t('expiredUsedLinks') }}
                </h3>
                <ul class="space-y-2">
                    <li v-for="link in inactiveLinks" :key="link.id"
                        class="flex items-center gap-2 rounded-xl bg-sunken p-3">
                        <div class="min-w-0 flex-1">
                            <p class="truncate font-mono text-sm text-ink-faint">{{ link.token }}</p>
                            <p v-if="link.is_used"
                                class="mt-1 inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400">
                                <CircleCheck :size="12" stroke-width="2.5" /> {{ t('usedBy') }} {{ link.used_by_username }}
                            </p>
                            <p v-else
                                class="mt-1 inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
                                <CircleAlert :size="12" stroke-width="2.5" /> {{ t('expired') }}
                            </p>
                        </div>
                        <UiIconButton :icon="Trash2" variant="danger" :label="t('deleteLink')"
                            @click="deleteInviteLink(link.id)" />
                    </li>
                </ul>
            </template>
        </UiSection>
    </PageShell>
</template>
