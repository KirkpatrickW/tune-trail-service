import os
import sys
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command
import asyncio
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Add the app directory to the Python path
app_dir = os.path.join(project_root, 'app')
sys.path.insert(0, app_dir)

from app.models.postgresql import Base

# Test database configuration
TEST_DB_HOST = "localhost"
TEST_DB_PORT = "5432"
TEST_DB_NAME = "tunetrail_test"
TEST_DB_USER = "postgres"
TEST_DB_PASSWORD = "postgres"

# Use synchronous URL for migrations
TEST_DATABASE_URL = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
# Use async URL for SQLAlchemy
TEST_DATABASE_URL_ASYNC = f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"

def create_test_database():
    """Create the test database if it doesn't exist."""
    # Connect to default postgres database
    conn = psycopg2.connect(
        host=TEST_DB_HOST,
        port=TEST_DB_PORT,
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # Check if database exists
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
    exists = cur.fetchone()
    
    if not exists:
        # Create the database
        cur.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
        print(f"Created test database: {TEST_DB_NAME}")
    
    cur.close()
    conn.close()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine and run migrations."""
    # Create test database if it doesn't exist
    create_test_database()
    
    # Run migrations synchronously first
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    
    # Create async engine for tests
    engine = create_async_engine(TEST_DATABASE_URL_ASYNC, echo=True)
    
    try:
        yield engine
    finally:
        # Clean up tables after all tests
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            await engine.dispose()

@pytest.fixture(autouse=True)
async def cleanup_database(test_engine):
    """Clean up the database after each test file."""
    try:
        async with test_engine.begin() as conn:
            # Delete all data from all tables
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
    except Exception as e:
        print(f"Error during database cleanup: {e}")

@pytest.fixture
async def test_session(test_engine):
    """Create a test database session."""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback() 