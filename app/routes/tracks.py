from fastapi import APIRouter, Depends, Request
from fastapi_cache.decorator import cache

from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.validate_jwt import validate_jwt
from dependencies.validate_admin import validate_admin

from decorators.handle_client_disconnect import handle_client_disconnect

from models.schemas.search_params import SearchParams

from services.providers.deezer_service import DeezerService
from services.providers.spotify_service import SpotifyService
from services.postgresql.track_service import TrackService

from clients.postgresql_client import PostgreSQLClient

from utils.routes.track_utils import get_or_create_track

tracks_router = APIRouter()
postgresql_client = PostgreSQLClient()
track_service = TrackService()

spotify_service = SpotifyService()
deezer_service = DeezerService()

@tracks_router.get("/search")
@handle_client_disconnect
@cache(expire=300)
async def search_tracks(request: Request, search_params: SearchParams = Depends(), session: AsyncSession = Depends(postgresql_client.get_session)):
    search_limit = 20
    offset = search_params.offset

    async with session.begin():
        banned_tracks = await track_service.get_all_banned_tracks(session)
        banned_spotify_ids = {track.spotify_id for track in banned_tracks}


    spotify_response = (await spotify_service.search_tracks(search_params.q, offset, search_limit)).get("tracks", {})
    tracks = spotify_response.get("items", [])

    data = []
    spotify_offset = 0
    
    for track in tracks:
        spotify_id = track.get("id")
        if spotify_id in banned_spotify_ids:
            spotify_offset += 1
            continue
            
        isrc = track.get("external_ids", {}).get("isrc")
        if not isrc:
            spotify_offset += 1
            continue

        
        deezer_id = await deezer_service.fetch_deezer_id_by_isrc(isrc)
        if not deezer_id:
            spotify_offset += 1
            continue

        covers = track.get("album", {}).get("images", [])
        data.append({
            "spotify_id": spotify_id,
            "deezer_id": deezer_id,
            "isrc": isrc,
            "name": track.get("name"),
            "artists": [artist["name"] for artist in track.get("artists", [])],
            "cover": {
                "small": covers[2]["url"] if len(covers) > 2 else None,
                "medium": covers[1]["url"] if len(covers) > 1 else None,
                "large": covers[0]["url"] if len(covers) > 0 else None
            }
        })

    return {
        "next_offset": spotify_offset + offset + search_limit,
        "total_matching_results": spotify_response.get("total", 0),
        "results": data
    }


@tracks_router.patch("/{spotify_track_id}/ban", dependencies=[
    Depends(validate_jwt),
    Depends(validate_admin)
])
async def ban_track(spotify_track_id: str, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        track = await get_or_create_track(session, spotify_track_id)
        await track_service.ban_track_by_track_id(session, track.track_id)
    
    return { "message": f"Successfully banned {track.name}" }


@tracks_router.patch("/{track_id}/unban", dependencies=[
    Depends(validate_jwt),
    Depends(validate_admin)
])
async def unban_track(track_id: int, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        track = await track_service.unban_track_by_track_id(session, track_id)

    return { "message": f"Successfully unbanned {track.name}" }


@tracks_router.get("/banned", dependencies=[
    Depends(validate_jwt),
    Depends(validate_admin)
])
async def get_banned_tracks(session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        banned_tracks = await track_service.get_all_banned_tracks(session)

    return [
        {
            **{k: v for k, v in banned_track.__dict__.items() if k not in {"cover_small", "cover_medium", "cover_large", "deezer_id", "isrc"}},
            "cover": {
                "small": banned_track.cover_small,
                "medium": banned_track.cover_medium,
                "large": banned_track.cover_large
            }
        }
        for banned_track in banned_tracks
    ]