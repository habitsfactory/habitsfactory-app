<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useLanguage } from '@/composables/useLanguage'
import { useHabits } from '@/composables/useHabits'
import { useCategories } from '@/composables/useCategories'
import { useTags } from '@/composables/useTags'
import { User, ArrowLeft, Lock, Save, RefreshCw, Plus, Trash2, Pencil, X, Check, ArchiveRestore, Archive, CheckCircle2, FolderOpen, Calendar, Tags } from 'lucide-vue-next'
import * as LucideIcons from 'lucide-vue-next'
import IconPicker from '@/components/IconPicker.vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'
import { useDarkMode } from '@/composables/useDarkMode'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const { isDark, toggleDarkMode } = useDarkMode()

const goBack = () => {
    router.push('/dashboard')
}
const { t } = useLanguage()
const { habits, archivedHabits, fetchHabits, fetchArchivedHabits, archiveHabit, unarchiveHabit, deleteActiveHabit, deleteArchivedHabit, updateHabit } = useHabits()
const { categories, isSavingCategory, isDeletingCategory, fetchCategories, addCategory, deleteCategory, updateCategory } = useCategories()
const { tags, isSavingTag, isDeletingTag, fetchTags, addTag, deleteTag, updateTag } = useTags()

// User info state
const userInfo = ref({
    username: '',
    email: '',
    is_staff: false,
    is_superuser: false
})

// Profile form state
const profileEmail = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isSavingProfile = ref(false)
const profileSaved = ref(false)
const passwordError = ref('')
const passwordSuccess = ref(false)

// Category management
const newCategoryName = ref('')
const editingCategory = ref(null)
const editingCategoryName = ref('')

// Tag management
const newTagName = ref('')
const newTagColor = ref('#6B7280')
const editingTag = ref(null)
const editingTagName = ref('')
const editingTagColor = ref('')

// Habit editing
const editingHabit = ref(null)
const editingHabitData = ref({
    name: '',
    icon: '',
    color: '',
    habit_type: '',
    max_value: 5,
    unit: '',
    category: null
})
const isSavingHabit = ref(false)

// Habit tag management
const addingTagToHabit = ref(null)
const tagSearchQuery = ref('')
const filteredTags = ref([])

const openTagSearch = (habitId) => {
    addingTagToHabit.value = habitId
    tagSearchQuery.value = ''
    updateFilteredTags(habitId)
}

const closeTagSearch = () => {
    addingTagToHabit.value = null
    tagSearchQuery.value = ''
}

const updateFilteredTags = (habitId) => {
    const habit = habits.value.find(h => h.id === habitId)
    const habitTagIds = habit?.tags?.map(t => t.id) || []
    filteredTags.value = tags.value.filter(tag =>
        !habitTagIds.includes(tag.id) &&
        tag.name.toLowerCase().includes(tagSearchQuery.value.toLowerCase())
    )
}

const addTagToHabit = async (habitId, tagId) => {
    const habit = habits.value.find(h => h.id === habitId)
    if (!habit) return

    const currentTagIds = habit.tags?.map(t => t.id) || []
    const newTagIds = [...currentTagIds, tagId]

    try {
        await updateHabit(habitId, { tag_ids: newTagIds })
        await fetchHabits(new Date().toISOString().split('T')[0])
        closeTagSearch()
    } catch (err) {
        console.error('Failed to add tag to habit:', err)
    }
}

const removeTagFromHabit = async (habitId, tagId) => {
    const habit = habits.value.find(h => h.id === habitId)
    if (!habit) return

    const currentTagIds = habit.tags?.map(t => t.id) || []
    const newTagIds = currentTagIds.filter(id => id !== tagId)

    try {
        await updateHabit(habitId, { tag_ids: newTagIds })
        await fetchHabits(new Date().toISOString().split('T')[0])
    } catch (err) {
        console.error('Failed to remove tag from habit:', err)
    }
}

// Fetch user info
const fetchUserInfo = async () => {
    try {
        const response = await api.get('auth/user/')
        userInfo.value = response.data
        profileEmail.value = response.data.email
    } catch (err) {
        console.error('Failed to fetch user info:', err)
    }
}

