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

# Test database configuration
TEST_DB_HOST = "localhost"
TEST_DB_PORT = "5432"
TEST_DB_NAME = "tunetrail_test"
TEST_DB_USER = "postgres"
TEST_DB_PASSWORD = "postgres"

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "app"))

from app.models.postgresql import Base

# Use synchronous URL for migrations
TEST_DATABASE_URL = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
# Use async URL for SQLAlchemy
TEST_DATABASE_URL_ASYNC = f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"

def create_test_database():
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
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    # Create test database if it doesn't exist
    create_test_database()
    
    # Run migrations synchronously first
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    
    try:
        # Drop only our application tables
        conn = psycopg2.connect(
            host=TEST_DB_HOST,
            port=TEST_DB_PORT,
            user=TEST_DB_USER,
            password=TEST_DB_PASSWORD,
            database=TEST_DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Drop only our application tables
        cur.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            AND tablename NOT IN ('spatial_ref_sys')  -- Exclude system tables
        """)
        tables = cur.fetchall()
        for table in tables:
            cur.execute(f'DROP TABLE IF EXISTS "{table[0]}" CASCADE')
        
        cur.close()
        conn.close()
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        print("Migrations applied successfully")
    except Exception as e:
        print(f"Error during migration: {e}")
        raise
    
    # Create async engine for tests
    engine = create_async_engine(TEST_DATABASE_URL_ASYNC, echo=True)
    
    try:
        yield engine
    finally:
        # Clean up tables after all tests
        try:
            async with engine.begin() as conn:
                # Only drop our application tables
                for table in reversed(Base.metadata.sorted_tables):
                    await conn.execute(table.delete())
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            await engine.dispose()

@pytest.fixture(autouse=True)
async def cleanup_database(test_engine):
    try:
        async with test_engine.begin() as conn:
            # Delete all data from all tables
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
    except Exception as e:
        print(f"Error during database cleanup: {e}")

@pytest.fixture(scope="session")
def test_sessionmaker(test_engine):
    return sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture
async def test_session(test_sessionmaker):
    async with test_sessionmaker() as session:
        yield session
        await session.rollback()