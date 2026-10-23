/** Build instaladores e copia para cliente-backoffice (win + linux no PC; mac só em macOS). */
const { execSync } = require('child_process')
const path = require('path')

const root = path.join(__dirname, '..')

function run(cmd) {
  execSync(cmd, { stdio: 'inherit', cwd: root, env: process.env })
}

run('node scripts/write-gate.cjs')
run('npx vite build')

const platform = process.platform
const targets = []

if (platform === 'darwin') {
  targets.push(['npx electron-builder --mac dmg --universal', 'macOS'])
} else if (platform === 'linux') {
  targets.push(['npx electron-builder --linux AppImage --x64', 'Linux'])
} else {
  targets.push(['npx electron-builder --win portable --x64', 'Windows'])
  // AppImage no Windows falha (symlinks) — Linux/macOS via GitHub Actions
}

for (const [cmd, label] of targets) {
  console.log(`\n=== Build ${label} ===`)
  try {
    run(cmd)
  } catch (err) {
    if (label === 'Windows' && process.platform === 'win32') {
      console.warn('AVISO: portable falhou — a tentar output alternativo release-fresh/')
      try {
        run('npx electron-builder --win portable --x64 --config.directories.output=release-fresh')
      } catch (err2) {
        console.warn(`AVISO: build ${label} falhou — ${err2.message || err2}`)
      }
    } else {
      console.warn(`AVISO: build ${label} falhou — ${err.message || err}`)
    }
  }
}

if (platform !== 'darwin') {
  console.warn(
    '\nAVISO: .dmg macOS só se constrói num Mac ou via GitHub Actions (backoffice-release.yml).'
  )
}

require('./prepare-cliente-pack.cjs')
