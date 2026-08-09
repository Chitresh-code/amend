-- DATA_MODEL.md §1.5
-- Not a secret (it's a host, not a key), so it's stored and returned as
-- plaintext, unlike encrypted_key. NULL uses provider's own default API host.
ALTER TABLE model_credentials ADD COLUMN base_url TEXT;
