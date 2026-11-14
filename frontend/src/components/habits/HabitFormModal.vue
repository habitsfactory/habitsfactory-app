<script setup>
// Create / edit form for a habit. Pass `habit` to edit, leave it null to create.
// Emits `save` with a payload ready for the API.
import { reactive, computed, watch } from 'vue'
import { ToggleRight, Hash, Ruler, Star, Percent, Plus, Save, PenLine } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import { useCategories } from '@/composables/useCategories'
import UiModal from '@/components/ui/UiModal.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiInput from '@/components/ui/UiInput.vue'
import UiSelect from '@/components/ui/UiSelect.vue'
import UiColorField from '@/components/ui/UiColorField.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import IconPicker from '@/components/IconPicker.vue'
import { labelClass } from '@/components/ui/styles'

const props = defineProps({
  open: Boolean,
  habit: { type: Object, default: null },
  saving: Boolean,
  error: { type: String, default: '' },
})

const emit = defineEmits(['close', 'save'])

const { t } = useLanguage()
const { categories } = useCategories()

const isEditing = computed(() => !!props.habit)

const blank = () => ({
  name: '',
  habit_type: 'boolean',
  icon: 'calendar-check',
  color: '#1490c9',
  category_id: null,
  unit: '',
  max_value: 5,
})

const form = reactive(blank())

// (Re)initialise the form each time the dialog opens
watch(() => props.open, (open) => {
  if (!open) return
  const habit = props.habit
  Object.assign(form, habit
    ? {
      name: habit.name,
      habit_type: habit.habit_type,
      icon: habit.icon || 'calendar-check',
      color: habit.color || '#1490c9',
      category_id: habit.category?.id ?? null,
      unit: habit.unit || '',
      max_value: habit.max_value || 5,
    }
    : blank())
})

const types = computed(() => [
  { value: 'boolean', icon: ToggleRight, label: t('boolean'), description: t('booleanDesc') },
  { value: 'counter', icon: Hash, label: t('counter'), description: t('counterDesc') },
  { value: 'value', icon: Ruler, label: t('value'), description: t('valueDesc') },
  { value: 'rating', icon: Star, label: t('rating'), description: t('ratingDesc') },
  { value: 'percentage', icon: Percent, label: t('percentage'), description: t('percentageDesc') },
])

const hasUnit = computed(() => form.habit_type === 'counter' || form.habit_type === 'value')

const submit = () => {
  const isRating = form.habit_type === 'rating'
  emit('save', {
    name: form.name.trim(),
    habit_type: form.habit_type,
    icon: form.icon,
    color: form.color,
    category_id: form.category_id,
    unit: (hasUnit.value && form.unit.trim()) || null,
    max_value: isRating ? Math.min(10, Math.max(1, Number(form.max_value) || 5)) : null,
  })
}
</script>

<template>
  <UiModal :open="open" :title="isEditing ? t('editHabit') : t('newHabit')" :icon="isEditing ? PenLine : Plus"
    :busy="saving" @close="emit('close')">
    <form id="habit-form" class="space-y-5" @submit.prevent="submit">
      <UiAlert v-if="error">{{ error }}</UiAlert>

      <UiInput v-model="form.name" :label="t('habitName')" :placeholder="t('habitNamePlaceholder')" required
        maxlength="100" />

      <div>
        <span :class="labelClass">{{ t('metricType') }}</span>
        <div class="grid grid-cols-2 gap-2" role="radiogroup">
          <button v-for="type in types" :key="type.value" type="button" role="radio"
            :aria-checked="form.habit_type === type.value" :class="[
              'flex items-start gap-2.5 rounded-xl border p-3 text-left transition-colors last:odd:col-span-2',
              form.habit_type === type.value
                ? 'border-primary-500 bg-primary-500/10 ring-1 ring-primary-500'
                : 'border-line hover:border-line-strong hover:bg-sunken/60',
            ]" @click="form.habit_type = type.value">
            <component :is="type.icon" :size="18" stroke-width="2.25" :class="[
              'mt-0.5 shrink-0',
              form.habit_type === type.value ? 'text-primary-600 dark:text-primary-400' : 'text-ink-faint',
            ]" />
            <span class="min-w-0">
              <span class="block text-sm font-semibold text-ink">{{ type.label }}</span>
              <span class="block text-xs text-ink-soft">{{ type.description }}</span>
            </span>
          </button>
        </div>
      </div>

      <UiInput v-if="hasUnit" v-model="form.unit" :label="t('habitUnit')" :placeholder="t('unitPlaceholder')"
        maxlength="30" />

      <UiInput v-if="form.habit_type === 'rating'" v-model.number="form.max_value" type="number" min="1" max="10"
        :label="t('numberOfStars')" :hint="t('starsHint')" />

      <IconPicker v-model="form.icon" :label="t('visualIcon')" />

      <UiColorField v-model="form.color" :label="t('identityColor')" />

      <UiSelect v-model="form.category_id" :label="t('category')">
        <option :value="null">{{ t('uncategorized') }}</option>
        <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
      </UiSelect>
    </form>

    <template #footer>
      <UiButton variant="secondary" :disabled="saving" @click="emit('close')">{{ t('cancel') }}</UiButton>
      <UiButton type="submit" form="habit-form" :icon="isEditing ? Save : Plus" :loading="saving">
        {{ isEditing ? t('save') : t('initiateHabit') }}
      </UiButton>
    </template>
  </UiModal>
</template>
