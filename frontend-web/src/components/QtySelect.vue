<script setup>
import { computed } from 'vue'
import { buildQtyOptions } from '@/composables/useCart'

const props = defineProps({
  modelValue: { type: Number, required: true },
  step: { type: Number, default: 6 },
  min: { type: Number, default: 6 },
  max: { type: Number, default: 6000 },
  unitLabel: { type: String, default: 'un.' },
})

const emit = defineEmits(['update:modelValue'])

const options = computed(() => buildQtyOptions(props.step, props.min, props.max))

const onChange = (event) => {
  emit('update:modelValue', Number(event.target.value))
}
</script>

<template>
  <select class="qty-select" :value="modelValue" @change="onChange">
    <option v-for="q in options" :key="q" :value="q">
      {{ q }} {{ unitLabel }}
    </option>
  </select>
</template>

<style scoped>
.qty-select {
  margin-top: 0.35rem;
  cursor: pointer;
}
</style>
