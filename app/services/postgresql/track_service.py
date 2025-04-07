from typing import List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.postgresql import LocalityTrack, Track, User

from services.postgresql.locality_service import LocalityService

class TrackService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TrackService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    

    def _init(self):
        self.locality_service = LocalityService()
    

    async def get_track_by_track_id(self, session: AsyncSession, track_id: int):
        stmt = select(Track).where(Track.track_id == track_id)
        result = await session.execute(stmt)
        track = result.scalars().first()

        return track


    async def get_track_by_spotify_id(self, session: AsyncSession, spotify_id: str):
        stmt = select(Track).where(Track.spotify_id == spotify_id)
        result = await session.execute(stmt)
        track = result.scalars().first()

        return track
    

    async def get_all_banned_tracks(self, session: AsyncSession):
        stmt = select(Track).where(Track.is_banned == True)
        result = await session.execute(stmt)
        banned_tracks = result.scalars().all()

        return banned_tracks


    async def add_new_track(self, session: AsyncSession, isrc: str, spotify_id: str, deezer_id: int, name: str, artists: List[str], cover_large: str, cover_medium: str = None, cover_small: str = None):
        existing_track = await self.get_track_by_spotify_id(session, spotify_id)
        if existing_track:
            raise HTTPException(status_code=400, detail="Track already exists")
        
        track = Track(
            isrc=isrc,
            spotify_id=spotify_id,
            deezer_id=deezer_id,
            name=name,
            artists=artists,
            cover_large=cover_large,
            cover_medium=cover_medium,
            cover_small=cover_small)
        session.add(track)

        await session.flush()
        await session.refresh(track)

        return track


    async def get_tracks_in_locality(self, session: AsyncSession, locality_id: int):
        locality = await self.locality_service.get_locality_by_locality_id(session, locality_id)
        if not locality:
            raise HTTPException(status_code=404, detail="Locality not found")

        stmt = select(Track, User.username, User.user_id, LocalityTrack.total_votes, LocalityTrack.locality_track_id) \
            .join(LocalityTrack, Track.track_id == LocalityTrack.track_id) \
            .join(User, LocalityTrack.user_id == User.user_id) \
            .where(LocalityTrack.locality_id == locality_id) \
            .order_by(LocalityTrack.total_votes.desc())
        result = await session.execute(stmt)

        attributed_tracks = []
        for track, username, user_id, total_votes, locality_track_id in result.all():
            track.locality_track_id = locality_track_id
            track.username = username
            track.user_id = user_id
            track.total_votes = total_votes
            attributed_tracks.append(track)

        return attributed_tracks
    

    async def ban_track_by_track_id(self, session: AsyncSession, track_id: int):
        track = await self.get_track_by_track_id(session, track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        if track.is_banned == False:
            track.is_banned = True

        await session.flush()
        await session.refresh(track)

        return track
    

    async def unban_track_by_track_id(self, session: AsyncSession, track_id: int):
        track = await self.get_track_by_track_id(session, track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        if track.is_banned == True:
            track.is_banned = False

        await session.flush()
        await session.refresh(track)

        return track