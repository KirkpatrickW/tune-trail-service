from alembic import op
from sqlalchemy.sql import text

revision = 'V5'
down_revision = 'V4'

def upgrade():
    sql = """
    ALTER TABLE tracks ADD COLUMN is_banned BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE tracks ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
    ALTER TABLE tracks ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

    ALTER TABLE localities ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
    ALTER TABLE localities ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

    ALTER TABLE locality_tracks ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
    ALTER TABLE locality_tracks ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

    -- Create a trigger function to delete associated records when a track is banned
    CREATE OR REPLACE FUNCTION delete_associated_records_on_ban()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Check if the track is being banned (is_banned set to TRUE)
        IF NEW.is_banned = TRUE THEN
            -- Delete associated records in locality_tracks
            DELETE FROM locality_tracks WHERE track_id = NEW.track_id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Create a trigger to invoke the function whenever a track is updated
    CREATE TRIGGER trg_delete_associated_records_on_ban
    BEFORE UPDATE ON tracks
    FOR EACH ROW
    EXECUTE FUNCTION delete_associated_records_on_ban();

    CREATE TRIGGER trg_update_tracks_updated_at
    BEFORE UPDATE ON tracks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

    CREATE TRIGGER trg_update_localities_updated_at
    BEFORE UPDATE ON localities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

    CREATE TRIGGER trg_update_locality_tracks_updated_at
    BEFORE UPDATE ON locality_tracks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
    """
    op.execute(text(sql))


def downgrade():
    sql = """
    DROP TRIGGER IF EXISTS trg_update_locality_tracks_updated_at ON locality_tracks;
    DROP TRIGGER IF EXISTS trg_update_localities_updated_at ON localities;
    DROP TRIGGER IF EXISTS trg_update_tracks_updated_at ON tracks;

    DROP TRIGGER IF EXISTS trg_delete_associated_records_on_ban ON tracks;
    DROP FUNCTION IF EXISTS delete_associated_records_on_ban;

    ALTER TABLE tracks DROP COLUMN IF EXISTS is_banned;
    ALTER TABLE tracks DROP COLUMN IF EXISTS created_at;
    ALTER TABLE tracks DROP COLUMN IF EXISTS updated_at;

    ALTER TABLE localities DROP COLUMN IF EXISTS created_at;
    ALTER TABLE localities DROP COLUMN IF EXISTS updated_at;

    ALTER TABLE locality_tracks DROP COLUMN IF EXISTS created_at;
    ALTER TABLE locality_tracks DROP COLUMN IF EXISTS updated_at;
    """
    op.execute(text(sql))