// Update profile email
const updateProfile = async () => {
    isSavingProfile.value = true
    try {
        await api.patch('auth/user/', { email: profileEmail.value })
        profileSaved.value = true
        setTimeout(() => { profileSaved.value = false }, 3000)
    } catch (err) {
        console.error('Failed to update profile:', err)
    } finally {
        isSavingProfile.value = false
    }
}

// Change password
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

    isSavingProfile.value = true
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
        passwordError.value = err.response?.data?.old_password?.[0] || t('passwordChangeFailed')
    } finally {
        isSavingProfile.value = false
    }
}

// Category management
const handleAddCategory = async () => {
    if (!newCategoryName.value.trim()) return
    await addCategory(newCategoryName.value.trim())
    newCategoryName.value = ''
}

const startEditCategory = (category) => {
    editingCategory.value = category.id
    editingCategoryName.value = category.name
}

const saveEditCategory = async (categoryId) => {
    if (!editingCategoryName.value.trim()) return
    await updateCategory(categoryId, editingCategoryName.value.trim())
    editingCategory.value = null
    await fetchCategories()
}

const cancelEditCategory = () => {
    editingCategory.value = null
    editingCategoryName.value = ''
}

const handleDeleteCategory = async (categoryId) => {
    if (confirm(t('confirmDeleteCategory'))) {
        await deleteCategory(categoryId)
    }
}

// Tag management
const handleAddTag = async () => {
    if (!newTagName.value.trim()) return
    await addTag(newTagName.value.trim(), newTagColor.value)
    newTagName.value = ''
    newTagColor.value = '#6B7280'
}

const startEditTag = (tag) => {
    editingTag.value = tag.id
    editingTagName.value = tag.name
    editingTagColor.value = tag.color
}

const saveEditTag = async (tagId) => {
    if (!editingTagName.value.trim()) return
    await updateTag(tagId, {
        name: editingTagName.value.trim(),
        color: editingTagColor.value
    })
    editingTag.value = null
}

const cancelEditTag = () => {
    editingTag.value = null
    editingTagName.value = ''
    editingTagColor.value = ''
}

const handleDeleteTag = async (tagId) => {
    if (confirm(t('confirmDeleteTag'))) {
        await deleteTag(tagId)
    }
}

// Habit editing (for archived habits)
const startEditHabit = (habit) => {
    editingHabit.value = habit.id
    editingHabitData.value = {
        name: habit.name,
        icon: habit.icon,
        color: habit.color,
        habit_type: habit.habit_type,
        max_value: habit.max_value || 5,
        unit: habit.unit || '',
        category: habit.category?.id || null
    }
}

const saveEditHabit = async () => {
    isSavingHabit.value = true
    try {
        await updateHabit(editingHabit.value, {
            name: editingHabitData.value.name,
            icon: editingHabitData.value.icon,
            color: editingHabitData.value.color,
            habit_type: editingHabitData.value.habit_type,
            max_value: editingHabitData.value.max_value,
            unit: editingHabitData.value.unit,
            category: editingHabitData.value.category
        })
        editingHabit.value = null
        await fetchHabits(new Date().toISOString().split('T')[0])
        await fetchArchivedHabits()
    } catch (err) {
        console.error('Failed to update habit:', err)
    } finally {
        isSavingHabit.value = false
    }
}

const cancelEditHabit = () => {
    editingHabit.value = null
}

const handleArchiveHabit = async (habitId) => {
    await archiveHabit(habitId)
}

const handleDeleteActiveHabit = async (habitId) => {
    if (confirm(t('confirmDeletePermanent'))) {
        await deleteActiveHabit(habitId)
        await fetchHabits(new Date().toISOString().split('T')[0])
    }
}

const handleUnarchive = async (habitId) => {
    await unarchiveHabit(habitId)
    await fetchHabits(new Date().toISOString().split('T')[0])
}

const handleArchivedDelete = async (habitId) => {
    if (confirm(t('confirmDeletePermanent'))) {
        await deleteArchivedHabit(habitId)
        await fetchArchivedHabits()
    }
}

// Get icon component
const getIcon = (iconName) => {
    if (!iconName) return LucideIcons.Calendar
    const pascalCase = iconName
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join('')
    return LucideIcons[pascalCase] || LucideIcons.Calendar
}

