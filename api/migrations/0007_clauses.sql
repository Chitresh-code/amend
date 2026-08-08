-- DATA_MODEL.md §1.2
CREATE TABLE clauses (
    clause_id         TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL REFERENCES documents(document_id),
    parent_clause_id  TEXT REFERENCES clauses(clause_id),
    clause_number      TEXT NOT NULL,
    heading            TEXT,
    text               TEXT NOT NULL,
    page_number        INT,
    effective_from     DATE,
    effective_until    DATE,
    status             TEXT NOT NULL DEFAULT 'active',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_clauses_document_id ON clauses (document_id);
CREATE INDEX idx_clauses_effective_range ON clauses (effective_from, effective_until);
