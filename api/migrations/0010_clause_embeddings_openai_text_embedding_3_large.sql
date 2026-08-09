-- DATA_MODEL.md §1.3
--
-- text-embedding-3-large's native output is 3072 dimensions, but pgvector's
-- hnsw index rejects columns over 2000 dimensions (confirmed against a real
-- migration run: "column cannot have more than 2000 dimensions for hnsw
-- index"). OpenAI's `dimensions` request parameter shortens the embedding
-- server-side (a trained matryoshka-style reduction, not naive truncation)
-- without materially hurting retrieval quality - OpenAI's own docs note a
-- -large embedding shortened to 256 still outperforms full-size ada-002 at
-- 1536. The ingestion embedding call passes dimensions=1536 to match this
-- column; see app/ingestion/embed.py.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE clause_embeddings_openai_text_embedding_3_large (
    clause_id  TEXT PRIMARY KEY REFERENCES clauses(clause_id),
    embedding  VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_emb_openai_3_large_hnsw
    ON clause_embeddings_openai_text_embedding_3_large
    USING hnsw (embedding vector_cosine_ops);

INSERT INTO embedding_models (embedding_model_id, provider, model_id, dimension, status, table_name)
VALUES ('openai:text-embedding-3-large', 'openai', 'text-embedding-3-large', 1536, 'building',
        'clause_embeddings_openai_text_embedding_3_large')
ON CONFLICT (embedding_model_id) DO UPDATE SET
    status = 'building', table_name = EXCLUDED.table_name, dimension = EXCLUDED.dimension;
