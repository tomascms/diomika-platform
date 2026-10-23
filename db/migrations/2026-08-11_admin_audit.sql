-- Auditoria de acções do backoffice (admin local)
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    resource_id TEXT,
    role TEXT NOT NULL DEFAULT 'admin',
    actor TEXT,
    request_id TEXT,
    client_ip TEXT,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE admin_audit_log ADD COLUMN IF NOT EXISTS actor TEXT;

CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_resource ON admin_audit_log (resource, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_actor ON admin_audit_log (actor, created_at DESC);

ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_audit_deny_anon" ON admin_audit_log;
CREATE POLICY "admin_audit_deny_anon" ON admin_audit_log FOR ALL TO anon USING (false);
