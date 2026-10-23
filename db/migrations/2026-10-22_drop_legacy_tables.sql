-- Apaga as 36 tabelas legacy_* (renomeadas a 2026-10-03, sem uso desde então; sem views nem FKs
-- de fora). Aplicado a 2026-10-22. Dump antes do DROP: pre-drop-legacy-20261021.dump
-- (VM ~/backups e PC deploy/backups/). Reverter: pg_restore desse dump.
DO $$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'legacy\_%' LOOP
    EXECUTE format('DROP TABLE public.%I CASCADE', t);
  END LOOP;
END $$;
