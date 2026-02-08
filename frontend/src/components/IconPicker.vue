<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import * as LucideIcons from 'lucide-vue-next'
import { ChevronDown } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: 'Icon'
  }
})

const emit = defineEmits(['update:modelValue'])

const isPickerOpen = ref(false)
const searchQuery = ref('')
const toggleButton = ref(null)
const dropdown = ref(null)
const searchInput = ref(null)
const dropdownStyle = ref({})

// Get all available Lucide icon names
const allIcons = computed(() => {
  // Filter out non-icon exports
  const excluded = ['createElement', 'createIcons', 'default', 'icons', 'Icon', 'createLucideIcon']
  return Object.keys(LucideIcons)
    .filter(key => {
      if (excluded.includes(key)) return false
      if (key[0] !== key[0].toUpperCase()) return false
      // Ensure it's a valid component (object or function)
      const component = LucideIcons[key]
      return component && (typeof component === 'object' || typeof component === 'function')
    })
    .sort()
})

// Filter icons based on search query (limited to 100 for performance)
const filteredIcons = computed(() => {
  let icons = allIcons.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    icons = icons.filter(iconName => iconName.toLowerCase().includes(query))
  }

  return icons.slice(0, 100)
})

// Get the component for a given icon name
const getIconComponent = (iconName) => {
  const component = LucideIcons[iconName]
  if (component && (typeof component === 'object' || typeof component === 'function')) {
    return component
  }
  return null
}

// Get the currently selected icon component
const selectedIconComponent = computed(() => {
  if (!props.modelValue) return null

  // Try exact match first
  if (LucideIcons[props.modelValue]) {
    return LucideIcons[props.modelValue]
  }

  // Try with capitalized first letter
  const capitalized = props.modelValue.charAt(0).toUpperCase() + props.modelValue.slice(1)
  if (LucideIcons[capitalized]) {
    return LucideIcons[capitalized]
  }

  return null
})

// Calculate dropdown position
const updateDropdownPosition = () => {
  if (!toggleButton.value) return

  const rect = toggleButton.value.getBoundingClientRect()
  const viewportHeight = window.innerHeight
  const dropdownHeight = 384 // max-h-96 = 384px

  // Check if there's enough space below
  const spaceBelow = viewportHeight - rect.bottom
  const spaceAbove = rect.top

  if (spaceBelow >= dropdownHeight || spaceBelow >= spaceAbove) {
    // Position below
    dropdownStyle.value = {
      top: `${rect.bottom + 8}px`,
      left: `${rect.left}px`,
      width: `${rect.width}px`
    }
  } else {
    // Position above
    dropdownStyle.value = {
      bottom: `${viewportHeight - rect.top + 8}px`,
      left: `${rect.left}px`,
      width: `${rect.width}px`
    }
  }
}

// Toggle picker
const togglePicker = () => {
  isPickerOpen.value = !isPickerOpen.value
  if (isPickerOpen.value) {
    nextTick(() => {
      updateDropdownPosition()
      searchInput.value?.focus()
    })
  }
}

// Select an icon
const selectIcon = (iconName) => {
  emit('update:modelValue', iconName)
  isPickerOpen.value = false
  searchQuery.value = ''
}

// Handle click outside
const handleClickOutside = (event) => {
  if (!isPickerOpen.value) return

  if (
    dropdown.value &&
    !dropdown.value.contains(event.target) &&
    toggleButton.value &&
    !toggleButton.value.contains(event.target)
  ) {
    isPickerOpen.value = false
    searchQuery.value = ''
  }
}

// Handle escape key
const handleEscape = (event) => {
  if (event.key === 'Escape' && isPickerOpen.value) {
    isPickerOpen.value = false
    searchQuery.value = ''
  }
}

// Lifecycle
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <div class="space-y-2 relative">
    <label class="text-[10px] font-black uppercase tracking-widest text-neutral-400 ml-2">
      {{ label }}
    </label>

    <!-- Selected Icon Display & Button -->
    <button ref="toggleButton" type="button" @click="togglePicker"
      class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-3xl px-6 py-4 font-bold outline-none text-neutral-900 dark:text-white hover:border-primary-500 transition-colors flex items-center justify-between">
      <div class="flex items-center gap-3">
        <component v-if="selectedIconComponent" :is="selectedIconComponent" :size="24" class="text-primary-600" />
        <span>{{ modelValue || 'Select an icon' }}</span>
      </div>
      <ChevronDown :size="20" :class="{ 'rotate-180': isPickerOpen }" class="transition-transform" />
    </button>

    <!-- Icon Picker Dropdown - Teleported to body -->
    <Teleport to="body">
      <div v-if="isPickerOpen" ref="dropdown" @click.stop :style="dropdownStyle"
        class="fixed z-9999 bg-white dark:bg-neutral-800 border-2 border-neutral-200 dark:border-neutral-700 rounded-3xl p-6 shadow-2xl max-h-96 overflow-hidden flex flex-col animate-in fade-in duration-200">
        <!-- Search Input -->
        <div class="mb-4">
          <input ref="searchInput" v-model="searchQuery" type="text" placeholder="Search icons..."
            class="w-full bg-neutral-50 dark:bg-neutral-700 border-2 border-neutral-50 dark:border-neutral-700 rounded-2xl px-4 py-3 font-bold text-neutral-900 dark:text-white focus:border-primary-500 transition outline-none" />
        </div>

        <!-- Icons Grid -->
        <div class="overflow-y-auto flex-1 -mx-2">
          <div class="grid grid-cols-6 gap-2 px-2">
            <button v-for="iconName in filteredIcons" :key="iconName" type="button" @click="selectIcon(iconName)"
              :class="[
                'flex flex-col items-center justify-center p-3 rounded-xl hover:bg-primary-50 dark:hover:bg-primary-900/30 transition-colors border-2',
                modelValue === iconName
                  ? 'bg-primary-100 dark:bg-primary-900/50 border-primary-500'
                  : 'border-transparent'
              ]" :title="iconName">
              <component v-if="getIconComponent(iconName)" :is="getIconComponent(iconName)" :size="24"
                class="text-neutral-700 dark:text-neutral-300" />
              <span class="text-[8px] mt-1 text-neutral-500 dark:text-neutral-400 truncate w-full text-center">
                {{ iconName }}
              </span>
            </button>
          </div>

          <!-- No Results Message -->
          <div v-if="filteredIcons.length === 0" class="text-center py-8 text-neutral-400">
            No icons found
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>


<style scoped>
/* Custom scrollbar */
.overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #d6d3d1;
  border-radius: 4px;
}

.dark .overflow-y-auto::-webkit-scrollbar-thumb {
  background: #57534e;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #a8a29e;
}

.dark .overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #92400e;
}
</style>
