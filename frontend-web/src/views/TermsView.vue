<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Aviso Legal</h1>
      <p class="updated">Última actualização: {{ new Date().getFullYear() }}</p>

      <section>
        <h2>Identificação</h2>
        <p>
          Este site é operado pela Diomika. Para dados de contacto comercial, consulte a página
          <RouterLink to="/contacto">Contacto</RouterLink>.
        </p>
      </section>

      <section>
        <h2>Objecto do site</h2>
        <p>
          O site destina-se à apresentação do catálogo B2B e à recepção de pedidos de orçamento.
          A informação publicada tem carácter informativo e pode ser alterada sem aviso prévio.
        </p>
      </section>

      <section>
        <h2>Propriedade intelectual</h2>
        <p>
          Textos, imagens, logótipos e design são propriedade da Diomika ou dos respectivos titulares.
          É proibida a reprodução sem autorização escrita.
        </p>
      </section>

      <section>
        <h2>Responsabilidade</h2>
        <p>
          A Diomika esforça-se por manter informação correcta, mas não garante a ausência de erros
          tipográficos ou indisponibilidade temporária do serviço.
        </p>
      </section>

      <section>
        <h2>Legislação aplicável</h2>
        <p>Lei portuguesa. Foro competente: Portugal.</p>
      </section>
    </article>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'

const breadcrumbItems = [
  { label: 'Início', to: { name: 'home' } },
  { label: 'Aviso legal' },
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
</style>
