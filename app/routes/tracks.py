from fastapi import APIRouter, Depends, HTTPException

from decorators.handle_client_disconnect import handle_client_disconnect
from models.schemas.tracks.search_tracks_params import SearchTracksParams
from services.providers.deezer_service import DeezerService
from services.providers.spotify_service import SpotifyService

spotify_service = SpotifyService()
deezer_service = DeezerService()

tracks_router = APIRouter()

@tracks_router.get("/search")
@handle_client_disconnect
async def search_tracks(search_tracks_params: SearchTracksParams = Depends()):
    search_limit = 20
    offset = search_tracks_params.offset

    try:
        spotify_response = (await spotify_service.search_tracks(search_tracks_params.q, offset, search_limit)).get("tracks", {})
        tracks = spotify_response.get("items", [])

        data = []
        spotify_offset = 0
        
        for track in tracks:
            isrc = track.get("external_ids", {}).get("isrc")
            if not isrc:
                spotify_offset += 1
                continue

            deezer_response = await deezer_service.fetch_track_by_isrc(isrc)
            if not deezer_response or deezer_response.get("error"):
                spotify_offset += 1
                continue

            covers = track.get("album", {}).get("images", [])
            data.append({
                "spotify_id": track.get("id"),
                "deezer_id": deezer_response.get("id"),
                "isrc": isrc,
                "name": track.get("name"),
                "artists": [artist["name"] for artist in track.get("artists", [])],
                "cover": {
                    "small": covers[2]["url"] if len(covers) > 2 else None,
                    "medium": covers[1]["url"] if len(covers) > 1 else None,
                    "large": covers[0]["url"] if len(covers) > 0 else None
                },
                "preview_url": deezer_response.get("preview")
            })

        return {
            "next_offset": spotify_offset + offset + search_limit,
            "total_matching_results": spotify_response.get("total", 0),
            "results": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
