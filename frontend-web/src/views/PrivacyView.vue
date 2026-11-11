<template>
  <div class="legal-page">
    <Breadcrumbs :items="breadcrumbItems" />
    <article class="legal-content">
      <h1>Política de Privacidade</h1>
      <p class="updated">Última actualização: {{ UPDATED }}</p>
      <p>
        Explica que dados pessoais tratamos quando visita este site, pede um orçamento ou nos
        contacta, para quê, durante quanto tempo, quem os recebe e que direitos tem (Regulamento
        (UE) 2016/679, o RGPD, e Lei n.º 58/2019).
      </p>

      <section id="responsavel">
        <h2>1. Responsável pelo tratamento</h2>
        <CompanyIdentity />
        <p>
          Não temos encarregado de protecção de dados, porque a lei não o exige. Para qualquer
          questão sobre dados pessoais, ou para exercer os seus direitos, use o
          <RouterLink to="/contacto">formulário de contacto</RouterLink> ou escreva-nos para a sede.
        </p>
      </section>

      <section id="finalidades">
        <h2>2. Para que tratamos os seus dados</h2>
        <table class="legal-table">
          <caption class="visually-hidden">
            Finalidade, dados, base legal e prazo de conservação de cada tratamento
          </caption>
          <thead>
            <tr>
              <th scope="col">Finalidade</th>
              <th scope="col">Dados</th>
              <th scope="col">Base legal</th>
              <th scope="col">Prazo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in PURPOSES" :key="row.purpose">
              <th scope="row" data-label="Finalidade">{{ row.purpose }}</th>
              <td data-label="Dados">{{ row.data }}</td>
              <td data-label="Base legal">{{ row.basis }}</td>
              <td data-label="Prazo">{{ row.term }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section id="interesses">
        <h2>3. Interesses legítimos</h2>
        <p>
          Quando a base legal é o interesse legítimo (art. 6.º, n.º 1, al. f)), esse interesse é:
          manter o site e a empresa seguros e evitar fraude e spam; e gerir a relação com clientes e
          contactos de empresas, respondendo-lhes e acompanhando a conversa. Pesámos esse interesse
          contra os seus direitos e tratamos só o que é necessário. Tem o direito de se
          <a href="#oposicao">opor</a> a este tratamento.
        </p>
      </section>

      <section id="obrigatorios">
        <h2>4. Dados obrigatórios e facultativos</h2>
        <p>
          Para o pedido de orçamento e para o contacto, o nome e o email são obrigatórios: sem eles
          não podemos responder-lhe (art. 13.º, n.º 2, al. e)). O telefone, a empresa, o NIF e a
          localidade são facultativos. A medição de audiência também: o site funciona sem ela.
        </p>
      </section>

      <section id="destinatarios">
        <h2>5. Quem recebe os dados</h2>
        <p>
          Não vendemos os seus dados. Recorremos aos fornecedores abaixo. A tabela diz, em cada um,
          quem decide para que os dados servem.
        </p>
        <table class="legal-table">
          <caption class="visually-hidden">
            Fornecedores, função, quem decide, local dos dados e mecanismo de transferência
          </caption>
          <thead>
            <tr>
              <th scope="col">Entidade</th>
              <th scope="col">Função</th>
              <th scope="col">Quem decide para que os dados servem</th>
              <th scope="col">Onde ficam os dados</th>
              <th scope="col">Transferência para fora da União Europeia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in RECIPIENTS" :key="row.name">
              <th scope="row" data-label="Entidade">{{ row.name }}</th>
              <td data-label="Função">{{ row.role }}</td>
              <td data-label="Quem decide para que os dados servem">{{ row.decides }}</td>
              <td data-label="Onde ficam os dados">{{ row.where }}</td>
              <td data-label="Transferência para fora da União Europeia">{{ row.transfer }}</td>
            </tr>
          </tbody>
        </table>
        <p>
          Comunicamos também dados a quem a lei obrigue (por exemplo, à Autoridade Tributária e
          Aduaneira), ao contabilista da empresa, para a faturação, e às transportadoras que
          entregam as encomendas.
        </p>
      </section>

      <section id="transferencias">
        <h2>6. Transferências para fora da União Europeia</h2>
        <p>
          Alguns fornecedores da tabela acima tratam dados fora da União Europeia, nomeadamente nos
          EUA. Nesses casos, a transferência assenta na decisão de adequação UE-EUA (Data Privacy
          Framework; art. 45.º do RGPD), quando o fornecedor está certificado, ou em outras
          garantias adequadas do art. 46.º do RGPD, como as cláusulas contratuais-tipo da Comissão.
          Pode pedir-nos uma cópia dessas garantias pelo
          <RouterLink to="/contacto">formulário de contacto</RouterLink> ou por carta para a sede.
        </p>
      </section>

      <section id="conservacao">
        <h2>7. Quanto tempo conservamos os dados</h2>
        <p>Os prazos de cada tratamento estão na tabela do ponto 2. Em resumo:</p>
        <ul>
          <li>
            As mensagens de contacto guardadas na nossa base de dados são apagadas automaticamente
            ao fim de 24 meses.
          </li>
          <li>
            Os pedidos de orçamento que não dão venda conservam-se 24 meses. O que deu venda, e a
            correspondência dessa venda, conserva-se 10 anos, como a lei exige para os documentos
            comerciais e fiscais.
          </li>
          <li>Os registos de auditoria do backoffice são apagados ao fim de 12 meses.</li>
          <li>
            Os registos técnicos e os erros não têm um prazo nosso. No servidor (Render), os registos
            da aplicação ficam pelo período de retenção do Render e os ficheiros de falhas e de avisos
            que a aplicação escreve apagam-se sempre que ela reinicia ou é actualizada. No Axiom
            (registos do servidor) e no Sentry (erros) ficam pelo período de retenção de cada um, que é
            de 30 dias no plano gratuito.
          </li>
          <li>
            As cópias de segurança diárias da base de dados guardam-se 14 dias, num espaço privado do
            GitHub, e depois apagam-se sozinhas; o que for apagado da base de dados desaparece das
            cópias nesse prazo.
          </li>
          <li>
            As cópias que existam na caixa de email seguem os mesmos prazos: revemos a caixa uma vez
            por ano e apagamos o que já passou do prazo.
          </li>
        </ul>
        <p>
          Passado o prazo, apagamos os dados ou tornamo-los anónimos. Se pedir o apagamento,
          apagamos o que não tenhamos de conservar por lei.
        </p>
      </section>

      <section id="direitos">
        <h2>8. Os seus direitos</h2>
        <p>
          Tem direito de acesso, de rectificação, de apagamento, de limitação do tratamento e de
          portabilidade dos seus dados. Pode retirar o consentimento a qualquer momento, sem afectar
          o tratamento anterior: para a medição de audiência, em «Preferências de cookies», no
          rodapé de qualquer página.
        </p>
        <div id="oposicao" class="highlight">
          <h3>Direito de oposição</h3>
          <p>
            Pode opor-se a qualquer momento ao tratamento dos seus dados que se baseie no nosso
            interesse legítimo (art. 21.º do RGPD). Deixamos de os tratar, salvo se demonstrarmos
            razões legítimas imperiosas que prevaleçam sobre os seus interesses, direitos e
            liberdades.
          </p>
        </div>
        <p>
          Para exercer um direito, use o
          <RouterLink to="/contacto">formulário de contacto</RouterLink>, por exemplo com o assunto
          «Acesso aos meus dados» ou «Apagar os meus dados», ou escreva-nos para a sede. Podemos
          pedir o que for necessário para confirmar a sua identidade. Respondemos no prazo de um
          mês, que pode ser prorrogado por mais dois meses se o pedido for complexo, e avisamo-lo se
          assim for. O exercício dos direitos é gratuito.
        </p>
      </section>

      <section id="cnpd">
        <h2>9. Reclamação à CNPD</h2>
        <p>
          Se considerar que tratamos mal os seus dados, tem o direito de reclamar à Comissão
          Nacional de Proteção de Dados (CNPD):
          <a href="https://www.cnpd.pt" target="_blank" rel="noopener noreferrer">www.cnpd.pt</a>.
        </p>
      </section>

      <section id="decisoes">
        <h2>10. Decisões automatizadas e perfis</h2>
        <p>
          Não tomamos decisões automatizadas nem definimos perfis a seu respeito (art. 22.º do
          RGPD). A verificação anti-spam dos formulários só distingue pessoas de programas
          automáticos.
        </p>
      </section>

      <section id="seguranca">
        <h2>11. Segurança</h2>
        <p>
          Protegemos os dados com ligações cifradas (HTTPS), acesso ao backoffice só para
          utilizadores autorizados, com perfis e registo de acessos, e verificação anti-spam nos
          formulários. Se houver uma violação de dados com risco elevado para si, avisamo-lo sem
          demora e notificamos a CNPD no prazo legal de 72 horas, quando a lei o exigir.
        </p>
      </section>

      <section id="menores">
        <h2>12. Menores</h2>
        <p>Este site destina-se a maiores de 18 anos.</p>
      </section>

      <section id="cookies-alteracoes">
        <h2>13. Cookies e alterações</h2>
        <p>
          O que o site guarda no seu dispositivo está na
          <RouterLink to="/cookies">Política de Cookies</RouterLink>. Pode mudar a sua escolha sobre
          analytics a qualquer momento:
        </p>
        <p>
          <button
            type="button"
            class="btn btn-secondary ph-no-capture"
            @click="cookieBanner.open($event.currentTarget)"
          >
            Abrir as preferências de cookies
          </button>
        </p>
        <p>
          Se alterarmos esta política, publicamos aqui a nova versão com a nova data, no início da
          página.
        </p>
      </section>
    </article>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import CompanyIdentity from '@/components/CompanyIdentity.vue'
