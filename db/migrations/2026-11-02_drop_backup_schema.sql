-- ============================================================================
-- Apagar o schema `backup` (auditoria BD-10)  —  DESTRUTIVO: confirmar antes de aplicar
-- ============================================================================
-- backup.image_urls_20261021 guarda 35 URLs assinadas antigas de 2026-10-21, com tokens já expirados. Há 0
-- referências partidas hoje, por isso a tabela já não faz falta (docs/runbook.md pede para a apagar quando
-- deixar de ser precisa). Está à parte da restante dureza da BD para poder ser aplicada, ou não, por si.
--
-- Não há volta atrás por SQL: antes de aplicar, confirmar que o dump mais recente (VM ~/backups) existe.
-- Idempotente. DROP SCHEMA sem CASCADE: falha, em vez de apagar, se houver mais alguma coisa lá dentro.
-- ============================================================================

DROP TABLE IF EXISTS backup.image_urls_20261021;
DROP SCHEMA IF EXISTS backup;
