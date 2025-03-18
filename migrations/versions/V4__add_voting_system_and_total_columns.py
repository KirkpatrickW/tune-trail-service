from alembic import op
from sqlalchemy.sql import text

revision = 'V4'
down_revision = 'V3'

def upgrade():
    sql = """
    ALTER TABLE locality_tracks DROP CONSTRAINT locality_tracks_pkey;

    ALTER TABLE locality_tracks ADD COLUMN locality_track_id SERIAL PRIMARY KEY;

    CREATE UNIQUE INDEX unique_locality_track ON locality_tracks(locality_id, track_id);

    CREATE TABLE locality_track_votes (
        locality_track_id INTEGER NOT NULL REFERENCES locality_tracks(locality_track_id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        vote SMALLINT NOT NULL CHECK (vote IN (-1, 1)),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (locality_track_id, user_id)
    );

    CREATE TRIGGER trg_update_votes_updated_at
    BEFORE UPDATE ON locality_track_votes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

    ALTER TABLE locality_tracks ADD COLUMN total_votes INTEGER NOT NULL DEFAULT 0;

    CREATE INDEX idx_locality_tracks_total_votes ON locality_tracks (total_votes);

    CREATE OR REPLACE FUNCTION update_total_votes()
    RETURNS TRIGGER AS $$
    BEGIN
        UPDATE locality_tracks 
        SET total_votes = (
            SELECT COUNT(*) FROM locality_track_votes 
            WHERE locality_track_id = NEW.locality_track_id
        )
        WHERE locality_tracks.locality_id = NEW.locality_track_id;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_update_total_votes_on_insert
    AFTER INSERT ON locality_track_votes
    FOR EACH ROW EXECUTE FUNCTION update_total_votes();

    CREATE TRIGGER trg_update_total_votes_on_delete
    AFTER DELETE ON locality_track_votes
    FOR EACH ROW EXECUTE FUNCTION update_total_votes();

    CREATE TRIGGER trg_update_total_votes_on_update
    AFTER UPDATE ON locality_track_votes
    FOR EACH ROW EXECUTE FUNCTION update_total_votes();

    ALTER TABLE localities ADD COLUMN total_tracks INTEGER NOT NULL DEFAULT 0;

    CREATE INDEX idx_localities_total_tracks ON localities (total_tracks);

    CREATE OR REPLACE FUNCTION update_total_tracks()
    RETURNS TRIGGER AS $$
    BEGIN
        UPDATE localities 
        SET total_tracks = (
            SELECT COUNT(*) FROM locality_tracks 
            WHERE locality_id = NEW.locality_id
        )
        WHERE localities.locality_id = NEW.locality_id;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_update_total_tracks_on_insert
    AFTER INSERT ON locality_tracks
    FOR EACH ROW EXECUTE FUNCTION update_total_tracks();

    CREATE TRIGGER trg_update_total_tracks_on_delete
    AFTER DELETE ON locality_tracks
    FOR EACH ROW EXECUTE FUNCTION update_total_tracks();

    CREATE TRIGGER trg_update_total_tracks_on_update
    AFTER UPDATE ON locality_tracks
    FOR EACH ROW EXECUTE FUNCTION update_total_tracks();
    """
    op.execute(text(sql))

def downgrade():
    sql = """
    DROP TRIGGER IF EXISTS trg_update_total_votes_on_insert ON locality_track_votes;
    DROP TRIGGER IF EXISTS trg_update_total_votes_on_delete ON locality_track_votes;
    DROP TRIGGER IF EXISTS trg_update_total_votes_on_update ON locality_track_votes;

    DROP TRIGGER IF EXISTS trg_update_total_tracks_on_insert ON locality_tracks;
    DROP TRIGGER IF EXISTS trg_update_total_tracks_on_delete ON locality_tracks;
    DROP TRIGGER IF EXISTS trg_update_total_tracks_on_update ON locality_tracks;

    DROP FUNCTION IF EXISTS update_total_votes;
    DROP FUNCTION IF EXISTS update_total_tracks;

    DROP INDEX IF EXISTS idx_locality_tracks_total_votes;
    DROP INDEX IF EXISTS idx_localities_total_tracks;

    ALTER TABLE locality_tracks DROP COLUMN IF EXISTS total_votes;

    ALTER TABLE localities DROP COLUMN IF EXISTS total_tracks;

    DROP TABLE IF EXISTS locality_track_votes;

    DROP INDEX IF EXISTS unique_locality_track;

    ALTER TABLE locality_tracks DROP COLUMN locality_track_id;
    ALTER TABLE locality_tracks ADD PRIMARY KEY (locality_id, track_id);
    """
    op.execute(text(sql))