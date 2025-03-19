from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas.locality_tracks.vote_on_locality_track_request import VoteOnTrackLocalityRequest, VoteValueEnum
from services.postgresql.locality_track_vote_service import LocalityTrackVoteService

from dependencies.validate_jwt import access_token_data_ctx, validate_jwt
from clients.postgresql_client import PostgreSQLClient

locality_tracks_router = APIRouter()
postgresql_client = PostgreSQLClient()

locality_track_vote_service = LocalityTrackVoteService()

@locality_tracks_router.patch("/{locality_track_id}/vote", dependencies=[
    Depends(validate_jwt)
])
async def vote_on_locality_track(locality_track_id: int, vote_on_locality_track_request: VoteOnTrackLocalityRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    user_id = access_token_data["payload"]["user_id"]

    async with session.begin():
        vote_value = vote_on_locality_track_request.vote_value
        if vote_value == VoteValueEnum.UNVOTE:
            await locality_track_vote_service.unvote_locality_track(session, locality_track_id, user_id)
        else:
            await locality_track_vote_service.vote_locality_track(session, locality_track_id, user_id, vote_value)

    return { "message": f"Successfully {vote_value.name.lower()}d track"}