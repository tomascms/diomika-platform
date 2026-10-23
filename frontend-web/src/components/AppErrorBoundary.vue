<script setup>
import { ref, onErrorCaptured } from 'vue'

const error = ref(null)

onErrorCaptured((err) => {
  error.value = err?.message || 'Ocorreu um erro inesperado.'
  return false
})

const retry = () => {
  error.value = null
  window.location.reload()
}
</script>

<template>
  <div v-if="error" class="error-boundary" role="alert">
    <div class="error-card surface-card">
      <h2>Algo correu mal</h2>
      <p>{{ error }}</p>
      <button type="button" class="btn btn-primary" @click="retry">Recarregar página</button>
    </div>
  </div>
  <slot v-else />
</template>

<style scoped>
.error-boundary {
  min-height: 50vh;
  display: grid;
  place-items: center;
  padding: 2rem;
}
.error-card {
  max-width: 420px;
  padding: 2rem;
  text-align: center;
}
.error-card h2 {
  margin: 0 0 0.75rem;
}
.error-card p {
  color: var(--color-muted);
  margin: 0 0 1.25rem;
}
</style>
