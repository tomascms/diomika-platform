<script setup>

import { ref, watch, computed } from 'vue'

import CompositionField from '@/components/CompositionField.vue'

import ImageField from '@/components/ImageField.vue'



const props = defineProps({

  fields: { type: Array, default: () => [] },

  modelValue: { type: Object, default: () => ({}) },

  relations: { type: Object, default: () => ({}) },

  fieldOptions: { type: Object, default: () => ({}) },

  readonly: { type: Boolean, default: false },

  editing: { type: Boolean, default: false },

  tableName: { type: String, default: '' },

})



const emit = defineEmits(['update:modelValue', 'pending-files'])



const local = ref({ ...props.modelValue })

const pendingFiles = ref({})

const stringListRows = ref({})

const dimParts = ref({})

const fieldErrors = ref({})

let syncingFromLocal = false

const sync = () => {
  syncingFromLocal = true
  emit('update:modelValue', { ...local.value })
  queueMicrotask(() => {
    syncingFromLocal = false
  })
}

const syncFiles = () => emit('pending-files', { ...pendingFiles.value })



const relationOptions = (field) => props.relations[field.relation] || []



const isLocked = (field) => {

  if (props.readonly || field.readonly) return true

  if (field.lock_on_edit && props.editing) return true

  if (props.editing && field.name === 'id_modelo') return true

  return false

}



const initStringList = (name, val) => {
  let parsed = val
  if (typeof val === 'string') {
    const trimmed = val.trim()
    if (trimmed.startsWith('[')) {
      try {
        parsed = JSON.parse(trimmed)
      } catch {
        parsed = val
      }
    }
  }
  const vals = Array.isArray(parsed)
    ? parsed.map((item) => String(item).trim()).filter(Boolean)
    : parsed
      ? [String(parsed).trim()].filter(Boolean)
      : []
  stringListRows.value[name] = vals.length ? [...vals] : ['']
}



const initDimensions = (name, val) => {

  if (val && typeof val === 'string' && val.includes('x')) {

    const [w, h] = val.split('x', 2)

    dimParts.value[name] = { w: w.trim(), h: h.trim() }

  } else {

    dimParts.value[name] = { w: '', h: '' }

  }

}



const initWidgetFields = (source = local.value) => {
  for (const f of props.fields) {
    const val = source?.[f.name]
    if (f.widget === 'string_list') initStringList(f.name, val)
    if (f.widget === 'dimensions') initDimensions(f.name, val)
  }
}

// Sem deep-watch: só reage quando o pai substitui o objecto (load), não a cada tecla.
watch(
  () => props.modelValue,
  (v) => {
    if (syncingFromLocal) return
    local.value = { ...v }
    initWidgetFields(v)
  },
)

watch(() => props.fields, () => initWidgetFields(), { immediate: true })



const syncStringList = (name) => {

  local.value[name] = (stringListRows.value[name] || []).map((s) => s.trim()).filter(Boolean)

  sync()

}



const addStringRow = (name) => {

  if (!stringListRows.value[name]) stringListRows.value[name] = ['']

  stringListRows.value[name].push('')

}



const removeStringRow = (name, idx) => {

  stringListRows.value[name].splice(idx, 1)

  if (!stringListRows.value[name].length) stringListRows.value[name] = ['']

  syncStringList(name)

}



const syncDimensions = (name) => {

  const p = dimParts.value[name] || { w: '', h: '' }

  local.value[name] = p.w && p.h ? `${p.w}x${p.h}` : ''

  sync()

}



const onImageFile = (fieldName, fileOrFiles) => {

  if (Array.isArray(fileOrFiles)) {

    pendingFiles.value[fieldName] = fileOrFiles

  } else {

    pendingFiles.value[fieldName] = fileOrFiles

  }

  syncFiles()

}



const onComposition = (name, val) => {

  local.value[name] = val

  sync()

}



const clearFieldError = (name) => {

  if (fieldErrors.value[name]) {

    const next = { ...fieldErrors.value }

    delete next[name]

    fieldErrors.value = next

  }

}



const validate = () => {
  const errors = {}
  for (const field of props.fields) {
    if (field.hidden) continue
    const val = local.value[field.name]
    if (!field.required && field.widget !== 'composition') continue

    if (field.widget === 'composition') {
      const obj = val && typeof val === 'object' && !Array.isArray(val) ? val : {}
      const sum = Object.values(obj).reduce((a, b) => a + (parseInt(b, 10) || 0), 0)
      if (field.required || Object.keys(obj).length || sum > 0) {
        if (sum !== 100) {
          errors[field.name] = `Composição deve somar 100% (atual: ${sum}%). Indique material e % em cada linha.`
        }
      }
      continue
    }

    if (!field.required) continue
    const empty = val === null || val === undefined || val === ''
      || (Array.isArray(val) && val.length === 0)
      || (field.widget === 'dimensions' && !(dimParts.value[field.name]?.w && dimParts.value[field.name]?.h))
    if (empty) errors[field.name] = `${field.label} é obrigatório.`
  }
  fieldErrors.value = errors
  return Object.keys(errors).length === 0
}



defineExpose({ validate })

</script>



