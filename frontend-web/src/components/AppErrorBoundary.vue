<script setup>
import { ref, onErrorCaptured } from 'vue'
import ErrorState from '@/components/ErrorState.vue'

const failed = ref(false)

// A mensagem técnica do erro («Cannot read properties of undefined…») fica na consola, não no ecrã (FE-09).
onErrorCaptured((err) => {
  console.error('[Diomika]', err)
  failed.value = true
  return false
})

const retry = () => {
  failed.value = false
  window.location.reload()
}
</script>

<template>
  <div v-if="failed" class="error-boundary">
    <ErrorState
      title="Algo correu mal"
      text="Ocorreu um erro inesperado nesta página. Tente de novo; se continuar, fale connosco por WhatsApp ou telefone."
      @retry="retry"
    />
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
</style>
