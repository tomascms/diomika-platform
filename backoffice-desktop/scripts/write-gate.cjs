/** Escreve electron/desktop-gate.cjs a partir de DIOMIKA_DESKTOP_GATE ou .env na raiz. */
const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const repoRoot = path.resolve(root, '..')
const out = path.join(root, 'electron', 'desktop-gate.cjs')

function readEnvFile(file) {
  if (!fs.existsSync(file)) return {}
  const map = {}
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const t = line.trim()
    if (!t || t.startsWith('#')) continue
    const i = t.indexOf('=')
    if (i < 1) continue
    const k = t.slice(0, i).trim()
    let v = t.slice(i + 1).trim()
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1)
    }
    map[k] = v
  }
  return map
}

const fromEnv = (process.env.DIOMIKA_DESKTOP_GATE || '').trim()
const fromFile = readEnvFile(path.join(repoRoot, '.env')).DIOMIKA_DESKTOP_GATE || ''
const gate = (fromEnv || fromFile || '').trim()
if (!gate || gate.length < 24) {
  console.error('ERRO: defina DIOMIKA_DESKTOP_GATE (>=24 chars) no .env ou no ambiente de CI.')
  process.exit(1)
}
fs.writeFileSync(out, `module.exports = ${JSON.stringify(gate)}\n`, 'utf8')
console.log('OK — desktop-gate.cjs escrito')
