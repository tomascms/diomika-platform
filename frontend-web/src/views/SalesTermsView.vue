<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Condições Gerais de Venda</h1>
      <p class="updated">Última actualização: {{ UPDATED }}</p>

      <p>
        Estas condições regem as vendas da {{ COMPANY.legalName }} («Diomika»). A
        <a href="#parte-comum">parte comum</a> aplica-se a todas as vendas; a
        <a href="#parte-empresas">parte para empresas</a>, às vendas a empresas e profissionais; a
        <a href="#parte-consumidores">parte para consumidores</a>, às vendas a consumidores. Quem
        compra como consumidor encontra o
        <a href="#formulario-livre-resolucao">formulário-modelo de livre resolução</a> na parte para
        consumidores.
      </p>

      <section>
        <h2 id="parte-comum">Parte comum: todas as vendas</h2>

        <h3 id="vendedor">Vendedor e contactos</h3>
        <p>O vendedor é:</p>
        <CompanyIdentity />
        <p>
          Os contactos para encomendas, esclarecimentos e reclamações são os indicados acima. Também
          pode falar connosco por
          <a :href="whatsappUrl()" target="_blank" rel="noopener noreferrer">WhatsApp</a>.
        </p>

        <h3 id="ambito">Âmbito</h3>
        <p>
          Estas condições regem todas as vendas da Diomika. Prevalecem sobre elas as condições
          particulares escritas na proposta, que nunca afastam os direitos do consumidor. A parte
          para empresas aplica-se a quem compra para a sua actividade comercial, industrial,
          artesanal ou profissional. A parte para consumidores aplica-se ao consumidor, isto é, a
          quem compra para fins que não pertencem a essa actividade, ainda que compre em quantidade.
          A proposta indica qual das partes se aplica; na dúvida, aplica-se a parte para
          consumidores.
        </p>

        <h3 id="formacao-do-contrato">Formação do contrato</h3>
        <p>
          O pedido de orçamento feito neste site não vincula o cliente nem a Diomika: é um convite
          para que a Diomika apresente uma proposta (Decreto-Lei n.º 7/2004, art. 32.º). O contrato
          forma-se assim:
        </p>
        <ol>
          <li>a Diomika envia uma proposta escrita, válida pelo prazo nela indicado;</li>
          <li>
            o cliente aceita a proposta por escrito, por exemplo por email ou por mensagem de
            WhatsApp;
          </li>
          <li>
            a Diomika confirma a encomenda num suporte duradouro, por exemplo por email. Nas vendas
            a consumidores, a confirmação é enviada no prazo de 5 dias a contar da celebração do
            contrato e, o mais tardar, até à entrega dos bens (Decreto-Lei n.º 24/2014, art. 6.º).
          </li>
        </ol>
        <p>
          Uma aceitação dada apenas por telefone não fecha o contrato: tem de ser confirmada por
          escrito.
        </p>

        <h3 id="produtos">Produtos</h3>
        <p>
          As características essenciais de cada produto (modelo, cor, medida e composição) constam
          do catálogo e da proposta. A composição indica-se com as denominações legais das fibras
          têxteis (Regulamento (UE) n.º 1007/2011). A cor no ecrã pode diferir da cor real e o
          fabrico têxtil admite pequenas variações de cor e de medida; as tolerâncias, quando as
          houver, indicam-se na proposta. Nas vendas a consumidores, estas variações não afastam o
          direito a receber bens conformes com o que foi contratado. Estar no catálogo não garante
          que o produto exista em stock: a disponibilidade confirma-se na proposta.
        </p>

        <h3 id="precos">Preços</h3>
        <p>
          Os preços são em euros e constam da proposta; o site não apresenta preços. A empresas, os
          preços indicam-se sem IVA, que acresce à taxa legal. {{ PRICE_NOTE }} Cada preço vale
          durante o prazo de validade da proposta.
        </p>

        <h3 id="encomenda-minima">Encomenda mínima</h3>
        <p>A encomenda mínima é de {{ MIN_ORDER }}. A proposta indica a taxa de IVA aplicável.</p>

        <h3 id="pagamento">Pagamento</h3>
        <p>
          Os meios de pagamento, os prazos e o eventual sinal ou pagamento antecipado são indicados
          na proposta escrita.
        </p>

        <h3 id="entrega">Entrega</h3>
        <p>
          As zonas de entrega, os prazos e os portes são indicados na proposta escrita. Recomendamos
          que, ao receber a encomenda, verifique o estado das embalagens e a quantidade entregue e
          nos avise de imediato de qualquer anomalia. Nas vendas a empresas, a inspecção e a
          reclamação seguem a parte para empresas; nas vendas a consumidores, esta verificação não
          condiciona nenhum direito.
        </p>

        <h3 id="produtos-por-medida">Produtos por medida ou personalizados</h3>
        <p>
          Os produtos feitos por medida ou manifestamente personalizados, por exemplo com bordado,
          logótipo ou medida feita a pedido, são identificados na proposta. Escolher uma cor ou uma
          medida do catálogo não torna o produto personalizado. Nas vendas a consumidores, o direito
          de livre resolução não se aplica a estes produtos (Decreto-Lei n.º 24/2014, art. 17.º, n.º
          1, al. c)).
        </p>

        <h3 id="reclamacoes">Reclamações</h3>
        <p>
          Pode reclamar por telefone, pelo
          <RouterLink to="/contacto">formulário de contacto</RouterLink>, por carta para a sede ou
          no
          <a :href="COMPLAINTS_BOOK_URL" target="_blank" rel="noopener noreferrer"
            >Livro de Reclamações Eletrónico</a
          >. Respondemos às reclamações no prazo de 15 dias úteis.
        </p>

        <h3 id="dados-pessoais">Dados pessoais</h3>
        <p>
          Os dados pessoais tratam-se nos termos da
          <RouterLink to="/privacidade">Política de Privacidade</RouterLink>.
        </p>

        <h3 id="lei-e-litigios">Lei aplicável e litígios</h3>
        <p>
          Aplica-se a lei portuguesa. Os litígios com consumidores seguem o que consta da parte para
          consumidores; os litígios com empresas, o que consta da parte para empresas.
        </p>

        <h3 id="versao">Entrega destas condições e versão</h3>
        <p>
          A Diomika envia estas condições ao cliente com a proposta, antes de este a aceitar. A cada
          venda aplica-se a versão enviada com a proposta. A versão em vigor é a desta página, com a
          data indicada no início.
        </p>
      </section>

      <section>
        <h2 id="parte-empresas">Parte para empresas: vendas a empresas e profissionais</h2>
        <p>
          Esta parte aplica-se a quem compra para a sua actividade comercial, industrial, artesanal
          ou profissional, e completa a parte comum.
        </p>

        <h3 id="empresas-pagamento">Pagamento e atraso</h3>
        <p>
          O pagamento faz-se como a proposta indicar, antecipadamente ou a prazo. Se não for feito
          até à data de vencimento, vencem-se juros de mora à taxa legal aplicável às transacções
          comerciais e o comprador paga, pelos custos de cobrança, o montante mínimo de 40&nbsp;€,
          sem prejuízo de indemnização superior se se provarem custos razoáveis mais elevados
          (Decreto-Lei n.º 62/2013, arts. 4.º e 7.º).
        </p>

        <h3 id="empresas-reserva-de-propriedade">Reserva de propriedade</h3>
        <p>
          A Diomika mantém a propriedade dos bens até receber o pagamento integral do preço (Código
          Civil, art. 409.º).
        </p>

        <h3 id="empresas-defeitos">Inspecção e reclamação de defeitos</h3>
        <p>
          O comprador deve inspeccionar os bens no acto da entrega. Os defeitos aparentes
          reclamam-se no acto da entrega ou nos 8 dias seguintes (Código Comercial, art. 471.º). Os
          defeitos ocultos comunicam-se até 30 dias depois de o comprador os conhecer e dentro de 6
          meses a contar da entrega (Código Civil, art. 916.º).
        </p>

        <h3 id="empresas-devolucoes">Devoluções</h3>
        <p>
          Nas vendas a empresas não existe direito de devolução por arrependimento. A devolução de
          artigos só é possível por acordo escrito prévio da Diomika, com os artigos intactos e com
          os custos de devolução a cargo do comprador, nas condições indicadas na proposta.
        </p>

        <h3 id="empresas-responsabilidade">Responsabilidade</h3>
        <p>
          A responsabilidade da Diomika por culpa leve limita-se ao valor da encomenda e não abrange
          danos indirectos, como os lucros cessantes. Esta limitação não se aplica a danos pessoais
          nem à morte, nem a danos causados com dolo ou culpa grave, nem ao que a lei não permita
          limitar (Decreto-Lei n.º 446/85, art. 18.º).
        </p>

        <h3 id="empresas-forca-maior">Força maior</h3>
        <p>
          Nenhuma das partes responde pelo atraso ou pelo incumprimento causados por força maior,
          isto é, por um acontecimento imprevisível e inevitável, alheio à sua vontade, enquanto
          durar o impedimento. A parte afectada avisa a outra logo que possível.
        </p>

        <h3 id="empresas-foro">Foro</h3>
        <p>
          Para os litígios das vendas a empresas é competente o tribunal da comarca de Guimarães,
          sem prejuízo das normas legais imperativas.
        </p>
      </section>

      <section>
        <h2 id="parte-consumidores">Parte para consumidores: vendas a consumidores</h2>
        <p>
          Esta parte aplica-se ao consumidor e completa a parte comum. As vendas a consumidores
          tratam-se como contratos celebrados à distância (Decreto-Lei n.º 24/2014). Nada nestas
          condições nem na proposta afasta ou limita os direitos que a lei reconhece ao consumidor.
        </p>

        <h3 id="informacao-pre-contratual">Informação antes de comprar</h3>
        <p>
          Antes de o consumidor aceitar a proposta, a Diomika dá-lhe, de forma clara e
          compreensível, as informações do art. 4.º, n.º 1, do Decreto-Lei n.º 24/2014 que se
          aplicam:
        </p>
        <ul>
          <li>
            a identidade e os contactos da Diomika, incluindo onde apresentar reclamações (<a
              href="#vendedor"
              >Vendedor e contactos</a
            >);
          </li>
          <li>as características essenciais dos bens (<a href="#produtos">Produtos</a>);</li>
          <li>
            o preço total, com IVA, e os portes ou, se não puderem ser calculados antes, o modo de
            os calcular (<a href="#precos">Preços</a>);
          </li>
          <li>
            as modalidades de pagamento e de entrega, o prazo de entrega e o tratamento de
            reclamações (<a href="#pagamento">Pagamento</a>, <a href="#entrega">Entrega</a> e
            <a href="#reclamacoes">Reclamações</a>);
          </li>
          <li>
            a existência do direito de livre resolução, o prazo e o modo de o exercer, com o
            formulário-modelo, e quem paga os custos de devolução (<a href="#livre-resolucao"
              >Livre resolução</a
            >);
          </li>
          <li>
            os casos em que não há livre resolução (<a href="#produtos-por-medida"
              >Produtos por medida ou personalizados</a
            >);
          </li>
          <li>
            a garantia legal de conformidade, o serviço pós-venda e as garantias comerciais, se as
            houver (<a href="#garantia">Garantia legal</a>);
          </li>
          <li>os códigos de conduta: a Diomika não está vinculada a nenhum;</li>
          <li>
            a entidade de resolução alternativa de litígios (<a href="#reclamacoes-e-litigios"
              >Livro de Reclamações e resolução de litígios</a
            >).
          </li>
        </ul>

        <h3 id="livre-resolucao">Livre resolução: 14 dias</h3>
        <p>
          O consumidor pode resolver o contrato, sem indicar qualquer motivo, no prazo de 14 dias
          (Decreto-Lei n.º 24/2014, arts. 10.º a 13.º). O direito não se aplica aos
          <a href="#produtos-por-medida">produtos por medida ou personalizados</a>. Seguem-se a
          informação sobre este direito e o formulário-modelo, tal como constam do anexo ao
          Decreto-Lei n.º 24/2014 (partes A e B), preenchidos para a Diomika.
        </p>

        <div id="informacao-livre-resolucao" class="statutory">
          <h4>Formulário de informação sobre o direito de livre resolução</h4>

          <h5>Direito de livre resolução</h5>
          <p>
            O consumidor tem o direito de livre resolução do presente contrato no prazo de 14 dias
            de calendário, sem necessidade de indicar qualquer motivo.
          </p>
          <p>
            O prazo para exercício do direito de livre resolução expira 14 dias a contar do dia
            seguinte ao dia em que adquire ou um terceiro por si indicado, que não seja o
            transportador, adquire a posse física dos bens; no caso de vários bens encomendados numa
            única encomenda e entregues separadamente, a posse física do último bem; no caso de um
            bem entregue em vários lotes ou partes, a posse física do último lote ou da última
            parte.
          </p>
          <!-- Canais da livre resolução: o formulário por carta para a sede e, em alternativa, qualquer outra
               declaração inequívoca, por qualquer meio (DL 24/2014, art. 11.º, n.os 1 e 2: carta, telefone,
               devolução do bem, outro meio suscetível de prova). Não prender «qualquer outra declaração
               inequívoca» à carta, nesta secção nem na resposta «Posso devolver os artigos?» das perguntas
               frequentes. Quando COMPANY.email tiver valor (ficha do cliente, Parte D, item 2), o email passa a
               canal: os v-if de COMPANY.email nesta secção tratam disso. O formulário de contacto não é canal:
               seria resolução por via electrónica no sítio e obrigaria a acusar a recepção em 24 h (art. 11.º,
               n.º 4). -->
          <p>
            A fim de exercer o seu direito de livre resolução, tem de nos comunicar a sua decisão de
            resolução do presente contrato por meio de uma declaração inequívoca (por exemplo, carta
            enviada pelo correio<template v-if="COMPANY.email"> ou correio eletrónico</template>).
            Pode utilizar o modelo de formulário de resolução, mas tal não é obrigatório.
          </p>
          <p>
            A comunicação dirige-se a {{ COMPANY.legalName }}, {{ COMPANY.address }},
            {{ COMPANY.postal }}, {{ COMPANY.municipality }}; telefone
            <a :href="`tel:${COMPANY.phoneTel}`">{{ COMPANY.phoneDisplay }}</a
            ><template v-if="phoneCost"> ({{ phoneCost }})</template
            ><template v-if="COMPANY.email"
              >; correio eletrónico
              <a :href="`mailto:${COMPANY.email}`">{{ COMPANY.email }}</a></template
            >.
          </p>
          <p>
            Para que o prazo de livre resolução seja respeitado, basta que a sua comunicação
            referente ao exercício do direito de livre resolução seja enviada antes do termo do
            prazo de resolução.
          </p>

          <h5>Efeitos da livre resolução</h5>
          <p>
            Em caso de resolução do presente contrato, ser-lhe-ão reembolsados todos os pagamentos
            efetuados, incluindo os custos de entrega (com exceção de custos suplementares
            resultantes da sua escolha de uma modalidade de envio diferente da modalidade menos
            onerosa de envio normal por nós oferecida), sem demora injustificada e, em qualquer
            caso, o mais tardar 14 dias a contar da data em que formos informados da sua decisão de
            resolução do presente contrato. Efetuamos esses reembolsos usando o mesmo meio de
            pagamento que usou na transação inicial, salvo acordo expresso em contrário da sua
            parte; em qualquer caso, não incorre em quaisquer custos como consequência de tal
            reembolso. Podemos reter o reembolso até termos recebido os bens devolvidos, ou até que
            apresente prova do envio dos bens, consoante o que ocorrer primeiro.
          </p>
          <p>
            Deve devolver os bens ou entregar-no-los, na morada da nossa sede ou na que lhe
            indicarmos, sem demora injustificada e o mais tardar 14 dias a contar do dia em que nos
            informar da livre resolução do contrato. Considera-se que o prazo é respeitado se
            devolver os bens antes do termo do prazo de 14 dias.
          </p>
          <p>
            Os custos diretos da devolução dos bens são os que a proposta indicar («Suportaremos os
            custos da devolução dos bens» ou «Tem de suportar os custos diretos da devolução dos
            bens»). Se a proposta nada indicar, suportamo-los nós. Se, pela sua natureza, os bens
            não puderem ser devolvidos normalmente pelo correio, a proposta indica o montante dos
            custos de devolução a cargo do consumidor.
          </p>
          <p>
            Só é responsável pela depreciação dos bens que decorra de uma manipulação que exceda o
            necessário para verificar a natureza, as características e o funcionamento dos bens.
          </p>
        </div>

        <div id="formulario-livre-resolucao" class="statutory">
          <h4>Modelo de formulário de livre resolução</h4>
          <p>(só deve preencher e devolver o presente formulário se quiser resolver o contrato)</p>
          <ul class="form-lines">
            <li>
              Para {{ COMPANY.legalName }}, {{ COMPANY.address }}, {{ COMPANY.postal }},
              {{ COMPANY.municipality
              }}<template v-if="COMPANY.email">, {{ COMPANY.email }}</template
              >:
            </li>
            <li>
              Pela presente comunico/comunicamos (*) que resolvo/resolvemos (*) do meu/nosso (*)
              contrato de compra e venda relativo ao seguinte bem (*)/para a prestação do seguinte
              serviço (*)
            </li>
            <li>Solicitado em (*)/recebido em (*)</li>
            <li>Nome do(s) consumidor(es)</li>
            <li>Endereço do(s) consumidor(es)</li>
            <li>
              Assinatura do(s) consumidor(es) (só no caso de o presente formulário ser notificado em
              papel)
            </li>
            <li>Data</li>
          </ul>
          <p>(*) Riscar o que não interessa.</p>
        </div>
        <p>
          Envie o formulário por carta para a nossa sede<template v-if="COMPANY.email">
            ou por correio eletrónico para
            <a :href="`mailto:${COMPANY.email}`">{{ COMPANY.email }}</a></template
          >, ou comunique a sua decisão por qualquer outra declaração inequívoca.
        </p>

        <h3 id="contratos-por-telefone">Contratos por telefone</h3>
        <p>
          Nas chamadas telefónicas, a Diomika identifica-se e indica o fim comercial da chamada logo
          no início (Decreto-Lei n.º 24/2014, art. 5.º, n.º 7). Se foi a Diomika a telefonar ao
          consumidor, este só fica vinculado depois de assinar a proposta ou de a aceitar por
          escrito (art. 5.º, n.º 8). Em qualquer caso, a Diomika confirma o contrato num suporte
          duradouro, no prazo de 5 dias a contar da sua celebração e, o mais tardar, até à entrega
          dos bens (art. 6.º).
        </p>

        <h3 id="garantia">Garantia legal</h3>
        <p>
          Os bens vendidos a consumidores têm garantia legal de conformidade de 3 anos a contar da
          entrega (Decreto-Lei n.º 84/2021, art. 12.º). Se a falta de conformidade se manifestar nos
          primeiros 2 anos, presume-se que já existia na data da entrega (art. 13.º). Em caso de
          falta de conformidade, o consumidor tem direito à reparação ou à substituição do bem, à
          redução proporcional do preço ou à resolução do contrato, nos termos da lei (art. 15.º).
        </p>
        <p>
          Para reclamar, comunique-nos a falta de conformidade por carta, pelo
          <RouterLink to="/contacto">formulário de contacto</RouterLink> ou por outro meio que lhe
          permita provar a comunicação (art. 12.º, n.º 5).
        </p>
        <p>
          O serviço pós-venda e qualquer garantia comercial, se os houver, constam da proposta. A
          garantia comercial é dada por escrito ou noutro suporte duradouro até à entrega dos bens,
          com as menções exigidas pelo art. 43.º do Decreto-Lei n.º 84/2021, e não afecta a garantia
          legal.
        </p>

        <h3 id="pagamentos-adicionais">Pagamentos adicionais</h3>
        <p>
          A Diomika não cobra nenhum pagamento adicional ao preço acordado sem o consentimento
          expresso do consumidor e não usa opções pré-seleccionadas que o consumidor tenha de
          recusar. Se isso acontecer, o consumidor tem direito à restituição do pagamento (Lei n.º
          24/96, art. 9.º-A).
        </p>

        <h3 id="entrega-e-risco">Entrega e risco</h3>
        <p>
          Se nada for acordado, a Diomika entrega os bens sem demora injustificada e, o mais tardar,
          30 dias após a celebração do contrato (Decreto-Lei n.º 84/2021, art. 11.º, n.º 5;
          Decreto-Lei n.º 24/2014, art. 19.º, n.º 1). O risco de perda ou de dano dos bens passa
          para o consumidor quando este, ou um terceiro por si indicado que não seja o
          transportador, recebe os bens (Decreto-Lei n.º 84/2021, art. 11.º, n.º 12).
        </p>

        <h3 id="reclamacoes-e-litigios">Livro de Reclamações e resolução de litígios</h3>
        <p>
          O consumidor pode apresentar a sua reclamação no
          <a :href="COMPLAINTS_BOOK_URL" target="_blank" rel="noopener noreferrer"
            >Livro de Reclamações Eletrónico</a
          >. Em caso de litígio de consumo, pode recorrer ao {{ ADR_ENTITY.name }} (<a
            :href="`https://${ADR_ENTITY.site}`"
            target="_blank"
            rel="noopener noreferrer"
            >{{ ADR_ENTITY.site }}</a
          >). Nos litígios de valor até 5&nbsp;000&nbsp;€, a arbitragem é necessária quando o
          consumidor a escolha (Lei n.º 24/96, art. 14.º, n.º 2). Mais informação no Portal do
          Consumidor (<a
            href="https://www.consumidor.gov.pt"
            target="_blank"
            rel="noopener noreferrer"
            >www.consumidor.gov.pt</a
          >) e em <RouterLink to="/termos#resolucao-de-litigios">Informação legal</RouterLink>.
        </p>

        <h3 id="lei-aplicavel-consumidores">Lei aplicável</h3>
        <p>
          Aplica-se a lei portuguesa, sem prejuízo das normas imperativas de protecção do
          consumidor. Estas condições não têm cláusula de foro: o consumidor pode recorrer aos
          tribunais competentes nos termos da lei.
        </p>
      </section>
    </article>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import CompanyIdentity from '@/components/CompanyIdentity.vue'
