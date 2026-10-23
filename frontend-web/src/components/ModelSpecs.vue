<script setup>
import { computed } from 'vue'
import { formatStorefrontValue } from '@/lib/storefrontFormat'

const props = defineProps({
  model: { type: Object, default: null },
  specs: { type: Array, default: () => [] },
  extras: { type: Array, default: () => [] },
})

const rows = computed(() =>
  (props.specs || [])
    .map((spec) => {
      const raw = props.model?.[spec.field]
      return {
        ...spec,
        raw,
        display: formatStorefrontValue(spec, raw),
        isComposition: spec.widget === 'composition' && raw && typeof raw === 'object',
        compositionEntries: spec.widget === 'composition' && raw && typeof raw === 'object'
          ? Object.entries(raw)
          : [],
      }
    })
    .filter((row) => row.display || row.compositionEntries.length),
)
</script>

<template>
  <div v-if="rows.length || extras.length" class="specs-panel">
    <h3 class="specs-title">Especificações</h3>
    <dl class="specs-grid">
      <template v-for="row in rows" :key="row.field">
        <div class="spec-item">
          <dt>{{ row.label }}</dt>
          <dd v-if="row.isComposition" class="composition-tags">
            <span v-for="([material, percent], idx) in row.compositionEntries" :key="material" class="mat-tag">
              {{ percent }}% {{ material }}<span v-if="idx < row.compositionEntries.length - 1"> </span>
            </span>
          </dd>
          <dd v-else>{{ row.display }}</dd>
        </div>
      </template>
      <div v-for="extra in extras" :key="`extra-${extra.label}`" class="spec-item">
        <dt>{{ extra.label }}</dt>
        <dd>{{ extra.display }}</dd>
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

.composition-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.mat-tag {
  display: inline-block;
  padding: 0.3rem 0.65rem;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  font-size: 0.88rem;
  font-weight: 500;
}
</style>
