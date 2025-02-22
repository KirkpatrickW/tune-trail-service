from fastapi import HTTPException
from alembic.config import Config
from alembic import command
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from geoalchemy2 import functions as geo_functions, Geography
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, aliased
from sqlalchemy.future import select
from sqlalchemy import func

from config.logger import Logger
from models.postgresql.locality import Locality
from models.postgresql.track import Track
from models.postgresql.locality_track import LocalityTrack

logger = Logger()

class PostgreSQLClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
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


    async def get_or_create_locality(self, session: AsyncSession, locality_id: int, name: str, latitude: float, longitude: float):
        locality = await session.get(Locality, locality_id)
        if not locality:
            locality = Locality(locality_id=locality_id, name=name, latitude=latitude, longitude=longitude)
            session.add(locality)
            await session.flush()
        return locality


    async def get_or_create_track(self, session: AsyncSession, track_data: dict):
        cover_data = track_data.get("cover", {})
        track_data["cover_small"] = str(cover_data.get("small"))
        track_data["cover_medium"] = str(cover_data.get("medium"))
        track_data["cover_large"] = str(cover_data.get("large"))
        track_data["preview_url"] = str(track_data["preview_url"])

        track_data.pop("cover", None)

        stmt = select(Track).where(Track.isrc == track_data["isrc"])
        result = await session.execute(stmt)
        track = result.scalars().first()

        if not track:
            track = Track(**track_data)
            session.add(track)
            await session.flush()
            await session.refresh(track)

        return track


    async def link_track_to_locality(self, session: AsyncSession, locality_id: int, track_id: int):
        stmt = select(LocalityTrack).where(
            (LocalityTrack.locality_id == locality_id) &
            (LocalityTrack.track_id == track_id))
        result = await session.execute(stmt)
        link = result.scalars().first()

        if not link:
            new_link = LocalityTrack(locality_id=locality_id, track_id=track_id)
            session.add(new_link)
            await session.flush()


    async def get_localities(self, session: AsyncSession, north: float, east: float, south: float, west: float):
        bbox = geo_functions.ST_MakeEnvelope(west, south, east, north, 4326).cast(Geography)

        track_count = select(func.count(LocalityTrack.track_id))\
            .where(LocalityTrack.locality_id == Locality.locality_id)\
            .correlate(Locality)\
            .scalar_subquery()
        
        stmt = select(
                Locality,
                track_count.label('track_count'))\
            .where(geo_functions.ST_Intersects(Locality.geog, bbox))

        result = await session.execute(stmt)
        localities = result.all()
        return [
            {
                **locality.__dict__,
                "track_count": track_count
            }
            for locality, track_count in localities
        ]
    
    async def get_tracks_in_locality(self, session: AsyncSession, locality_id: int):
        stmt = select(Track)\
            .join(LocalityTrack, Track.track_id == LocalityTrack.track_id)\
            .where(LocalityTrack.locality_id == locality_id)
        
        result = await session.execute(stmt)
        return result.scalars().all()