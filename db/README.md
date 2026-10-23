# Base de dados (Supabase)

Todo o SQL do projecto vive aqui. Não há ferramenta de migrações: cada ficheiro
corre-se à mão no SQL Editor do Supabase, por ordem do nome.

## `migrations/` — esquema actual

| Ficheiro | O que faz |
|---|---|
| `2026-08-11_create_messages_tables.sql` | `contact_messages` + `message_history` |
| `2026-08-11_admin_audit.sql` | auditoria do backoffice |
| `2026-08-11_admin_users_audit_actor.sql` | coluna `actor` na auditoria |
| `2026-08-11_outbox_claim.sql` | claim atómico do outbox |
| `2026-08-14_email_indexes.sql` | índices de email (retenção, apagamento RGPD) |
| `2026-10-01_0001_unified_catalog_schema.sql` | 3 tabelas de catálogo + RLS |
| `2026-10-01_0002_migrate_catalog_data.sql` | cópia das tabelas antigas para as novas |
| `2026-10-01_0004_integrity_guards.sql` | restrições de integridade do catálogo |
| `2026-10-03_0003_cleanup_legacy_tables_TEMPLATE.sql` | renomeia as tabelas antigas para `legacy_*` (aplicado a 2026-10-03) |
| `2026-10-13_catalog_indexes.sql` | índices de catálogo |
| `2026-10-21_function_search_path.sql` | `search_path` fixo no trigger de variantes (advisor de segurança) |

Estado em produção (2026-10-21): esquema unificado aplicado; advisor de segurança sem avisos.
As tabelas `legacy_*` (36, sem dependências) continuam na BD até se decidir o DROP; o dump
`pre-drop-legacy-20261021.dump` (VM `~/backups` e PC `deploy/backups/`) guarda-as.

Novas famílias de produto **não** precisam de SQL: ver `backend-api/models/catalog_attributes.py`.

## `legacy/` — não aplicar

Esquema anterior ao catálogo unificado (tabelas por família, hoje `legacy_*`)
e dois ficheiros nunca usados pelo código (`audit_archive_table.sql`,
`orders_invoice_columns.sql` — a tabela `orders` não existe). Ficam só como histórico.

Ver também `RUNBOOK_unified_catalog_migration.md`.
