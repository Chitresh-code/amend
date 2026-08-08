-- ingestion_state must be able to record a failed attempt for a document that
-- never successfully fetched (and so never got a documents row: source_checksum
-- and retrieved_at are NOT NULL there and only exist once a fetch succeeds).
-- Discovered running a real ingestion: a fetch timeout on one document crashed
-- the whole run because recording its failure violated this FK.
ALTER TABLE ingestion_state DROP CONSTRAINT ingestion_state_document_id_fkey;
