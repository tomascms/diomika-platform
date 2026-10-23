const SITE = 'https://www.diomika.com'

export function injectOrganizationJsonLd() {
  if (typeof document === 'undefined') return
  const id = 'diomika-org-jsonld'
  if (document.getElementById(id)) return
  const script = document.createElement('script')
  script.id = id
  script.type = 'application/ld+json'
  script.textContent = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Diomika',
    url: SITE,
    logo: `${SITE}/icon-512.png`,
  })
  document.head.appendChild(script)
}

export function injectProductJsonLd(product) {
  if (typeof document === 'undefined' || !product) return
  const id = 'diomika-product-jsonld'
  let script = document.getElementById(id)
  if (!script) {
    script = document.createElement('script')
    script.id = id
    script.type = 'application/ld+json'
    document.head.appendChild(script)
  }
  script.textContent = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name || '',
    description: product.description || '',
    image: product.image || undefined,
    url: product.url || undefined,
  })
}
