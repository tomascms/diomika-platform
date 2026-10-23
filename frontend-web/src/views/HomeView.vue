<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useCategories } from '@/composables/useCategories'
import { categoryProductsRoute } from '@/lib/catalogRoutes'
import { COMPANY, whatsappUrl } from '@/lib/constants'
import SoftImage from '@/components/SoftImage.vue'

const { categories, loading, error, load } = useCategories()

const pretty = (name) => {
  const t = String(name || '').trim()
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
}

const withImage = computed(() => categories.value.filter((c) => c.imagem))
/** Até três imagens reais de categorias para o mosaico do topo. */
const heroTiles = computed(() => withImage.value.slice(0, 3))
const featured = computed(() => categories.value.slice(0, 6))
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-copy">
          <h1>Têxteis para o lar, prontos para a sua loja.</h1>
          <p class="hero-lead">
            Almofadas, assentos, toalhas de mesa, aventais e mais. Escolha modelos, cores e medidas
            e receba uma proposta comercial à medida.
          </p>
          <div class="hero-actions">
            <RouterLink to="/categorias" class="btn btn-primary">Ver catálogo</RouterLink>
            <RouterLink to="/contacto" class="btn btn-secondary">Falar connosco</RouterLink>
          </div>
          <p class="hero-note">Pedido mínimo de 500&nbsp;€ + IVA · Sem preços públicos: cada proposta é feita para si.</p>
        </div>

        <div class="hero-visual" aria-hidden="true">
          <span class="ribbon ribbon--blue" />
          <span class="ribbon ribbon--red" />
          <div class="mosaic" :class="`mosaic--${Math.max(heroTiles.length, 1)}`">
            <template v-if="heroTiles.length">
              <SoftImage
                v-for="(cat, i) in heroTiles"
                :key="cat.id"
                :src="cat.imagem"
                alt=""
                :eager="true"
                :fetchpriority="i === 0 ? 'high' : undefined"
                :thumb="i > 0"
                :sizes="i === 0 ? '(max-width: 900px) 50vw, 25vw' : undefined"
                img-class="mosaic-img"
              />
            </template>
            <span v-else class="mosaic-empty" />
          </div>
        </div>
      </div>
    </section>

    <section class="steps-section" aria-labelledby="how-title">
      <div class="page-shell">
        <h2 id="how-title" class="section-title">Como pedir um orçamento</h2>
        <ol class="steps">
          <li>
            <span class="step-n">1</span>
            <h3>Escolha os modelos</h3>
            <p>Percorra o catálogo e abra os modelos que lhe interessam.</p>
          </li>
          <li>
            <span class="step-n">2</span>
            <h3>Defina cores e quantidades</h3>
            <p>Para cada modelo, escolha cor, medida e quantidade e junte ao pedido.</p>
          </li>
          <li>
            <span class="step-n">3</span>
            <h3>Envie o pedido</h3>
            <p>A equipa comercial responde com a proposta para o seu pedido.</p>
          </li>
        </ol>
      </div>
    </section>

    <section class="catalog-section" aria-labelledby="catalog-title">
      <div class="page-shell">
        <div class="section-head">
          <h2 id="catalog-title" class="section-title">Catálogo</h2>
          <RouterLink to="/categorias" class="btn btn-ghost">Ver todas as categorias</RouterLink>
        </div>

        <div v-if="loading && !categories.length" class="cat-grid" aria-busy="true" aria-label="A carregar categorias">
          <span v-for="n in 3" :key="n" class="cat-skeleton" />
        </div>

        <div v-else-if="error && !categories.length" class="alert alert-error load-error" role="alert">
          <p>Não foi possível carregar o catálogo.</p>
          <button type="button" class="btn btn-secondary btn-sm" @click="load(true)">Tentar de novo</button>
        </div>

        <ul v-else-if="featured.length" class="cat-grid">
          <li v-for="cat in featured" :key="cat.id">
            <RouterLink :to="categoryProductsRoute(cat)" class="cat-tile">
              <span class="cat-media">
                <SoftImage v-if="cat.imagem" :src="cat.imagem" alt="" img-class="cat-img" thumb />
                <span v-else class="cat-fallback">{{ pretty(cat.nome).charAt(0) }}</span>
              </span>
              <span class="cat-name">{{ pretty(cat.nome) }}</span>
            </RouterLink>
          </li>
        </ul>
      </div>
    </section>

    <section class="contact-band" aria-labelledby="help-title">
      <div class="contact-inner">
        <div>
          <h2 id="help-title">Precisa de ajuda a escolher?</h2>
          <p>Fale directamente com a equipa comercial — por telefone, WhatsApp ou mensagem.</p>
        </div>
        <div class="contact-actions">
          <a :href="`tel:${COMPANY.phoneTel}`" class="btn btn-hero">{{ COMPANY.phoneDisplay }}</a>
          <a :href="whatsappUrl('Olá! Gostaria de pedir um orçamento.')" class="btn btn-hero-outline" target="_blank" rel="noopener">WhatsApp</a>
          <RouterLink to="/contacto" class="btn btn-hero-outline">Enviar mensagem</RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ---------- Topo ---------- */
