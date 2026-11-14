// composables/useCategoryDrag.js
// Drag & drop reordering of category groups (shared by Tracking and Summary).
import { ref } from 'vue'
import { useCategories } from '@/composables/useCategories'

export function useCategoryDrag() {
    const { categoryOrder, saveLayoutToServer } = useCategories()

    const draggedId = ref(null)
    const dragOverId = ref(null)

    const reset = () => {
        draggedId.value = null
        dragOverId.value = null
    }

    const onDragStart = (event, groupId) => {
        draggedId.value = groupId
        event.dataTransfer.effectAllowed = 'move'
        // Firefox needs data to be set for the drag to start
        event.dataTransfer.setData('text/plain', String(groupId))
    }

    const onDragOver = (event, groupId) => {
        if (draggedId.value === null) return
        event.preventDefault()
        event.dataTransfer.dropEffect = 'move'
        dragOverId.value = groupId
    }

    // Put the source group where the target group is (the target shifts over)
    const moveGroup = (sourceId, targetId) => {
        if (sourceId === null || sourceId === targetId) return
        const order = [...categoryOrder.value]
        const from = order.indexOf(sourceId)
        const to = order.indexOf(targetId)
        if (from === -1 || to === -1) return
        order.splice(from, 1)
        order.splice(to, 0, sourceId)
        categoryOrder.value = order
        saveLayoutToServer()
    }

    const onDrop = (event, targetId) => {
        event.preventDefault()
        moveGroup(draggedId.value, targetId)
        reset()
    }

    // `moveGroup` backs the up/down buttons: native drag & drop does not
    // exist on touch screens and is not keyboard accessible.
    return { draggedId, dragOverId, onDragStart, onDragOver, onDrop, onDragEnd: reset, moveGroup }
}
