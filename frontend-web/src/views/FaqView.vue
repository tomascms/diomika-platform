<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Perguntas frequentes</h1>
      <p class="updated">Última actualização: {{ UPDATED }}</p>
      <p>
        As respostas resumem as
        <RouterLink to="/condicoes-de-venda">Condições gerais de venda</RouterLink>, onde está o
        texto completo.
      </p>

      <!-- O que aqui se promete a um consumidor passa a fazer parte do contrato (Lei n.º 24/96, art. 7.º, n.º 5):
           cada resposta tem de dizer o mesmo que as Condições gerais de venda. O e2e confere os valores. -->
      <details>
        <summary>Vendem a particulares?</summary>
        <div class="answer">
          <p>
            Sim. Vendemos a lojas, hotelaria e também a particulares, desde que a encomenda atinja o
            mínimo de {{ MIN_ORDER }}. Quem compra para fins que não são profissionais é consumidor
            e tem os direitos previstos na
            <RouterLink to="/condicoes-de-venda#parte-consumidores"
              >parte para consumidores das Condições gerais de venda</RouterLink
            >: informação antes de comprar, 14 dias para resolver o contrato e garantia legal de 3
            anos.
          </p>
        </div>
      </details>

      <details>
        <summary>Porque não há preços no site?</summary>
        <div class="answer">
          <p>
            Cada proposta é feita à medida: depende dos artigos, das quantidades e da entrega.
            {{ PRICE_NOTE }}
          </p>
        </div>
      </details>

      <details>
        <summary>Qual é a encomenda mínima?</summary>
        <div class="answer">
          <p>A encomenda mínima é de {{ MIN_ORDER }}.</p>
        </div>
      </details>

      <details>
        <summary>Como peço um orçamento? O pedido obriga-me a comprar?</summary>
        <div class="answer">
          <p>
            Junte os artigos ao <RouterLink to="/carrinho">pedido de orçamento</RouterLink> e
            envie-o com os seus dados, ou fale connosco por telefone, por WhatsApp ou pelo
            <RouterLink to="/contacto">formulário de contacto</RouterLink>. O pedido não o obriga a
            comprar nem obriga a Diomika a vender: o contrato só se forma quando aceitar por escrito
            a proposta que lhe enviarmos e nós confirmarmos a encomenda.
          </p>
        </div>
      </details>

      <details>
        <summary>Em quanto tempo respondem?</summary>
        <div class="answer">
          <p>Respondemos aos pedidos de orçamento no prazo de 1 dia útil.</p>
        </div>
      </details>

      <details>
        <summary>Quais são os prazos e as zonas de entrega? E os portes?</summary>
        <div class="answer">
          <p>
            A proposta indica as zonas de entrega, o prazo e os portes. A consumidores, se nada for
            acordado, entregamos sem demora injustificada e, o mais tardar, 30 dias após a
            celebração do contrato. Veja as secções «<RouterLink to="/condicoes-de-venda#entrega"
              >Entrega</RouterLink
            >» e «<RouterLink to="/condicoes-de-venda#entrega-e-risco">Entrega e risco</RouterLink
            >».
          </p>
        </div>
      </details>

      <details>
        <summary>Como posso pagar?</summary>
        <div class="answer">
          <p>
            Os meios de pagamento, os prazos e o eventual sinal ou pagamento antecipado constam da
            proposta. A consumidores, não cobramos nenhum pagamento adicional sem o seu
            consentimento expresso.
          </p>
        </div>
      </details>

      <!-- Canais da livre resolução: os mesmos das condições (SalesTermsView): carta para a sede e, em alternativa,
           qualquer outra declaração inequívoca (não só por carta). Quando COMPANY.email tiver valor (ficha do
           cliente, Parte D, item 2), acrescentar aqui o email, como lá. -->
      <details>
        <summary>Posso devolver os artigos?</summary>
        <div class="answer">
          <p>
            <strong>Particulares (consumidores):</strong> sim. Tem 14 dias, a contar do dia seguinte
            ao da recepção dos bens, para resolver o contrato sem indicar motivo. Envie o
            <RouterLink to="/condicoes-de-venda#formulario-livre-resolucao"
              >formulário-modelo</RouterLink
            >
            por carta para a nossa sede, ou comunique a sua decisão por qualquer outra declaração
            inequívoca, antes de o prazo acabar, e devolva os bens no máximo 14 dias depois de nos
            informar. Reembolsamos tudo o que pagou, incluindo os portes normais de envio, no prazo
            de 14 dias, e podemos esperar pelos bens ou pela prova do envio. Os custos de devolução
            são os que a proposta indicar; se nada indicar, pagamo-los nós. O direito não se aplica
            aos produtos por medida ou personalizados.
          </p>
          <p>
            <strong>Empresas:</strong> não há devolução por arrependimento; só por acordo escrito
            prévio, com os artigos intactos e com os custos de devolução a cargo do comprador.
          </p>
        </div>
      </details>

      <details>
        <summary>Que garantia têm os produtos?</summary>
        <div class="answer">
          <p>
            <strong>Particulares (consumidores):</strong> garantia legal de 3 anos a contar da
            entrega. Se o defeito aparecer nos primeiros 2 anos, presume-se que já existia na
            entrega. Pode pedir a reparação ou a substituição do bem, a redução do preço ou a
            resolução do contrato. Veja a secção «<RouterLink to="/condicoes-de-venda#garantia"
              >Garantia legal</RouterLink
            >».
          </p>
          <p>
            <strong>Empresas:</strong> devem inspeccionar os artigos na entrega e reclamar os
            defeitos aparentes no acto ou nos 8 dias seguintes; os defeitos ocultos, até 30 dias
            depois de os conhecerem e dentro de 6 meses a contar da entrega.
          </p>
        </div>
      </details>

      <details>
        <summary>Passam faturas com NIF de empresa?</summary>
        <div class="answer">
          <p>
            Sim. Indique o NIF e a denominação da empresa ao aceitar a proposta e a fatura é emitida
            com esses dados.
          </p>
        </div>
      </details>

      <details>
        <summary>Onde vejo a composição, os cuidados e o fabricante dos produtos?</summary>
        <div class="answer">
          <p>
            A composição, quando disponível, e as restantes características de cada modelo estão na
            página do produto no catálogo e na proposta. Se precisar de mais informação (composição,
            instruções de conservação ou identificação do fabricante), peça-a por telefone, por
            WhatsApp ou pelo
            <RouterLink to="/contacto">formulário de contacto</RouterLink> antes de aceitar a
            proposta.
          </p>
        </div>
      </details>

      <details>
        <summary>Fazem personalização? E a devolução?</summary>
        <div class="answer">
          <p>
            Pergunte-nos, antes de pedir a proposta, se o artigo que procura pode ser feito por
            medida ou personalizado. Quando um artigo é feito por medida ou personalizado (por
            exemplo, com bordado, logótipo ou medida feita a pedido), a proposta di-lo e o
            consumidor não pode resolver o contrato em 14 dias (Decreto-Lei n.º 24/2014, art. 17.º,
            n.º 1, al. c)). Escolher uma cor ou uma medida do catálogo não é personalizar. Veja a
            secção «<RouterLink to="/condicoes-de-venda#produtos-por-medida"
              >Produtos por medida ou personalizados</RouterLink
            >».
          </p>
        </div>
      </details>

      <details>
        <summary>Como posso reclamar?</summary>
        <div class="answer">
          <p>
            Por telefone, pelo <RouterLink to="/contacto">formulário de contacto</RouterLink> ou por
            carta para a nossa sede. Também pode usar o
            <a :href="COMPLAINTS_BOOK_URL" target="_blank" rel="noopener noreferrer"
              >Livro de Reclamações Eletrónico</a
            >
            e, sendo consumidor, recorrer ao {{ ADR_ENTITY.name }} (<a
              :href="`https://${ADR_ENTITY.site}`"
              target="_blank"
              rel="noopener noreferrer"
              >{{ ADR_ENTITY.site }}</a
            >). Respondemos às reclamações no prazo de 15 dias úteis.
          </p>
        </div>
      </details>

      <details>
        <summary>Como peço acesso ou apagamento dos meus dados?</summary>
        <div class="answer">
          <p>
            Pelo <RouterLink to="/contacto">formulário de contacto</RouterLink>, com o assunto
            «Acesso aos meus dados» ou «Apagar os meus dados». Tratamos o pedido depois de verificar
            a sua identidade. Veja a
            <RouterLink to="/privacidade">Política de Privacidade</RouterLink>.
          </p>
        </div>
      </details>
    </article>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { ADR_ENTITY, COMPLAINTS_BOOK_URL, MIN_ORDER, PRICE_NOTE } from '@/lib/constants'

// Actualizar à mão sempre que o texto mudar; as versões anteriores estão no git (log deste ficheiro).
const UPDATED = '29 de outubro de 2026'

const breadcrumbItems = [
  { label: 'Início', to: { name: 'home' } },
  { label: 'Perguntas frequentes' },
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
.legal-content a {
  text-decoration: underline;
  text-underline-offset: 2px;
}
details {
  border-bottom: 1px solid var(--color-border-strong);
}
details:first-of-type {
  border-top: 1px solid var(--color-border-strong);
}
summary {
  padding: 1rem 0;
  color: var(--color-ink-deep);
  font-weight: 650;
  cursor: pointer;
}
.answer {
  padding-bottom: 0.5rem;
}
.answer p {
  margin: 0 0 1rem;
}
</style>
