<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { COMPANY, MAP_URL, PRICE_NOTE, SELLS_TO_LINE, whatsappUrl } from '@/lib/constants'
import CallButton from '@/components/CallButton.vue'
import CompanyIdentity from '@/components/CompanyIdentity.vue'
const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Sobre nós' }]
</script>
<template>
  <div class="about-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <section class="hero">
      <div class="hero-inner">
        <h1>Têxteis para o lar, de Caldas das Taipas</h1>
        <p>
          A Diomika é uma empresa têxtil de Caldas das Taipas, em Guimarães. Temos têxteis para o
          lar: almofadas, assentos, toalhas de mesa, aventais e mais.
        </p>
        <p class="hero-note">{{ SELLS_TO_LINE }}</p>
      </div>
    </section>
    <section class="page-shell section">
      <div class="intro">
        <h2>Quem somos</h2>
        <p>
          Reunimos a oferta por categorias, modelos, cores e medidas, para escolher com calma e
          pedir só o que precisa.
        </p>
        <p>
          O site não apresenta preços: peça um orçamento e a nossa equipa responde com uma proposta
          à medida do seu pedido. {{ PRICE_NOTE }}
        </p>
      </div>
    </section>
    <section class="band">
      <div class="page-shell section">
        <h2>Como encomendar</h2>
        <ol class="steps">
          <li>
            <b>1</b><strong>Explore</strong
            ><span>Consulte as categorias ou pesquise por modelo ou EAN.</span>
          </li>
          <li>
            <b>2</b><strong>Escolha</strong><span>Selecione cores, medidas e quantidades.</span>
          </li>
          <li>
            <b>3</b><strong>Peça orçamento</strong
            ><span>Reveja o pedido e indique os seus dados.</span>
          </li>
          <li>
            <b>4</b><strong>Receba a resposta</strong
            ><span>A nossa equipa responde no prazo de 1 dia útil.</span>
          </li>
        </ol>
      </div>
    </section>
    <!-- Quem é e onde fica (RP-09): a identificação do prestador e uma ligação ao mapa, sem incorporar um mapa de terceiros. -->
    <section class="page-shell section where-section">
      <h2>Onde estamos</h2>
      <CompanyIdentity />
      <p class="where-map">
        <a :href="MAP_URL" target="_blank" rel="noopener noreferrer">Ver a morada no mapa</a>
      </p>
    </section>
    <section class="page-shell section contact-section">
      <h2>Fale diretamente connosco</h2>
      <p>Estamos disponíveis para esclarecer modelos, mínimos e condições de venda.</p>
      <div class="actions">
        <a
          class="btn btn-primary"
          :href="whatsappUrl('Olá! Gostaria de conhecer melhor a Diomika.')"
          target="_blank"
          rel="noopener noreferrer"
          >WhatsApp</a
        ><CallButton class="btn btn-secondary">Ligar {{ COMPANY.phoneDisplay }}</CallButton
        ><RouterLink class="btn btn-secondary" to="/categorias">Ver catálogo</RouterLink>
      </div>
    </section>
  </div>
</template>
<style scoped>
.about-page {
  background: var(--color-surface);
}
.hero {
  border-bottom: 1px solid var(--color-border);
}
.hero-inner {
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 2rem var(--page-pad) 2.5rem;
}
.hero h1 {
  max-width: 20ch;
  margin: 0 0 1rem;
}
.hero p {
  max-width: 60ch;
  margin: 0;
  color: var(--color-ink-soft);
  font-size: 1.1rem;
}
.hero .hero-note {
  margin-top: 1rem;
  color: var(--color-muted);
  font-size: 0.95rem;
}
.section {
  padding-top: 3rem;
  padding-bottom: 3rem;
}
.intro {
  max-width: 760px;
}
.where-section {
  padding-bottom: 0;
}
.where-section address {
  color: var(--color-muted);
  line-height: 1.65;
  font-size: 1.03rem;
}
.where-map {
  margin: 0.75rem 0 0;
}
.where-map a {
  font-weight: 600;
}
h2 {
  color: var(--color-ink-deep);
}
.intro p,
.contact-section p {
  color: var(--color-muted);
  line-height: 1.65;
  font-size: 1.03rem;
}
.band {
  background: var(--color-bg);
}
.steps {
  list-style: none;
  margin: 1.75rem 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}
.steps li {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding-top: 1.1rem;
  border-top: 2px solid var(--color-ink-deep);
}
.steps b {
  color: var(--color-accent);
  font-variant-numeric: tabular-nums;
}
.steps strong {
  color: var(--color-ink-deep);
}
.steps span {
  color: var(--color-muted);
  line-height: 1.5;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.7rem;
  margin-top: 1.25rem;
}
@media (max-width: 900px) {
  .steps {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 520px) {
  .steps {
    grid-template-columns: 1fr;
  }
}
</style>
