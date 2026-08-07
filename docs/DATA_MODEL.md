# Amend: Data Model

Concrete schema for the storage layers described in [ARCHITECTURE.md §5](./ARCHITECTURE.md#5-storage-responsibilities). The PRD specifies properties conceptually (§13 to §16, §43); this document fixes them to actual DDL and Cypher so ingestion and API code have a single source of truth. Treat this as a starting schema: it should evolve through migrations once real ingestion data exercises it, not as a frozen spec.

## 1. PostgreSQL

### 1.1 `documents`

```sql
CREATE TABLE documents (
    document_id       TEXT PRIMARY KEY,        -- deterministic id (PRD §11)
    regulator          TEXT NOT NULL CHECK (regulator IN ('RBI', 'SEBI')),
    document_type      TEXT NOT NULL,           -- circular, notification, master_direction, ...
    title              TEXT NOT NULL,
    reference_number   TEXT,
    publication_date   DATE,
    effective_date     DATE,
    status             TEXT NOT NULL DEFAULT 'active',
    source_url         TEXT NOT NULL,
    source_checksum    TEXT NOT NULL,           -- SHA-256 (PRD §48)
    retrieved_at       TIMESTAMPTZ NOT NULL,
    parser_version     TEXT NOT NULL,
    ingestion_version  TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_regulator_type ON documents (regulator, document_type);
CREATE INDEX idx_documents_effective_date ON documents (effective_date);
```

`regulator` is a plain `CHECK` constraint, not a lookup table: the MVP corpus (PRD §9) has exactly two values, and a lookup table would add a join for no behavioral benefit. Widen the `CHECK` when a third regulator (PRD §66) is added.

### 1.2 `clauses`

```sql
CREATE TABLE clauses (
    clause_id         TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL REFERENCES documents(document_id),
    parent_clause_id  TEXT REFERENCES clauses(clause_id),  -- nesting, e.g. 4.2 -> 4.2(a) (PRD §12)
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
```

The temporal validity check in PRD §22 (`effective_from <= T AND (effective_until IS NULL OR effective_until > T)`) runs directly against `idx_clauses_effective_range`.

### 1.3 Embeddings and embedding model registry (PRD §70.4)

A stored embedding is only comparable to a query embedding from the same model and dimension. Rather than one table with a single fixed-width `vector` column shared across models (which either restricts the deployment to one embedding model forever, or requires padding tricks to fake a shared dimension), each registered embedding model gets its own table with a `vector(N)` column sized exactly to that model's dimension. This keeps every table's HNSW index a normal, single-model index, no cross-model filtering logic required.

```sql
CREATE TABLE embedding_models (
    embedding_model_id TEXT PRIMARY KEY,   -- e.g. 'openai:text-embedding-3-large'
    provider            TEXT NOT NULL,
    model_id             TEXT NOT NULL,
    dimension            INT NOT NULL,
    table_name           TEXT NOT NULL UNIQUE,  -- e.g. 'clause_embeddings_openai_text_embedding_3_large'
    is_default            BOOLEAN NOT NULL DEFAULT false,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Registering a new embedding model is an ops action (ingestion configuration, PRD §70.4), performed through a migration, not a runtime client request; `table_name` is never built from request input, which is what makes per-model dynamic table creation safe here. Example for one registered model:

```sql
CREATE TABLE clause_embeddings_openai_text_embedding_3_large (
    clause_id  TEXT PRIMARY KEY REFERENCES clauses(clause_id),
    embedding  VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_emb_openai_3_large_hnsw
    ON clause_embeddings_openai_text_embedding_3_large
    USING hnsw (embedding vector_cosine_ops);
```

The ingestion worker writes to whichever table `INGESTION_EMBEDDING_PROVIDER`/`INGESTION_EMBEDDING_MODEL_ID` resolves to via `embedding_models.table_name`. The query path (§20) embeds the caller's question with the same model, per the `retrieval.embedding_model_id` request field in PRD §70.4, and searches only that table.

### 1.4 `model_credentials` (PRD §70.2)

```sql
CREATE TABLE api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash    TEXT NOT NULL UNIQUE,   -- HMAC(API_KEY_HASH_PEPPER, issued key), never the raw key
    label       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);

CREATE TABLE model_credentials (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id     UUID NOT NULL REFERENCES api_keys(id),
    provider       TEXT NOT NULL,
    encrypted_key  BYTEA NOT NULL,      -- Fernet(CREDENTIAL_ENCRYPTION_KEY) ciphertext
    key_suffix     TEXT NOT NULL,       -- last 4 chars, for display only
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (api_key_id, provider)
);
```

`encrypted_key` is opaque ciphertext; the decryption key (`CREDENTIAL_ENCRYPTION_KEY`) lives only in the deployment's secret store, never in this database. No column here or in `query_telemetry` ever holds a plaintext provider key.

### 1.5 `ingestion_state`

```sql
CREATE TABLE ingestion_state (
    document_id      TEXT PRIMARY KEY REFERENCES documents(document_id),
    stage             TEXT NOT NULL,   -- fetch, parse, segment, extract, embed, graph_write
    status            TEXT NOT NULL,   -- pending, succeeded, failed
    last_run_at       TIMESTAMPTZ,
    last_error        TEXT,
    checksum_at_run   TEXT             -- detects source drift on re-ingestion (PRD §11)
);
```

### 1.6 `query_telemetry` (PRD §52)

```sql
CREATE TABLE query_telemetry (
    query_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id           UUID NOT NULL REFERENCES api_keys(id),
    intent                TEXT,
    extracted_entities    JSONB,
    extracted_concepts    JSONB,
    requested_date        DATE,
    model_provider        TEXT,
    model_id              TEXT,
    embedding_model_id    TEXT REFERENCES embedding_models(embedding_model_id),
    vector_candidates     INT,
    graph_candidates      INT,
    validated_evidence    INT,
    final_citations       JSONB,
    latency_ms            INT,
    token_usage           JSONB,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_query_telemetry_created_at ON query_telemetry (created_at);
```

`idx_query_telemetry_created_at` supports the retention purge (PRD §52.1):

```sql
DELETE FROM query_telemetry WHERE created_at < now() - (current_setting('amend.telemetry_retention_days')::int || ' days')::interval;
```

run on a schedule (e.g. daily), with `amend.telemetry_retention_days` set from `TELEMETRY_RETENTION_DAYS` at connection time, not hardcoded into the query.

### 1.7 `conversations` and `conversation_turns` (PRD §71, ADR 0001)

```sql
CREATE TABLE conversations (
    conversation_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id        UUID NOT NULL REFERENCES api_keys(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversation_turns (
    turn_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID NOT NULL REFERENCES conversations(conversation_id),
    turn_index        INT NOT NULL,
    query_id          UUID NOT NULL REFERENCES query_telemetry(query_id),
    question          TEXT NOT NULL,
    answer            TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, turn_index)
);

CREATE INDEX idx_conversation_turns_conversation ON conversation_turns (conversation_id, turn_index);
```

A conversation belongs to exactly one `api_key_id`; nothing here lets one caller read another caller's conversation. `turn_id` links to `query_telemetry.query_id` rather than duplicating token usage/latency/citation fields, so a turn's full pipeline detail stays in one place. Only the last N turns (ADR 0001, bounded context window) are read back when building context for a new turn, not the whole conversation.

## 2. Neo4j

### 2.1 Node labels and properties

```text
(:Regulator {name})
(:Document {document_id, title, document_type, reference_number,
            publication_date, effective_date, status, source_url, checksum})
(:Clause {clause_id, document_id, clause_number, heading, text,
          page_number, effective_from, effective_until, status})
(:Entity {canonical_name, aliases})
(:RegulatoryConcept {name})
```

`Document` and `Clause` properties mirror the Postgres row for the same id, duplicated deliberately: Postgres is the system of record for content and metadata ([ARCHITECTURE.md §5](./ARCHITECTURE.md#5-storage-responsibilities)), Neo4j holds just enough of each node to make lineage traversal results self-describing without a join back to Postgres on every hop. The Postgres row remains authoritative if the two ever disagree.

### 2.2 Relationships

```text
(:Regulator)-[:ISSUES]->(:Document)
(:Document)-[:CONTAINS]->(:Clause)

(:Document)-[:AMENDS]->(:Document)
(:Document)-[:SUPERSEDES]->(:Document)
(:Document)-[:CLARIFIES]->(:Document)
(:Document)-[:CONSOLIDATES]->(:Document)
(:Document)-[:WITHDRAWS]->(:Document)

(:Clause)-[:AMENDS_CLAUSE]->(:Clause)
(:Clause)-[:SUPERSEDES_CLAUSE]->(:Clause)
(:Clause)-[:REFERENCES]->(:Clause)
(:Clause)-[:POTENTIALLY_CONTRADICTS]->(:Clause)

(:Clause)-[:APPLIES_TO]->(:Entity)
(:Clause)-[:RELATES_TO]->(:RegulatoryConcept)
```

Every automatically-inferred relationship (all except `ISSUES` and `CONTAINS`, which come directly from ingestion metadata) carries the provenance properties from PRD §15:

```text
extraction_method: explicit_reference | metadata | rule_based | llm_extraction | manual_review
confidence: float
review_status: automatic | reviewed
```

### 2.3 Constraints and indexes

```cypher
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.document_id IS UNIQUE;

CREATE CONSTRAINT clause_id_unique IF NOT EXISTS
FOR (c:Clause) REQUIRE c.clause_id IS UNIQUE;

CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.canonical_name IS UNIQUE;

CREATE CONSTRAINT concept_name_unique IF NOT EXISTS
FOR (rc:RegulatoryConcept) REQUIRE rc.name IS UNIQUE;

CREATE CONSTRAINT regulator_name_unique IF NOT EXISTS
FOR (r:Regulator) REQUIRE r.name IS UNIQUE;

CREATE INDEX clause_effective_range IF NOT EXISTS
FOR (c:Clause) ON (c.effective_from, c.effective_until);
```

These uniqueness constraints are what makes re-ingestion idempotent (PRD §11) at the graph level: a `MERGE` on `document_id` or `clause_id` cannot create a duplicate node once the constraint exists.

## 3. Cross-store consistency

`document_id` and `clause_id` are the join keys between Postgres and Neo4j. They are generated once, at ingestion time, from stable metadata and content hashes (PRD §11), and never regenerated for the same source content, so both stores stay addressable by the same id without a mapping table.
