<script setup>
import { TriangleAlert, CircleHelp } from 'lucide-vue-next'
import { useConfirm } from '@/composables/useConfirm'
import { useLanguage } from '@/composables/useLanguage'
import UiModal from './UiModal.vue'
import UiButton from './UiButton.vue'

const { state, settle } = useConfirm()
const { t } = useLanguage()
</script>

<template>
  <UiModal :open="state.open" :title="state.title || t('confirm')" :icon="state.danger ? TriangleAlert : CircleHelp"
    :tone="state.danger ? 'danger' : 'default'" size="sm" @close="settle(false)">
    <p class="text-sm leading-relaxed whitespace-pre-line text-ink-soft">{{ state.message }}</p>

    <template #footer>
      <UiButton variant="secondary" @click="settle(false)">{{ t('cancel') }}</UiButton>
      <UiButton :variant="state.danger ? 'danger' : 'primary'" @click="settle(true)">
        {{ state.confirmLabel || t('confirm') }}
      </UiButton>
    </template>
  </UiModal>
</template>
