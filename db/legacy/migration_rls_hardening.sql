-- Políticas RLS em falta (Supabase advisor 0008) — idempotente.
-- Ver também deploy/generated_catalog_infra.sql (fonte completa por família).

CREATE INDEX IF NOT EXISTS idx_message_history_message_id ON message_history (message_id);

-- passadeira
DROP POLICY IF EXISTS "modelos_passadeiras_public_read" ON modelos_passadeiras;
CREATE POLICY "modelos_passadeiras_public_read" ON modelos_passadeiras FOR SELECT TO anon USING (visibilidade = true);
DROP POLICY IF EXISTS "passadeira_public_read" ON passadeira;
CREATE POLICY "passadeira_public_read" ON passadeira FOR SELECT TO anon USING (visibilidade = true);
DROP POLICY IF EXISTS "modelo_passadeira_cores_public_read" ON modelo_passadeira_cores;
CREATE POLICY "modelo_passadeira_cores_public_read" ON modelo_passadeira_cores FOR SELECT TO anon USING (visibilidade = true);

-- protetor_colchao
DROP POLICY IF EXISTS "modelos_protetores_colchao_public_read" ON modelos_protetores_colchao;
CREATE POLICY "modelos_protetores_colchao_public_read" ON modelos_protetores_colchao FOR SELECT TO anon USING (visibilidade = true);
DROP POLICY IF EXISTS "protetor_colchao_public_read" ON protetor_colchao;
CREATE POLICY "protetor_colchao_public_read" ON protetor_colchao FOR SELECT TO anon USING (visibilidade = true);
DROP POLICY IF EXISTS "modelo_protetor_colchao_cores_public_read" ON modelo_protetor_colchao_cores;
CREATE POLICY "modelo_protetor_colchao_cores_public_read" ON modelo_protetor_colchao_cores FOR SELECT TO anon USING (visibilidade = true);
