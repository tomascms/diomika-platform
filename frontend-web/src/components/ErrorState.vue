<script setup>
// O estado de uma página que não conseguiu os seus dados (FE-09), em vez de uma frase técnica e sem saída.
//  - `unavailable` (rede, servidor, erro desconhecido): «O nosso servidor não respondeu», «Tentar de novo»,
//    WhatsApp e telefone.
//  - `not-found` (o endereço já não existe): o título diz o que falta, sem «Tentar de novo» (não resolve) e com
//    uma saída (`back`: { to, label }), por exemplo a categoria.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import ContactAlternatives from '@/components/ContactAlternatives.vue'

const props = defineProps({
  kind: { type: String, default: 'unavailable' },
  title: { type: String, default: '' },
  text: { type: String, default: '' },
  back: { type: Object, default: null },
  whatsappText: { type: String, default: undefined },
})
defineEmits(['retry'])

const unavailable = computed(() => props.kind !== 'not-found')
const heading = computed(
  () =>
    props.title ||
    (unavailable.value ? 'O nosso servidor não respondeu' : 'Esta página já não está disponível'),
)
const body = computed(
  () =>
    props.text ||
    (unavailable.value
      ? 'Tente de novo daqui a pouco. Se precisar de ajuda já, fale connosco por WhatsApp ou telefone.'
      : ''),
)
</script>

<template>
  <div class="error-state surface-card" role="alert">
    <h2 class="error-state__title">{{ heading }}</h2>
    <p v-if="body" class="error-state__text">{{ body }}</p>
    <div class="error-state__actions">
      <button
        v-if="unavailable"
        type="button"
        class="btn btn-primary btn-sm"
        @click="$emit('retry')"
      >
        Tentar de novo
      </button>
      <RouterLink v-if="back" :to="back.to" class="btn btn-secondary btn-sm">{{
        back.label
      }}</RouterLink>
    </div>
    <ContactAlternatives
      v-if="unavailable"
      class="error-state__help"
      :whatsapp-text="whatsappText"
    />
  </div>
</template>

<style scoped>
.error-state {
  max-width: 560px;
  margin: 2rem auto;
  padding: 2rem 1.5rem;
  text-align: center;
}

.error-state__title {
  margin: 0 0 0.6rem;
  font-size: 1.35rem;
}

.error-state__text {
  margin: 0 0 1.25rem;
  color: var(--color-muted);
  line-height: 1.5;
}

.error-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.65rem;
}

.error-state__help {
  justify-content: center;
  margin-top: 0.85rem;
}
</style>
