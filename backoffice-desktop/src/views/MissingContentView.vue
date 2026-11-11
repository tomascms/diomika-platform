<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/lib/api'

// RP-11: o que falta preencher em cada modelo, com ligação directa para o editar.
const items = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    items.value = (await api.missingContent()).items || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="missing">
    <h2>Conteúdo em falta</h2>
    <p class="hint">
      Modelos com campos obrigatórios por preencher.
    </p>
    <p v-if="loading" class="muted">A procurar…</p>
    <p v-if="error" class="err">{{ error }}</p>
    <p v-else-if="!loading && !items.length" class="ok">Nada em falta: todos os modelos estão completos.</p>
    <ul v-if="items.length" class="list">
      <li v-for="m in items" :key="m.id" class="card item">
        <div>
          <RouterLink v-if="m.tabela" :to="`/workspace/${m.tabela}/${m.id}`" class="name">{{ m.nome }}</RouterLink>
          <span v-else class="name">{{ m.nome }}</span>
          <span class="state" :class="{ live: m.visivel }">{{ m.visivel ? 'Visível na loja' : 'Oculto' }}</span>
        </div>
        <ul class="gaps">
          <li v-for="f in m.faltas" :key="f">{{ f }}</li>
        </ul>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.missing { max-width: 820px; }
h2 { margin: 0 0 6px; font-size: 1.1rem; }
.hint, .muted { color: var(--text-muted); font-size: 0.9rem; }
.err { color: var(--danger); }
.ok { color: var(--success); }
.list { list-style: none; padding: 0; margin: 14px 0 0; display: grid; gap: 10px; }
.item { padding: 12px 14px; display: grid; gap: 8px; }
.name { font-weight: 600; margin-right: 10px; }
.state { font-size: 0.78rem; color: var(--text-muted); }
.state.live { color: var(--success); }
.gaps { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.gaps li { background: var(--warning-soft); color: var(--warning); border-radius: 999px; padding: 2px 10px; font-size: 0.8rem; }
</style>
