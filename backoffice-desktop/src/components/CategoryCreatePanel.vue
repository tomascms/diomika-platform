<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/lib/api'
import ImageField from '@/components/ImageField.vue'

const emit = defineEmits(['created', 'error'])

const tipos = ref([])
const tipoCatalogo = ref('')
const nome = ref('')
const imagem = ref('')
const imageFile = ref(null)
const saving = ref(false)
const loadingTipos = ref(true)

onMounted(async () => {
  try {
    const data = await api.categoryTipos()
    tipos.value = data.tipos || []
    if (tipos.value.length) tipoCatalogo.value = tipos.value[0].tipo
  } catch (e) {
    emit('error', e.message)
  } finally {
    loadingTipos.value = false
  }
})

const onImageFile = (file) => {
  imageFile.value = file
}

const create = async () => {
  saving.value = true
  emit('error', '')
  try {
    if (!nome.value.trim()) throw new Error('Indique o nome da categoria.')
    if (!tipoCatalogo.value) throw new Error('Escolha a família de produto.')
    let imageUrl = imagem.value
    if (imageFile.value) {
      const up = await api.uploadImage('categories', 'imagem', imageFile.value)
      imageUrl = up.url
    }
    if (!imageUrl) throw new Error('Escolha uma imagem para a categoria.')
    await api.createRecord('categories', {
      nome: nome.value.trim(),
      imagem: imageUrl,
      tipo_catalogo: tipoCatalogo.value,
    })
    nome.value = ''
    imagem.value = ''
    imageFile.value = null
    emit('created')
  } catch (e) {
    emit('error', e.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="card panel">
    <h3>Nova categoria</h3>
    <p class="hint">A família define os campos dos modelos.</p>

    <label for="cat-nome">Nome</label>
    <input id="cat-nome" v-model="nome" class="input" placeholder="Ex.: Almofadas de Natal" />

    <label for="cat-imagem">Imagem</label>
    <ImageField id="cat-imagem" v-model="imagem" @file-selected="onImageFile" />

    <label for="cat-tipo">Família de produto</label>
    <select id="cat-tipo" v-model="tipoCatalogo" class="input" :disabled="loadingTipos">
      <option v-for="t in tipos" :key="t.tipo" :value="t.tipo">{{ t.label }}</option>
    </select>


    <button class="btn btn-primary" :disabled="saving || loadingTipos" @click="create">
      {{ saving ? 'A criar…' : 'Criar categoria' }}
    </button>
  </div>
</template>

<style scoped>
.panel { max-width: 640px; padding: 18px 20px; display: grid; gap: 8px; }
.panel h3 { margin: 0; }
.hint { margin: 0 0 4px; }
label { margin-top: 6px; font-size: 13px; font-weight: 560; color: var(--text-secondary); }
.panel > .btn { justify-self: start; margin-top: 8px; }
</style>