.hero {
  overflow: hidden;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.hero-inner {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  align-items: center;
  gap: clamp(2rem, 5vw, 4.5rem);
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: clamp(2.5rem, 6vw, 5rem) var(--page-pad);
}

.hero-copy h1 {
  max-width: 14ch;
  font-size: clamp(2.25rem, 5vw, 3.75rem);
}

.hero-lead {
  max-width: 48ch;
  margin: 1.25rem 0 0;
  color: var(--color-ink-soft);
  font-size: 1.125rem;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 2rem;
}

.hero-note {
  margin: 1.5rem 0 0;
  color: var(--color-muted);
  font-size: 0.9rem;
}

/* A faixa em ângulo do símbolo (D azul, M vermelho) a enquadrar o mosaico.
   Desenhada com clip-path dentro da própria caixa — nada sai para cima do
   texto quando o layout passa a uma coluna. */
.hero-visual {
  position: relative;
  min-height: 380px;
  isolation: isolate;
}

.ribbon {
  position: absolute;
  display: block;
  z-index: -1;
}

.ribbon--blue {
  inset: 0 24% 4% 0;
  background: var(--brand-blue);
  clip-path: polygon(0 34%, 100% 0, 100% 70%, 0 100%);
}

.ribbon--red {
  top: 4%;
  right: 0;
  width: 20%;
  height: 62%;
  background: var(--brand-red);
  clip-path: polygon(0 22%, 100% 0, 100% 100%, 0 100%);
}

.mosaic {
  position: relative;
  display: grid;
  gap: 6px;
  min-height: 320px;
  margin: 12% 4% 0 10%;
  overflow: hidden;
  background: var(--color-bg-soft);
  clip-path: polygon(0 16%, 100% 0, 100% 100%, 0 100%);
}

.mosaic--2 {
  grid-template-columns: 1fr 1fr;
}

.mosaic--3 {
  grid-template-columns: 1.4fr 1fr;
  grid-template-rows: 1fr 1fr;
}

.mosaic--3 > :first-child {
  grid-row: 1 / 3;
}

.mosaic :deep(.soft-image),
.mosaic :deep(.soft-image__img) {
  width: 100%;
  height: 100%;
}

.mosaic :deep(.soft-image__img) {
  object-fit: cover;
}

/* ---------- Passos ---------- */
.steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
  margin: 1.5rem 0 0;
  padding: 0;
  list-style: none;
}

.steps li {
  padding-top: 1.25rem;
  border-top: 2px solid var(--color-ink-deep);
}

.step-n {
  display: block;
  margin-bottom: 0.75rem;
  color: var(--color-accent);
  font-size: 0.95rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.steps h3 {
  margin-bottom: 0.35rem;
}

.steps p {
  margin: 0;
  max-width: 34ch;
  color: var(--color-muted);
}

/* ---------- Catálogo ---------- */
.catalog-section .page-shell {
  padding-top: 0;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.section-head .section-title {
  margin: 0;
}

.cat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 240px), 1fr));
  gap: 1.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.cat-tile {
  display: grid;
  gap: 0.75rem;
  color: inherit;
}

.cat-media {
  position: relative;
  display: block;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: var(--color-bg-soft);
}

.cat-media :deep(.soft-image),
.cat-media :deep(.soft-image__img) {
  width: 100%;
  height: 100%;
}

.cat-media :deep(.soft-image__img) {
  object-fit: cover;
  transition: transform 0.5s cubic-bezier(0.2, 0, 0, 1);
}

.cat-tile:hover :deep(.soft-image__img) {
  transform: scale(1.03);
}

.cat-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--color-border-strong);
  font-size: 3.5rem;
  font-weight: 700;
  font-stretch: 125%;
}

.cat-name {
  color: var(--color-ink-deep);
  font-size: 1.1rem;
  font-weight: 660;
  font-stretch: 112%;
}

.cat-tile:hover .cat-name {
  color: var(--color-accent);
}

.cat-skeleton {
  display: block;
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-lg);
  background: linear-gradient(90deg, var(--color-bg-soft), var(--color-bg), var(--color-bg-soft));
  background-size: 200% 100%;
  animation: shimmer 1.3s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.load-error {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.load-error p {
  margin: 0;
}

/* ---------- Contacto ---------- */
.contact-band {
  background: var(--brand-blue-deep);
  color: rgba(255, 255, 255, 0.85);
}

.contact-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem 3rem;
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 3rem var(--page-pad);
}

.contact-inner h2 {
  color: #fff;
}

.contact-inner p {
  margin: 0.5rem 0 0;
}

.contact-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

/* ---------- Responsivo ---------- */
@media (max-width: 900px) {
  .hero-inner {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-visual {
    min-height: 0;
    max-width: 620px;
  }

  .mosaic {
    min-height: 260px;
  }

  .steps {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.25rem;
  }
}

@media (max-width: 560px) {
  .mosaic {
    min-height: 200px;
  }

  .hero-actions .btn {
    flex: 1 1 auto;
  }

  .section-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .section-head .btn {
    padding-left: 0;
  }
}
</style>
