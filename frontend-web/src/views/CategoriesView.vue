<script setup>
import { RouterLink } from 'vue-router'
import { useCategories } from '@/composables/useCategories'
import { categoryProductsRoute } from '@/lib/catalogRoutes'
import { pretty } from '@/lib/describe'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ErrorState from '@/components/ErrorState.vue'
import SoftImage from '@/components/SoftImage.vue'

const { categories, loading, error, load } = useCategories()

const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Catálogo' }]
</script>

<template>
  <div class="categories-page">
    <Breadcrumbs :items="breadcrumbItems" />

    <header class="page-head">
      <div class="page-head-inner">
        <h1 class="page-title">Catálogo</h1>
        <p class="page-lead">
          Escolha uma categoria para ver modelos, cores e medidas.
        </p>
      </div>
    </header>

    <div class="page-shell page-shell--grid">
      <div
        v-if="loading && !categories.length"
        class="grid"
        aria-busy="true"
        aria-label="A carregar categorias"
      >
        <div v-for="n in 6" :key="n" class="tile tile--skeleton">
          <span class="tile-media skeleton" />
          <span class="tile-body"><span class="sk sk-title" /><span class="sk sk-sub" /></span>
        </div>
      </div>

      <ErrorState v-else-if="error && !categories.length" @retry="load(true)" />

      <ul v-else-if="categories.length" class="grid">
        <li v-for="(cat, i) in categories" :key="cat.id">
          <RouterLink :to="categoryProductsRoute(cat)" class="tile">
            <span class="tile-media">
              <SoftImage
                v-if="cat.imagem"
                :src="cat.imagem"
                :alt="''"
                :eager="i < 3"
                img-class="tile-img"
                thumb
              />
              <span v-else class="tile-fallback" aria-hidden="true">{{
                pretty(cat.nome).charAt(0)
              }}</span>
            </span>
            <span class="tile-body">
              <span class="tile-name">{{ pretty(cat.nome) }}</span>
              <span class="tile-cta">Ver modelos</span>
            </span>
          </RouterLink>
        </li>
      </ul>

      <div v-else class="state empty">
        <p>O catálogo está a ser atualizado. Entretanto, fale connosco para um orçamento.</p>
        <RouterLink to="/contacto" class="btn btn-primary">Contactar a Diomika</RouterLink>
      </div>

      <!-- Para quem já conhece as referências ou quer o catálogo em papel (RP-14). -->
      <p v-if="categories.length" class="shortcuts">
        Já conhece as referências?
        <RouterLink to="/pedido-rapido">Pedido rápido por EAN</RouterLink>
        ·
        <RouterLink to="/catalogo-imprimir">Catálogo para imprimir ou guardar em PDF</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.page-head {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.page-head-inner {
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 2rem var(--page-pad) 2.25rem;
}

.page-head .page-lead {
  margin-bottom: 0;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
  gap: 1.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.tile {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: inherit;
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.tile:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
  color: inherit;
}

.tile-media {
  position: relative;
  display: block;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--color-bg-soft);
}

.tile-media :deep(.soft-image),
.tile-media :deep(.soft-image__img) {
  width: 100%;
  height: 100%;
}

.tile-media :deep(.soft-image__img) {
  object-fit: cover;
  transition: transform 0.5s cubic-bezier(0.2, 0, 0, 1);
}

.tile:hover .tile-media :deep(.soft-image__img) {
  transform: scale(1.03);
}

.tile-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--color-border-strong);
  font-size: 4rem;
  font-weight: 700;
  font-stretch: 125%;
}

.tile-body {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.15rem 1.1rem;
}

.tile-name {
  color: var(--color-ink-deep);
  font-size: 1.15rem;
  font-weight: 680;
  font-stretch: 112%;
}

.tile-cta {
  flex: none;
  color: var(--color-accent);
  font-size: 0.9rem;
  font-weight: 600;
}

.tile:hover .tile-cta {
  color: var(--color-accent-hover);
}

.tile--skeleton {
  pointer-events: none;
}

.sk-title {
  width: 45%;
}

.sk-sub {
  width: 22%;
}

.tile--skeleton .tile-body {
  flex-direction: column;
  gap: 0.6rem;
}

.empty {
  padding: 2rem;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  color: var(--color-muted);
}

.shortcuts {
  margin: 2rem 0 0;
  color: var(--color-muted);
}

.shortcuts a {
  font-weight: 600;
}
</style>
