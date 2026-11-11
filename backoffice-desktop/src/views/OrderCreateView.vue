<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'

const emit = defineEmits(['saved'])

const categories = ref([])
const categoryId = ref('')
const picker = ref(null)
const cliente = ref('')
const lines = ref([])
const error = ref('')
const message = ref('')
const saving = ref(false)

const mode = computed(() => picker.value?.mode || '')
const step = computed(() => picker.value?.carrinho_step || 6)
const minQ = computed(() => picker.value?.carrinho_min || 6)

const variantForm = ref({ ean: '', numero_cor: '', quantidade: minQ })
const assentoForm = ref({ modelo_id: '', altura: '', numero_cor: '', quantidade: minQ })

const loadCategories = async () => {
  categories.value = await api.listCategories()
}

const loadPicker = async () => {
  if (!categoryId.value) {
    picker.value = null
    return
  }
  picker.value = await api.orderPicker(categoryId.value)
}

const addVariantLine = () => {
  const p = picker.value?.products?.find((x) => x.ean === variantForm.value.ean)
  if (!p) {
    error.value = 'Escolha um produto válido.'
    return
  }
  lines.value.push({
    ean: p.ean,
    numero_cor: Number(variantForm.value.numero_cor),
    quantidade: Number(variantForm.value.quantidade),
    label: `${p.modelo_nome} ${p.dimensoes} · cor ${variantForm.value.numero_cor}`,
  })
  error.value = ''
}

const addAssentoLine = () => {
  const m = picker.value?.models?.find((x) => x.modelo_id === assentoForm.value.modelo_id)
  const altura = assentoForm.value.altura
  const product =
    (m?.products || []).find((p) => String(p.altura || '') === String(altura || '')) || null
  const ean = product?.ean || m?.ean
  if (!ean) {
    error.value = 'Modelo sem EAN para esta altura.'
    return
  }
  lines.value.push({
    ean,
    numero_cor: Number(assentoForm.value.numero_cor),
    altura,
    quantidade: Number(assentoForm.value.quantidade),
    label: `${m.modelo_nome} · ${altura} · cor ${assentoForm.value.numero_cor}`,
  })
  error.value = ''
}

const removeLine = (idx) => lines.value.splice(idx, 1)

const save = async () => {
  if (!cliente.value.trim()) {
    error.value = 'Indica o cliente.'
    return
  }
  if (!lines.value.length) {
    error.value = 'Adiciona pelo menos uma linha.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload = {
      referencia_cliente: cliente.value.trim(),
      linhas: lines.value.map(({ ean, numero_cor, quantidade, altura }) => ({
        ean,
        numero_cor,
        quantidade,
        ...(altura ? { altura } : {}),
      })),
    }
    const res = await api.createOrder(payload)
    message.value = 'Encomenda criada.'
    lines.value = []
    cliente.value = ''
    emit('saved', res?.data)
    if (res?.data?.id) {
      const blob = await api.orderPdf(res.data.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    }
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

onMounted(loadCategories)
</script>

<template>
  <div class="order-create">
    <div class="card section">
      <h2>Nova encomenda interna</h2>
      <label>Cliente / referência</label>
      <input v-model="cliente" class="input" />
      <label>Categoria</label>
      <select v-model="categoryId" class="input" @change="loadPicker">
        <option value="">— Selecionar —</option>
        <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.nome }}</option>
      </select>
    </div>

    <div v-if="picker && mode === 'variantes'" class="card section">
      <h3>Adicionar linha</h3>
      <label>Produto (EAN)</label>
      <select v-model="variantForm.ean" class="input">
        <option value="">—</option>
        <option v-for="p in picker.products" :key="p.ean" :value="p.ean">
          {{ [p.familia, p.modelo_nome, p.dimensoes, p.ean].filter(Boolean).join(' · ') }}
        </option>
      </select>
      <label>Cor</label>
      <select v-model="variantForm.numero_cor" class="input">
        <option value="">—</option>
        <option
          v-for="c in (picker.products.find((p) => p.ean === variantForm.ean)?.cores || [])"
          :key="c.numero"
          :value="c.numero"
        >
          {{ c.numero }} {{ c.nome }}
        </option>
      </select>
      <label>Quantidade (mín. {{ minQ }}, passo {{ step }})</label>
      <input v-model.number="variantForm.quantidade" type="number" class="input" :step="step" :min="minQ" />
      <button class="btn btn-primary" @click="addVariantLine">Adicionar linha</button>
    </div>

    <div v-if="picker && mode === 'assento'" class="card section">
      <h3>Adicionar linha (assentos)</h3>
      <label>Modelo</label>
      <select v-model="assentoForm.modelo_id" class="input">
        <option value="">—</option>
        <option v-for="m in picker.models" :key="m.modelo_id" :value="m.modelo_id">{{ m.modelo_nome }}</option>
      </select>
      <label>Altura</label>
      <select v-model="assentoForm.altura" class="input">
        <option value="">—</option>
        <option
          v-for="a in (picker.models.find((m) => m.modelo_id === assentoForm.modelo_id)?.alturas || [])"
          :key="a"
          :value="a"
        >
          {{ a }}
        </option>
      </select>
      <label>Cor</label>
      <select v-model="assentoForm.numero_cor" class="input">
        <option value="">—</option>
        <option
          v-for="c in (picker.models.find((m) => m.modelo_id === assentoForm.modelo_id)?.cores || [])"
          :key="c.numero"
          :value="c.numero"
        >
          {{ c.numero }} {{ c.nome }}
        </option>
      </select>
      <label>Quantidade</label>
      <input v-model.number="assentoForm.quantidade" type="number" class="input" :step="step" :min="minQ" />
      <button class="btn btn-primary" @click="addAssentoLine">Adicionar linha</button>
    </div>

    <div class="card section">
      <h3>Linhas ({{ lines.length }})</h3>
      <ul class="lines">
        <li v-for="(l, i) in lines" :key="i">
          {{ l.label }} · qtd {{ l.quantidade }}
          <button class="btn btn-ghost" @click="removeLine(i)">×</button>
        </li>
      </ul>
      <button class="btn btn-primary" :disabled="saving" @click="save">{{ saving ? 'A guardar…' : 'Guardar encomenda' }}</button>
    </div>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="message" class="ok">{{ message }}</p>
  </div>
</template>

<style scoped>
.section { padding: 20px; margin-bottom: 16px; display: grid; gap: 10px; }
.section h2, .section h3 { margin: 0 0 4px; }
.lines { list-style: none; padding: 0; margin: 0 0 12px; }
.lines li { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border); }
.err { color: var(--danger); }
.ok { color: var(--success); }
</style>
