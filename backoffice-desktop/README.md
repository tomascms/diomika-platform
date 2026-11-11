# Diomika Backoffice

App Electron (Win/Mac/Linux) para gestão do catálogo — liga a `https://api.diomika.com`.

Uso: [`docs/guia-cliente.md`](../docs/guia-cliente.md). Operação: [`docs/runbook.md`](../docs/runbook.md).

## Build

```bash
npm ci
npm run dist:win       # release/Diomika-Backoffice-<versão>-setup.exe
```

## Dev

```bash
npm run dev:ui         # browser http://127.0.0.1:5174
npm run dev            # Electron + Vite
```

## Entrega ao cliente (só em mão, nunca publicar)

Sem palavra-passe, o instalador é a chave de admin. Nada vai para releases, sites ou email.

1. Windows: `npm run dist:win`.
2. Mac: Actions → «Backoffice Mac build» → Run; `gh run download <id> -n diomika-backoffice-mac`;
   apagar o artefacto logo a seguir.
3. Pasta `cliente-backoffice/` (fora do git): `setup.exe`, `.dmg` e `packaging/LEIA-ME.txt`. Entregar por pen.
