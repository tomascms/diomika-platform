<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Informação legal</h1>
      <p class="updated">Última actualização: {{ UPDATED }}</p>

      <section>
        <h2>Identificação</h2>
        <CompanyIdentity />
        <p>Actividade: comércio por grosso de têxteis para o lar</p>
      </section>

      <section>
        <h2>Objecto do site</h2>
        <p>
          O site destina-se à apresentação do catálogo e à recepção de pedidos de orçamento. O
          pedido de orçamento é um convite a contratar e não vincula o cliente nem a Diomika
          (Decreto-Lei n.º 7/2004, art. 32.º). A informação publicada tem carácter informativo e
          pode ser alterada sem aviso prévio.
        </p>
      </section>

      <section>
        <h2>Destinatários</h2>
        <p>
          O site destina-se a empresas e profissionais e também a particulares. Os particulares têm
          os direitos de consumidor descritos nas
          <RouterLink to="/condicoes-de-venda#parte-consumidores"
            >Condições gerais de venda</RouterLink
          >.
        </p>
      </section>

      <section>
        <h2>Propriedade intelectual</h2>
        <p>
          Textos, imagens, logótipos e design são propriedade da Diomika ou dos respectivos
          titulares. É proibida a reprodução sem autorização escrita.
        </p>
      </section>

      <section>
        <h2>Responsabilidade</h2>
        <p>
          A Diomika esforça-se por manter informação correcta, mas não garante a ausência de erros
          tipográficos ou indisponibilidade temporária do serviço, sem prejuízo dos direitos legais
          dos consumidores e da responsabilidade por dolo ou culpa grave.
        </p>
      </section>

      <section id="livro-de-reclamacoes">
        <h2>Livro de Reclamações</h2>
        <p>
          Pode apresentar a sua reclamação no
          <a :href="COMPLAINTS_BOOK_URL" target="_blank" rel="noopener noreferrer"
            >Livro de Reclamações Eletrónico</a
          >
          (www.livroreclamacoes.pt).
        </p>
      </section>

      <section id="resolucao-de-litigios">
        <h2>Resolução de litígios</h2>
        <p>
          Em caso de litígio de consumo, o consumidor pode recorrer ao {{ ADR_ENTITY.name }} · Rua
          Capitão Alfredo Guimarães, 1, 4800-019 Guimarães · 253 422 410 · geral@triave.pt ·
          <a :href="`https://${ADR_ENTITY.site}`" target="_blank" rel="noopener noreferrer">{{
            ADR_ENTITY.site
          }}</a
          >. Nos litígios de valor até 5&nbsp;000&nbsp;€, a arbitragem é necessária quando o
          consumidor a escolha (Lei n.º 24/96, art. 14.º, n.º 2). Mais informação no Portal do
          Consumidor (<a
            href="https://www.consumidor.gov.pt"
            target="_blank"
            rel="noopener noreferrer"
            >www.consumidor.gov.pt</a
          >).
        </p>
      </section>

      <section>
        <h2>Legislação aplicável</h2>
        <p>
          Lei portuguesa. Os litígios são decididos pelos tribunais competentes, sem prejuízo das
          normas imperativas aplicáveis aos consumidores e do recurso aos meios de resolução
          alternativa de litígios acima indicados.
        </p>
      </section>
    </article>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import CompanyIdentity from '@/components/CompanyIdentity.vue'
import { ADR_ENTITY, COMPLAINTS_BOOK_URL } from '@/lib/constants'

// Actualizar à mão sempre que o texto mudar; as versões anteriores estão no git (log deste ficheiro).
const UPDATED = '29 de outubro de 2026'

const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Informação legal' }]
</script>

<style scoped>
.legal-page {
  padding-bottom: 2rem;
}
.legal-content {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem var(--page-pad) 3rem;
  line-height: 1.7;
}
.legal-content h1 {
  font-size: clamp(1.85rem, 3vw, 2.25rem);
  margin-bottom: 0.5rem;
}
.updated {
  color: var(--color-muted);
  margin-bottom: 2rem;
}
section {
  margin-bottom: 1.5rem;
}
section h2 {
  font-family: var(--font-body);
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--color-ink-soft);
}
</style>
