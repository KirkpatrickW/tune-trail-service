from fastapi import HTTPException

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from geoalchemy2 import Geography, functions as geo_functions

from models.postgresql import Locality

class LocalityService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalityService, cls).__new__(cls)
        return cls._instance
    

    async def get_locality_by_locality_id(self, session: AsyncSession, locality_id: int):
        stmt = select(Locality).where(Locality.locality_id == locality_id)
        result = await session.execute(stmt)
        locality = result.scalars().first()

        session.expunge_all()
        
        return locality
    

    async def add_new_locality(self, session: AsyncSession, locality_id: int, name: str, latitude: float, longitude: float):
        existing_locality = await self.get_locality_by_locality_id(session, locality_id)
        if existing_locality:
            raise HTTPException(status_code=400, detail="Locality already exists")

        locality = Locality(locality_id=locality_id, name=name, latitude=latitude, longitude=longitude)
        session.add(locality)

        await session.flush()
        await session.refresh(locality)
        session.expunge_all()

        return locality


    async def get_localities_by_bounds(self, session: AsyncSession, north: float, east: float, south: float, west: float):
        bbox = geo_functions.ST_MakeEnvelope(west, south, east, north, 4326).cast(Geography)

        stmt = select(Locality).where(geo_functions.ST_Intersects(Locality.geog, bbox))
        result = await session.execute(stmt)
        localities = result.scalars().all()

        session.expunge_all()

        return localities
