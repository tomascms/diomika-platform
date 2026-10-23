<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  active: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  online: { type: Boolean, default: null },
  user: { type: Object, default: null },
})

defineEmits(['navigate', 'logout'])

const ROLE_LABELS = {
  admin: 'Administrador',
  catalog: 'Catálogo',
  pedidos: 'Pedidos',
  mensagens: 'Mensagens',
  ops: 'Operações',
}

const displayName = computed(() => {
  const name = props.user?.username || ''
  if (!name || name === 'api-key' || name === 'dev-open') return 'Sessão de desenvolvimento'
  return name
})

const initial = computed(() => displayName.value.charAt(0).toUpperCase() || 'D')
const roleLabel = computed(() => ROLE_LABELS[props.user?.role] || props.user?.role || '')
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <img class="logo" src="/mark.svg" alt="" width="24" height="29" />
      <div>
        <strong>Diomika</strong>
        <small>Backoffice</small>
      </div>
    </div>

    <nav class="nav" aria-label="Secções">
      <template v-if="loading && !items.length">
        <span v-for="n in 6" :key="n" class="nav-skeleton sk-line" aria-hidden="true" />
      </template>
      <RouterLink
        v-for="item in items"
        :key="item.key"
        :to="`/workspace/${item.key}`"
        class="nav-item"
        :class="{ active: active === item.key }"
        :aria-current="active === item.key ? 'page' : undefined"
        @click="$emit('navigate')"
      >
        <AppIcon :name="item.icon || 'folder'" :size="17" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <div v-if="user" class="user-box">
        <span class="avatar" aria-hidden="true">{{ initial }}</span>
        <div class="user-meta">
          <span class="user-name">{{ displayName }}</span>
          <span class="user-role">{{ roleLabel }}</span>
        </div>
        <button type="button" class="btn btn-ghost btn-sm logout-btn" @click="$emit('logout')">
          Sair
        </button>
      </div>
      <p class="conn">
        <span class="status-dot" :class="{ online, offline: online === false }" aria-hidden="true" />
        {{ online ? 'Ligado à API' : online === false ? 'Sem ligação à API' : 'A ligar à API…' }}
      </p>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-w);
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 10px 12px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 6px 10px 16px;
}

.logo {
  flex: none;
}

.brand strong {
  display: block;
  font-size: 15px;
  font-weight: 700;
  font-stretch: 118%;
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.brand small {
  display: block;
  margin-top: 1px;
  font-size: 12px;
  color: var(--text-muted);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.nav-skeleton {
  height: 34px;
  margin: 2px 0;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 36px;
  padding: 0 10px;
  border-radius: var(--radius);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.nav-item .app-icon {
  opacity: 0.7;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.nav-item.active .app-icon {
  opacity: 1;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
}

.sidebar-footer {
  display: grid;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.user-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 4px 0 6px;
}

.avatar {
  flex: none;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 700;
  font-size: 13px;
}

.user-meta {
  flex: 1;
  min-width: 0;
  display: grid;
  line-height: 1.25;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 12px;
  color: var(--text-muted);
}

.conn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.status-dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-dot.online {
  background: var(--success);
}

.status-dot.offline {
  background: var(--danger);
}
</style>