// Click outside handler to close tag search dropdown
const handleClickOutside = (event) => {
    if (addingTagToHabit.value !== null) {
        const dropdown = event.target.closest('.relative')
        if (!dropdown || !dropdown.contains(event.target)) {
            closeTagSearch()
        }
    }
}

onMounted(() => {
    fetchUserInfo()
    fetchCategories()
    fetchTags()
    fetchHabits(new Date().toISOString().split('T')[0])
    fetchArchivedHabits()
    document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
})
</script>


<template>
    <div
        class="min-h-screen bg-neutral-50 dark:bg-neutral-900 p-6 md:p-12 font-sans text-neutral-900 dark:text-neutral-100 transition-colors duration-300">
        <div class="max-w-4xl mx-auto">
            <!-- Header -->
            <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
                <div>
                    <button @click="goBack"
                        class="flex items-center gap-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors mb-4 font-bold">
                        <ArrowLeft :size="20" stroke-width="2.5" />
                        {{ t('returnDashboard') }}
                    </button>
                    <h1 class="text-4xl font-black tracking-tighter text-neutral-900 dark:text-white uppercase italic">
                        {{ t('profile') }}
                    </h1>
                    <p class="text-neutral-400 dark:text-neutral-500 font-medium">{{ t('profileDescription') }}</p>
                </div>
            </header>

            <!-- Main Content -->
            <div class="space-y-6">
                <div class="space-y-8">
                    <!-- Account Section -->
                    <div
                        class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="p-3 rounded-2xl bg-primary-100 dark:bg-primary-900">
                                <User :size="24" class="text-primary-600 dark:text-primary-400" stroke-width="2.5" />
                            </div>
                            <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ t('accountInformation')
                            }}</h2>
                        </div>

                        <div class="space-y-6">
                            <!-- Username (read-only) -->
                            <div class="space-y-2">
                                <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                    t('username')
                                }}</label>
                                <div
                                    class="bg-neutral-100 dark:bg-neutral-700 rounded-2xl px-6 py-4 font-bold text-neutral-600 dark:text-neutral-300">
                                    {{ userInfo.username }}
                                </div>
                            </div>

                            <!-- Email -->
                            <div class="space-y-2">
                                <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                    t('email')
                                }}</label>
                                <div class="flex gap-3">
                                    <input v-model="profileEmail" type="email"
                                        class="flex-1 bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-100 dark:border-neutral-600 rounded-2xl px-6 py-4 font-bold outline-none focus:border-primary-500 transition text-neutral-900 dark:text-white" />
                                    <button @click="updateProfile" :disabled="isSavingProfile"
                                        class="px-6 py-4 bg-primary-600 text-white rounded-2xl font-bold hover:bg-primary-700 transition-all disabled:opacity-50 flex items-center gap-2">
                                        <RefreshCw v-if="isSavingProfile" :size="20" class="animate-spin" />
                                        <Save v-else :size="20" />
                                        {{ profileSaved ? (t('saved')) : (t('save')) }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Password Section -->
                    <div
                        class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="p-3 rounded-2xl bg-orange-100 dark:bg-orange-900">
                                <Lock :size="24" class="text-orange-600 dark:text-orange-400" stroke-width="2.5" />
                            </div>
                            <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ t('changePassword') }}
                            </h2>
                        </div>

                        <div class="space-y-4">
                            <div class="space-y-2">
                                <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                    t('currentPassword') }}</label>
                                <input v-model="currentPassword" type="password"
                                    class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-100 dark:border-neutral-600 rounded-2xl px-6 py-4 font-bold outline-none focus:border-primary-500 transition text-neutral-900 dark:text-white" />
                            </div>

                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div class="space-y-2">
                                    <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                        t('newPassword') }}</label>
                                    <input v-model="newPassword" type="password"
                                        class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-100 dark:border-neutral-600 rounded-2xl px-6 py-4 font-bold outline-none focus:border-primary-500 transition text-neutral-900 dark:text-white" />
                                </div>
                                <div class="space-y-2">
                                    <label class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                        t('confirmNewPassword') }}</label>
                                    <input v-model="confirmPassword" type="password"
                                        class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-100 dark:border-neutral-600 rounded-2xl px-6 py-4 font-bold outline-none focus:border-primary-500 transition text-neutral-900 dark:text-white" />
                                </div>
                            </div>

                            <div v-if="passwordError"
                                class="p-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-2xl font-bold">
                                {{ passwordError }}
                            </div>

                            <div v-if="passwordSuccess"
                                class="p-4 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-2xl font-bold">
                                {{ t('passwordChanged') }}
                            </div>

                            <button @click="changePassword"
                                :disabled="isSavingProfile || !currentPassword || !newPassword || !confirmPassword"
                                class="w-full py-4 bg-orange-600 text-white rounded-2xl font-bold hover:bg-orange-700 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
                                <RefreshCw v-if="isSavingProfile" :size="20" class="animate-spin" />
                                <Lock v-else :size="20" />
                                {{ t('updatePassword') }}
                            </button>
                        </div>
                    </div>

                    <!-- Category Management -->
                    <div
                        class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="p-3 rounded-2xl bg-purple-100 dark:bg-purple-900">
                                <component :is="LucideIcons.FolderOpen" :size="24"
                                    class="text-purple-600 dark:text-purple-400" stroke-width="2.5" />
                            </div>
                            <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ t('yourCategories') }}
                            </h2>
                        </div>

                        <!-- Add Category -->
                        <div class="flex gap-3 mb-6">
                            <input v-model="newCategoryName" type="text" :placeholder="t('newCategoryName')"
                                @keyup.enter="handleAddCategory"
                                class="flex-1 bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-100 dark:border-neutral-600 rounded-2xl px-6 py-4 font-bold outline-none focus:border-primary-500 transition text-neutral-900 dark:text-white" />
                            <button @click="handleAddCategory" :disabled="isSavingCategory || !newCategoryName.trim()"
                                class="px-6 py-4 bg-purple-600 text-white rounded-2xl font-bold hover:bg-purple-700 transition-all disabled:opacity-50 flex items-center gap-2">
                                <RefreshCw v-if="isSavingCategory" :size="20" class="animate-spin" />
                                <Plus v-else :size="20" />
                                {{ t('add') }}
                            </button>
                        </div>

                        <!-- Category List -->
                        <div class="space-y-3">
                            <div v-for="category in categories" :key="category.id"
                                class="flex items-center gap-4 p-4 bg-neutral-50 dark:bg-neutral-700 rounded-2xl">
                                <template v-if="editingCategory === category.id">
                                    <input v-model="editingCategoryName" type="text"
                                        class="flex-1 bg-white dark:bg-neutral-600 border-2 border-primary-500 rounded-xl px-4 py-2 font-bold outline-none text-neutral-900 dark:text-white"
                                        @keyup.enter="saveEditCategory(category.id)" />
                                    <button @click="saveEditCategory(category.id)"
                                        class="p-2 rounded-xl bg-green-500 text-white hover:bg-green-600 transition-all hover:scale-120">
                                        <Check :size="20" />
                                    </button>
                                    <button @click="cancelEditCategory"
                                        class="p-2 rounded-xl bg-neutral-300 dark:bg-neutral-500 text-neutral-700 dark:text-white hover:bg-neutral-400 transition-all hover:scale-120">
                                        <X :size="20" />
                                    </button>
                                </template>
                                <template v-else>
                                    <span class="flex-1 font-bold text-neutral-900 dark:text-white">{{ category.name
                                    }}</span>
                                    <button @click="startEditCategory(category)"
                                        class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                        <Pencil :size="18" class="text-neutral-400 hover:text-primary-500" />
                                    </button>
                                    <button @click="handleDeleteCategory(category.id)"
                                        :disabled="isDeletingCategory === category.id"
                                        class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                        <RefreshCw v-if="isDeletingCategory === category.id" :size="18"
                                            class="animate-spin text-neutral-400" />
                                        <Trash2 v-else :size="18" class="text-neutral-400 hover:text-red-500" />
                                    </button>
                                </template>
                            </div>

                            <div v-if="categories.length === 0" class="text-center py-8 text-neutral-400 font-medium">
                                {{ t('noCategories') }}
                            </div>
                        </div>
                    </div>

                    <!-- Tag Management -->
                    <div
                        class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="p-3 rounded-2xl bg-teal-100 dark:bg-teal-900">
                                <Tags :size="24" class="text-teal-600 dark:text-teal-400" stroke-width="2.5" />
                            </div>
                            <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ t('yourTags') }}</h2>
                        </div>

                        <!-- Add Tag -->
                        <div class="flex gap-3 mb-6">
                            <input v-model="newTagName" type="text" :placeholder="t('newTagName')"
                                @keyup.enter="handleAddTag"
                                class="flex-1 bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-100 dark:border-neutral-600 rounded-2xl px-6 py-4 font-bold outline-none focus:border-primary-500 transition text-neutral-900 dark:text-white" />
                            <div class="flex items-center gap-2 bg-neutral-50 dark:bg-neutral-700 rounded-2xl px-4">
                                <input v-model="newTagColor" type="color"
                                    class="w-10 h-10 rounded-xl cursor-pointer border-none bg-transparent" />
                            </div>
                            <button @click="handleAddTag" :disabled="isSavingTag || !newTagName.trim()"
                                class="px-6 py-4 bg-teal-600 text-white rounded-2xl font-bold hover:bg-teal-700 transition-all disabled:opacity-50 flex items-center gap-2">
                                <RefreshCw v-if="isSavingTag" :size="20" class="animate-spin" />
                                <Plus v-else :size="20" />
                                {{ t('add') }}
                            </button>
                        </div>

                        <!-- Tag List -->
                        <div class="space-y-3">
                            <div v-for="tag in tags" :key="tag.id"
                                class="flex items-center gap-4 p-4 bg-neutral-50 dark:bg-neutral-700 rounded-2xl">
                                <template v-if="editingTag === tag.id">
                                    <div class="w-6 h-6 rounded-full shrink-0"
                                        :style="{ backgroundColor: editingTagColor }"></div>
                                    <input v-model="editingTagName" type="text"
                                        class="flex-1 bg-white dark:bg-neutral-600 border-2 border-primary-500 rounded-xl px-4 py-2 font-bold outline-none text-neutral-900 dark:text-white"
                                        @keyup.enter="saveEditTag(tag.id)" />
                                    <input v-model="editingTagColor" type="color"
                                        class="w-10 h-10 rounded-xl cursor-pointer border-none bg-transparent" />
                                    <button @click="saveEditTag(tag.id)"
                                        class="p-2 rounded-xl bg-green-500 text-white hover:bg-green-600 transition-all hover:scale-120">
                                        <Check :size="20" />
                                    </button>
                                    <button @click="cancelEditTag"
                                        class="p-2 rounded-xl bg-neutral-300 dark:bg-neutral-500 text-neutral-700 dark:text-white hover:bg-neutral-400 transition-all hover:scale-120">
                                        <X :size="20" />
                                    </button>
                                </template>
                                <template v-else>
                                    <div class="w-6 h-6 rounded-full shrink-0" :style="{ backgroundColor: tag.color }">
                                    </div>
                                    <span class="flex-1 font-bold text-neutral-900 dark:text-white">{{ tag.name
                                        }}</span>
                                    <button @click="startEditTag(tag)"
                                        class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                        <Pencil :size="18" class="text-neutral-400 hover:text-primary-500" />
                                    </button>
                                    <button @click="handleDeleteTag(tag.id)" :disabled="isDeletingTag === tag.id"
                                        class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                        <RefreshCw v-if="isDeletingTag === tag.id" :size="18"
                                            class="animate-spin text-neutral-400" />
                                        <Trash2 v-else :size="18" class="text-neutral-400 hover:text-red-500" />
                                    </button>
                                </template>
                            </div>

                            <div v-if="tags.length === 0" class="text-center py-8 text-neutral-400 font-medium">
                                {{ t('noTags') }}
                            </div>
                        </div>
                    </div>

                    <!-- Manage Habits -->
                    <div
                        class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-2xl">
                                <CheckCircle2 :size="24" class="text-blue-600 dark:text-blue-400" stroke-width="2.5" />
                            </div>
                            <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ t('yourHabits') }}</h2>
                        </div>

                        <!-- Existing Habits -->
                        <div class="space-y-3">
                            <p class="text-xs font-black uppercase tracking-widest text-neutral-400 ml-2 mb-3">
                                Your Habits ({{ habits.length }})
                            </p>

                            <div v-if="habits.length === 0"
                                class="text-center py-8 text-neutral-400 dark:text-neutral-500">
                                No habits yet. Create your first habit using the "+ Add Habit" button at the top.
                            </div>

                            <div v-for="habit in habits" :key="habit.id"
                                class="flex items-center justify-between p-4 bg-neutral-50 dark:bg-neutral-700 rounded-2xl hover:shadow-md transition-all">
                                <div class="flex items-center gap-4 flex-1">
                                    <div class="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center"
                                        :style="{ backgroundColor: habit.color + '20' }">
                                        <component :is="getIcon(habit.icon)" :size="20" :style="{ color: habit.color }"
                                            stroke-width="2.5" />
                                    </div>
                                    <div class="flex-1">
                                        <p class="font-bold text-neutral-900 dark:text-white">{{ habit.name }}</p>
                                        <div class="flex flex-wrap gap-2 mt-1 items-center">
                                            <span
                                                class="text-xs px-2 py-1 rounded-full bg-neutral-200 dark:bg-neutral-600 text-neutral-700 dark:text-neutral-300 font-bold">
                                                {{ habit.habit_type }}
                                            </span>
                                            <span v-if="habit.category"
                                                class="text-xs px-2 py-1 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-bold">
                                                {{ habit.category.name }}
                                            </span>
                                            <!-- Tags -->
                                            <span v-for="tag in habit.tags" :key="tag.id"
                                                class="text-xs px-2 py-1 rounded-full font-bold flex items-center justify-center group min-w-8"
                                                :style="{
                                                    backgroundColor: tag.color + '20',
                                                    color: tag.color
                                                }">
                                                <span>{{ tag.name }}</span>
                                                <X :size="12" class="hidden group-hover:block ml-2 cursor-pointer"
                                                    @click.stop="removeTagFromHabit(habit.id, tag.id)" />
                                            </span>
                                            <!-- Add Tag Button -->
                                            <div class="relative">
                                                <button @click.stop="openTagSearch(habit.id)"
                                                    class="text-xs px-2 py-1 rounded-full bg-neutral-100 dark:bg-neutral-600 text-neutral-500 dark:text-neutral-400 font-bold hover:bg-neutral-200 dark:hover:bg-neutral-500 transition-colors flex items-center gap-1">
                                                    <Plus :size="12" />
                                                </button>
                                                <!-- Tag Search Dropdown -->
                                                <div v-if="addingTagToHabit === habit.id"
                                                    class="absolute top-full left-0 mt-1 w-48 bg-white dark:bg-neutral-700 rounded-xl shadow-lg border border-neutral-200 dark:border-neutral-600 z-20 overflow-hidden">
                                                    <input v-model="tagSearchQuery"
                                                        @input="updateFilteredTags(habit.id)" type="text"
                                                        :placeholder="t('searchTags')"
                                                        class="w-full px-3 py-2 text-sm bg-neutral-50 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-600 outline-none text-neutral-900 dark:text-white"
                                                        @click.stop />
                                                    <div class="max-h-32 overflow-y-auto">
                                                        <button v-for="tag in filteredTags" :key="tag.id"
                                                            @click.stop="addTagToHabit(habit.id, tag.id)"
                                                            class="w-full px-3 py-2 text-sm text-left hover:bg-neutral-100 dark:hover:bg-neutral-600 flex items-center gap-2 transition-colors">
                                                            <span class="w-3 h-3 rounded-full shrink-0"
                                                                :style="{ backgroundColor: tag.color }"></span>
                                                            <span class="text-neutral-900 dark:text-white">{{ tag.name
                                                            }}</span>
                                                        </button>
                                                        <div v-if="filteredTags.length === 0"
                                                            class="px-3 py-2 text-sm text-neutral-400 dark:text-neutral-500">
                                                            {{ t('noTagsFound') }}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="flex gap-2 ml-4">
                                    <button @click="startEditHabit(habit)" :title="t('editHabit')"
                                        class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                        <Pencil :size="18" class="text-neutral-400 hover:text-blue-500" />
                                    </button>
                                    <button @click="handleArchiveHabit(habit.id)" :title="t('archiveHabit')"
                                        class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                        <Archive :size="18" class="text-neutral-400 hover:text-primary-500" />
                                    </button>
                                    <button @click="handleDeleteActiveHabit(habit.id)"
                                        :title="t('deleteHabitPermanently')"
                                        class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                        <Trash2 :size="18" class="text-neutral-400 hover:text-red-500" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Archived Habits -->
                    <div
                        class="bg-white dark:bg-neutral-800 rounded-4xl p-8 shadow-lg border border-neutral-100 dark:border-neutral-700">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="p-3 rounded-2xl bg-amber-100 dark:bg-amber-900">
                                <Archive :size="24" class="text-amber-600 dark:text-amber-400" stroke-width="2.5" />
                            </div>
                            <h2 class="text-2xl font-black text-neutral-900 dark:text-white">{{ t('archivedHabits') }}
                            </h2>
                        </div>

                        <div class="space-y-4">
                            <div v-for="habit in archivedHabits" :key="habit.id"
                                class="flex items-center gap-2 p-4 bg-neutral-50 dark:bg-neutral-700 rounded-2xl">
                                <!-- Icon -->
                                <div class="p-3 rounded-xl" :style="{ backgroundColor: habit.color + '20' }">
                                    <component :is="getIcon(habit.icon)" :size="24" :style="{ color: habit.color }"
                                        stroke-width="2.5" />
                                </div>

                                <!-- Info -->
                                <div class="flex-1">
                                    <h4 class="font-bold text-neutral-900 dark:text-white">{{ habit.name }}</h4>
                                    <div class="flex flex-wrap gap-2 mt-1">
                                        <span
                                            class="text-xs px-2 py-1 rounded-full bg-neutral-200 dark:bg-neutral-600 text-neutral-700 dark:text-neutral-300 font-bold">
                                            {{ habit.habit_type }}
                                        </span>
                                        <span v-if="habit.category"
                                            class="text-xs px-2 py-1 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 font-bold">
                                            {{ habit.category.name }}
                                        </span>
                                        <!-- Tags -->
                                        <span v-for="tag in habit.tags" :key="tag.id"
                                            class="text-xs px-2 py-1 rounded-full font-bold" :style="{
                                                backgroundColor: tag.color + '20',
                                                color: tag.color
                                            }">
                                            {{ tag.name }}
                                        </span>
                                    </div>
                                </div>

                                <!-- Actions -->
                                <button @click="startEditHabit(habit)"
                                    class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120"
                                    :title="t('edit')">
                                    <Pencil :size="18" class="text-neutral-400 hover:text-blue-500" />
                                </button>
                                <button @click="handleUnarchive(habit.id)"
                                    class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120"
                                    :title="t('unarchive')">
                                    <ArchiveRestore :size="18" class="text-neutral-400 hover:text-green-500" />
                                </button>
                                <button @click="handleArchivedDelete(habit.id)" :title="t('deleteHabitPermanently')"
                                    class="p-2 rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all hover:scale-120">
                                    <Trash2 :size="18" class="text-neutral-400 hover:text-red-500" />
                                </button>
                            </div>

                            <div v-if="archivedHabits.length === 0"
                                class="text-center py-8 text-neutral-400 font-medium">
                                {{ t('noArchivedHabits') }}
                            </div>
                        </div>
                    </div>

                    <!-- Edit Habit Modal -->
                    <Teleport to="body">
                        <Transition name="fade">
                            <div v-if="editingHabit" class="fixed inset-0 z-50 flex items-center justify-center p-4">
                                <div class="absolute inset-0 bg-neutral-900/60 backdrop-blur-md"
                                    @click="cancelEditHabit"></div>
                                <div
                                    class="relative z-10 bg-white dark:bg-neutral-800 w-full max-w-lg rounded-4xl p-12 shadow-2xl overflow-hidden">
                                    <div class="absolute top-0 left-0 right-0 h-2 bg-blue-500"></div>

                                    <div class="flex justify-between items-center mb-10">
                                        <h2 class="text-3xl font-black text-neutral-900 dark:text-white">{{
                                            t('editHabit') }}
                                        </h2>
                                        <button @click="cancelEditHabit"
                                            class="text-neutral-300 hover:text-neutral-900 dark:hover:text-white transition">
                                            <X :size="32" />
                                        </button>
                                    </div>

                                    <form @submit.prevent="saveEditHabit" class="space-y-8">
                                        <div class="space-y-2">
                                            <label
                                                class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                                    t('habitName') || 'Habit Name' }}</label>
                                            <input v-model="editingHabitData.name" type="text" required
                                                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-lg text-neutral-900 dark:text-white" />
                                        </div>

                                        <IconPicker v-model="editingHabitData.icon" :label="t('icon') || 'Icon'" />

                                        <div class="space-y-2">
                                            <label
                                                class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                                    t('type') }}</label>
                                            <select v-model="editingHabitData.habit_type"
                                                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white appearance-none cursor-pointer">
                                                <option value="boolean">{{ t('typeBoolean') }}</option>
                                                <option value="counter">{{ t('typeCounter') }}</option>
                                                <option value="value">{{ t('typeValue') }}</option>
                                                <option value="rating">{{ t('typeRating') }}</option>
                                            </select>
                                        </div>

                                        <div class="space-y-2">
                                            <label
                                                class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                                    t('category') }}</label>
                                            <select v-model="editingHabitData.category"
                                                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white appearance-none cursor-pointer">
                                                <option :value="null">{{ t('noCategory') }}</option>
                                                <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{
                                                    cat.name }}
                                                </option>
                                            </select>
                                        </div>

                                        <div v-if="editingHabitData.habit_type === 'value'" class="space-y-2">
                                            <label
                                                class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                                    t('unit') }}</label>
                                            <input v-model="editingHabitData.unit" type="text"
                                                :placeholder="t('unitPlaceholder')"
                                                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-neutral-900 dark:text-white" />
                                        </div>

                                        <div v-if="editingHabitData.habit_type === 'rating'" class="space-y-2">
                                            <label
                                                class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                                    t('maxRating') }}</label>
                                            <input v-model.number="editingHabitData.max_value" type="number" min="1"
                                                max="10"
                                                class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 focus:bg-white dark:focus:bg-neutral-600 focus:border-primary-500 transition outline-none font-bold text-lg text-neutral-900 dark:text-white" />
                                        </div>

                                        <div class="space-y-2">
                                            <label
                                                class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">{{
                                                    t('color') }}</label>
                                            <div
                                                class="flex items-center gap-4 bg-neutral-50 dark:bg-neutral-700 p-4 rounded-3xl">
                                                <input v-model="editingHabitData.color" type="color"
                                                    class="w-16 h-10 rounded-2xl cursor-pointer border-none" />
                                                <span
                                                    class="font-mono text-sm text-neutral-600 dark:text-neutral-400">{{
                                                        editingHabitData.color
                                                    }}</span>
                                            </div>
                                        </div>

                                        <div class="flex gap-3">
                                            <button type="submit" :disabled="isSavingHabit"
                                                class="flex-1 bg-blue-600 text-white py-4 rounded-3xl font-black hover:bg-blue-700 transition-all shadow-xl disabled:opacity-50 flex items-center justify-center gap-2">
                                                <RefreshCw v-if="isSavingHabit" :size="20" class="animate-spin" />
                                                <Save v-else :size="20" stroke-width="2.5" />
                                                {{ isSavingHabit ? (t('saving')) : (t('save')) }}
                                            </button>
                                            <button type="button" @click="cancelEditHabit"
                                                class="flex-1 bg-neutral-300 dark:bg-neutral-600 text-neutral-700 dark:text-neutral-300 py-4 rounded-3xl font-black hover:bg-neutral-400 dark:hover:bg-neutral-500 transition-all">
                                                {{ t('cancel') }}
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </Transition>
                    </Teleport>
                </div>

                <!-- Footer -->
                <SiteFooter />
            </div>
        </div>
    </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
