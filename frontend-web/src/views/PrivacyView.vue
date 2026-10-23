<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Política de Privacidade</h1>
      <p class="updated">Última actualização: {{ new Date().getFullYear() }}</p>

      <section>
        <h2>Responsável</h2>
        <p>
          A Diomika trata os dados pessoais recolhidos através deste site e do formulário de contacto
          para responder aos seus pedidos e gerir a relação comercial.
        </p>
      </section>

      <section>
        <h2>Dados que recolhemos</h2>
        <ul>
          <li>Nome</li>
          <li>Endereço de email</li>
          <li>Contacto telefónico</li>
          <li>Conteúdo da mensagem enviada</li>
        </ul>
      </section>

      <section>
        <h2>Finalidade e base legal</h2>
        <p>
          Os dados são utilizados para responder ao seu contacto e, quando aplicável, para a gestão de
          encomendas ou pedidos de informação. A base legal é o <strong>interesse legítimo</strong> e/ou
          a <strong>execução de diligências pré-contratuais</strong> a seu pedido.
        </p>
      </section>

      <section>
        <h2>Conservação</h2>
        <p>
          Conservamos os dados pelo tempo necessário para responder e acompanhar a conversa, ou enquanto
          existir interesse comercial legítimo, salvo obrigação legal em contrário.
        </p>
        <ul>
          <li>Mensagens de contacto: até 24 meses (depois são apagadas automaticamente)</li>
          <li>Pedidos de orçamento: até 24 meses em estados terminais</li>
          <li>Registos técnicos de auditoria interna: até 12 meses</li>
        </ul>
        <p>
          Pode pedir o apagamento dos seus dados através do
          <RouterLink to="/contacto">formulário de contacto</RouterLink>
          (assunto: «Apagar os meus dados»). Tratamos o pedido após verificação de identidade.
        </p>
      </section>

      <section>
        <h2>Partilha com terceiros</h2>
        <p>
          Utilizamos fornecedores de alojamento e base de dados (Supabase), email (Gmail/SMTP) e, com o
          seu consentimento, analytics (PostHog) para melhorar o serviço. Não vendemos os seus dados.
        </p>
      </section>

      <section>
        <h2>Cookies e analytics</h2>
        <p>
          Utilizamos cookies estritamente necessários para o funcionamento do site. Analytics de produto
          (PostHog) só são activados se aceitar no banner de consentimento.
        </p>
      </section>

      <section>
        <h2>Os seus direitos</h2>
        <p>
          Pode solicitar acesso, rectificação, apagamento ou limitação do tratamento contactando-nos
          através do formulário de contacto ou do email indicado no site.
        </p>
      </section>

      <section>
        <h2>Contacto</h2>
        <p>
          Para questões sobre privacidade, use a página
          <RouterLink to="/contacto">Contacte-nos</RouterLink>.
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
  { label: 'Privacidade' },
]
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
ul {
  padding-left: 1.25rem;
}
</style>
