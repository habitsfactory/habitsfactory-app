// Shared Tailwind class strings for form controls, so native inputs/selects
// look identical wherever they are rendered.

// Without a height, for compact variants (pair it with an h-* class)
export const inputBaseClass =
  'w-full rounded-xl border border-line bg-surface px-3.5 text-sm text-ink ' +
  'placeholder:text-ink-faint transition-colors hover:border-line-strong ' +
  'focus:border-primary-500 focus:ring-3 focus:ring-primary-500/20 focus:outline-none ' +
  'disabled:cursor-not-allowed disabled:opacity-60'

export const inputClass = inputBaseClass + ' h-11'

export const labelClass =
  'mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink-soft'

export const hintClass = 'mt-1.5 block text-xs text-ink-faint'
