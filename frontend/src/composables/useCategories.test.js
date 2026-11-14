import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('@/services/api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import api from '@/services/api'
import { useCategories } from './useCategories'
import { useCategoryDrag } from './useCategoryDrag'

const storage = new Map()
vi.stubGlobal('localStorage', {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
})

const { categoryOrder, fetchCategories, groupByCategory } = useCategories()

const HEALTH = { id: 1, name: 'Health', order: 0 }
const MIND = { id: 2, name: 'Mind', order: 1 }
const WORK = { id: 3, name: 'Work', order: 2 }

const habits = [
  { name: 'Run', category: HEALTH },
  { name: 'Read', category: MIND },
  { name: 'Vitamins', category: null },
  { name: 'Sleep', category: HEALTH },
]
const group = () =>
  groupByCategory(habits, (h) => h.category?.id ?? null, 'Other').map((g) => [g.name, g.habits.map((h) => h.name)])

describe('categories', () => {
  beforeEach(async () => {
    storage.clear()
    api.post.mockResolvedValue({})
    api.get.mockResolvedValue({ data: [MIND, WORK, HEALTH] })
    await fetchCategories()
  })

  it('sorts by server order and puts uncategorized last by default', () => {
    expect(categoryOrder.value).toEqual([1, 2, 3, 'uncategorized'])
  })

  it('groups habits, keeps their order and skips empty categories', () => {
    expect(group()).toEqual([
      ['Health', ['Run', 'Sleep']],
      ['Mind', ['Read']],
      ['Other', ['Vitamins']],
    ])
  })

  it('treats a habit with an unknown category as uncategorized', () => {
    const groups = groupByCategory([{ name: 'Ghost', category_id: 99 }], (h) => h.category_id, 'Other')
    expect(groups).toMatchObject([{ id: 'uncategorized', habits: [{ name: 'Ghost' }] }])
  })

  it('moveGroup reorders, saves to the server and remembers the uncategorized slot', async () => {
    const { moveGroup } = useCategoryDrag()

    moveGroup('uncategorized', 1) // move "Other" to the top

    expect(group().map(([name]) => name)).toEqual(['Other', 'Health', 'Mind'])
    expect(api.post).toHaveBeenCalledWith('categories/update_layout/', {
      layout: [{ id: 1, order: 0 }, { id: 2, order: 1 }, { id: 3, order: 2 }],
    })

    // After a reload the server knows nothing about "uncategorized"
    await fetchCategories()
    expect(categoryOrder.value[0]).toBe('uncategorized')
  })

  it('moveGroup ignores unknown or identical groups', () => {
    const { moveGroup } = useCategoryDrag()
    api.post.mockClear()

    moveGroup(1, 1)
    moveGroup(1, 42)
    moveGroup(null, 2)

    expect(categoryOrder.value).toEqual([1, 2, 3, 'uncategorized'])
    expect(api.post).not.toHaveBeenCalled()
  })
})
