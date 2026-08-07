-- ponytail: conversation_turns is deferred to epic I (query submission), since it
-- references query_telemetry which doesn't exist until POST /v1/query is built.
CREATE TABLE conversations (
    conversation_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id),
    title             TEXT,
    pinned            BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversations_user ON conversations (user_id, pinned DESC, last_active_at DESC);
