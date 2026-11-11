<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Política de Cookies</h1>
      <p class="updated">Última actualização: {{ UPDATED }}</p>

      <section>
        <h2>O que são cookies e tecnologias semelhantes</h2>
        <p>
          Cookies são pequenos ficheiros que um site guarda no seu dispositivo. A lei dá o mesmo
          tratamento às tecnologias semelhantes (Lei n.º 41/2004, art. 5.º): o armazenamento local
          do navegador (<code>localStorage</code> e <code>sessionStorage</code>) e os scripts que
          leem o dispositivo. Este site não grava cookies próprios: usa o armazenamento do
          navegador, que está listado abaixo.
        </p>
      </section>

      <section id="tabela">
        <h2>O que o site guarda no seu dispositivo</h2>
        <p>
          <strong>Necessário</strong>: indispensável para o site funcionar e ser seguro; não precisa
          do seu consentimento. <strong>Funcional</strong>: guarda um rascunho a seu pedido.
          <strong>Analytics</strong>: mede a utilização do site e só funciona com o seu
          consentimento.
        </p>
        <table class="legal-table">
          <caption class="visually-hidden">
            Nome, tipo, finalidade, categoria, duração e fornecedor de cada item
          </caption>
          <thead>
            <tr>
              <th scope="col">Nome e tipo</th>
              <th scope="col">Finalidade</th>
              <th scope="col">Categoria</th>
              <th scope="col">Duração</th>
              <th scope="col">Fornecedor</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in ITEMS" :key="row.names[0]">
              <th scope="row" data-label="Nome e tipo">
                <template v-for="name in row.names" :key="name">
                  <strong v-if="row.script">{{ name }}</strong
                  ><code v-else
                    ><template v-for="(part, i) in breakable(name)" :key="i"
                      ><wbr v-if="i" />{{ part }}</template
                    ></code
                  ><br />
                </template>
                <span class="item-type">{{ row.type }}</span>
              </th>
              <td data-label="Finalidade">{{ row.purpose }}</td>
              <td data-label="Categoria">{{ row.category }}</td>
              <td data-label="Duração">{{ row.duration }}</td>
              <td data-label="Fornecedor">{{ row.provider }}</td>
            </tr>
          </tbody>
        </table>
        <p>
          A Cloudflare, que serve o site, pode gravar cookies técnicos de segurança da sua rede. São
          estritamente necessários.
        </p>
      </section>

      <section id="gerir">
        <h2>Como gerir o consentimento</h2>
        <ul>
          <li>
            Na primeira visita aparece um banner com dois botões do mesmo tamanho, «Recusar» e
            «Aceitar»: recusar custa o mesmo clique que aceitar. Sem consentimento, o PostHog nunca
            é carregado e o site funciona na mesma.
          </li>
          <li>
            Pode mudar de escolha a qualquer momento em «Preferências de cookies», no rodapé de
            qualquer página, ou no botão abaixo: reabre o banner. Se retirar o consentimento, o
            PostHog pára de imediato e apagamos do seu dispositivo o que ele guardou para medir;
            fica apenas uma marca a lembrar que recusou.
          </li>
          <li>
            A sua escolha (estado, versão desta política e data) fica guardada 12 meses. Passado
            esse prazo, ou quando esta política mudar, voltamos a perguntar.
          </li>
          <li>
            Pode também apagar os dados do site nas definições do navegador, o que apaga o pedido de
            orçamento em curso e a sua escolha, ou bloquear o armazenamento (o site pode deixar de
            funcionar bem).
          </li>
        </ul>
        <button
          type="button"
          class="btn btn-secondary ph-no-capture"
          @click="cookieBanner.open($event.currentTarget)"
        >
          Abrir as preferências de cookies
        </button>
      </section>

      <section>
        <h2>Políticas dos fornecedores</h2>
        <ul>
          <li>
            Cloudflare Turnstile:
            <a
              href="https://www.cloudflare.com/turnstile-privacy-policy/"
              target="_blank"
              rel="noopener noreferrer"
              >política de privacidade do Turnstile</a
            >.
          </li>
          <li>
            PostHog:
            <a href="https://posthog.com/privacy" target="_blank" rel="noopener noreferrer"
              >posthog.com/privacy</a
            >.
          </li>
        </ul>
      </section>

      <section>
        <h2>Responsável e contacto</h2>
        <p>
          O responsável é a {{ COMPANY.legalName }} (<RouterLink to="/termos"
            >identificação completa</RouterLink
          >). Para qualquer questão sobre cookies ou dados pessoais use o
          <RouterLink to="/contacto">formulário de contacto</RouterLink>. Consulte também a
          <RouterLink to="/privacidade">Política de Privacidade</RouterLink>.
        </p>
      </section>
    </article>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { useCookieBanner } from '@/composables/useCookieBanner'
