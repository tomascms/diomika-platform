<script setup>
// Pedido rápido por EAN (RP-14): quem já conhece as referências cola uma linha por artigo, «EAN; cor; quantidade», e
// junta tudo ao pedido de uma vez. Cada EAN é procurado no catálogo (a pesquisa já encontra por EAN) e a linha do
// pedido é a mesma que a ficha do produto junta; o que não puder ser junto fica no campo, com o motivo, para corrigir.
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { useCart } from '@/composables/useCart'
import { useCatalog } from '@/composables/useCatalog'
import { PLACEHOLDER, resolveImageUrls } from '@/lib/images'
import { findByEan, MAX_QUOTE_LINES, parseQuickOrder, resolveQuickLine } from '@/lib/quickOrder'
import { itemKey } from '@/lib/quoteLines'

const cart = useCart()
const catalog = useCatalog()
const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Pedido rápido' }]
const EXAMPLE = '5606044506574; 12; 240\n5606044506598; 12; 120'
const LOOKUP_ERROR = 'Não foi possível consultar o catálogo agora. Tente de novo daqui a pouco.'

const text = ref('')
const busy = ref(false)
const results = ref([]) // por linha: { n, raw, ok, text, notice }
const added = computed(() => results.value.filter((r) => r.ok).length)

/** Procura cada EAN no catálogo, quatro de cada vez (um pedido por EAN; a loja guarda as respostas em cache). */
async function lookup(eans) {
  const found = new Map()
  const pending = [...eans]
  const worker = async () => {
    while (pending.length) {
      const ean = pending.shift()
      try {
        found.set(ean, { match: findByEan(ean, await catalog.searchCatalog(ean, { limit: 5 })) })
      } catch {
        found.set(ean, { failed: true })
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, pending.length) }, worker))
  return found
}

async function submit() {
  if (busy.value) return
  busy.value = true
  results.value = []
  try {
    const { rows, errors } = parseQuickOrder(text.value)
    const looked = await lookup([...new Set(rows.map((row) => row.ean))])
    const done = errors.map(({ n, raw, message }) => ({ n, raw, ok: false, text: message }))

    for (const row of rows) {
      const entry = looked.get(row.ean)
      const result = entry.failed
        ? { ok: false, message: LOOKUP_ERROR }
        : resolveQuickLine(row, entry.match)
      if (!result.ok) {
        done.push({ n: row.n, raw: row.raw, ok: false, text: result.message })
        continue
      }
      const current = cart.getItems()
      if (
        current.length >= MAX_QUOTE_LINES &&
        !current.some((line) => itemKey(line) === itemKey(result.item))
      ) {
        done.push({
          n: row.n,
          raw: row.raw,
          ok: false,
          text: `O pedido tem, no máximo, ${MAX_QUOTE_LINES} artigos.`,
        })
        continue
      }
      const [image] = await resolveImageUrls([result.color.imagem], PLACEHOLDER)
      cart.addItem({ ...result.item, imagem: image })
      done.push({ n: row.n, raw: row.raw, ok: true, text: result.label, notice: result.notice })
    }

    results.value = done.sort((a, b) => a.n - b.n)
    // O que ficou por juntar fica no campo, para corrigir e tentar de novo (juntar duas vezes o mesmo artigo não o duplica).
    text.value = results.value
      .filter((r) => !r.ok)
      .map((r) => r.raw)
      .join('\n')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="quick-order">
    <Breadcrumbs :items="breadcrumbItems" />
    <div class="page-shell">
      <header class="page-header">
        <h1 class="page-title">Pedido rápido por EAN</h1>
        <p class="page-lead">
          Já conhece as referências? Escreva ou cole uma linha por artigo e junte tudo ao pedido de
          orçamento de uma vez.
        </p>
      </header>

      <form
        class="surface-card surface-card--elevated quick-form"
        novalidate
        @submit.prevent="submit"
      >
        <label class="field-label" for="quick-lines"
          >Artigos, um por linha: EAN; cor; quantidade</label
        >
        <textarea
          id="quick-lines"
          v-model="text"
          class="field-textarea quick-lines"
          rows="8"
          spellcheck="false"
          autocomplete="off"
          :placeholder="EXAMPLE"
          aria-describedby="quick-help"
        />
        <p id="quick-help" class="form-hint">
          A cor é o número da cor (por exemplo, 12) e pode faltar nos artigos de uma só cor. Pode
          colar de uma folha de cálculo, com o EAN, a cor e a quantidade em colunas. As quantidades
          seguem o mínimo e os múltiplos de cada categoria: se uma não cumprir, ajustamo-la e
          dizemos-lhe.
        </p>
        <div class="quick-actions">
          <button type="submit" class="btn btn-primary" :disabled="busy || !text.trim()">
            {{ busy ? 'A juntar…' : 'Juntar ao pedido' }}
          </button>
          <RouterLink to="/categorias" class="btn btn-secondary">Ver o catálogo</RouterLink>
        </div>
      </form>

      <section v-if="results.length" class="quick-results" aria-live="polite">
        <p v-if="added" class="alert alert-success quick-summary">
          {{ added === 1 ? '1 artigo junto' : `${added} artigos juntos` }} ao pedido.
          <RouterLink to="/carrinho">Ver pedido</RouterLink>
        </p>
        <p v-if="added < results.length" class="alert alert-error">
          {{
            results.length - added === 1
              ? '1 linha não foi junta'
              : `${results.length - added} linhas não foram juntas`
          }}: ficam no campo acima, para corrigir.
        </p>
        <ul class="result-list">
          <li v-for="r in results" :key="r.n" :class="r.ok ? 'is-ok' : 'is-error'">
            <template v-if="r.ok">
              <strong>Junto:</strong> {{ r.text }}
              <span v-if="r.notice" class="result-notice">{{ r.notice }}</span>
            </template>
            <template v-else>
              <strong>Linha {{ r.n }}, não junta:</strong> {{ r.text }}
            </template>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.quick-order {
  background: var(--color-surface);
  padding-bottom: 2rem;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-lead {
  margin-bottom: 0;
}

.quick-form {
  max-width: 760px;
  padding: 1.25rem 1.35rem;
}

.quick-lines {
  font-family: var(--font-mono);
  font-size: 0.95rem;
}

.form-hint {
  margin: 0.6rem 0 1rem;
  font-size: 0.88rem;
  color: var(--color-muted);
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
}

.quick-results {
  max-width: 760px;
  margin-top: 1.5rem;
}

.quick-summary a {
  font-weight: 600;
}

.result-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.result-list li {
  padding: 0.55rem 0.8rem;
  border-left: 3px solid var(--color-border-strong);
  margin-bottom: 0.4rem;
  background: var(--color-bg);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  overflow-wrap: anywhere;
}

.result-list li.is-ok {
  border-left-color: var(--color-success);
}

.result-list li.is-error {
  border-left-color: var(--color-danger);
}

.result-notice {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.875rem;
  color: var(--color-warning);
}
</style>
