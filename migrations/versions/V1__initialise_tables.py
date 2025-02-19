from alembic import op
from sqlalchemy.sql import text

revision = 'V1'
down_revision = None

def upgrade():
    # On Azure PostgreSQL, the PostGIS extension must be explicitly enabled at the server level before it can be 
    # installed in the database.
    sql = """
    CREATE EXTENSION IF NOT EXISTS postgis;

    CREATE TABLE IF NOT EXISTS tracks (
        track_id SERIAL PRIMARY KEY,
        isrc VARCHAR(50) UNIQUE NOT NULL,
        spotify_id VARCHAR(255) UNIQUE NOT NULL,
        deezer_id INTEGER UNIQUE NOT NULL CHECK (deezer_id > 0),
        name VARCHAR(255) NOT NULL,
        artists TEXT[] NOT NULL CHECK (array_length(artists, 1) > 0),
        cover_small TEXT,
        cover_medium TEXT,
        cover_large TEXT NOT NULL,
        preview_url TEXT NOT NULL,
        CONSTRAINT unique_identifiers UNIQUE (isrc, spotify_id, deezer_id)
    );

    CREATE TABLE IF NOT EXISTS localities (
        locality_id INTEGER PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
        longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
        geog GEOGRAPHY(Point, 4326) GENERATED ALWAYS AS (
            ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        ) STORED
    );

    CREATE INDEX IF NOT EXISTS localities_geog_gist ON localities USING GIST (geog);

    CREATE TABLE IF NOT EXISTS locality_tracks (
        locality_id INTEGER REFERENCES localities(locality_id) ON DELETE CASCADE,
        track_id INTEGER REFERENCES tracks(track_id) ON DELETE CASCADE,
        PRIMARY KEY (locality_id, track_id)
    );

    CREATE INDEX IF NOT EXISTS ix_locality_tracks_locality_id ON locality_tracks (locality_id);
    """
    op.execute(text(sql))


def downgrade():
    sql = """
    DROP TABLE IF EXISTS locality_tracks;
    DROP INDEX IF EXISTS localities_geog_gist;
    DROP TABLE IF EXISTS localities;
    DROP TABLE IF EXISTS tracks;
    DROP EXTENSION IF EXISTS postgis;
    """
    op.execute(text(sql))
