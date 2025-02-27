from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.logger import Logger
from clients.http_client import HTTPClient
from clients.postgresql_client import PostgreSQLClient
from models.schemas.localities.bounds_params import BoundsParams
from models.schemas.localities.locality_track_request import LocalityTrackRequest
from services.postgresql.locality_service import LocalityService

logger = Logger()
http_client = HTTPClient()

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

localities_router = APIRouter()
postgresql_client = PostgreSQLClient()
locality_service = LocalityService()

@localities_router.get("")
async def get_localities(bounds_params: BoundsParams = Depends(), session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        localities = await locality_service.get_localities(session, **bounds_params.model_dump())
    
    locality_ids = {locality['locality_id'] for locality in localities}

    query = urlencode({
        'data': f"""
            [out:json];
            (
                node["place"="city"]({bounds_params.south}, {bounds_params.west}, {bounds_params.north}, {bounds_params.east});
                node["place"="town"]({bounds_params.south}, {bounds_params.west}, {bounds_params.north}, {bounds_params.east});
                node["place"="village"]({bounds_params.south}, {bounds_params.west}, {bounds_params.north}, {bounds_params.east});
                node["place"="hamlet"]({bounds_params.south}, {bounds_params.west}, {bounds_params.north}, {bounds_params.east});
            );
            out;
        """
    })

    url = f"{OVERPASS_API_URL}?{query}"
    logger.info(f"Beginning to fetch data from Overpass API: {url}")

    response = await http_client.get(url, timeout=30.0)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching localities")
    
    data = response.json()
    logger.info(f"Raw data received from Overpass API: {len(data.get('elements', []))} entries found")

    overpass_localities = [
        {
            "locality_id": element["id"],
            "name": element["tags"].get("name", ""),
            "latitude": element["lat"],
            "longitude": element["lon"],
            "track_count": 0
        }
        for element in data.get("elements", [])
        if "tags" in element and "name" in element["tags"] and element["id"] not in locality_ids
    ]

    combined_localities = localities + overpass_localities

    extracted_point_features = [
        {
            "type": "Feature",
            "properties": {
                "id": locality["locality_id"],
                "name": locality["name"],
                "track_count": locality["track_count"]
            },
            "geometry": {
                "type": "Point",
                "coordinates": [locality["longitude"], locality["latitude"]],
            }
        }
        for locality in combined_localities
    ]

    logger.info(f"Extracted point features: {extracted_point_features}")

    return extracted_point_features


@localities_router.get("/{locality_id}/tracks")
async def get_tracks_in_locality(locality_id: int, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        tracks = await locality_service.get_tracks_in_locality(session, locality_id)

    return [
        {
            **{k: v for k, v in track.__dict__.items() if k not in {"cover_small", "cover_medium", "cover_large"}},
            "cover": {
                "small": track.cover_small,
                "medium": track.cover_medium,
                "large": track.cover_large
            }
        }
        for track in tracks
    ]


@localities_router.put("/tracks")
async def add_track_to_locality(locality_track_request: LocalityTrackRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        locality = await locality_service.get_or_create_locality(session, **locality_track_request.locality.model_dump())
        track = await locality_service.get_or_create_track(session, locality_track_request.track.model_dump())

        await locality_service.link_track_to_locality(session, locality.locality_id, track.track_id)

    return {
        "locality": locality,
        "track": track,
    }