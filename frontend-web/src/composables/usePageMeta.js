import { watch } from 'vue'

const DEFAULT_TITLE = 'Diomika'
const DEFAULT_DESC = 'Catálogo Diomika — explore categorias, modelos e peça orçamento online.'
// Domínio canónico fixo: visitas por *.pages.dev não podem declarar-se canónicas.
const SITE_ORIGIN = 'https://www.diomika.com'

const ROUTE_META = {
  home: {
    // Título completo — sem o sufixo « | Diomika» (ver applyMeta).
    title: 'Diomika — Têxteis para o lar, para revenda',
    fullTitle: true,
    description:
      'Catálogo B2B da Diomika: almofadas, assentos, toalhas de mesa, aventais e mais. Escolha modelos, cores e medidas e peça orçamento online.',
  },
  categories: {
    title: 'Catálogo',
    description: 'Todas as categorias do catálogo Diomika — almofadas, assentos, toalhas, aventais e mais.',
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
  about: {
    title: 'Sobre nós',
    description: 'Conheça a Diomika e o processo de pedido do catálogo B2B.',
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
    title: 'Aviso legal',
    description: 'Informação legal sobre o site Diomika.',
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
  const img = metaImage.startsWith('http') ? metaImage : `${SITE_ORIGIN}${metaImage.startsWith('/') ? '' : '/'}${metaImage}`
  setOg('og:image', img)
  setMeta('twitter:image', img)
  const pagePath = path && SITE_ORIGIN ? `${SITE_ORIGIN}${path.startsWith('/') ? path : `/${path}`}` : ''
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
      path: to.fullPath,
    })
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
