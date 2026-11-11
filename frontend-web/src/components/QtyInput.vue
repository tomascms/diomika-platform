<script setup>
// Quantidade de um artigo: campo numérico com − e + (BR-03, FE-08, RP-12). Antes era uma lista com 500 opções
// (de 12 a 6000, de 12 em 12): 240 un. num telemóvel eram 20 posições a percorrer.
// A quantidade só é corrigida quando se confirma (sair do campo ou Enter), nunca a cada tecla («2» não salta para 12
// a meio de «240»); um valor que não é múltiplo do passo sobe ao seguinte, com um aviso que diz o que mudou.
import { computed, ref, useId, watch } from 'vue'
import { adjustQuantity, MAX_QTY, normalizeQuantity } from '@/lib/quantity'

const props = defineProps({
  modelValue: { type: Number, required: true },
  step: { type: Number, default: 6 },
  min: { type: Number, default: 6 },
  max: { type: Number, default: MAX_QTY },
  unitLabel: { type: String, default: 'un.' },
  label: { type: String, default: 'Quantidade' },
  // Nome para o leitor de ecrã quando a página tem vários campos iguais (uma linha do pedido cada).
  ariaLabel: { type: String, default: '' },
  // Explica a regra («Em múltiplos de 12 un., de 12 a 6000 un.»), por exemplo na ficha do produto.
  hint: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const id = useId()
const draft = ref(String(props.modelValue))
const notice = ref('')

watch(
  () => props.modelValue,
  (value) => {
    draft.value = String(value)
  },
)

const lowest = computed(() => normalizeQuantity(0, props.min, props.step, props.max))
const highest = computed(() => normalizeQuantity(props.max, props.min, props.step, props.max))

function set(value, message = '') {
  draft.value = String(value)
  notice.value = message
  if (value !== props.modelValue) emit('update:modelValue', value)
}

function commit() {
  const typed = String(draft.value ?? '').trim()
  if (typed === '' || !Number.isFinite(Number(typed))) {
    // Campo vazio: volta ao que estava, em vez de saltar para o mínimo.
    set(props.modelValue)
    return
  }
  const { value, notice: message } = adjustQuantity(typed, props.min, props.step, props.max)
  set(value, message)
}

function bump(direction) {
  const typed = String(draft.value ?? '').trim()
  const from =
    typed !== '' && Number.isFinite(Number(typed))
      ? normalizeQuantity(typed, props.min, props.step, props.max)
      : props.modelValue
  set(normalizeQuantity(from + direction * props.step, props.min, props.step, props.max))
}
</script>

<template>
  <div class="qty-input">
    <label class="field-label" :for="id">{{ label }}</label>
    <div class="qty-control">
      <button
        type="button"
        class="qty-btn"
        aria-label="Diminuir quantidade"
        :disabled="modelValue <= lowest"
        @click="bump(-1)"
      >
        −
      </button>
      <input
        :id="id"
        v-model="draft"
        class="field-input qty-number"
        type="number"
        inputmode="numeric"
        :min="lowest"
        :max="highest"
        :step="step"
        :aria-label="ariaLabel || undefined"
        :aria-describedby="`${id}-info`"
        @change="commit"
        @keydown.enter.prevent="commit"
        @focus="$event.target.select()"
      />
      <button
        type="button"
        class="qty-btn"
        aria-label="Aumentar quantidade"
        :disabled="modelValue >= highest"
        @click="bump(1)"
      >
        +
      </button>
      <span class="qty-unit">{{ unitLabel }}</span>
    </div>
    <div :id="`${id}-info`">
      <p v-if="hint" class="qty-hint">
        Em múltiplos de {{ step }} un., de {{ lowest }} a {{ highest }} un.
      </p>
      <p v-if="notice" class="qty-notice" role="status">{{ notice }}</p>
    </div>
  </div>
</template>

<style scoped>
.qty-control {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.qty-btn {
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-ink);
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  transition:
    border-color var(--transition),
    color var(--transition);
}

.qty-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.qty-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Os − e + já fazem o que as setas do navegador fazem. */
.qty-number {
  width: 5.25rem;
  min-width: 0;
  text-align: center;
  font-variant-numeric: tabular-nums;
  appearance: textfield;
  -moz-appearance: textfield;
}

.qty-number::-webkit-outer-spin-button,
.qty-number::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.qty-unit {
  color: var(--color-muted);
}

.qty-hint,
.qty-notice {
  margin: 0.4rem 0 0;
  font-size: 0.875rem;
  line-height: 1.4;
}

.qty-hint {
  color: var(--color-muted);
}

.qty-notice {
  color: var(--color-warning);
}
</style>
