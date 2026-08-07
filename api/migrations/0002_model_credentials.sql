-- DATA_MODEL.md §1.5

CREATE TABLE model_credentials (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(id),
    provider       TEXT NOT NULL,
    model_id       TEXT NOT NULL,
    encrypted_key  BYTEA NOT NULL,
    key_suffix     TEXT NOT NULL,
    is_default     BOOLEAN NOT NULL DEFAULT false,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);

CREATE UNIQUE INDEX idx_model_credentials_one_default
    ON model_credentials (user_id) WHERE is_default;
