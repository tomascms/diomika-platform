// O Organization e o WebSite estão no index.html (estáticos); aqui só o JSON-LD de produto.
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
