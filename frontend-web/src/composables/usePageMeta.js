import { watch } from 'vue'

import { SITE_ORIGIN } from '@/lib/constants'

const DEFAULT_TITLE = 'Diomika'
const DEFAULT_DESC = 'Catálogo Diomika — explore categorias, modelos e peça orçamento online.'
// Domínio canónico fixo (SITE_ORIGIN): visitas por *.pages.dev não podem declarar-se canónicas.

const ROUTE_META = {
  home: {
    // Título completo — sem o sufixo « | Diomika» (ver applyMeta).
    title: 'Diomika — Têxteis para o lar',
    fullTitle: true,
    description:
      'Diomika: almofadas, assentos, toalhas de mesa, aventais e mais. Escolha modelos, cores e medidas e peça orçamento online.',
  },
  categories: {
    title: 'Catálogo',
    description:
      'Todas as categorias do catálogo Diomika — almofadas, assentos, toalhas, aventais e mais.',
  },
  products: {
    title: 'Catálogo',
    description: 'Modelos e variantes disponíveis.',
  },
  'product-detail': {
    title: 'Detalhe do produto',
    description: 'Especificações, cores e pedido de orçamento.',
  },
  cart: {
    title: 'Pedido de orçamento',
    description: 'Revise o seu pedido e envie o orçamento.',
  },
  'quick-order': {
    title: 'Pedido rápido por EAN',
    description:
      'Cole uma linha por artigo, com EAN, cor e quantidade, e junte tudo ao pedido de orçamento de uma vez.',
  },
  'catalogue-print': {
    title: 'Catálogo para imprimir',
    description:
      'O catálogo Diomika numa só página, com modelos, medidas, cores e EAN, para imprimir ou guardar em PDF.',
  },
  about: {
    title: 'Sobre nós',
    description: 'Conheça a Diomika e como funciona o pedido de orçamento.',
  },
  search: {
    title: 'Pesquisar catálogo',
    description: 'Pesquise modelos e referências em todo o catálogo Diomika.',
  },
  contact: {
    title: 'Contacto',
    description: 'Entre em contacto connosco.',
  },
  privacy: {
    title: 'Política de privacidade',
    description: 'Como tratamos os seus dados pessoais.',
  },
  terms: {
    title: 'Informação legal',
    description:
      'Identificação do prestador, Livro de Reclamações e resolução de litígios de consumo.',
  },
  'sales-terms': {
    title: 'Condições gerais de venda',
    description:
      'Condições gerais de venda da Diomika a empresas e a consumidores: proposta, preços, entrega, livre resolução, garantia e reclamações.',
  },
  faq: {
    title: 'Perguntas frequentes',
    description:
      'Respostas sobre encomenda mínima, preços, entrega, pagamento, devoluções, garantia e reclamações.',
  },
  cookies: {
    title: 'Política de cookies',
    description: 'Como utilizamos cookies no site Diomika.',
  },
  'not-found': {
    title: 'Página não encontrada',
    description: DEFAULT_DESC,
  },
}

function setMeta(name, content) {
  if (!content) return
  let el = document.querySelector(`meta[name="${name}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('name', name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

function setOg(property, content) {
  if (!content) return
  let el = document.querySelector(`meta[property="${property}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('property', property)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

/**
 * `<meta name="robots" content="noindex">`: acrescenta-o ou tira-o. Uma categoria sem modelos abre a loja com HTTP 200
 * (a Function serve a loja a qualquer categoria que exista), e um endereço desconhecido também quando a API não
 * respondeu à Function; nesses casos é esta marca que diz ao Google para não os guardar.
 */
export function setNoindex(noindex) {
  let el = document.querySelector('meta[name="robots"]')
  if (!noindex) {
    el?.remove()
    return
  }
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('name', 'robots')
    document.head.appendChild(el)
  }
  el.setAttribute('content', 'noindex')
}

function setCanonical(href) {
  if (!href) return
  let el = document.querySelector('link[rel="canonical"]')
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', 'canonical')
    document.head.appendChild(el)
  }
  el.setAttribute('href', href)
}

export function applyPageMeta({ title, description, image, path, fullTitle: isFull = false } = {}) {
  const fullTitle = title ? (isFull ? title : `${title} | Diomika`) : DEFAULT_TITLE
  const desc = description || DEFAULT_DESC
  document.title = fullTitle
  setMeta('description', desc)
  setOg('og:title', fullTitle)
  setOg('og:description', desc)
  setOg('og:type', 'website')
  setOg('og:locale', 'pt_PT')
  setMeta('twitter:card', 'summary_large_image')
  setMeta('twitter:title', fullTitle)
  setMeta('twitter:description', desc)
  const metaImage = image || `${SITE_ORIGIN}/icon-512.png`
  const img = metaImage.startsWith('http')
    ? metaImage
    : `${SITE_ORIGIN}${metaImage.startsWith('/') ? '' : '/'}${metaImage}`
  setOg('og:image', img)
  setMeta('twitter:image', img)
  const pagePath =
    path && SITE_ORIGIN ? `${SITE_ORIGIN}${path.startsWith('/') ? path : `/${path}`}` : ''
  if (pagePath) {
    setOg('og:url', pagePath)
    setCanonical(pagePath)
  } else if (path && SITE_ORIGIN) {
    setCanonical(`${SITE_ORIGIN}${path.startsWith('/') ? path : `/${path}`}`)
  }
}

export function useRouteMeta(router) {
  router.afterEach((to) => {
    const base = ROUTE_META[to.name] || {}
    applyPageMeta({
      title: to.meta?.title || base.title,
      fullTitle: Boolean(base.fullTitle && !to.meta?.title),
      description: to.meta?.description || base.description,
      // Sem a query: `?utm_source=` ou `?cor=2` não fazem outra página, e o canonical dizia que sim (SEO-05).
      path: to.path,
    })
    // Cada página parte de «indexável»; as que não o são (rota `meta.noindex`, categoria vazia, produto que já não
    // existe) marcam-se depois, quando a vista sabe o que carregou.
    setNoindex(Boolean(to.meta?.noindex))
  })
}

export function watchDynamicTitle(source, getMeta) {
  watch(
    source,
    () => {
      const meta = getMeta()
      if (meta?.title) applyPageMeta(meta)
    },
    { immediate: true, deep: true },
  )
}
