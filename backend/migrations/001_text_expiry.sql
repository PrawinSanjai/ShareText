-- Apply once to existing PostgreSQL installations before deploying the expiry-aware API.
BEGIN;

ALTER TABLE text_secret_key
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

UPDATE text_secret_key
SET expires_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) + INTERVAL '24 hours'
WHERE expires_at IS NULL;

ALTER TABLE text_secret_key
    ALTER COLUMN expires_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_text_secret_key_expires_at
    ON text_secret_key (expires_at);
CREATE INDEX IF NOT EXISTS ix_text_secret_key_is_deleted
    ON text_secret_key (is_deleted);
CREATE INDEX IF NOT EXISTS ix_assoc_text_data_key_text_data_id
    ON assoc_text_data_key (text_data_id);
CREATE INDEX IF NOT EXISTS ix_assoc_text_data_key_text_secret_key
    ON assoc_text_data_key (text_secret_key);

COMMIT;
