# Base de dados (Supabase)

Todo o SQL do projecto vive aqui. Não há ferramenta de migrações: cada ficheiro de `migrations/` aplica-se
com `apply_migration` do Supabase (fica no histórico `supabase_migrations.schema_migrations`) ou no SQL Editor,
**por ordem do nome**, e com o nome do ficheiro como nome da migração. Todos são idempotentes.
O que já está em produção vê-se nesse histórico (Supabase → *Database* → *Migrations*).

## `migrations/`

`2026-10-28_0000_baseline.sql` é o esquema `public` de produção a 2026-10-21, sem as tabelas `legacy_*` nem dados.
Serve para criar uma BD nova (ensaio de recuperação): baseline + os ficheiros seguintes, por ordem. Em produção não
faz nada (só corre se `public.categories` ainda não existir). As migrações anteriores (2026-08-11 a 2026-10-22) estão
dentro dela; os ficheiros antigos ficam no histórico do git.

| Ficheiro | O que faz |
|---|---|
| `2026-10-28_0000_baseline.sql` | esquema `public` de base (ver acima) |
| `2026-10-28_pedidos_orcamento_b2b.sql` | colunas `nif`, `localidade`, `tipo_cliente` em `pedidos_orcamento` |
| `2026-10-28_modelos_fabricante.sql` | `fabricante_*` e `avisos` em `product_models` (LEGAL-12) |
| `2026-11-01_modelos_sem_descricao.sql` | «Sem descrição» passa a vazio (dados) |
| `2026-11-01_barcode_url_publica.sql` | URL público nos códigos de barras (dados) |
| `2026-11-02_new_columns.sql` | `categories.descricao`, `origem` (orçamentos e contactos), `pedidos_orcamento.vendido_em` |
| `2026-11-02_catalogue_functions.sql` | `save_model_bundle` e `set_catalog_visibility` (gravações atómicas, só service_role) |
| `2026-11-02_database_hardening.sql` | privilégios, RLS dos filhos, Storage, Realtime, índices, restrições |
| `2026-11-02_drop_backup_schema.sql` | apaga o schema `backup` (**destrutivo**: confirmar antes) |
| `2026-11-03_app_state.sql` | tabela `app_state` (utilizadores do backoffice e estado do email; o disco do Render apaga-se) |
| `2026-11-03_quote_lifecycle.sql` | `valor_proposta`, `nota_interna` e estados do orçamento |
| `2026-11-10_modelos_made_in.sql` | país de fabrico do modelo («Fabricado em …» na etiqueta) |

Ordem de um deploy: migrações (por ordem do nome) → API → loja. Não há staging; antes de produção, ensaiar numa
BD nova criada com a baseline.

Novas famílias de produto **não** precisam de SQL: ver `backend-api/models/catalog_attributes.py`.
