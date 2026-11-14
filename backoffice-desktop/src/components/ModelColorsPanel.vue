<script setup>
import { ref, watch, computed } from 'vue'
import { api } from '@/lib/api'
import { mapPool } from '@/lib/pool'
import { colorItems } from '@/lib/bundle'
import ImageField from '@/components/ImageField.vue'

const props = defineProps({
  modelId: { type: String, default: null },
  colorsTable: { type: String, default: null },
  readOnly: { type: Boolean, default: false },
  // Linhas já vindas no formulário agregado (/admin/form) — evita um pedido ao abrir.
  initialRows: { type: Array, default: null },
})

const rows = ref([])
const loading = ref(false)
const error = ref('')
// Estado gravado por id: só se envia ao servidor o que mudou (antes: um PUT por cor a cada gravação).
let saved = new Map()

// Uma cor tem várias imagens: `imagens` são as já guardadas (a primeira é a principal) e `pendingFiles` as escolhidas
// que ainda não subiram. Ao gravar, sobem por ordem e passam para `imagens`.
const emptyRow = () => ({ id: null, numero: '', nome: '', imagens: [], pendingFiles: [], vis: false })
const toRow = (c) => ({
  id: c.id,
  numero: String(c.numero ?? ''),
  nome: c.nome || '',
  imagens: Array.isArray(c.imagens) && c.imagens.length ? [...c.imagens] : c.imagem ? [c.imagem] : [],
  pendingFiles: [],
  vis: c.visibilidade === true,
})
const contentKey = (row, vis) =>
  JSON.stringify([
    String(row.numero || '').trim(),
    (row.nome || '').trim(),
    row.imagens || [],
    (row.pendingFiles || []).length,
    Boolean(vis),
  ])

const setRows = (data) => {
  rows.value = data.length ? data.map(toRow) : props.readOnly ? [] : [emptyRow()]
  saved = new Map(rows.value.filter((r) => r.id).map((r) => [r.id, contentKey(r, r.vis)]))
}

let usedInitial = false
const load = async () => {
  if (!props.modelId || !props.colorsTable) {
    rows.value = props.readOnly ? [] : [emptyRow()]
    saved = new Map()
    return
  }
  if (props.initialRows && !usedInitial) {
    usedInitial = true
    setRows(props.initialRows)
    return
  }
  loading.value = true
  error.value = ''
  try {
    setRows(await api.listModelColors(props.colorsTable, props.modelId))
  } catch (e) {
    error.value = e.message
    if (!props.readOnly) rows.value = [emptyRow()]
  } finally {
    loading.value = false
  }
}

watch(() => [props.modelId, props.colorsTable], load, { immediate: true })

const addRow = () => {
  rows.value.push(emptyRow())
}

// Tirar uma cor da lista só a apaga ao gravar (dentro do mesmo pedido atómico do modelo).
let removed = []
const removeRow = (idx) => {
  const row = rows.value[idx]
  if (row.id && !confirm('Eliminar esta cor? Sai da loja quando gravar o modelo.')) return
  if (row.id && saved.has(row.id)) removed.push(row.id)
  rows.value.splice(idx, 1)
  if (!rows.value.length && !props.readOnly) rows.value.push(emptyRow())
}

const addFiles = (row, files) => {
  row.pendingFiles.push(...files)
}
const removePending = (row, i) => {
  row.pendingFiles.splice(i, 1)
}
const removeImage = (row, i) => {
  row.imagens.splice(i, 1)
}

/**
 * Prepara as cores para o pedido do modelo (não grava): envia as imagens escolhidas, valida e devolve
 * `{ items, deleteIds }`. Depois de o pedido ter sucesso, `commit()` marca-as como gravadas.
 */
