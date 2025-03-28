from fastapi import HTTPException

from sqlalchemy import join
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from geoalchemy2 import Geography, functions as geo_functions

from models.postgresql import Locality, LocalityTrack, Track

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
        
        return locality
    

    async def add_new_locality(self, session: AsyncSession, locality_id: int, name: str, latitude: float, longitude: float):
        existing_locality = await self.get_locality_by_locality_id(session, locality_id)
        if existing_locality:
            raise HTTPException(status_code=400, detail="Locality already exists")

        locality = Locality(locality_id=locality_id, name=name, latitude=latitude, longitude=longitude)
        session.add(locality)

        await session.flush()
        await session.refresh(locality)

        return locality


    async def get_localities_by_bounds(self, session: AsyncSession, north: float, east: float, south: float, west: float):
        bbox = geo_functions.ST_MakeEnvelope(west, south, east, north, 4326).cast(Geography)

        stmt = select(Locality).where(geo_functions.ST_Intersects(Locality.geog, bbox))
        result = await session.execute(stmt)
        localities = result.scalars().all()

        return localities


    async def get_tracks_for_localities_within_radius(self, session: AsyncSession, latitude: float, longitude: float, radius: float):
        center_point = geo_functions.ST_SetSRID(geo_functions.ST_MakePoint(longitude, latitude), 4326).cast(Geography)

        stmt = select(Locality.locality_id, Locality.name, Track, LocalityTrack.total_votes) \
            .select_from(join(Locality, LocalityTrack, Locality.locality_id == LocalityTrack.locality_id)
                .join(Track, Track.track_id == LocalityTrack.track_id)) \
            .where(geo_functions.ST_DWithin(Locality.geog, center_point, radius)) \
            .order_by(geo_functions.ST_Distance(Locality.geog, center_point))
        

        result = await session.execute(stmt)
        rows = result.all()

        locality_map = {}
        for locality_id, locality_name, track, total_votes in rows:
            key = (locality_id, locality_name)
            if key not in locality_map:
                locality_map[key] = {
                    "locality_id": locality_id,
                    "name": locality_name,
                    "tracks": []
                }
            locality_map[key]["tracks"].append((track, total_votes))

        return [
            {
                "locality_id": locality_id,
                "name": name,
                "tracks": [track for track, _ in sorted(data["tracks"], key=lambda t: t[1], reverse=True)]
            }
            for (locality_id, name), data in locality_map.items()
        ]