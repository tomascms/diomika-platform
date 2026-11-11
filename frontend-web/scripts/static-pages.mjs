/**
 * Páginas estáticas da loja que o `prerender-seo.mjs` escreve em HTML (título e descrição próprios,
 * para crawlers e pré-visualizações) e lista no sitemap. Está à parte do script para um teste
 * (`static-pages.test.mjs`) a poder ler sem correr o pré-render, que pede o catálogo à API.
 *
 * `sitemap: false` = tem página gerada mas não entra no sitemap. Uma rota nova da loja que deva ser
 * encontrada por motores de busca acrescenta-se aqui e em `public/sitemap.xml`.
 * `noscript: true` = o pré-render escreve o texto da vista no `<noscript>` da página (scripts/render-views.mjs), para
 * quem não corre JavaScript (SEO-10). O início e o catálogo têm o seu, com a lista de categorias.
 */
export const STATIC_PAGES = [
  { path: '/', changefreq: 'weekly', priority: '1.0' },
  { path: '/categorias', title: 'Catálogo', description: 'Todas as categorias do catálogo Diomika — almofadas, assentos, toalhas de mesa, aventais e mais.', changefreq: 'weekly', priority: '0.9' },
  { path: '/sobre', noscript: true, title: 'Sobre nós', description: 'Conheça a Diomika e como funciona o pedido de orçamento.', changefreq: 'monthly', priority: '0.6' },
  { path: '/contacto', noscript: true, title: 'Contacto', description: 'Fale com a equipa comercial da Diomika por telefone, WhatsApp ou mensagem.', changefreq: 'monthly', priority: '0.6' },
  { path: '/pesquisa', noscript: true, title: 'Pesquisa', description: 'Pesquise modelos no catálogo Diomika.', changefreq: 'weekly', priority: '0.5' },
  { path: '/perguntas-frequentes', noscript: true, title: 'Perguntas frequentes', description: 'Respostas sobre encomenda mínima, preços, entrega, pagamento, devoluções, garantia e reclamações.', changefreq: 'monthly', priority: '0.5' },
  { path: '/condicoes-de-venda', noscript: true, title: 'Condições gerais de venda', description: 'Condições gerais de venda da Diomika a empresas e a consumidores: proposta, preços, entrega, livre resolução, garantia e reclamações.', changefreq: 'yearly', priority: '0.2' },
  { path: '/privacidade', noscript: true, title: 'Política de Privacidade', description: 'Como a Diomika trata os dados pessoais recolhidos no site.', changefreq: 'yearly', priority: '0.2' },
  { path: '/termos', noscript: true, title: 'Informação legal', description: 'Identificação do prestador, Livro de Reclamações e resolução de litígios de consumo.', changefreq: 'yearly', priority: '0.2' },
  { path: '/cookies', noscript: true, title: 'Cookies', description: 'Que cookies o site Diomika usa e como gerir o consentimento.', changefreq: 'yearly', priority: '0.2' },
  // Sem página gerada, abrir o link directo (ou recarregar) mostrava o 404 estático.
  { path: '/carrinho', title: 'Pedido de orçamento', description: 'Reveja os produtos e envie o pedido de orçamento.', sitemap: false },
  { path: '/pedido-rapido', title: 'Pedido rápido por EAN', description: 'Cole uma linha por artigo, com EAN, cor e quantidade, e junte tudo ao pedido de orçamento de uma vez.', sitemap: false },
  { path: '/catalogo-imprimir', title: 'Catálogo para imprimir', description: 'O catálogo Diomika numa só página, com modelos, medidas, cores e EAN, para imprimir ou guardar em PDF.', sitemap: false },
]
