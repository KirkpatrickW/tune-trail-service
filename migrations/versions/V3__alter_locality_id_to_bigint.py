from alembic import op
from sqlalchemy.sql import text

revision = 'V3'
down_revision = 'V2'

def upgrade():
    sql = """
    ALTER TABLE locality_tracks ALTER COLUMN locality_id TYPE BIGINT;
    ALTER TABLE localities ALTER COLUMN locality_id TYPE BIGINT;
    """
    op.execute(text(sql))

def downgrade():
    sql = """
    ALTER TABLE locality_tracks ALTER COLUMN locality_id TYPE INTEGER;
    ALTER TABLE localities ALTER COLUMN locality_id TYPE INTEGER;
    """
    op.execute(text(sql))
