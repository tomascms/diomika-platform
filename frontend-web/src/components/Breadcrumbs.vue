<script setup>
defineOptions({ name: 'BreadcrumbTrail' })

defineProps({
  items: {
    type: Array,
    required: true,
  },
})
</script>

<template>
  <nav class="breadcrumbs" aria-label="Navegação">
    <div class="page-shell breadcrumbs-inner">
      <ol class="breadcrumb-list">
        <li v-for="(item, index) in items" :key="index" class="breadcrumb-item">
          <RouterLink v-if="item.to" :to="item.to">{{ item.label }}</RouterLink>
          <span v-else class="current">{{ item.label }}</span>
        </li>
      </ol>
    </div>
  </nav>
</template>

<style scoped>
/* Trilho discreto por cima do título — já não é uma barra escura fixa. */
.breadcrumbs {
  background: var(--color-surface);
}

.breadcrumbs-inner {
  padding-top: 1.1rem;
  padding-bottom: 0;
}

.breadcrumb-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.875rem;
}

.breadcrumb-item {
  display: inline-flex;
  align-items: center;
  color: var(--color-muted);
}

.breadcrumb-item:not(:last-child)::after {
  content: '/';
  margin-left: 0.4rem;
  color: var(--color-border-strong);
}

.breadcrumb-item a {
  color: var(--color-muted);
}

.breadcrumb-item a:hover {
  color: var(--color-accent);
}

.breadcrumb-item .current {
  color: var(--color-ink);
  font-weight: 560;
}
</style>
