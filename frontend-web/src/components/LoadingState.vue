<script setup>
defineProps({
  message: { type: String, default: 'A carregar…' },
})
</script>

<template>
  <div class="loading-state" role="status" aria-live="polite">
    <div class="spinner" aria-hidden="true" />
    <p>{{ message }}</p>
  </div>
</template>
