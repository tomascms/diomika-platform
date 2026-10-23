/**
 * Stress test k6 — API pública Diomika
 *
 * Uso:
 *   k6 run deploy/load/k6_stress.js
 *   k6 run -e BASE_URL=https://api.diomika.com deploy/load/k6_stress.js
 */
import http from 'k6/http'
import { check, sleep } from 'k6'

const BASE = __ENV.BASE_URL || 'https://api.diomika.com'

export const options = {
  stages: [
    { duration: '20s', target: 5 },
    { duration: '40s', target: 10 },
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<3000'],
  },
}

const paths = ['/health', '/categorias', '/catalogo/meta']

export default function () {
  const path = paths[Math.floor(Math.random() * paths.length)]
  const res = http.get(`${BASE}${path}`, {
    headers: { 'User-Agent': 'DiomikaLoadTest/1.0 (k6 stress)' },
    tags: { path },
  })
  check(res, {
    'status 2xx': (r) => r.status >= 200 && r.status < 300,
    'not 5xx': (r) => r.status < 500,
  })
  sleep(0.5)
}
