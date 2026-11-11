<script setup>
import { computed } from 'vue'
import { storeLabel } from '@/lib/describe'
import { specRows } from '@/lib/storefrontFormat'

const props = defineProps({
  model: { type: Object, default: null },
  specs: { type: Array, default: () => [] },
  extras: { type: Array, default: () => [] },
})

const rows = computed(() => specRows(props.model, props.specs))

// Quem fabrica ou importa o artigo e os avisos de segurança (LEGAL-12: Reg. UE 2023/988, art. 19.º). Só o que o cliente
// preencheu no backoffice: um campo vazio, ou espaços, não mostra nada.
const text = (value) => String(value ?? '').trim()
const maker = computed(() => ({
  name: text(props.model?.fabricante_nome),
  address: text(props.model?.fabricante_morada),
  email: text(props.model?.fabricante_email),
}))
const hasMaker = computed(() =>
  Boolean(maker.value.name || maker.value.address || maker.value.email),
)
const warnings = computed(() => text(props.model?.avisos))
</script>

<template>
  <div v-if="rows.length || extras.length || hasMaker || warnings" class="specs-panel">
    <h3 class="specs-title">Especificações</h3>
    <dl class="specs-grid">
      <template v-for="row in rows" :key="row.field">
        <div class="spec-item">
          <dt>{{ storeLabel(row.label) }}</dt>
          <dd v-if="row.isComposition" class="composition-tags">
            <span
              v-for="([material, percent], idx) in row.compositionEntries"
              :key="material"
              class="mat-tag"
            >
              {{ percent }}% {{ material
              }}<span v-if="idx < row.compositionEntries.length - 1"> </span>
            </span>
          </dd>
          <dd v-else>{{ row.display }}</dd>
        </div>
      </template>
      <div v-for="extra in extras" :key="`extra-${extra.label}`" class="spec-item">
        <dt>{{ extra.label }}</dt>
        <dd>{{ extra.display }}</dd>
      </div>
      <div v-if="hasMaker" class="spec-item" data-spec="fabricante">
        <dt>Fabricante ou importador</dt>
        <dd class="maker">
          <strong v-if="maker.name">{{ maker.name }}</strong>
          <span v-if="maker.address">{{ maker.address }}</span>
          <a v-if="maker.email" :href="`mailto:${maker.email}`">{{ maker.email }}</a>
        </dd>
      </div>
      <div v-if="warnings" class="spec-item" data-spec="avisos">
        <dt>Avisos de segurança</dt>
        <dd class="warnings">{{ warnings }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.specs-panel {
  margin-top: 1.25rem;
  padding: 1.15rem 1.25rem;
  background: var(--color-cream);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.specs-title {
  margin: 0 0 0.85rem;
  font-size: 1rem;
  font-weight: 650;
  color: var(--color-ink-deep);
}

.specs-grid {
  margin: 0;
  display: grid;
  gap: 0.85rem;
}

.spec-item dt {
  margin: 0 0 0.2rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-muted);
}

.spec-item dd {
  margin: 0;
  font-size: 1rem;
  color: var(--color-ink);
  line-height: 1.45;
}

.maker {
  display: grid;
  gap: 0.1rem;
}

/* Um aviso por linha, como o cliente os escreveu. */
.warnings {
  white-space: pre-line;
}

.composition-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.mat-tag {
  display: inline-block;
  padding: 0.3rem 0.65rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  font-size: 0.88rem;
  font-weight: 500;
}
</style>
