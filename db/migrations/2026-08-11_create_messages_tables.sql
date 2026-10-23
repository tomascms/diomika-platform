-- Create contact_messages table
CREATE TABLE IF NOT EXISTS contact_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome text,
    email text,
    contacto text,
    assunto text,
    mensagem text,
    lida boolean DEFAULT false,
    visibilidade boolean DEFAULT true,
    status text DEFAULT 'Nova',
    last_sender text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create message_history table
CREATE TABLE IF NOT EXISTS message_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id uuid REFERENCES contact_messages(id) ON DELETE CASCADE,
    sender_email text,
    body text,
    created_at timestamptz DEFAULT now()
);

-- Migração para bases de dados existentes
ALTER TABLE contact_messages ADD COLUMN IF NOT EXISTS contacto text;
