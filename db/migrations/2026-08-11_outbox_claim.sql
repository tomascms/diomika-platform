-- Outbox claim atomico (multi-worker / scale) — idempotente
ALTER TABLE outbox_events ADD COLUMN IF NOT EXISTS claimed_by text;
ALTER TABLE outbox_events ADD COLUMN IF NOT EXISTS claimed_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_outbox_processing ON outbox_events (status, claimed_at)
  WHERE status = 'processing';
