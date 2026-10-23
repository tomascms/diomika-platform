-- Add invoice generation columns to orders table
-- Migration: 002_orders_invoice_columns
-- Purpose: Track invoice PDF generation and storage

BEGIN;

-- Add invoice tracking columns to orders table
ALTER TABLE orders
ADD COLUMN IF NOT EXISTS invoice_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS invoice_generated_at TIMESTAMP WITH TIME ZONE;

-- Create index for invoice tracking
CREATE INDEX IF NOT EXISTS idx_orders_invoice_url ON orders(invoice_url);
CREATE INDEX IF NOT EXISTS idx_orders_invoice_generated ON orders(invoice_generated_at);

-- Add comment
COMMENT ON COLUMN orders.invoice_url IS 'S3 URL to generated invoice PDF';
COMMENT ON COLUMN orders.invoice_generated_at IS 'Timestamp when invoice was generated';

-- Verify columns added
\d orders

COMMIT;