const collect = async ({ visible = false, requireRows = false } = {}) => {
  if (props.readOnly || !props.colorsTable) return { items: [], deleteIds: [] }
  error.value = ''
  const withNumber = rows.value.filter((row) => String(row.numero || '').trim())
  await mapPool(withNumber, 4, async (row) => {
    // Uma a uma e por ordem: se uma falhar, as que já subiram ficam em `imagens` e não se repetem ao tentar de novo.
    while (row.pendingFiles.length) {
      const up = await api.uploadImage(props.colorsTable, 'imagem', row.pendingFiles[0])
      row.imagens.push(up.url)
      row.pendingFiles.shift()
    }
  })
  const items = colorItems(rows.value, { visible, requireRows, newId: () => crypto.randomUUID() })
  // Os ids das linhas novas ficam já na linha: se o pedido falhar e o utilizador repetir, é o mesmo id.
  items.forEach((item, i) => {
    withNumber[i].id = item.id // `items` sai pela mesma ordem das linhas com número
  })
  return { items, deleteIds: [...removed] }
}

const commit = (visible) => {
  removed = []
  saved = new Map(rows.value.filter((r) => r.id).map((r) => [r.id, contentKey(r, visible)]))
  for (const row of rows.value) row.vis = visible
}

/** Cores gravadas com imagem (para o aviso «Para aparecer na loja»). */
const savedWithImage = computed(() => rows.value.filter((r) => r.id && r.imagens.length).length)

defineExpose({ collect, commit, savedWithImage })
</script>

<template>
  <section class="colors-panel">
    <h3>Cores do modelo</h3>
    <p class="hint">
      Pelo menos uma cor com número e imagem. Cada cor pode ter várias imagens; a primeira é a principal.
    </p>
    <p v-if="loading" class="muted">A carregar cores…</p>
    <p v-if="error" class="err">{{ error }}</p>

    <article v-for="(row, idx) in rows" :key="row.id || `new-${idx}`" class="color-row card">
      <div class="fields">
        <input v-model="row.numero" class="input num" type="number" min="1" placeholder="Nº" :disabled="readOnly" />
        <input v-model="row.nome" class="input" placeholder="Nome cor" :disabled="readOnly" />

        <div class="imgs">
          <div v-for="(url, i) in row.imagens" :key="`${url}-${i}`" class="img-item">
            <img :src="url" alt="" class="thumb" />
            <span v-if="i === 0" class="tag">principal</span>
            <button v-if="!readOnly" type="button" class="btn btn-ghost btn-sm" @click="removeImage(row, i)">Remover</button>
          </div>
          <div v-for="(file, i) in row.pendingFiles" :key="`pending-${i}-${file.name}`" class="img-item pending">
            <span class="muted">{{ file.name }} (por enviar)</span>
            <button v-if="!readOnly" type="button" class="btn btn-ghost btn-sm" @click="removePending(row, i)">Remover</button>
          </div>
        </div>

        <ImageField
          v-if="!readOnly"
          multiple
          :model-value="''"
          @file-selected="addFiles(row, $event)"
        />
      </div>
      <button v-if="!readOnly" type="button" class="btn btn-danger btn-sm" @click="removeRow(idx)">X</button>
    </article>

    <button v-if="!readOnly" type="button" class="btn btn-ghost" @click="addRow">+ Adicionar cor</button>
  </section>
</template>

<style scoped>
.colors-panel { margin-top: 28px; padding-top: 20px; border-top: 1px solid var(--border); display: grid; gap: 12px; }
.hint, .muted { margin: 0; font-size: 0.85rem; color: var(--text-muted); }
.err { color: var(--danger); margin: 0; }
.color-row { padding: 14px; display: flex; gap: 12px; align-items: flex-start; }
.fields { flex: 1; display: grid; gap: 10px; }
.num { max-width: 80px; }
.imgs { display: flex; flex-wrap: wrap; gap: 10px; }
.img-item { display: grid; gap: 6px; justify-items: start; }
.img-item.pending { display: flex; gap: 8px; align-items: center; }
.thumb { max-width: 120px; border-radius: 8px; border: 1px solid var(--border); }
.tag { font-size: 0.75rem; color: var(--text-muted); }
.btn-sm { padding: 6px 10px; }
</style>
