// npm audit --omit=dev que falha com alertas high/critical, menos os da lista IGNORE.
// O npm audit não deixa ignorar um alerta; isto deixa, para alertas sem correção que não afetam a produção.
// Uso: node ../scripts/npm-audit.mjs (dentro de frontend-web ou backoffice-desktop)
import { execSync } from 'node:child_process'

const IGNORE = {
  // picomatch <= 4.0.7, ReDoS com padrões glob maliciosos. Ainda sem versão corrigida (2026-11-18).
  // Só é usado no build (vite, vue-router) com padrões do próprio código: nada vem dos visitantes.
  // Tirar daqui assim que sair o picomatch corrigido.
  'GHSA-fc5q-39xc-vjpf': 'picomatch, só no build, sem correção',
}

let out
try {
  out = execSync('npm audit --omit=dev --json', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] })
} catch (err) {
  out = err.stdout // npm audit sai com código ≠ 0 quando há alertas
}
const report = JSON.parse(out)
const bad = new Map()
for (const vuln of Object.values(report.vulnerabilities || {})) {
  for (const via of vuln.via) {
    if (typeof via !== 'object' || !['high', 'critical'].includes(via.severity)) continue
    const id = via.url?.split('/').pop()
    if (!(id in IGNORE)) bad.set(id, `${via.severity} ${via.name}: ${via.title} ${via.url}`)
  }
}
for (const [id, why] of Object.entries(IGNORE)) console.log(`ignorado ${id}: ${why}`)
if (bad.size) {
  for (const line of bad.values()) console.error(line)
  process.exit(1)
}
console.log('npm audit: sem alertas high/critical por resolver')
