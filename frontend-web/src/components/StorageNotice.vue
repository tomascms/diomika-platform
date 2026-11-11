<script setup>
// Aviso quando o navegador não deixa guardar o pedido (FE-11): o pedido fica em memória e perde-se ao fechar ou
// recarregar a página. Só aparece depois de uma tentativa de guardar que falhou.
import { RouterLink } from 'vue-router'
import { useCart } from '@/composables/useCart'
import { whatsappUrl } from '@/lib/constants'

const { storageBlocked } = useCart()
</script>

<template>
  <p v-if="storageBlocked" class="alert alert-info storage-notice" role="status">
    O seu navegador está a bloquear o armazenamento do site: o pedido só se mantém enquanto não
    fechar nem recarregar a página. Envie-o já, ou fale connosco por
    <a
      :href="whatsappUrl('Olá! Gostaria de pedir um orçamento.')"
      target="_blank"
      rel="noopener noreferrer"
      >WhatsApp</a
    >
    ou pelo <RouterLink to="/contacto">formulário de contacto</RouterLink>.
  </p>
</template>