import { useCookieBanner } from '@/composables/useCookieBanner'

// Actualizar à mão sempre que o texto mudar; as versões anteriores estão no git (log deste ficheiro).
const UPDATED = '10 de novembro de 2026'

const cookieBanner = useCookieBanner()

const CONTRACT = 'Diligências pré-contratuais a seu pedido (art. 6.º, n.º 1, al. b))'
const LEGITIMATE = 'Interesse legítimo (art. 6.º, n.º 1, al. f))'

// Ponto 2: uma linha por finalidade.
const PURPOSES = [
  {
    purpose: 'Pedido de orçamento',
    data: 'Nome, email, telefone (facultativo), empresa, NIF e localidade (facultativos), se compra como empresa ou como particular, artigos e quantidades, observações; só se aceitou os cookies de analytics, a página por onde entrou, o site de onde veio e o último modelo que viu',
    basis: CONTRACT,
    term: '24 meses se não houver venda; 10 anos se houver venda (Código Comercial, art. 40.º)',
  },
  {
    purpose: 'Contacto',
    data: 'Nome, email, telefone (facultativo), assunto, mensagem e as nossas respostas; só se aceitou os cookies de analytics, a página por onde entrou, o site de onde veio e o último modelo que viu',
    basis: `${CONTRACT}, ou, nos restantes casos, ${LEGITIMATE.toLowerCase()}`,
    term: '24 meses',
  },
  {
    purpose: 'Vendas, faturação e arquivo',
    data: 'Identificação, NIF, encomendas e pagamentos',
    basis:
      'Execução do contrato (art. 6.º, n.º 1, al. b)) e obrigação legal (art. 6.º, n.º 1, al. c))',
    term: '10 anos (Código Comercial, art. 40.º; Código do IVA, art. 52.º)',
  },
  {
    purpose: 'Correspondência por email, WhatsApp e telefone',
    data: 'O que nos escreve ou diz e os seus contactos',
    basis: `${CONTRACT}, ou ${LEGITIMATE.toLowerCase()}`,
    term: 'Os mesmos prazos da finalidade a que respeita',
  },
  {
    purpose: 'Segurança e anti-spam',
    data: 'Endereço IP, identificação do navegador, resultado da verificação anti-spam (Turnstile), registos técnicos e avisos',
    basis: LEGITIMATE,
    term: 'Registos técnicos: ver o ponto 7',
  },
  {
    purpose: 'Medição de audiência (PostHog)',
    data: 'Páginas e cliques visitados, o que pesquisa no catálogo, o tempo que as páginas demoram a abrir, identificador aleatório no navegador, tipo de dispositivo e de navegador, localização aproximada calculada a partir do endereço IP',
    basis: 'Consentimento (art. 6.º, n.º 1, al. a); Lei n.º 41/2004, art. 5.º)',
    term: 'Pelo período de retenção do PostHog (1 ano no plano gratuito). Deixamos de medir quando retirar o consentimento',
  },
  {
    purpose: 'Auditoria do backoffice',
    data: 'Utilizador interno, acções realizadas e endereço IP',
    basis: LEGITIMATE,
    term: '12 meses',
  },
  {
    purpose: 'Resposta a pedidos de direitos',
    data: 'O pedido, a verificação de identidade e a resposta',
    basis: 'Obrigação legal (art. 6.º, n.º 1, al. c))',
    term: '3 anos depois da resposta',
  },
]