<template>

  <form class="schema-form" @submit.prevent>

    <div v-for="field in fields" :key="field.name" class="field" :class="{ 'has-error': fieldErrors[field.name] }">

      <label :for="field.name">
        {{ field.label }}<span v-if="field.required" class="req"> *</span>
      </label>



      <CompositionField

        v-if="field.widget === 'composition'"

        :model-value="local[field.name]"

        :disabled="isLocked(field)"

        @update:model-value="onComposition(field.name, $event)"

      />



      <ImageField

        v-else-if="field.widget === 'image' || field.widget === 'multi_image'"

        :model-value="local[field.name] || ''"

        :multiple="field.widget === 'multi_image'"

        :disabled="isLocked(field)"

        @update:model-value="local[field.name] = $event; sync()"

        @file-selected="onImageFile(field.name, $event)"

      />



      <div v-else-if="field.widget === 'dimensions' && dimParts[field.name]" class="dim-row">

        <input

          v-model="dimParts[field.name].w"

          class="input dim"

          placeholder="Larg"

          :disabled="isLocked(field)"

          @input="syncDimensions(field.name)"

        />

        <span>×</span>

        <input

          v-model="dimParts[field.name].h"

          class="input dim"

          placeholder="Alt"

          :disabled="isLocked(field)"

          @input="syncDimensions(field.name)"

        />

      </div>



      <div v-else-if="field.widget === 'string_list' && stringListRows[field.name]" class="string-list">
        <div v-for="(row, idx) in stringListRows[field.name]" :key="idx" class="sl-row">
          <input
            v-model="stringListRows[field.name][idx]"
            class="input"
            :placeholder="field.placeholder || (field.name === 'alturas' ? 'ex: 32mm' : 'ex: 100x200')"
            :disabled="isLocked(field)"
            @input="syncStringList(field.name)"
          />
          <button v-if="!isLocked(field)" type="button" class="btn btn-danger btn-sm" @click="removeStringRow(field.name, idx)">X</button>
        </div>
        <button v-if="!isLocked(field)" type="button" class="btn btn-ghost btn-sm" @click="addStringRow(field.name)">+ Adicionar</button>
      </div>



      <p v-else-if="isLocked(field) && field.widget === 'enum'" class="readonly-val">

        {{ field.enum_labels?.[local[field.name]] || local[field.name] || '—' }}

      </p>



      <select

        v-else-if="field.widget === 'relation'"

        :id="field.name"

        v-model="local[field.name]"

        class="input"

        :disabled="isLocked(field)"

        @change="sync"

      >

        <option value="">— Selecionar —</option>

        <option v-for="opt in relationOptions(field)" :key="opt.id" :value="opt.id">{{ opt.label }}</option>

      </select>



      <select

        v-else-if="field.widget === 'altura_modelo'"

        :id="field.name"

        v-model="local[field.name]"

        class="input"

        :disabled="isLocked(field)"

        @change="sync"

      >

        <option value="">— Selecionar altura —</option>

        <option v-for="opt in (fieldOptions.altura_modelo || [])" :key="opt" :value="opt">{{ opt }}</option>

      </select>



      <select

        v-else-if="field.widget === 'dimensao_modelo'"

        :id="field.name"

        v-model="local[field.name]"

        class="input"

        :disabled="isLocked(field)"

        @change="sync"

      >

        <option value="">— Selecionar dimensão —</option>

        <option v-for="opt in (fieldOptions.dimensoes_modelo || [])" :key="opt" :value="opt">{{ opt }}</option>

      </select>



      <select

        v-else-if="field.widget === 'enum'"

        :id="field.name"

        v-model="local[field.name]"

        class="input"

        :disabled="isLocked(field)"

        @change="sync"

      >

        <option v-for="opt in field.enum_options || []" :key="opt" :value="opt">

          {{ field.enum_labels?.[opt] || opt }}

        </option>

      </select>



      <textarea

        v-else-if="['textarea', 'json_dict', 'json_list'].includes(field.widget)"

        :id="field.name"

        v-model="local[field.name]"

        class="input textarea"

        rows="4"

        :readonly="isLocked(field)"

        @blur="sync"

      />



      <label v-else-if="field.widget === 'boolean'" class="checkbox-row">

        <input :id="field.name" v-model="local[field.name]" type="checkbox" :disabled="isLocked(field)" @change="sync" />

        {{ field.label }}

      </label>



      <p v-else-if="isLocked(field)" class="readonly-val">{{ local[field.name] ?? '—' }}</p>



      <input

        v-else

        :id="field.name"

        v-model="local[field.name]"

        class="input"

        :required="field.required"

        @input="clearFieldError(field.name); sync()"

      />

      <p v-if="fieldErrors[field.name]" class="field-error">{{ fieldErrors[field.name] }}</p>

    </div>

  </form>

</template>



<style scoped>
.schema-form {
  display: grid;
  gap: 18px;
}

.field {
  display: grid;
  gap: 6px;
}

.field label {
  display: block;
  font-size: 13px;
  font-weight: 560;
  color: var(--text-secondary);
}

.req {
  color: var(--danger);
}

.field.has-error .input {
  border-color: var(--danger);
  box-shadow: 0 0 0 3px var(--danger-soft);
}

.field-error {
  margin: 0;
  font-size: 12.5px;
  color: var(--danger);
}

.textarea {
  line-height: 1.55;
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  font-weight: 500;
  cursor: pointer;
}

.readonly-val {
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-secondary);
  color: var(--text-secondary);
}

.dim-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dim {
  width: 110px;
}

.dim-row > span {
  color: var(--text-muted);
  font-weight: 600;
}

.string-list {
  display: grid;
  gap: 8px;
}

.sl-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sl-row .input {
  flex: 1;
}
</style>
