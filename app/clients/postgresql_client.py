from fastapi import HTTPException
from alembic.config import Config
from alembic import command
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config.logger import Logger

logger = Logger()

class PostgreSQLClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgreSQLClient, cls).__new__(cls)
            cls._instance._init()
        return cls._instance


    def _init(self):
        self._db_host = "tunetrail-postgresql-server.postgres.database.azure.com"
        self._db_port = "5432"
        self._db_name = "tunetrail"
        self._db_user = "tunetrail_admin"
        self._db_password = "COM668PostgreSQL!"

        self._database_url = (
            f"postgresql+asyncpg://{self._db_user}:{self._db_password}@{self._db_host}:{self._db_port}/{self._db_name}?ssl=require"
        )

        logger.info(f"Initialising Azure PostgreSQL client for {self._db_host}...")

        self._engine = create_async_engine(self._database_url, echo=True)
        self._SessionLocal = sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)

        logger.info("Azure PostgreSQL client initialised successfully.")


    def run_migrations(self):
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"postgresql://{self._db_user}:{self._db_password}@{self._db_host}:{self._db_port}/{self._db_name}?sslmode=require")

        try:
            logger.info("Starting Alembic migration process...")
            command.upgrade(alembic_cfg, "head")
            logger.info("Migrations applied successfully.")
        except OperationalError as e:
            raise RuntimeError("Could not connect to the database. Check your connection settings.") from e
        except Exception as e:
            raise RuntimeError("Alembic migration process failed.") from e
        

    async def get_session(self):
        try:
            async with self._SessionLocal() as session:
                yield session
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail=f"Database error occurred: {str(e)}")