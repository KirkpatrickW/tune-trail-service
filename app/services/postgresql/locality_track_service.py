from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.postgresql import LocalityTrack

from services.postgresql.locality_service import LocalityService
from services.postgresql.track_service import TrackService
from services.postgresql.user_service import UserService

class LocalityTrackService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalityTrackService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    

    def _init(self):
        self.user_service = UserService()
        self.locality_service = LocalityService()
        self.track_service = TrackService()


    async def get_locality_track_by_locality_track_id(self, session: AsyncSession, locality_track_id: int):
        stmt = select(LocalityTrack).where(LocalityTrack.locality_track_id == locality_track_id)
        result = await session.execute(stmt)
        locality_track = result.scalars().first()
        
        return locality_track


    async def add_track_to_locality(self, session: AsyncSession, locality_id: int, track_id: int, user_id: int):
        locality = await self.locality_service.get_locality_by_locality_id(session, locality_id)
        if not locality:
            raise HTTPException(status_code=404, detail="Locality not found")

        track = await self.track_service.get_track_by_track_id(session, track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        user = await self.user_service.get_user_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        stmt = select(LocalityTrack).where(
            (LocalityTrack.locality_id == locality_id) &
            (LocalityTrack.track_id == track_id))
        result = await session.execute(stmt)
        link = result.scalars().first()

        if not link:
            new_link = LocalityTrack(locality_id=locality_id, track_id=track_id, user_id=user_id)
            session.add(new_link)
            await session.flush()