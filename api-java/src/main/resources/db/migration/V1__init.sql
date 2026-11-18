CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    fields JSON,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processing_notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'processing'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER,
    invoice_value DOUBLE PRECISION,
    hs_code VARCHAR(255),
    party VARCHAR(255),
    risk_score DOUBLE PRECISION,
    is_flagged BOOLEAN DEFAULT FALSE,
    metadata JSON,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_document_id ON transactions(document_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    action VARCHAR(255),
    payload JSON,
    hash VARCHAR(255)
);
