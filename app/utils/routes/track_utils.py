from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.providers.deezer_service import DeezerService
from services.providers.spotify_service import SpotifyService
from services.postgresql.track_service import TrackService

track_service = TrackService()
spotify_service = SpotifyService()
deezer_service = DeezerService()

async def get_or_create_track(session: AsyncSession, spotify_track_id: str):
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

    return track