import {
  ADR_ENTITY,
  COMPANY,
  COMPLAINTS_BOOK_URL,
  MIN_ORDER,
  PRICE_NOTE,
  callCostNote,
  whatsappUrl,
} from '@/lib/constants'

// Actualizar à mão sempre que o texto mudar; as versões anteriores estão no git (log deste ficheiro).
const UPDATED = '29 de outubro de 2026'

const phoneCost = callCostNote(COMPANY.phoneDisplay)

const breadcrumbItems = [
  { label: 'Início', to: { name: 'home' } },
  { label: 'Condições gerais de venda' },
]
</script>

<style scoped>
.legal-page {
  padding-bottom: 2rem;
}
/*
 * Condições a consumidores: letra não inferior a 11 pt (2,5 mm) nem entrelinha inferior a 1,15
 * (Decreto-Lei n.º 446/85, art. 21.º, al. i)). O texto herda 16 px (12 pt) do `body`; nada nesta página
 * fica abaixo de 1rem nem de 1,15 de entrelinha, e o e2e mede-o.
 */
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
.legal-content h2 {
  margin: 3rem 0 1rem;
  padding-top: 1.25rem;
  border-top: 2px solid var(--color-ink-deep);
  font-size: clamp(1.35rem, 2.4vw, 1.75rem);
}
.legal-content h3 {
  margin: 2rem 0 0.5rem;
  font-size: 1.15rem;
}
.legal-content h4 {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
}
.legal-content h5 {
  margin: 1.25rem 0 0.4rem;
  font-size: 1rem;
}
.legal-content p {
  margin: 0 0 1rem;
}
.legal-content ul,
.legal-content ol {
  margin: 0 0 1rem;
  padding-left: 1.25rem;
}
.legal-content li {
  margin-bottom: 0.4rem;
}
.legal-content a {
  text-decoration: underline;
  text-underline-offset: 2px;
}
.legal-content address {
  margin: 0 0 1rem;
}

/* O texto do anexo ao Decreto-Lei n.º 24/2014 (partes A e B), à parte do resto das condições. */
.statutory {
  margin: 1.25rem 0;
  padding: 1.25rem 1.35rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
}
.statutory > :last-child {
  margin-bottom: 0;
}
.legal-content .form-lines {
  list-style: none;
  padding-left: 0;
}
.form-lines li {
  margin: 0;
  padding: 0.6rem 0;
  border-bottom: 1px dashed var(--color-border-strong);
}
</style>
