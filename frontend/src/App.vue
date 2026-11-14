<script setup>
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ToastHost from '@/components/ui/ToastHost.vue'
</script>

<template>
  <router-view />
  <ConfirmDialog />
  <ToastHost />
</template>
