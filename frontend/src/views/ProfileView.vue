<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import { notifyError } from '@/composables/useToast'
import { useHabits } from '@/composables/useHabits'
import { useCategories } from '@/composables/useCategories'
import { useTags } from '@/composables/useTags'
import { useConfirm } from '@/composables/useConfirm'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { toISODate } from '@/utils/dates'
import {
    UserRound, KeyRound, Save, Plus, Trash2, Pencil, X, Check, ArchiveRestore, Archive,
    ListChecks, FolderOpen, Tags, TriangleAlert, Search, ChevronUp, ChevronDown,
} from 'lucide-vue-next'
import api from '@/services/api'
import PageShell from '@/components/layout/PageShell.vue'
import UiSection from '@/components/ui/UiSection.vue'
import UiInput from '@/components/ui/UiInput.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiModal from '@/components/ui/UiModal.vue'
import UiDropdown from '@/components/ui/UiDropdown.vue'
import HabitRow from '@/components/habits/HabitRow.vue'
import TagChip from '@/components/habits/TagChip.vue'
import HabitFormModal from '@/components/habits/HabitFormModal.vue'
import { inputClass, inputBaseClass, labelClass } from '@/components/ui/styles'

const { t } = useLanguage()
const { confirm } = useConfirm()
const { fetchUser } = useCurrentUser()
const { habits, archivedHabits, fetchHabits, fetchArchivedHabits, archiveHabit, unarchiveHabit, deleteActiveHabit, deleteArchivedHabit, updateHabit, moveHabit } = useHabits()
const { categories, isSavingCategory, isDeletingCategory, fetchCategories, addCategory, deleteCategory, updateCategory } = useCategories()
const { tags, isSavingTag, isDeletingTag, fetchTags, addTag, deleteTag, updateTag } = useTags()

const refreshHabits = () => fetchHabits(toISODate())

// --- Account ---
const userInfo = ref({ username: '', email: '' })
const profileEmail = ref('')
const isSavingEmail = ref(false)
const profileSaved = ref(false)

const loadUser = async () => {
    const data = await fetchUser(true)
    if (data) {
        userInfo.value = data
        profileEmail.value = data.email
    }
}

const updateProfile = async () => {
    isSavingEmail.value = true
    try {
        await api.patch('auth/user/', { email: profileEmail.value })
        profileSaved.value = true
        setTimeout(() => { profileSaved.value = false }, 3000)
        fetchUser(true)
    } catch (err) {
        notifyError(err, 'saveFailed')
    } finally {
        isSavingEmail.value = false
    }
}

// --- Password ---
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isSavingPassword = ref(false)
const passwordError = ref('')
const passwordSuccess = ref(false)

const changePassword = async () => {
    passwordError.value = ''
    passwordSuccess.value = false

    if (newPassword.value !== confirmPassword.value) {
        passwordError.value = t('passwordMismatch')
        return
    }

    if (newPassword.value.length < 8) {
        passwordError.value = t('passwordTooShort')
        return
    }

    isSavingPassword.value = true
    try {
        await api.post('auth/password/change/', {
            old_password: currentPassword.value,
            new_password1: newPassword.value,
            new_password2: confirmPassword.value
        })
        passwordSuccess.value = true
        currentPassword.value = ''
        newPassword.value = ''
        confirmPassword.value = ''
        setTimeout(() => { passwordSuccess.value = false }, 3000)
    } catch (err) {
        const errors = err.response?.data || {}
        passwordError.value = errors.old_password?.[0] || errors.new_password2?.[0] || errors.new_password1?.[0] || t('passwordChangeFailed')
    } finally {
        isSavingPassword.value = false
    }
}

// --- Categories ---
const newCategoryName = ref('')
const editingCategory = ref(null)
const editingCategoryName = ref('')

