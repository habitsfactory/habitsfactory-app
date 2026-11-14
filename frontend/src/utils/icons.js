import { shallowRef, computed } from 'vue'
import { CalendarCheck } from 'lucide-vue-next'

// Habits can use any Lucide icon, so the whole set is needed — but it is
// loaded on demand, in a separate chunk, the first time an icon is shown.
const library = shallowRef(null)
let pending = null

const NON_ICONS = new Set(['Icon', 'icons', 'createLucideIcon', 'default'])

const isIcon = (key) =>
  /^[A-Z]/.test(key) &&
  !NON_ICONS.has(key) &&
  // lucide exports every icon three times (Foo, FooIcon, LucideFoo)
  !key.startsWith('Lucide') &&
  !key.endsWith('Icon')

const toPascalCase = (name) =>
  name
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join('')

/** Start loading the icon set (idempotent). */
export const loadIcons = () => {
  pending ??= import('./lucide-all.js')
    .then((module) => { library.value = module })
    .catch(() => { pending = null }) // allow a retry on the next call
  return pending
}

/** True once the icon set is available. */
export const iconsReady = computed(() => library.value !== null)

/** Every icon name available in the picker (PascalCase, sorted). Empty until loaded. */
export const iconNames = computed(() =>
  library.value ? Object.keys(library.value).filter(isIcon).sort() : []
)

/**
 * Resolve a stored icon name to a Lucide component.
 * Accepts both formats found in the database: "book-open" and "BookOpen".
 * Reactive: returns null while the icon set is still loading.
 */
export const resolveIcon = (name, fallback = CalendarCheck) => {
  if (!name) return fallback
  const icons = library.value
  if (!icons) return null
  if (isIcon(name) && icons[name]) return icons[name]
  const pascal = toPascalCase(name)
  return (isIcon(pascal) && icons[pascal]) || fallback
}