// Os artigos vêm no ponto 6. A certificação de cada fornecedor não está verificada: diz-se a base, não quem a tem.
const SAFEGUARDS =
  'garantias adequadas do art. 46.º do RGPD, como as cláusulas contratuais-tipo da Comissão'
const IN_EU = `Só se o fornecedor aceder de fora da UE: ${SAFEGUARDS}.`
const IN_US = `Sim: decisão de adequação UE-EUA (Data Privacy Framework), quando o fornecedor está certificado, ou outras ${SAFEGUARDS}.`
const OURS = 'A Diomika'

// Ponto 5: empresa e função, nunca pessoas (o prestador de manutenção não tem nome nem email aqui).
// «Quem decide» diz quem fixa os fins, não que acordo existe: o do art. 28.º só se afirma depois de assinado (LEGAL-06).
// Cada linha confere-se com o que o fornecedor diz de si: a Cloudflare é responsável pelos sinais do Turnstile que
// usa para o melhorar; na Google não se sabe o tipo de conta (hipótese da auditoria), por isso não se diz só «A Diomika».
const RECIPIENTS = [
  {
    name: 'Supabase',
    role: 'Base de dados do site e imagens do catálogo',
    decides: OURS,
    where: 'Irlanda (União Europeia)',
    transfer: IN_EU,
  },
  {
    name: 'Render (Render Services, Inc.)',
    role: 'Servidor da aplicação, por onde passam os formulários',
    decides: OURS,
    where: 'Frankfurt (União Europeia)',
    transfer: IN_EU,
  },
  {
    name: 'GitHub (Microsoft)',
    role: 'Cópias de segurança diárias da base de dados',
    decides: OURS,
    where: 'EUA',
    transfer: IN_US,
  },
  {
    name: 'Cloudflare',
    role: 'Alojamento do site, rede de distribuição e verificação anti-spam (Turnstile)',
    decides:
      'A Diomika, quanto ao alojamento, à rede e à verificação anti-spam. A Cloudflare, quanto a melhorar o Turnstile (política do Turnstile)',
    where: 'Rede mundial, incluindo os EUA',
    transfer: IN_US,
  },
  {
    name: 'Google (Gmail)',
    role: 'Caixa de email que recebe os formulários e envia as respostas',
    decides:
      'A Diomika, quanto às mensagens que trata. A Google, quanto ao funcionamento e à segurança do serviço de email, segundo os termos da conta',
    where: 'Centros de dados da Google, incluindo os EUA',
    transfer: IN_US,
  },
  {
    name: 'Sentry',
    role: 'Registo de erros técnicos',
    decides: OURS,
    where: 'União Europeia',
    transfer: IN_EU,
  },
  {
    name: 'Axiom',
    role: 'Registos técnicos do servidor, que incluem o endereço IP',
    decides: OURS,
    where: 'União Europeia',
    transfer: IN_EU,
  },
  {
    name: 'PostHog',
    role: 'Medição de audiência, só com o seu consentimento',
    decides: OURS,
    where: 'União Europeia',
    transfer: IN_EU,
  },
  {
    name: 'ntfy.sh',
    role: 'Avisos técnicos de funcionamento do servidor, que não levam endereços IP, nomes nem outros dados pessoais',
    decides: 'Não aplicável',
    where: 'Não aplicável',
    transfer: 'Não aplicável',
  },
  {
    name: 'Meta (WhatsApp)',
    role: 'Mensagens, só se escolher falar connosco por WhatsApp',
    decides:
      'A Meta, quanto às mensagens que lhe enviar: é responsável pelo seu tratamento, segundo a sua política. A Diomika, quanto às que recebe',
    where: 'Rede mundial, incluindo os EUA',
    transfer: IN_US,
  },
  {
    name: 'Prestador de manutenção do site',
    role: 'Manutenção e suporte técnico, com acesso aos sistemas acima só quando necessário',
    decides: OURS,
    where: 'Acede aos sistemas acima',
    transfer: 'Não aplicável',
  },
]

const breadcrumbItems = [{ label: 'Início', to: { name: 'home' } }, { label: 'Privacidade' }]
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
  margin-bottom: 1.25rem;
}
section {
  margin-top: 2rem;
}
section h2 {
  font-family: var(--font-body);
  font-size: 1.15rem;
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
/* Direito de oposição: destacado e separado do resto (RGPD, art. 21.º, n.º 4). */
.highlight {
  margin: 1rem 0;
  padding: 1rem 1.25rem;
  background: var(--color-surface);
  border: 2px solid var(--color-ink-deep);
  border-radius: var(--radius-md);
}
.highlight h3 {
  margin: 0 0 0.4rem;
  font-size: 1.05rem;
}
.highlight p {
  margin: 0;
}
</style>
