/**
 * Stress test pesado — API Diomika (produção ou staging).
 *
 * Uso:
 *   k6 run deploy/load/k6_stress_heavy.js
 *   k6 run -e BASE_URL=https://api.diomika.com deploy/load/k6_stress_heavy.js
 *
 * Nota: acima de ~600 req/min por IP o rate limit devolve 429 (protecção activa).
 */
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Counter, Rate, Trend } from 'k6/metrics'

const BASE = __ENV.BASE_URL || 'https://api.diomika.com'
const UA = 'DiomikaLoadTest/2.0 (k6 heavy)'

const rateLimited = new Counter('rate_limited_429')
const serverErrors = new Counter('server_errors_5xx')
const okRate = new Rate('ok_2xx_rate')
const catalogLatency = new Trend('catalog_latency', true)

const paths = [
  '/health',
  '/categorias',
  '/catalogo/meta',
  '/catalogo/search?q=toalha&limit=10',
  '/catalogo/search?q=toalha&limit=40',
  '/categorias/slug/toalhas',
]

export const options = {
  scenarios: {
    ramp_stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 15 },
        { duration: '60s', target: 40 },
        { duration: '90s', target: 70 },
        { duration: '60s', target: 100 },
        { duration: '60s', target: 100 },
        { duration: '45s', target: 0 },
      ],
      gracefulRampDown: '20s',
    },
    burst: {
      executor: 'constant-vus',
      vus: 50,
      duration: '30s',
      startTime: '330s',
    },
  },
  thresholds: {
    server_errors_5xx: ['count<10'],
    ok_2xx_rate: ['rate>0.35'],
    catalog_latency: ['p(95)<5000'],
  },
}

export default function () {
  const path = paths[Math.floor(Math.random() * paths.length)]
  const res = http.get(`${BASE}${path}`, {
    headers: { 'User-Agent': UA },
    tags: { path: path.split('?')[0] },
  })

  if (res.status === 429) rateLimited.add(1)
  if (res.status >= 500) serverErrors.add(1)
  if (path.indexOf('/catalogo') === 0 || path.indexOf('/categorias') === 0) {
    catalogLatency.add(res.timings.duration)
  }

  const ok = res.status >= 200 && res.status < 300
  okRate.add(ok)
  check(res, {
    'not 5xx': function (r) {
      return r.status < 500
    },
  })

  sleep(Math.random() * 0.4 + 0.15)
}

function metricVal(data, name, field) {
  const m = data.metrics[name]
  if (!m || !m.values) return 0
  return m.values[field] || 0
}

export function handleSummary(data) {
  const lines = [
    '=== k6 heavy summary ===',
    'ok_2xx_rate: ' + (metricVal(data, 'ok_2xx_rate', 'rate') * 100).toFixed(1) + '%',
    '429 count: ' + metricVal(data, 'rate_limited_429', 'count'),
    '5xx count: ' + metricVal(data, 'server_errors_5xx', 'count'),
    'catalog p95: ' + metricVal(data, 'catalog_latency', 'p(95)').toFixed(0) + 'ms',
    'http p95: ' + metricVal(data, 'http_req_duration', 'p(95)').toFixed(0) + 'ms',
    'iterations: ' + metricVal(data, 'iterations', 'count'),
  ]
  console.log(lines.join('\n'))
  return {}
}
