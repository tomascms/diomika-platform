// @ts-check
import { test, expect } from '@playwright/test'

const site = process.env.E2E_SITE_URL || 'https://www.diomika.com'
const api = process.env.E2E_API_URL || 'https://api.diomika.com'

test.describe('Diomika critical flow', () => {
  test('API health ready', async ({ request }) => {
    const h = await request.get(`${api}/health`, {
      headers: { 'User-Agent': 'Mozilla/5.0 DiomikaE2E' },
    })
    expect(h.ok()).toBeTruthy()
    const ready = await request.get(`${api}/health/ready`, {
      headers: { 'User-Agent': 'Mozilla/5.0 DiomikaE2E' },
    })
    expect(ready.ok()).toBeTruthy()
  })

  test('loja home carrega', async ({ page }) => {
    await page.goto(site, { waitUntil: 'domcontentloaded' })
    await expect(page.locator('body')).toBeVisible()
    await expect(page.locator('#app')).toBeVisible()
  })

  test('privacidade acessível', async ({ page }) => {
    await page.goto(`${site}/privacidade`, { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('admin público bloqueado', async ({ request }) => {
    const r = await request.get(`${api}/admin/auth/status`, {
      headers: { 'User-Agent': 'Mozilla/5.0 DiomikaE2E' },
    })
    expect([401, 403, 404, 405]).toContain(r.status())
  })

  test('status page e security.txt', async ({ request }) => {
    const status = await request.get(`${site}/status.html`)
    expect(status.ok()).toBeTruthy()
    expect(await status.text()).toContain('Estado dos serviços')

    const sec = await request.get(`${site}/.well-known/security.txt`)
    expect(sec.ok()).toBeTruthy()
    expect(await sec.text()).toContain('Contact:')

    const root = await request.get(`${api}/`)
    expect(root.ok()).toBeTruthy()
    const body = await root.json()
    expect(body.service).toBe('diomika-api')
  })
})
