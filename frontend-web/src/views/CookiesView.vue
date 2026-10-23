<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Política de Cookies</h1>
      <p class="updated">Última actualização: {{ new Date().getFullYear() }}</p>

      <section>
        <h2>O que são cookies</h2>
        <p>
          Cookies são pequenos ficheiros guardados no seu dispositivo para recordar preferências
          ou medir utilização do site.
        </p>
      </section>

      <section>
        <h2>Cookies que utilizamos</h2>
        <ul>
          <li><strong>Estritamente necessários</strong> — sessão do carrinho e preferência de consentimento.</li>
          <li><strong>Analytics (opcional)</strong> — PostHog, apenas se aceitar no banner.</li>
        </ul>
      </section>

      <section>
        <h2>Como gerir</h2>
        <p>
          Pode recusar cookies não essenciais no banner ao entrar no site. Para revogar analytics,
          limpe os dados do site no browser ou contacte-nos.
        </p>
      </section>

      <section>
        <h2>Mais informação</h2>
        <p>
          Consulte também a <RouterLink to="/privacidade">Política de Privacidade</RouterLink>.
        </p>
      </section>
    </article>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'

const breadcrumbItems = [
  { label: 'Início', to: { name: 'home' } },
  { label: 'Cookies' },
]
</script>

<style scoped>
.legal-page { padding-bottom: 2rem; }
.legal-content {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem var(--page-pad) 3rem;
  line-height: 1.7;
}
.legal-content h1 { font-size: clamp(1.85rem, 3vw, 2.25rem); margin-bottom: 0.5rem; }
.updated { color: var(--color-muted); margin-bottom: 2rem; }
section { margin-bottom: 1.5rem; }
section h2 {
  font-family: var(--font-body);
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--color-ink-soft);
}
ul { padding-left: 1.25rem; }
</style>
