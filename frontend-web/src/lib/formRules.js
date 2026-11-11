/**
 * Regras dos formulários que o HTML não diz sozinho (FE-09): cada uma devolve a mensagem em português ou ''.
 * Servem a `useInlineValidation` (`{ nome: nameError }`) e dizem o mesmo que a API (core/validation_messages.py).
 * Campo vazio é «obrigatório» e fica ao cuidado do atributo `required`: aqui só se julga o que foi escrito.
 */

const MIN_NAME = 2

/** O nome só com espaços ou com 1 letra passava no navegador e a API recusava-o (mínimo de 2 caracteres). */
export function nameError(value) {
  const typed = String(value ?? '')
  if (!typed) return ''
  return typed.trim().length < MIN_NAME ? `O nome: mínimo de ${MIN_NAME} caracteres.` : ''
}

/** Regra «mínimo de N caracteres» para um campo com este nome («A mensagem»), sem contar espaços nas pontas. */
export const minLengthError = (label, min) => (value) => {
  const typed = String(value ?? '')
  return typed && typed.trim().length < min ? `${label}: mínimo de ${min} caracteres.` : ''
}
