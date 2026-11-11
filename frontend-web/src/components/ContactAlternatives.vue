<script setup>
// O que se oferece a quem não consegue usar o site (servidor parado, verificação anti-spam que falha): falar connosco.
// O telefone vai com o custo da chamada ao lado (DL 59/2021, art. 4.º), como em todo o site.
import { COMPANY, whatsappUrl } from '@/lib/constants'
import CallButton from '@/components/CallButton.vue'

defineProps({
  whatsappText: { type: String, default: 'Olá! Não consegui usar o site Diomika.' },
})
</script>

<template>
  <div class="alternatives">
    <a
      class="btn btn-secondary btn-sm"
      :href="whatsappUrl(whatsappText)"
      target="_blank"
      rel="noopener noreferrer"
      >Falar no WhatsApp</a
    >
    <CallButton class="btn btn-secondary btn-sm">Ligar {{ COMPANY.phoneDisplay }}</CallButton>
  </div>
</template>

<style scoped>
.alternatives {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.65rem;
}
</style>
