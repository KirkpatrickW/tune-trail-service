from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from clients.postgresql_client import PostgreSQLClient

from dependencies.validate_jwt import access_token_data_ctx, validate_jwt

from models.schemas.localities.add_track_to_locality_request import AddTrackToLocalityRequest
from models.schemas.localities.bounds_params import BoundsParams

from services.postgresql.locality_service import LocalityService
from services.postgresql.locality_track_service import LocalityTrackService
from services.postgresql.track_service import TrackService

from services.providers.deezer_service import DeezerService
from services.providers.overpass_service import OverpassService
from services.providers.spotify_service import SpotifyService

localities_router = APIRouter()
postgresql_client = PostgreSQLClient()
locality_service = LocalityService()
track_service = TrackService()
locality_track_service = LocalityTrackService()

spotify_service = SpotifyService()
overpass_service = OverpassService()
deezer_service = DeezerService()

@localities_router.get("")
@cache(expire=300)
async def get_localities(bounds_params: BoundsParams = Depends(), session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        localities = await locality_service.get_localities_by_bounds(session, **bounds_params.model_dump())
        overpass_localities = await overpass_service.get_localities_by_bounds(**bounds_params.model_dump())

    locality_ids = {locality['locality_id'] for locality in localities}
    filtered_overpass_localities = [
        {
            **locality,
            "total_tracks": 0
        }
        for locality in overpass_localities
        if locality["locality_id"] not in locality_ids
    ]

    combined_localities = localities + filtered_overpass_localities

    extracted_point_features = [
        {
            "type": "Feature",
            "properties": {
                "id": locality["locality_id"],
                "name": locality["name"],
                "total_tracks": locality["total_tracks"]
            },
            "geometry": {
                "type": "Point",
                "coordinates": [locality["longitude"], locality["latitude"]],
            }
        }
        for locality in combined_localities
    ]

    return extracted_point_features


@localities_router.get("/{locality_id}/tracks")
async def get_tracks_in_locality(locality_id: int, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        tracks = await track_service.get_tracks_in_locality(session, locality_id)

    return [
        {
            **{k: v for k, v in track.__dict__.items() if k not in {"cover_small", "cover_medium", "cover_large", "deezer_id", "isrc"}},
            "cover": {
                "small": track.cover_small,
                "medium": track.cover_medium,
                "large": track.cover_large
            }
        }
        for track in tracks
    ]


@localities_router.put("/tracks", dependencies=[
    Depends(validate_jwt)
])
async def add_track_to_locality(add_track_to_locality_request: AddTrackToLocalityRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        locality_id = add_track_to_locality_request.locality_id
        locality = await locality_service.get_locality_by_locality_id(session, locality_id)
        if not locality:
            overpass_locality = await overpass_service.get_locality_by_id(locality_id)
            if not overpass_locality:
                raise HTTPException(status_code=404, detail=f"Locality with ID {locality_id} not found in database or Overpass")
            
            locality = await locality_service.add_new_locality(session, locality_id, overpass_locality["name"], overpass_locality["latitude"], overpass_locality["longitude"])

        spotify_track_id = add_track_to_locality_request.spotify_track_id
        track = await track_service.get_track_by_spotify_id(session, spotify_track_id)
        if not track:
            spotify_track = await spotify_service.get_track_by_id(spotify_track_id)
            if not spotify_track:
                raise HTTPException(status_code=404, detail=f"Track with Spotify ID {spotify_track_id} not found in database or Spotify")
            
            isrc = spotify_track["isrc"]
            deezer_id = await deezer_service.fetch_deezer_id_by_isrc(isrc)
            if not deezer_id:
                raise HTTPException(status_code=404, detail=f"ISRC with the value {isrc} not found in Deezer")
            
            covers = spotify_track["cover"]
            track = await track_service.add_new_track(session, isrc, spotify_track_id, deezer_id, spotify_track["name"], spotify_track["artists"], covers["large"], covers["medium"], covers["small"])

        access_token_data = access_token_data_ctx.get()
        user_id = access_token_data["payload"]["user_id"]
        await locality_track_service.add_track_to_locality(session, locality.locality_id, track.track_id, user_id)

    return { "message": f"Successfully added {track.name} to {locality.name}" }