const handleAddCategory = async () => {
    if (!newCategoryName.value.trim()) return
    try {
        await addCategory(newCategoryName.value.trim())
        newCategoryName.value = ''
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const startEditCategory = (category) => {
    editingCategory.value = category.id
    editingCategoryName.value = category.name
}

const cancelEditCategory = () => {
    editingCategory.value = null
    editingCategoryName.value = ''
}

const saveEditCategory = async (categoryId) => {
    if (!editingCategoryName.value.trim()) return
    try {
        await updateCategory(categoryId, editingCategoryName.value.trim())
        editingCategory.value = null
        await fetchCategories()
        // Habits embed their category, so refresh them too
        refreshHabits()
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const handleDeleteCategory = async (category) => {
    const ok = await confirm({
        title: t('deleteCategory'),
        message: t('confirmDeleteCategory'),
        confirmLabel: t('delete'),
        danger: true,
    })
    if (!ok) return
    try {
        await deleteCategory(category.id)
        refreshHabits()
    } catch (err) {
        notifyError(err, 'deleteFailed')
    }
}

// --- Tags ---
const newTagName = ref('')
const newTagColor = ref('#64748b')
const editingTag = ref(null)
const editingTagName = ref('')
const editingTagColor = ref('')

const handleAddTag = async () => {
    if (!newTagName.value.trim()) return
    try {
        await addTag(newTagName.value.trim(), newTagColor.value)
        newTagName.value = ''
        newTagColor.value = '#64748b'
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const startEditTag = (tag) => {
    editingTag.value = tag.id
    editingTagName.value = tag.name
    editingTagColor.value = tag.color
}

const cancelEditTag = () => {
    editingTag.value = null
    editingTagName.value = ''
    editingTagColor.value = ''
}

const saveEditTag = async (tagId) => {
    if (!editingTagName.value.trim()) return
    try {
        await updateTag(tagId, {
            name: editingTagName.value.trim(),
            color: editingTagColor.value
        })
        editingTag.value = null
        refreshHabits()
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const handleDeleteTag = async (tag) => {
    const ok = await confirm({
        title: t('deleteTag'),
        message: t('confirmDeleteTag'),
        confirmLabel: t('delete'),
        danger: true,
    })
    if (!ok) return
    try {
        await deleteTag(tag.id)
        refreshHabits()
    } catch (err) {
        notifyError(err, 'deleteFailed')
    }
}

// --- Habit tags ---
const tagSearchQuery = ref('')

const availableTags = (habit) => {
    const assigned = new Set(habit.tags?.map(tag => tag.id) || [])
    const query = tagSearchQuery.value.trim().toLowerCase()
    return tags.value.filter(tag => !assigned.has(tag.id) && tag.name.toLowerCase().includes(query))
}

const setHabitTags = async (habit, tagIds) => {
    try {
        await updateHabit(habit.id, { tag_ids: tagIds })
        await refreshHabits()
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const addTagToHabit = (habit, tagId) => setHabitTags(habit, [...(habit.tags?.map(tag => tag.id) || []), tagId])

const removeTagFromHabit = (habit, tagId) =>
    setHabitTags(habit, (habit.tags || []).map(tag => tag.id).filter(id => id !== tagId))

// --- Habit editing (active and archived) ---
const editingHabit = ref(null)
const isSavingHabit = ref(false)
const habitFormError = ref('')

const startEditHabit = (habit) => {
    habitFormError.value = ''
    editingHabit.value = habit
}

const saveEditHabit = async (payload) => {
    isSavingHabit.value = true
    habitFormError.value = ''
    try {
        await updateHabit(editingHabit.value.id, payload)
        editingHabit.value = null
        await Promise.all([refreshHabits(), fetchArchivedHabits()])
    } catch (err) {
        habitFormError.value = t('saveFailed')
    } finally {
        isSavingHabit.value = false
    }
}

const handleMoveHabit = async (habit, direction) => {
    try {
        await moveHabit(habit.id, direction)
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const handleArchiveHabit = async (habit) => {
    const ok = await confirm({
        title: t('archiveHabit'),
        message: t('confirmHabitArchive'),
        confirmLabel: t('archive'),
    })
    if (!ok) return
    try {
        await archiveHabit(habit.id)
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const handleUnarchive = async (habit) => {
    try {
        await unarchiveHabit(habit.id)
        await refreshHabits()
    } catch (err) {
        notifyError(err, 'saveFailed')
    }
}

const handleDeleteHabit = async (habit, archived) => {
    const ok = await confirm({
        title: t('deleteHabit'),
        message: `${habit.name}\n\n${t('confirmDeletePermanent')}`,
        confirmLabel: t('delete'),
        danger: true,
    })
    if (!ok) return
    try {
        if (archived) await deleteArchivedHabit(habit.id)
        else await deleteActiveHabit(habit.id)
    } catch (err) {
        notifyError(err, 'deleteFailed')
    }
}

// --- Delete all data ---
const DELETE_KEYWORD = 'DELETE'
const showDeleteAllDataModal = ref(false)
const deleteConfirmationText = ref('')
const isDeletingAllData = ref(false)
const deleteAllDataError = ref('')

const canDeleteAll = computed(() => deleteConfirmationText.value === DELETE_KEYWORD)

const openDeleteAllDataModal = () => {
    deleteConfirmationText.value = ''
    deleteAllDataError.value = ''
    showDeleteAllDataModal.value = true
}

const closeDeleteAllDataModal = () => {
    showDeleteAllDataModal.value = false
}

const deleteAllUserData = async () => {
    if (!canDeleteAll.value) {
        deleteAllDataError.value = t('confirmationMismatch')
        return
    }

    isDeletingAllData.value = true
    deleteAllDataError.value = ''

    try {
        await api.post('auth/delete-all-data/')
        // Reload to show the empty state everywhere
        window.location.reload()
    } catch (err) {
        deleteAllDataError.value = err.response?.data?.message || t('deleteAllDataFailed')
        isDeletingAllData.value = false
    }
}

const rowClass = 'flex items-center gap-2 rounded-xl bg-sunken px-3 py-2'
const colorInputClass =
    'shrink-0 cursor-pointer rounded-lg border border-line bg-surface p-1 [&::-moz-color-swatch]:rounded-md [&::-moz-color-swatch]:border-0 [&::-webkit-color-swatch]:rounded-md [&::-webkit-color-swatch]:border-0 [&::-webkit-color-swatch-wrapper]:p-0'

onMounted(() => {
    loadUser()
    fetchCategories()
    fetchTags()
    refreshHabits()
    fetchArchivedHabits()
})
</script>

<template>
    <PageShell :title="t('profile')" :description="t('profileDescription')" width="max-w-4xl">
        <!-- Account -->
        <UiSection :title="t('accountInformation')" :icon="UserRound">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <UiInput :model-value="userInfo.username" :label="t('username')" :hint="t('cannotChange')" disabled />

                <form @submit.prevent="updateProfile">
                    <label :class="labelClass" for="profile-email">{{ t('email') }}</label>
                    <div class="flex gap-2">
                        <input id="profile-email" v-model="profileEmail" type="email" required autocomplete="email"
                            :class="inputClass" />
                        <UiButton type="submit" size="field" :icon="profileSaved ? Check : Save"
                            :loading="isSavingEmail">
                            {{ profileSaved ? t('saved') : t('save') }}
                        </UiButton>
                    </div>
                </form>
            </div>
        </UiSection>

        <!-- Password -->
        <UiSection :title="t('changePassword')" :icon="KeyRound">
            <form class="space-y-4" @submit.prevent="changePassword">
                <UiInput v-model="currentPassword" type="password" :label="t('currentPassword')" required
                    autocomplete="current-password" />

                <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <UiInput v-model="newPassword" type="password" :label="t('newPassword')"
                        :hint="t('passwordMinHint')" required autocomplete="new-password" />
                    <UiInput v-model="confirmPassword" type="password" :label="t('confirmNewPassword')" required
                        autocomplete="new-password" />
                </div>

                <UiAlert v-if="passwordError">{{ passwordError }}</UiAlert>
                <UiAlert v-if="passwordSuccess" variant="success">{{ t('passwordChanged') }}</UiAlert>

                <div class="flex justify-end">
                    <UiButton type="submit" :icon="KeyRound" :loading="isSavingPassword"
                        :disabled="!currentPassword || !newPassword || !confirmPassword">
                        {{ t('updatePassword') }}
                    </UiButton>
                </div>
            </form>
        </UiSection>

        <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <!-- Categories -->
            <UiSection :title="t('yourCategories')" :icon="FolderOpen">
                <form class="mb-4 flex gap-2" @submit.prevent="handleAddCategory">
                    <input v-model="newCategoryName" type="text" :placeholder="t('newCategoryName')"
                        :aria-label="t('newCategoryName')" maxlength="100" :class="inputClass" />
                    <UiButton type="submit" size="field" :icon="Plus"
                        :loading="isSavingCategory" :disabled="!newCategoryName.trim()">
                        {{ t('add') }}
                    </UiButton>
                </form>

                <ul class="space-y-2">
                    <li v-for="category in categories" :key="category.id" :class="rowClass">
                        <template v-if="editingCategory === category.id">
                            <input v-model="editingCategoryName" type="text" :aria-label="t('categoryName')"
                                :class="[inputBaseClass, 'h-9']" @keyup.enter="saveEditCategory(category.id)"
                                @keyup.esc="cancelEditCategory" />
                            <UiIconButton :icon="Check" variant="success" :label="t('save')"
                                @click="saveEditCategory(category.id)" />
                            <UiIconButton :icon="X" :label="t('cancel')" @click="cancelEditCategory" />
                        </template>
                        <template v-else>
                            <span class="min-w-0 flex-1 truncate py-1.5 text-sm font-semibold text-ink">
                                {{ category.name }}
                            </span>
                            <UiIconButton :icon="Pencil" :label="t('editCategory')"
                                @click="startEditCategory(category)" />
                            <UiIconButton :icon="Trash2" variant="danger" :label="t('deleteCategory')"
                                :loading="isDeletingCategory === category.id" @click="handleDeleteCategory(category)" />
                        </template>
                    </li>
                </ul>

                <p v-if="categories.length === 0" class="py-6 text-center text-sm text-ink-faint">
                    {{ t('noCategories') }}
                </p>
            </UiSection>

            <!-- Tags -->
            <UiSection :title="t('yourTags')" :icon="Tags">
                <form class="mb-4 flex gap-2" @submit.prevent="handleAddTag">
                    <input v-model="newTagName" type="text" :placeholder="t('newTagName')"
                        :aria-label="t('newTagName')" maxlength="50" :class="inputClass" />
                    <input v-model="newTagColor" type="color" :aria-label="t('tagColor')" :title="t('tagColor')"
                        :class="[colorInputClass, 'size-11']" />
                    <UiButton type="submit" size="field" :icon="Plus" :loading="isSavingTag"
                        :disabled="!newTagName.trim()">
                        {{ t('add') }}
                    </UiButton>
                </form>

                <ul class="space-y-2">
                    <li v-for="tag in tags" :key="tag.id" :class="rowClass">
                        <template v-if="editingTag === tag.id">
                            <input v-model="editingTagColor" type="color" :aria-label="t('tagColor')"
                                :class="[colorInputClass, 'size-9']" />
                            <input v-model="editingTagName" type="text" :aria-label="t('newTagName')"
                                :class="[inputBaseClass, 'h-9']" @keyup.enter="saveEditTag(tag.id)"
                                @keyup.esc="cancelEditTag" />
                            <UiIconButton :icon="Check" variant="success" :label="t('save')"
                                @click="saveEditTag(tag.id)" />
                            <UiIconButton :icon="X" :label="t('cancel')" @click="cancelEditTag" />
                        </template>
                        <template v-else>
                            <span class="min-w-0 flex-1 py-1.5">
                                <TagChip :tag="tag" class="text-sm" />
                            </span>
                            <UiIconButton :icon="Pencil" :label="t('edit')" @click="startEditTag(tag)" />
                            <UiIconButton :icon="Trash2" variant="danger" :label="t('delete')"
                                :loading="isDeletingTag === tag.id" @click="handleDeleteTag(tag)" />
                        </template>
                    </li>
                </ul>

                <p v-if="tags.length === 0" class="py-6 text-center text-sm text-ink-faint">{{ t('noTags') }}</p>
            </UiSection>
        </div>

        <!-- Active habits -->
        <UiSection :title="`${t('yourHabits')} (${habits.length})`" :icon="ListChecks">
            <p v-if="habits.length > 1" class="mb-3 text-sm text-ink-soft">{{ t('habitOrderHint') }}</p>
            <TransitionGroup tag="ul" class="divide-y divide-line border-y border-line"
                move-class="transition-transform duration-200">
                <HabitRow v-for="(habit, index) in habits" :key="habit.id" :habit="habit">
                    <TagChip v-for="tag in habit.tags" :key="tag.id" :tag="tag" removable
                        :remove-label="t('removeTag')" @remove="removeTagFromHabit(habit, tag.id)" />

                            <!-- Add tag -->
                            <UiDropdown align="left" width="w-52" @open="tagSearchQuery = ''">
                                <template #trigger="{ toggle }">
                                    <button type="button" :title="t('addTag')" :aria-label="t('addTag')"
                                        class="inline-flex h-5 items-center gap-0.5 rounded-full border border-dashed border-line-strong px-1.5 text-xs font-semibold text-ink-faint transition-colors hover:border-primary-500 hover:text-primary-600 dark:hover:text-primary-400"
                                        @click="toggle">
                                        <Plus :size="12" stroke-width="2.5" />
                                        <Tags :size="12" stroke-width="2.25" />
                                    </button>
                                </template>

                                <template #default="{ close }">
                                    <div class="relative mb-1">
                                        <Search :size="14"
                                            class="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ink-faint" />
                                        <input v-model="tagSearchQuery" type="search" :placeholder="t('searchTags')"
                                            :class="[inputBaseClass, 'h-9 pl-8']" />
                                    </div>
                                    <div class="max-h-40 overflow-y-auto">
                                        <button v-for="tag in availableTags(habit)" :key="tag.id" type="button"
                                            :style="{ '--tag': tag.color }"
                                            class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm font-medium text-ink transition-colors hover:bg-sunken"
                                            @click="addTagToHabit(habit, tag.id); close()">
                                            <span class="size-2.5 shrink-0 rounded-full bg-(--tag)"></span>
                                            <span class="truncate">{{ tag.name }}</span>
                                        </button>
                                        <p v-if="availableTags(habit).length === 0"
                                            class="px-2.5 py-2 text-sm text-ink-faint">
                                            {{ t('noTagsFound') }}
                                        </p>
                                    </div>
                                </template>
                            </UiDropdown>

                    <template #actions>
                        <!-- Order used on the dashboard (within each category) -->
                        <UiIconButton :icon="ChevronUp" :label="t('moveUp')" :disabled="index === 0"
                            @click="handleMoveHabit(habit, -1)" />
                        <UiIconButton :icon="ChevronDown" :label="t('moveDown')"
                            :disabled="index === habits.length - 1" @click="handleMoveHabit(habit, 1)" />
                        <span class="mx-1.5 h-5 w-px bg-line"></span>
                        <UiIconButton :icon="Pencil" :label="t('editHabit')" @click="startEditHabit(habit)" />
                        <UiIconButton :icon="Archive" :label="t('archiveHabit')" @click="handleArchiveHabit(habit)" />
                        <UiIconButton :icon="Trash2" variant="danger" :label="t('deleteHabitPermanently')"
                            @click="handleDeleteHabit(habit, false)" />
                    </template>
                </HabitRow>
            </TransitionGroup>

            <p v-if="habits.length === 0" class="py-6 text-center text-sm text-ink-faint">
                {{ t('noHabitsProfile') }}
            </p>
        </UiSection>

        <!-- Archived habits -->
        <UiSection :title="`${t('archivedHabits')} (${archivedHabits.length})`" :icon="Archive">
            <ul v-if="archivedHabits.length > 0" class="divide-y divide-line border-y border-line">
                <HabitRow v-for="habit in archivedHabits" :key="habit.id" :habit="habit" muted>
                    <TagChip v-for="tag in habit.tags" :key="tag.id" :tag="tag" />

                    <template #actions>
                        <UiIconButton :icon="Pencil" :label="t('editHabit')" @click="startEditHabit(habit)" />
                        <UiIconButton :icon="ArchiveRestore" :label="t('unarchiveHabit')"
                            @click="handleUnarchive(habit)" />
                        <UiIconButton :icon="Trash2" variant="danger" :label="t('deleteHabitPermanently')"
                            @click="handleDeleteHabit(habit, true)" />
                    </template>
                </HabitRow>
            </ul>

            <p v-if="archivedHabits.length === 0" class="py-6 text-center text-sm text-ink-faint">
                {{ t('noArchivedHabits') }}
            </p>
        </UiSection>

        <!-- Danger zone -->
        <UiSection :title="t('dangerZone')" :icon="TriangleAlert" tone="danger">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                    <h3 class="font-semibold text-ink">{{ t('deleteAllData') }}</h3>
                    <p class="mt-1 text-sm text-ink-soft">{{ t('deleteAllDataDescription') }}</p>
                </div>
                <UiButton variant="danger" :icon="Trash2" @click="openDeleteAllDataModal">
                    {{ t('deleteAllData') }}
                </UiButton>
            </div>
        </UiSection>

        <!-- Edit habit -->
        <HabitFormModal :open="!!editingHabit" :habit="editingHabit" :saving="isSavingHabit" :error="habitFormError"
            @close="editingHabit = null" @save="saveEditHabit" />

        <!-- Delete all data -->
        <UiModal :open="showDeleteAllDataModal" :title="t('deleteAllData')" :icon="TriangleAlert" tone="danger"
            :busy="isDeletingAllData" @close="closeDeleteAllDataModal">
            <form id="delete-all-form" class="space-y-5" @submit.prevent="deleteAllUserData">
                <UiAlert variant="warning">
                    <p class="whitespace-pre-line">{{ t('confirmDeleteAllData') }}</p>
                </UiAlert>

                <UiInput v-model="deleteConfirmationText" :label="t('typeDeleteToConfirm')"
                    :placeholder="DELETE_KEYWORD" autocomplete="off" spellcheck="false" />

                <UiAlert v-if="deleteAllDataError">{{ deleteAllDataError }}</UiAlert>
            </form>

            <template #footer>
                <UiButton variant="secondary" :disabled="isDeletingAllData" @click="closeDeleteAllDataModal">
                    {{ t('cancel') }}
                </UiButton>
                <UiButton type="submit" form="delete-all-form" variant="danger" :icon="Trash2"
                    :loading="isDeletingAllData" :disabled="!canDeleteAll">
                    {{ isDeletingAllData ? t('deletingAllData') : t('deleteAllData') }}
                </UiButton>
            </template>
        </UiModal>
    </PageShell>
</template>
