from alembic import op
from sqlalchemy.sql import text

revision = 'V2'
down_revision = 'V1'

def upgrade():
    sql = """
    CREATE TABLE users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE, -- NULL for incomplete profile (needs a username for OAuth accounts)
        hashed_password BYTEA, -- NULL for OAuth-only accounts
        is_oauth_account BOOLEAN NOT NULL,
        is_admin BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE user_spotify_oauth_accounts (
        user_spotify_oauth_account_id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
        provider_user_id VARCHAR(255) NOT NULL UNIQUE,
        encrypted_access_token TEXT,
        encrypted_refresh_token TEXT,
        access_token_expires_at TIMESTAMPTZ,
        subscription VARCHAR(50),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (provider_user_id)
    );

    CREATE TABLE user_sessions (
        user_session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at TIMESTAMPTZ NOT NULL, 
        is_invalidated BOOLEAN NOT NULL DEFAULT FALSE
    );

    ALTER TABLE locality_tracks ADD COLUMN user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE;

    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$ 
    BEGIN 
        NEW.updated_at = now(); 
        RETURN NEW; 
    END; 
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

    CREATE TRIGGER trg_update_oauth_accounts_updated_at
    BEFORE UPDATE ON user_spotify_oauth_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

    CREATE TRIGGER trg_update_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
    """
    op.execute(text(sql))


def downgrade():
    sql = """
    DROP TRIGGER IF EXISTS trg_update_user_sessions_updated_at ON user_sessions;
    DROP TRIGGER IF EXISTS trg_update_oauth_accounts_updated_at ON user_spotify_oauth_accounts;
    DROP TRIGGER IF EXISTS trg_update_users_updated_at ON users;

    DROP FUNCTION IF EXISTS update_updated_at_column;

    ALTER TABLE locality_tracks DROP COLUMN user_id;

    DROP TABLE IF EXISTS user_sessions;
    DROP TABLE IF EXISTS user_spotify_oauth_accounts;
    DROP TABLE IF EXISTS users;
    """
    op.execute(text(sql))
