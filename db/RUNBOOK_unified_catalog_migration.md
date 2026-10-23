# Runbook — migração para o catálogo unificado

Contexto: o catálogo passou de 13 famílias de tabelas quase-idênticas
(`modelos_almofadas`+`almofada`+`modelo_almofada_cores`, etc.) para 3 tabelas
partilhadas (`product_models`, `product_variants`, `product_model_colors`),
discriminadas por `tipo_catalogo`.

## Estado: APLICADO em produção (projeto Supabase `your-project-ref`)

0001 (esquema) e 0002 (dados) foram corridos. Resultado verificado:

| tipo_catalogo | modelos | variantes | cores |
|---|---|---|---|
| almofada | 2 | 6 | 6 |
| assento | 5 | 10 | 5 |
| avental | 6 | 6 | 6 |
| guarda_chuva | 3 | 0 | 3 |
| luva | 2 | 2 | 2 |
| oculo | 1 | 1 | 1 |
| pega | 2 | 2 | 2 |
| protetor_colchao | 3 | 21 | 3 |
| toalha_mesa | 5 | 20 | 5 |
| **total** | **29** | **68** | **33** |

Todas as contagens batem com as tabelas antigas, família a família. Também
confirmado: 68/68 variantes com EAN, 67 com `barcode_url` (a que falta já
faltava antes da migração), 33/33 cores com imagem, `catalog_ean_lookup`
devolve 68 linhas, `visibilidade` preservada registo a registo (todo o
catálogo estava — e continua — invisível na loja), 12 políticas RLS, 2
triggers `updated_at`, 3 tabelas no realtime, 0 avisos no advisor de
segurança do Supabase.

As famílias `pano_cozinha`, `passadeira` e `regional` não tinham dados
nenhuns, por isso não houve nada a migrar.

**As 13 famílias de tabelas antigas continuam intactas** — nada foi apagado
nem renomeado. O passo 6 (limpeza) ainda não foi feito.

## Esquema real da BD — confirmado

Dúvidas que este runbook tinha antes de haver acesso à BD, agora resolvidas:

- As cores **são** tabelas dedicadas por família (`modelo_almofada_cores`,
  `modelo_assento_cores`, ...). Não existe nenhuma tabela `modelo_cores`
  partilhada legada, por isso o caminho de fallback do 0002 nunca foi usado.
- Só `modelos_almofadas`, `almofada`, `modelos_assentos`, `assento`,
  `modelo_almofada_cores` e `modelo_assento_cores` têm coluna `updated_at`.
  As outras 10 famílias não têm — o 0002 foi corrigido para usar `now()`
  nessas (antes referia `COALESCE(updated_at, now())`, o que dava erro
  "column updated_at does not exist" e abortava a migração).
- Todas as colunas `dimensoes` ao nível do modelo são `jsonb`; ao nível da
  variante são `text`.

## Nota sobre como correr a SQL

O 0001 está escrito como um ficheiro só, para colar no SQL Editor do
Supabase. Se o correres por uma ligação com limite de tempo curto (uma
sessão MCP, por exemplo), divide-o: tabelas → índices → triggers → políticas
(uma a uma) → view → `ALTER PUBLICATION` (uma por tabela). Os blocos grandes
e os blocos `DO $$` com muitas instruções podem exceder o limite e ser
revertidos.

## 0004 — garantias de integridade (APLICADO, com uma exceção)

Aplicado: o trigger que faz a variante herdar o `tipo_catalogo` do modelo-pai
(testado em produção — forçar um tipo errado numa variante devolve o tipo do
modelo), e as restrições `CHECK` de forma dos dados (`attributes` tem de ser
objeto JSON, `tipo_catalogo` com forma de slug, `ean` com 13 dígitos).

**Falta** correr as três últimas linhas do ficheiro (`DROP INDEX` dos índices
redundantes). `DROP INDEX` precisa de lock exclusivo e excedia sempre o limite
de 60 s da ligação usada; no SQL Editor do Supabase, que não tem esse limite,
correm de imediato. Não há pressa — com 29 modelos / 68 variantes / 33 cores o
custo destes índices é irrelevante.

## Passo 6 — limpeza (ainda NÃO feito)

Só depois de a loja e o backoffice correrem bem sobre o esquema novo durante
alguns dias: corre `migrations/2026-10-03_0003_cleanup_legacy_tables_TEMPLATE.sql`, que renomeia
(não apaga) as 13 famílias antigas com o prefixo `legacy_`. Reversível: para
voltar atrás é só renomear de volta. Passados uns meses, se nunca
precisares, podes fazer `DROP TABLE legacy_*` à mão.

## Se alguma coisa correr mal

As tabelas antigas continuam lá, intactas. Podes:
1. Reverter o deploy para o commit anterior a este branch (o código antigo
   volta a ler as tabelas antigas, que não foram tocadas).
2. Investigar com calma, sem pressão de produção partida.

Os IDs foram preservados na migração (o `id` de cada modelo/variante/cor não
mudou), por isso referências externas — EANs em orçamentos, URLs de imagens,
links partilhados — continuam válidas.

## Nota para deploys futuros

**Não** definas `SCHEMA_BOOTSTRAP` — essa variável deixou de ter efeito (o
motor de auto-migração no arranque foi removido; ver commit "Unify catalog
schema"). O motor de sync automático Pydantic→BD foi apagado do repo, tal
como a SQL por-família que ele gerava: as migrações são agora os ficheiros
numerados desta pasta, aplicados à mão.
