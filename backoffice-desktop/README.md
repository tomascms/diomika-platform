# Diomika Backoffice

App Electron (Win/Mac/Linux) para gestão do catálogo — liga a `https://api.diomika.com`.

Uso: [`docs/guia-cliente.md`](../docs/guia-cliente.md). Operação: [`docs/runbook.md`](../docs/runbook.md).

## Build

```bash
npm ci
npm run dist:cliente   # Windows + copia para cliente-backoffice/
```

## Dev

```bash
npm run dev:ui         # browser http://127.0.0.1:5174
npm run dev            # Electron + Vite
```

Abrir instalador local: `Abrir-Windows.cmd` ou `packaging/Abrir-Windows.cmd`.
