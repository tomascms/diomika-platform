/** Corre `fn` sobre `items` com no máximo `concurrency` pedidos em simultâneo. */
export async function mapPool(items, concurrency, fn) {
  if (!items.length) return []
  const results = new Array(items.length)
  let next = 0
  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (next < items.length) {
      const idx = next++
      results[idx] = await fn(items[idx], idx)
    }
  })
  await Promise.all(workers)
  return results
}
