<script setup>
import { onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const onKey = (e) => {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  (v) => {
    document.body.style.overflow = v ? 'hidden' : ''
  },
)

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && src"
      class="lightbox"
      role="dialog"
      aria-modal="true"
      :aria-label="alt || 'Ampliar imagem'"
      @click.self="emit('close')"
    >
      <button type="button" class="lightbox-close" aria-label="Fechar" @click="emit('close')">×</button>
      <img :src="src" :alt="alt" class="lightbox-img" />
    </div>
  </Teleport>
</template>

<style scoped>
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(8, 16, 28, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  cursor: zoom-out;
}
.lightbox-img {
  max-width: min(96vw, 1200px);
  max-height: 92vh;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  cursor: default;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
}
.lightbox-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 2.5rem;
  height: 2.5rem;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 1.6rem;
  line-height: 1;
  cursor: pointer;
}
.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.28);
}
</style>
