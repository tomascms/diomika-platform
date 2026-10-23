<script setup>
import { whatsappUrl } from '@/lib/constants'
const props = defineProps({ text: { type: String, default: 'Olá! Gostaria de obter mais informações sobre o catálogo Diomika.' } })
</script>
<template>
  <a class="whatsapp-fab" :href="whatsappUrl(props.text)" target="_blank" rel="noopener noreferrer" aria-label="Falar com a Diomika no WhatsApp" title="Falar no WhatsApp">
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path fill="currentColor" d="M12 2a10 10 0 0 0-8.62 15.07L2 22l5.08-1.33A10 10 0 1 0 12 2Zm0 18a7.95 7.95 0 0 1-4.06-1.11l-.29-.17-3.01.79.8-2.93-.19-.3A8 8 0 1 1 12 20Zm4.38-5.37c-.24-.12-1.42-.7-1.64-.78-.22-.08-.38-.12-.54.12-.16.24-.62.78-.76.94-.14.16-.28.18-.52.06-.24-.12-1.01-.37-1.92-1.19-.71-.63-1.19-1.41-1.33-1.65-.14-.24-.02-.37.1-.49.11-.11.24-.28.36-.42.12-.14.16-.24.24-.4.08-.16.04-.3-.02-.42-.06-.12-.54-1.3-.74-1.78-.19-.47-.39-.4-.54-.41h-.46c-.16 0-.42.06-.64.3-.22.24-.84.82-.84 2s.86 2.32.98 2.48c.12.16 1.69 2.58 4.1 3.62.57.25 1.02.39 1.37.5.58.18 1.1.16 1.51.1.46-.07 1.42-.58 1.62-1.14.2-.56.2-1.04.14-1.14-.06-.1-.22-.16-.46-.28Z" />
    </svg>
  </a>
</template>
<style scoped>
.whatsapp-fab { position: fixed; right: 1.25rem; bottom: 1.25rem; z-index: 900; display: grid; place-items: center; width: 3.5rem; height: 3.5rem; border-radius: 50%; background: #25d366; color: #fff; box-shadow: var(--shadow-lg); text-decoration: none; transition: transform var(--transition), box-shadow var(--transition); }
.whatsapp-fab svg { width: 1.9rem; height: 1.9rem; }
.whatsapp-fab:hover { color: #fff; transform: translateY(-3px); box-shadow: 0 12px 28px rgba(37, 211, 102, 0.35); }
.whatsapp-fab:focus-visible { outline: 3px solid rgba(37, 211, 102, 0.35); outline-offset: 3px; }
@media print { .whatsapp-fab { display: none !important; } }
</style>
