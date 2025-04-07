from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.validate_jwt import access_token_data_ctx, validate_jwt
from clients.postgresql_client import PostgreSQLClient

from models.schemas.locality_tracks.vote_on_locality_track_request import VoteOnTrackLocalityRequest

from services.postgresql.locality_track_vote_service import LocalityTrackVoteService
from services.postgresql.locality_track_service import LocalityTrackService

locality_tracks_router = APIRouter()
postgresql_client = PostgreSQLClient()

locality_track_vote_service = LocalityTrackVoteService()
locality_track_service = LocalityTrackService()

vote_action_map = {
    1: "upvoted",
    0: "unvoted",
    -1: "downvoted"
}

@locality_tracks_router.patch("/{locality_track_id}/vote", dependencies=[
    Depends(validate_jwt)
])
async def vote_on_locality_track(locality_track_id: int, vote_on_locality_track_request: VoteOnTrackLocalityRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    user_id = access_token_data["payload"]["user_id"]

    async with session.begin():
        vote_value = vote_on_locality_track_request.vote_value
        if vote_value == 0:
            await locality_track_vote_service.unvote_locality_track(session, locality_track_id, user_id)
        else:
            await locality_track_vote_service.vote_locality_track(session, locality_track_id, user_id, vote_value)

    return { "message": f"Successfully {vote_action_map.get(vote_value, "voted")} track"}

@locality_tracks_router.delete("/{locality_track_id}", dependencies=[
    Depends(validate_jwt)
])
async def delete_locality_track(locality_track_id: int, session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    access_token = access_token_data["payload"]

    async with session.begin():
        locality_track = await locality_track_service.get_locality_track_by_locality_track_id(session, locality_track_id)
        
        if locality_track is None:
            raise HTTPException(status_code=404, detail="Track in Locality not found")

        if not access_token["is_admin"] and access_token["user_id"] != locality_track.user_id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        await locality_track_service.delete_locality_track_by_locality_track_id(session, locality_track_id)

    return { "message": f"Sucessfully deleted Track from Locality" }