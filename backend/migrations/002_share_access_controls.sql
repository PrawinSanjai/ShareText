-- Apply after 001_text_expiry.sql to support view limits and password protection.
BEGIN;

ALTER TABLE text_secret_key
    ADD COLUMN IF NOT EXISTS max_views INTEGER NULL,
    ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS password_hash TEXT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_text_secret_key_positive_max_views'
    ) THEN
        ALTER TABLE text_secret_key
            ADD CONSTRAINT ck_text_secret_key_positive_max_views
            CHECK (max_views IS NULL OR max_views > 0);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_text_secret_key_nonnegative_view_count'
    ) THEN
        ALTER TABLE text_secret_key
            ADD CONSTRAINT ck_text_secret_key_nonnegative_view_count
            CHECK (view_count >= 0);
    END IF;
END $$;

COMMIT;
