<script setup>
import { ref, computed, watch } from 'vue'
const props = defineProps({ modelValue: { type: String, default: '' }, multiple: { type: Boolean, default: false }, disabled: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'file-selected'])
const displayPath = ref('')
const previewUrl = ref('')
const errorMessage = ref('')
const isUrl = (v) => /^https?:\/\//i.test(v || '')
const isSignedUrl = computed(() => String(props.modelValue || '').includes('/object/sign/'))
const allowedTypes = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif'])
const allowedExtension = /\.(jpe?g|png|webp|gif)$/i
watch(() => props.modelValue, (v) => {
  if (isUrl(v)) { displayPath.value = 'Imagem carregada'; previewUrl.value = v }
  else { displayPath.value = v || ''; if (!v || !previewUrl.value?.startsWith('blob:')) previewUrl.value = '' }
}, { immediate: true })
const pickLabel = computed(() => (props.multiple ? 'Escolher ficheiros…' : 'Escolher ficheiro…'))
function validate(file) {
  if (file.size > 5 * 1024 * 1024) return `${file.name}: o ficheiro excede 5 MB.`
  if (!allowedTypes.has(file.type) && !allowedExtension.test(file.name)) return `${file.name}: formato não suportado. Use JPEG, PNG, WebP ou GIF.`
  return ''
}
const onPick = (e) => {
  const files = [...(e.target.files || [])]
  errorMessage.value = ''
  if (!files.length) return
  const invalid = files.map(validate).find(Boolean)
  if (invalid) { errorMessage.value = invalid; e.target.value = ''; return }
  if (props.multiple) {
    const paths = files.map((f) => f.name).join('; '); displayPath.value = paths; emit('update:modelValue', paths); emit('file-selected', files)
  } else {
    const file = files[0]; displayPath.value = file.name; emit('update:modelValue', file.name); emit('file-selected', file)
    if (previewUrl.value?.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = URL.createObjectURL(file)
  }
  e.target.value = ''
}
</script>
<template>
  <div class="image-field">
    <div class="row">
      <input class="input path" :value="displayPath" readonly placeholder="Nenhum ficheiro selecionado" />
      <label v-if="!disabled" class="btn btn-primary pick">{{ pickLabel }}<input type="file" accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif" :multiple="multiple" hidden @change="onPick" /></label>
    </div>
    <p v-if="errorMessage" class="field-error" role="alert">{{ errorMessage }}</p>
    <p v-if="isSignedUrl" class="field-warning">Não grave URLs assinadas — use upload ou path do storage</p>
    <img v-if="previewUrl" :src="previewUrl" alt="" class="thumb" />
  </div>
</template>
<style scoped>
.image-field {
  display: grid;
  gap: 12px;
}

.row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.path {
  flex: 1;
  min-width: 200px;
  color: var(--text-secondary);
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.pick {
  cursor: pointer;
  white-space: nowrap;
  margin: 0;
  padding: 10px 16px;
}

.pick input {
  display: none;
}

.field-error,
.field-warning {
  margin: 0;
  font-size: 12px;
  padding: 8px 12px;
  border-radius: 4px;
}

.field-error {
  color: var(--danger);
  background: rgba(239, 68, 68, 0.08);
  border-left: 2px solid var(--danger);
}

.field-warning {
  color: var(--warning);
  background: rgba(245, 158, 11, 0.08);
  border-left: 2px solid var(--warning);
}

.thumb {
  margin: 0;
  width: min(240px, 100%);
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-sm);
}
</style>
