import { nextTick, ref } from 'vue'

/**
 * Erros junto ao campo (WCAG 3.3.1): em vez da bolha do navegador, que desaparece em segundos, cada campo
 * inválido leva uma mensagem em português por baixo, `aria-invalid` e `aria-describedby`, e o primeiro
 * recebe o foco. As regras são as do próprio HTML (required, minlength, type="email", pattern) e, para o
 * que o HTML não diz, uma função por id de campo que devolve o erro ou '' (ex.: `{ nif: nifError }`).
 *
 * Uso: `<form ref="formRef" novalidate @submit.prevent="submit" @input="clear($event.target.id)">`; em cada
 * campo `v-bind="attrs('nome')"` e `<p v-if="errors.nome" id="nome-erro" class="field-error">`. O texto de um
 * `pattern` ou `type="email"` inválido vem de `data-erro` no campo.
 */
export function useInlineValidation(rules = {}) {
  const formRef = ref(null)
  const errors = ref({})

  const nameOf = (el) =>
    (el.labels?.[0]?.textContent || el.name || el.id).replace(/\(opcional\)|\*/g, '').trim()

  const messageFor = (el) => {
    const { validity } = el
    if (validity.customError) return el.validationMessage
    if (validity.valueMissing) return `Preencha «${nameOf(el)}».`
    if (validity.tooShort) return `«${nameOf(el)}» deve ter pelo menos ${el.minLength} caracteres.`
    if (validity.typeMismatch || validity.patternMismatch) {
      return el.dataset.erro || `Confira «${nameOf(el)}».`
    }
    return el.validationMessage
  }

  /** Mostra os erros dados (id do campo → texto) e põe o foco no primeiro campo com erro. */
  const showErrors = async (next) => {
    errors.value = next
    const first = Object.keys(next).find((id) => document.getElementById(id))
    if (!first) return
    await nextTick()
    document.getElementById(first).focus()
  }

  /** Verifica o formulário todo; devolve true se pode seguir. */
  const validate = async () => {
    const next = {}
    for (const el of formRef.value?.elements ?? []) {
      if (!el.willValidate || !el.id) continue
      if (rules[el.id]) el.setCustomValidity(rules[el.id](el.value))
      if (!el.checkValidity()) next[el.id] = messageFor(el)
    }
    await showErrors(next)
    return Object.keys(next).length === 0
  }

  /**
   * O envio falhou: o que a API recusou num campo do formulário (422, `err.fields`) mostra-se junto ao campo e o
   * foco vai para o primeiro. Devolve o texto para o aviso do formulário: o que não é de nenhum campo, ou a
   * mensagem do erro quando a API não disse nada por campo.
   */
  const showSubmitError = async (err, fallback) => {
    const fields = err?.fields ?? {}
    if (!Object.keys(fields).length) return err?.message || fallback
    const mine = {}
    const rest = []
    for (const [name, message] of Object.entries(fields)) {
      const el = formRef.value?.elements.namedItem(name)
      if (el?.id === name) mine[name] = message
      else rest.push(message)
    }
    await showErrors(mine)
    return rest.join(' · ') || 'Corrija os campos assinalados e envie de novo.'
  }

  /** O visitante corrigiu o campo: o erro sai logo, sem esperar pelo envio. */
  const clear = (id) => {
    if (errors.value[id]) errors.value = { ...errors.value, [id]: undefined }
  }

  const attrs = (id) =>
    errors.value[id] ? { 'aria-invalid': 'true', 'aria-describedby': `${id}-erro` } : {}

  return { formRef, errors, validate, clear, attrs, showSubmitError }
}
