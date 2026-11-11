/**
 * NIF português: 9 dígitos, o último é de controlo (módulo 11).
 * Espelha backend-api/core/validators/nif.py: mudar nos dois (os testes usam os mesmos valores).
 * Um número que não tenha 9 dígitos (depois de tirar espaços, pontos, hífenes e «PT») é estrangeiro e
 * não se verifica: o campo é facultativo e a loja vende também fora de Portugal.
 */

/** «PT 508.651.557» → «508651557». */
export const normalizeNif = (nif) =>
  String(nif ?? '')
    .replace(/[\s.-]/g, '')
    .replace(/^pt/i, '')

/** NIF português válido: 9 dígitos (o primeiro nunca é 0) e dígito de controlo certo. */
export function isValidNif(nif) {
  const digits = normalizeNif(nif)
  if (!/^[1-9]\d{8}$/.test(digits)) return false
  let total = 0
  for (let i = 0; i < 8; i += 1) total += Number(digits[i]) * (9 - i)
  const check = 11 - (total % 11)
  return Number(digits[8]) === (check >= 10 ? 0 : check)
}

export const NIF_ERROR = 'NIF inválido: o dígito de controlo não confere. Confira os 9 dígitos.'

/**
 * Texto de erro PT do campo NIF, ou '' se pode seguir: vazio e estrangeiro (que não tem 9 dígitos) passam;
 * um número com 9 dígitos tem de ser um NIF português válido, seja o tipo «empresa», «particular» ou nenhum.
 */
export function nifError(nif) {
  const digits = normalizeNif(nif)
  return /^\d{9}$/.test(digits) && !isValidNif(digits) ? NIF_ERROR : ''
}