import { COMPANY } from '@/lib/constants'

// Actualizar à mão sempre que o texto mudar; as versões anteriores estão no git (log deste ficheiro).
// Se a lista de baixo ou o PostHog mudarem, mudar também CONSENT_VERSION (lib/consent.js): pergunta-se de novo.
const UPDATED = '2 de novembro de 2026'

const cookieBanner = useCookieBanner()

// Os nomes das chaves partem-se depois do «_», e não a meio das palavras, quando a coluna é estreita.
const breakable = (name) =>
  name.split('_').map((part, i, parts) => (i < parts.length - 1 ? `${part}_` : part))

// Tudo o que o site guarda no navegador. O e2e (e2e/local/cookies.spec.js) confere que cada chave que
// o site escreve consta daqui.
const ITEMS = [
  {
    names: ['diomika_cart'],
    type: 'localStorage',
    purpose: 'Guarda os artigos do seu pedido de orçamento.',
    category: 'Necessário',
    duration: 'Até enviar o pedido ou limpar os dados do site',
    provider: 'Diomika',
  },
  {
    names: ['diomika_cookie_consent'],
    type: 'localStorage',
    purpose: 'Guarda a sua escolha sobre estes cookies: estado, versão da política e data.',
    category: 'Necessário',
    duration: '12 meses',
    provider: 'Diomika',
  },
  {
    names: ['diomika_quote_form_draft'],
    type: 'localStorage',
    purpose:
      'Rascunho das observações do pedido de orçamento, para não as perder. Não guarda o nome, o email nem o telefone.',
    category: 'Funcional',
    duration: 'Até enviar o pedido',
    provider: 'Diomika',
  },
  {
    names: ['diomika-contact-idempotency', 'diomika-orcamento-idempotency'],
    type: 'sessionStorage',
    purpose: 'Identificador que evita enviar duas vezes o mesmo formulário.',
    category: 'Necessário',
    duration: 'Sessão; apagado quando o formulário é enviado',
    provider: 'Diomika',
  },
  {
    names: ['diomika-origem'],
    type: 'sessionStorage',
    purpose:
      'Página por onde entrou, site de onde veio e último modelo visto, enviados com o pedido ou a mensagem para percebermos o que procura. Só com o seu consentimento; sem nome, email nem identificador.',
    category: 'Analytics',
    duration: 'Sessão',
    provider: 'Diomika',
  },
  {
    names: ['diomika_cats_v6', 'diomika_cat_models_v2', 'diomika_signed_v5'],
    type: 'sessionStorage',
    purpose:
      'Memória temporária das categorias, dos modelos e das imagens, para o catálogo abrir mais depressa.',
    category: 'Necessário',
    duration: 'Sessão',
    provider: 'Diomika',
  },
  {
    names: ['Cloudflare Turnstile'],
    script: true,
    type: 'Script e iframe de challenges.cloudflare.com, só em Contacto e Pedido de orçamento',
    purpose: 'Verificação anti-spam dos formulários.',
    category: 'Necessário (segurança)',
    duration: 'Definida pela Cloudflare',
    provider: 'Cloudflare',
  },
  {
    names: ['ph_<chave>_posthog', 'ph_<chave>_*'],
    type: 'localStorage e sessionStorage',
    purpose:
      'Medição das páginas e dos cliques visitados, do que pesquisa no catálogo e do tempo que as páginas demoram a abrir. Só com o seu consentimento.',
    category: 'Analytics',
    duration:
      'Até recusar; se a escolha expirar (12 meses), apagam-se na visita seguinte. As da sessão acabam com ela.',
    provider: 'PostHog (União Europeia)',
  },
  {
    names: ['__ph_opt_in_out_<chave>'],
    type: 'localStorage',
    purpose:
      'Lembra se aceitou ou recusou a medição, para o PostHog só medir com consentimento. Só existe depois de recusar.',
    category: 'Necessário',
    duration: 'Fica depois de recusar, mesmo que volte a aceitar, até limpar os dados do site',
    provider: 'PostHog (União Europeia)',
  },
]

const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Cookies' }]
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
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--color-ink-soft);
}
ul {
  padding-left: 1.25rem;
}
.legal-content a {
  text-decoration: underline;
  text-underline-offset: 2px;
}
.item-type {
  color: var(--color-muted);
  font-weight: 400;
}
</style>
