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
  /** Com `sizes`, oferece miniatura (480w) e original ao browser, que escolhe pelo ecrã. */
  sizes: { type: String, default: undefined },
})

const loaded = ref(false)
const original = () => normalizeStorageUrl(props.src)
const first = () => (props.thumb ? thumbUrl(original()) : original()) || PLACEHOLDER
const current = ref(first())
const srcset = ref(null)
const setSrcset = () => {
  const o = original()
  const t = thumbUrl(o)
  // Originais limitados a 1600 px no upload (image_resize.MAX_DIMENSION)
  srcset.value = props.sizes && o && t !== o ? `${t} 480w, ${thumbUrl(o, 960)} 960w, ${o} 1600w` : null
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
  background: linear-gradient(120deg, var(--color-bg-soft) 25%, var(--color-bg) 37%, var(--color-bg-soft) 63%);
  background-size: 200% 100%;
  animation: soft-shimmer 1.1s ease-in-out infinite;
}

.soft-image.is-loaded {
  animation: none;
  background: transparent;
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

@keyframes soft-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
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
