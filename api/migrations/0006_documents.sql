-- DATA_MODEL.md §1.1
CREATE TABLE documents (
    document_id       TEXT PRIMARY KEY,
    regulator          TEXT NOT NULL CHECK (regulator IN ('RBI', 'SEBI')),
    document_type      TEXT NOT NULL,
    title              TEXT NOT NULL,
    reference_number   TEXT,
    publication_date   DATE,
    effective_date     DATE,
    status             TEXT NOT NULL DEFAULT 'active',
    source_url         TEXT NOT NULL,
    source_checksum    TEXT NOT NULL,
    retrieved_at       TIMESTAMPTZ NOT NULL,
    parser_version     TEXT NOT NULL,
    ingestion_version  TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_regulator_type ON documents (regulator, document_type);
CREATE INDEX idx_documents_effective_date ON documents (effective_date);
