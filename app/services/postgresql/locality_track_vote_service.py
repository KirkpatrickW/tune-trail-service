from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.schemas.locality_tracks.vote_on_locality_track_request import VoteValueEnum
from models.postgresql import LocalityTrackVote

from services.postgresql.locality_track_service import LocalityTrackService
from services.postgresql.user_service import UserService

class LocalityTrackVoteService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalityTrackVoteService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    

    def _init(self):
        self.user_service = UserService()
        self.locality_track_service = LocalityTrackService()


    async def get_locality_track_vote_by_user_id_and_locality_track_id(self, session: AsyncSession, locality_track_id: int, user_id: int):
        stmt = select(LocalityTrackVote).filter_by(user_id=user_id, locality_track_id=locality_track_id)
        result = await session.execute(stmt)
        locality_track_vote = result.scalars().first()

        session.expunge_all()

        return locality_track_vote


    async def vote_locality_track(self, session: AsyncSession, locality_track_id: int, user_id: int, vote_value: VoteValueEnum):
        if vote_value not in [VoteValueEnum.UPVOTE, VoteValueEnum.DOWNVOTE]:
            raise HTTPException(status_code=500, detail="Invalid vote value, must be UPVOTE or DOWNVOTE")

        locality_track = await self.locality_track_service.get_locality_track_by_locality_track_id(session, locality_track_id)
        if not locality_track:
            raise HTTPException(status_code=404, detail="Track in locality not found")
        
        user = await self.user_service.get_user_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        

        locality_track_vote = await self.get_locality_track_vote_by_user_id_and_locality_track_id(session, user_id, locality_track_id)
        if locality_track_vote:
            locality_track_vote.vote = vote_value.value
        else:
            locality_track_vote = LocalityTrackVote(
                locality_track_id = locality_track_id,
                user_id = user_id,
                vote = vote_value.value)
            session.add(locality_track_vote)

        await session.flush()
        await session.refresh(locality_track_vote)

        session.expunge_all()

        return locality_track_vote
    

    async def unvote_locality_track(self, session: AsyncSession, locality_track_id: int, user_id: int):
        locality_track_vote = await self.get_locality_track_vote_by_user_id_and_locality_track_id(session, user_id, locality_track_id)
        if not locality_track_vote:
            raise HTTPException(status_code=404, detail="Vote on track in locality not found for this user")

        await session.delete(locality_track_vote)

        await session.flush()
        session.expunge_all()
        
        return
