<script setup>
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  variant: { type: String, default: 'catalog' },
  activeId: { type: [String, Number], default: null },
  emptyText: { type: String, default: 'Ainda não há registos aqui.' },
})
defineEmits(['open', 'toggle-visibility', 'toggle-read', 'delete'])

const primary = (row) => {
  const col = props.columns[0]
  if (!col) return '—'
  return col.format ? col.format(row) : row[col.key] ?? '—'
}

const subtitle = (row) => {
  if (props.columns.length < 2) return ''
  const col = props.columns[1]
  const value = col.format ? col.format(row) : row[col.key] ?? ''
  const sub = String(value ?? '').trim()
  if (!sub || sub.toLowerCase() === String(primary(row) ?? '').trim().toLowerCase()) return ''
  return sub
}

const isConversation = () => props.variant === 'conversation'
const isHidden = (row) => row.visibilidade === false

function stateLabel(row) {
  if (isConversation()) return row.lida ? 'Lida' : 'Nova'
  return isHidden(row) ? 'Oculto' : 'Visível'
}

function stateClass(row) {
  if (isConversation()) return row.lida ? 'is-muted' : 'is-new'
  return isHidden(row) ? 'is-muted' : 'is-live'
}

function toggleLabel(row) {
  if (isConversation()) return row.lida ? 'Marcar como não lida' : 'Marcar como lida'
  return isHidden(row) ? 'Mostrar no site' : 'Ocultar do site'
}
</script>

<template>
  <div class="list-wrapper">
    <div v-if="loading && !rows.length" class="list" aria-busy="true" aria-label="A carregar registos">
      <div v-for="n in 6" :key="`sk-${n}`" class="item skeleton-row">
        <div class="item-main">
          <span class="sk-line sk-title" />
          <span class="sk-line sk-sub" />
        </div>
      </div>
    </div>

    <p v-else-if="!rows.length" class="empty">{{ emptyText }}</p>

    <ul v-else class="list" :aria-busy="loading">
      <li
        v-for="row in rows"
        :key="row.id"
        class="item"
        :class="{ active: activeId != null && String(activeId) === String(row.id), dim: isHidden(row) }"
      >
        <button type="button" class="item-main" @click="$emit('open', row)">
          <span class="title">{{ primary(row) }}</span>
          <span v-if="subtitle(row)" class="sub">{{ subtitle(row) }}</span>
        </button>
        <span class="state" :class="stateClass(row)">{{ stateLabel(row) }}</span>
        <div class="item-actions">
          <button
            type="button"
            class="btn btn-ghost btn-icon"
            :title="toggleLabel(row)"
            :aria-label="toggleLabel(row)"
            @click.stop="isConversation() ? $emit('toggle-read', row) : $emit('toggle-visibility', row)"
          >
            <AppIcon :name="isConversation() ? 'mail' : 'eye'" :size="16" />
          </button>
          <button
            type="button"
            class="btn btn-ghost btn-icon danger"
            title="Apagar"
            aria-label="Apagar registo"
            @click.stop="$emit('delete', row)"
          >
            <AppIcon name="trash" :size="16" />
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.list {
  margin: 0;
  padding: 0;
  list-style: none;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 52px;
  padding-right: 10px;
  border-bottom: 1px solid var(--border);
  transition: background var(--transition-fast);
}

.item:last-child {
  border-bottom: none;
}

.item:hover,
.item:focus-within {
  background: var(--bg-hover);
}

.item.active {
  background: var(--accent-soft);
  box-shadow: inset 3px 0 0 var(--accent);
}

.item-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
  padding: 9px 16px;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.item-main:focus-visible {
  outline-offset: -2px;
}

.title {
  font-weight: 560;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item.dim .title {
  color: var(--text-secondary);
}

.sub {
  font-size: 12.5px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.state {
  flex: none;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 560;
}

.state.is-live {
  background: var(--success-soft);
  color: var(--success);
}

.state.is-new {
  background: var(--accent-soft);
  color: var(--accent);
}

.state.is-muted {
  background: var(--bg-secondary);
  color: var(--text-muted);
}

.item-actions {
  flex: none;
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.item:hover .item-actions,
.item:focus-within .item-actions {
  opacity: 1;
}

.item-actions .danger:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

@media (hover: none) {
  .item-actions {
    opacity: 1;
  }
}

.skeleton-row {
  pointer-events: none;
}

.skeleton-row .item-main {
  cursor: default;
}

.sk-title {
  display: block;
  width: 42%;
  height: 12px;
}

.sk-sub {
  display: block;
  width: 24%;
  height: 10px;
  margin-top: 6px;
}

.empty {
  margin: 0;
  padding: 40px 16px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-align: center;
}
</style>
