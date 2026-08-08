-- DATA_MODEL.md §1.6
CREATE TABLE ingestion_state (
    document_id      TEXT PRIMARY KEY REFERENCES documents(document_id),
    stage             TEXT NOT NULL,
    status            TEXT NOT NULL,
    last_run_at       TIMESTAMPTZ,
    last_error        TEXT,
    checksum_at_run   TEXT
);
