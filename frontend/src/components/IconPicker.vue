<script setup>
import { ref, computed, nextTick } from 'vue'
import { ChevronDown, Search, LoaderCircle } from 'lucide-vue-next'
import { useLanguage } from '@/composables/useLanguage'
import { iconNames, iconsReady, resolveIcon, loadIcons } from '@/utils/icons'
import { inputClass, inputBaseClass, labelClass } from '@/components/ui/styles'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useLanguage()

loadIcons()

const isOpen = ref(false)
const searchQuery = ref('')
const searchInput = ref(null)

// Rendering ~1500 icons at once is slow; show the first matches only.
const MAX_RESULTS = 96

const filteredIcons = computed(() => {
  const query = searchQuery.value.trim().toLowerCase().replace(/[\s-]+/g, '')
  const names = iconNames.value
  const matches = query ? names.filter((name) => name.toLowerCase().includes(query)) : names
  return matches.slice(0, MAX_RESULTS)
})

const selectedIcon = computed(() => (props.modelValue ? resolveIcon(props.modelValue) : null))

// Stored names can be "book-open" or "BookOpen" — compare them loosely
const normalize = (name) => (name || '').toLowerCase().replace(/[\s_-]+/g, '')
const isSelected = (name) => normalize(name) === normalize(props.modelValue)

const toggle = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) nextTick(() => searchInput.value?.focus())
}

const select = (name) => {
  emit('update:modelValue', name)
  isOpen.value = false
  searchQuery.value = ''
}
</script>

<template>
  <div>
    <span v-if="label" :class="labelClass">{{ label }}</span>

    <button type="button" :aria-expanded="isOpen"
      :class="[inputClass, 'flex items-center gap-3 text-left', isOpen && 'border-primary-500 ring-3 ring-primary-500/20']"
      @click="toggle">
      <component :is="selectedIcon" v-if="selectedIcon" :size="20" stroke-width="2.25"
        class="shrink-0 text-primary-600 dark:text-primary-400" />
      <span class="min-w-0 flex-1 truncate" :class="modelValue ? '' : 'text-ink-faint'">
        {{ modelValue || t('selectIcon') }}
      </span>
      <ChevronDown :size="18" class="shrink-0 text-ink-faint transition-transform" :class="isOpen && 'rotate-180'" />
    </button>

    <div v-if="isOpen" class="mt-2 rounded-xl border border-line bg-sunken/50 p-3">
      <div class="relative">
        <Search :size="16" class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-faint" />
        <input ref="searchInput" v-model="searchQuery" type="search" :placeholder="t('searchIcons')"
          :class="[inputBaseClass, 'h-10 pl-9']" @keydown.enter.prevent @keydown.esc.stop="isOpen = false" />
      </div>

      <div class="mt-3 grid max-h-52 grid-cols-6 gap-1 overflow-y-auto pr-1 sm:grid-cols-8">
        <button v-for="name in filteredIcons" :key="name" type="button" :title="name" :aria-label="name"
          :aria-pressed="isSelected(name)" :class="[
            'inline-flex aspect-square items-center justify-center rounded-lg transition-colors',
            isSelected(name)
              ? 'bg-primary-600 text-white'
              : 'text-ink-soft hover:bg-surface hover:text-ink',
          ]" @click="select(name)">
          <component :is="resolveIcon(name)" :size="20" stroke-width="2" />
        </button>
      </div>

      <div v-if="!iconsReady" class="flex justify-center py-6 text-primary-500">
        <LoaderCircle :size="22" class="animate-spin" />
      </div>
      <p v-else-if="filteredIcons.length === 0" class="py-6 text-center text-sm text-ink-faint">
        {{ t('noIconsFound') }}
      </p>
    </div>
  </div>
</template>
