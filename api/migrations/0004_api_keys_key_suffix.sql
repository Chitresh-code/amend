-- api_keys stores only a one-way HMAC of the raw key (0001), so the masked
-- display PRD §74 requires ("sk-amd-****1234") needs the suffix captured
-- separately, at issuance time, the same pattern as model_credentials.key_suffix.
ALTER TABLE api_keys ADD COLUMN key_suffix TEXT NOT NULL DEFAULT '';
ALTER TABLE api_keys ALTER COLUMN key_suffix DROP DEFAULT;
