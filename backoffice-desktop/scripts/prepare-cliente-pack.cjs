/**
 * Prepara cliente-backoffice: instaladores + credenciais + atalhos de abertura.
 * Windows local: .exe portátil ou .zip. macOS/Linux via CI ou fetch release.
 */
const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')
const packaging = path.join(root, 'packaging')
const release = path.join(root, 'release')
const releaseFresh = path.join(root, 'release-fresh')
const version = require('../package.json').version

/** Primeiro encontrado de cada grupo conta como artefacto da plataforma. */
const PLATFORM_GROUPS = [
  [`Diomika-Backoffice-${version}-setup.exe`],
  [`Diomika-Backoffice-${version}-windows.zip`],
  [`Diomika-Backoffice-${version}-mac.dmg`],
  [`Diomika-Backoffice-${version}-linux.AppImage`],
]

const HELPERS = ['Abrir-Windows.cmd', 'Abrir-Windows.ps1', 'Abrir-Mac.command']
const CRED_FILES = ['CREDENCIAIS.txt', 'CREDENCIAIS.secret.txt']

const destDirs = [
  path.join(root, '..', 'cliente-backoffice'),
  path.join(root, '..', '..', 'cliente-backoffice'),
]

const REMOVE_DIR_NAMES = new Set([
  'Diomika Backoffice',
  '.diomika',
  '_extract_tmp',
  'win-unpacked',
  'linux-unpacked',
  '__appImage-x64',
])

// Só a versão actual fica na pasta do cliente — instaladores antigos ao lado
// dos novos faziam abrir a versão errada.
const escapedVersion = version.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const KEEP_INSTALLER_RE = new RegExp(`^Diomika-Backoffice-${escapedVersion}-.*\\.(zip|dmg|AppImage|exe)$`)

const REMOVE_FILE_RE = /^(SETUP_|CHAVES_|ALERTAS_|LEIA-ME|\.DS_Store$)/

function artifactSrc(name) {
  for (const dir of [release, releaseFresh]) {
    const p = path.join(dir, name)
    if (fs.existsSync(p)) return p
  }
  return null
}

function firstInGroup(names) {
  for (const name of names) {
    const src = artifactSrc(name)
    if (src) return { name, src }
  }
  return null
}

function cleanDest(dest) {
  if (!fs.existsSync(dest)) return
  for (const entry of fs.readdirSync(dest)) {
    const full = path.join(dest, entry)
    let st
    try {
      st = fs.statSync(full)
    } catch {
      continue
    }
    if (st.isDirectory()) {
      if (REMOVE_DIR_NAMES.has(entry)) {
        fs.rmSync(full, { recursive: true, force: true })
        console.log(`  removido ${entry}/`)
      }
      continue
    }
    const keep =
      CRED_FILES.includes(entry) ||
      HELPERS.includes(entry) ||
      KEEP_INSTALLER_RE.test(entry)
    if (!keep || REMOVE_FILE_RE.test(entry)) {
      if (!CRED_FILES.includes(entry) && !HELPERS.includes(entry)) {
        try {
          fs.unlinkSync(full)
          console.log(`  removido ${entry}`)
        } catch {
          /* ignore */
        }
      }
    }
  }
}

function copyHelpers(dest) {
  for (const name of HELPERS) {
    const src = path.join(packaging, name)
    if (!fs.existsSync(src)) {
      console.warn(`AVISO: helper em falta — ${name}`)
      continue
    }
    fs.copyFileSync(src, path.join(dest, name))
    if (name.endsWith('.command')) {
      try {
        fs.chmodSync(path.join(dest, name), 0o755)
      } catch {
        /* Windows */
      }
    }
  }
}

function ensureCredentials(dest) {
  const secret = path.join(dest, 'CREDENCIAIS.secret.txt')
  const cred = path.join(dest, 'CREDENCIAIS.txt')
  const template = path.join(packaging, 'CREDENCIAIS.template.txt')
  // Instruções: sempre a versão actual. O ficheiro secreto nunca é tocado.
  if (fs.existsSync(template)) fs.copyFileSync(template, cred)
  if (!fs.existsSync(secret)) {
    fs.writeFileSync(
      secret,
      'Utilizador: (a preencher pela Diomika)' + String.fromCharCode(10) + 'Password: (a preencher pela Diomika)' + String.fromCharCode(10),
      'utf8'
    )
    console.warn('AVISO: CREDENCIAIS.secret.txt criado vazio — preencher antes de enviar ao cliente.')
  }
}

function main() {
  let copied = 0
  const missing = []

  for (const dest of destDirs) {
    fs.mkdirSync(dest, { recursive: true })
    console.log(`\n=== ${dest} ===`)
    cleanDest(dest)

    for (const group of PLATFORM_GROUPS) {
      const hit = firstInGroup(group)
      if (!hit) {
        missing.push(group.join(' | '))
        continue
      }
      fs.copyFileSync(hit.src, path.join(dest, hit.name))
      console.log(`OK — ${hit.name}`)
      copied += 1
    }

    copyHelpers(dest)
    ensureCredentials(dest)
  }

  if (missing.length) {
    console.warn(`\nAVISO: plataformas em falta (CI Mac/Linux ou fetch release):`)
    missing.forEach((m) => console.warn(`  - ${m}`))
  }
  if (copied === 0) {
    console.error('ERRO: nenhum instalador copiado.')
    process.exit(1)
  }
  console.log(`\nOK — pacote cliente preparado (${copied} instalador(es) + credenciais + atalhos).`)
}

main()

