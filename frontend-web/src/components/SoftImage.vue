<script setup>
import { ref, watch } from 'vue'
import { PLACEHOLDER, thumbUrl } from '@/lib/images'
import { normalizeStorageUrl } from '@/lib/supabaseConfig'

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  eager: { type: Boolean, default: false },
  fetchpriority: { type: String, default: undefined },
  width: { type: [Number, String], default: undefined },
  height: { type: [Number, String], default: undefined },
  imgClass: { type: String, default: '' },
  /** Pede a miniatura; se faltar, cai no original. */
  thumb: { type: Boolean, default: false },
  /** Largura da miniatura com `thumb` (480 por omissão; 160 nos botões de cor). */
  thumbWidth: { type: Number, default: 480 },
  /** Com `sizes`, oferece miniatura (480w) e original ao browser, que escolhe pelo ecrã. */
  sizes: { type: String, default: undefined },
})

const loaded = ref(false)
const original = () => normalizeStorageUrl(props.src)
const first = () =>
  (props.thumb ? thumbUrl(original(), props.thumbWidth) : original()) || PLACEHOLDER
const current = ref(first())
const srcset = ref(null)
const setSrcset = () => {
  const o = original()
  const t = thumbUrl(o)
  // Nunca o original no srcset: pesa até 2 MB e um telemóvel de ecrã 3x chegava a pedi-lo (PERF-02). 960 px chega.
  srcset.value = props.sizes && o && t !== o ? `${t} 480w, ${thumbUrl(o, 960)} 960w` : null
}
setSrcset()

watch(
  () => props.src,
  (value) => {
    loaded.value = false
    current.value = value ? first() : PLACEHOLDER
    setSrcset()
  },
)

function onLoad() {
  loaded.value = true
}

function onError() {
  if (srcset.value) {
    // Miniatura em falta: larga o srcset e fica com o original
    srcset.value = null
    current.value = original()
    return
  }
  // Miniatura pequena ainda por gerar (as imagens antigas): a de 480 antes do original, que pesa muito mais.
  if (
    props.thumb &&
    props.thumbWidth < 480 &&
    current.value === thumbUrl(original(), props.thumbWidth)
  ) {
    const fallback = thumbUrl(original())
    if (fallback !== current.value) {
      current.value = fallback
      return
    }
  }
  // Miniatura em falta → original; depois placeholder (sem loops)
  if (props.src && current.value !== original() && !String(current.value).includes('placeholder')) {
    current.value = original()
    return
  }
  if (current.value && !String(current.value).includes('placeholder')) {
    current.value = PLACEHOLDER
    loaded.value = true
  }
}
</script>

<template>
  <span class="soft-image" :class="{ 'is-loaded': loaded }">
    <span class="soft-image__skeleton" aria-hidden="true" />
    <img
      :src="current"
      :srcset="srcset || undefined"
      :sizes="srcset ? sizes : undefined"
      :alt="alt"
      :class="['soft-image__img', imgClass]"
      :loading="eager ? 'eager' : 'lazy'"
      :fetchpriority="fetchpriority"
      :width="width"
      :height="height"
      decoding="async"
      @load="onLoad"
      @error="onError"
    />
  </span>
</template>

<style scoped>
.soft-image {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: linear-gradient(
    120deg,
    var(--color-bg-soft) 25%,
    var(--color-bg) 37%,
    var(--color-bg-soft) 63%
  );
  background-size: 200% 100%;
  animation: shimmer 1.1s ease-in-out infinite;
}

.soft-image.is-loaded {
  animation: none;
  background: var(--color-photo-bg);
}

.soft-image__skeleton {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.soft-image__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.soft-image.is-loaded .soft-image__img {
  opacity: 1;
}

@media (prefers-reduced-motion: reduce) {
  .soft-image {
    animation: none;
  }
  .soft-image__img {
    transition: none;
    transform: none;
    opacity: 1;
  }
}
</style>
