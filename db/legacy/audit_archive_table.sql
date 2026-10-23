-- Create audit_archive table for long-term storage
-- Migration: 001_audit_archive_table
-- Purpose: Archive old audit logs before deletion
-- Retention: 365+ days for compliance

BEGIN;

-- Create audit_archive table (same schema as audit_trail)
CREATE TABLE IF NOT EXISTS audit_archive (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    result VARCHAR(20) NOT NULL,
    user_id VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    request_id VARCHAR(36),
    ip_address INET,
    error_message TEXT,
    old_values JSONB,
    new_values JSONB,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient archival queries
CREATE INDEX idx_audit_archive_created_at ON audit_archive(created_at DESC);
CREATE INDEX idx_audit_archive_action ON audit_archive(action, created_at DESC);
CREATE INDEX idx_audit_archive_user_id ON audit_archive(user_id, created_at DESC);
CREATE INDEX idx_audit_archive_resource ON audit_archive(resource_type, resource_id);

-- Create indexes on audit_trail for retention cleanup
CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at ON audit_trail(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trail_action ON audit_trail(action, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trail_user_id ON audit_trail(user_id, created_at DESC);

-- Verify table structure
\d audit_archive

COMMIT;
