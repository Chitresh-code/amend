-- DATA_MODEL.md §1.3
CREATE TABLE embedding_models (
    embedding_model_id TEXT PRIMARY KEY,
    provider            TEXT NOT NULL,
    model_id             TEXT NOT NULL,
    dimension            INT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'registered',
    table_name           TEXT UNIQUE,
    is_default            BOOLEAN NOT NULL DEFAULT false,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
