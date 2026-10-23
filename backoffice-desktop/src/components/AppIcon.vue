<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
})

// Nomes alinhados com o campo `icon` já devolvido por /system/workspace
// (models/table_map_builder.py, models/catalog_views.py) — não inventa
// taxonomia nova, só desenha o que o backend já descreve.
const PATHS = {
  folder: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z',
  layers: 'M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5M3 17l9 5 9-5',
  shopping_cart: 'M3 4h2l2.4 12.4a2 2 0 0 0 2 1.6h7.2a2 2 0 0 0 2-1.6L20 8H6',
  palette: 'M12 3a9 9 0 1 0 0 18c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.4-.3-.4-.5-.8-.5-1.3 0-1 .8-1.8 1.8-1.8H17a3 3 0 0 0 3-3c0-4.4-3.6-8.5-8-8.5z',
  receipt: 'M6 3h12v18l-2.5-1.5L13 21l-2.5-1.5L8 21l-2-1.5V3zM8.5 8h7M8.5 12h7',
  clipboard: 'M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2h1a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h3z M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2',
  mail: 'M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM3.5 6.5l8.5 7 8.5-7',
  database: 'M12 5c4.4 0 8-1.1 8-2.5S16.4 0 12 0 4 1.1 4 2.5 7.6 5 12 5zM4 2.5V19c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5V2.5M4 9.3c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5M4 15.2c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.3-4.3',
  close: 'M5 5l14 14M19 5L5 19',
  edit: 'M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17v3zM13.5 7.5l3 3',
  trash: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6',
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  'chevron-left': 'M15 18l-6-6 6-6',
  'chevron-right': 'M9 18l6-6-6-6',
}

const path = computed(() => PATHS[props.name] || '')
</script>

<template>
  <svg
    v-if="path"
    class="app-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  ><path :d="path" /></svg>
</template>

<style scoped>
.app-icon { flex-shrink: 0; display: inline-block; vertical-align: middle; }
</style>
