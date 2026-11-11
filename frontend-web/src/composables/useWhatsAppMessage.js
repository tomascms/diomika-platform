import { ref } from 'vue'

/**
 * O texto que o botão do WhatsApp (flutuante, em todas as páginas) leva quando a página sabe mais do que o texto geral:
 * a de um modelo põe aqui o modelo, a cor, a medida e o EAN escolhidos (RP-13). Vazio = o texto de sempre.
 */
const message = ref('')

export function useWhatsAppMessage() {
  return {
    message,
    set: (text) => (message.value = text),
    clear: () => (message.value = ''),
  }
}
