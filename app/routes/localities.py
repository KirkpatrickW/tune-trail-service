from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.logger import Logger
from clients.postgresql_client import PostgreSQLClient
from clients.http_client import HTTPClient
from models.schemas.locality_track_request import LocalityTrackRequest
from models.schemas.bounds_request import BoundsRequest

logger = Logger()
http_client = HTTPClient()

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

localities_router = APIRouter()
postgresql_client = PostgreSQLClient()

@localities_router.get("")
async def get_localities(bounds_request: BoundsRequest = Depends(), session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        localities = await postgresql_client.get_localities(session, **bounds_request.model_dump())
    
    locality_ids = {locality['locality_id'] for locality in localities}

    query = urlencode({
        'data': f"""
            [out:json];
            (
                node["place"="city"]({bounds_request.south}, {bounds_request.west}, {bounds_request.north}, {bounds_request.east});
                node["place"="town"]({bounds_request.south}, {bounds_request.west}, {bounds_request.north}, {bounds_request.east});
                node["place"="village"]({bounds_request.south}, {bounds_request.west}, {bounds_request.north}, {bounds_request.east});
                node["place"="hamlet"]({bounds_request.south}, {bounds_request.west}, {bounds_request.north}, {bounds_request.east});
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


@localities_router.put("/tracks")
async def add_track_to_locality(locality_track_request: LocalityTrackRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        locality = await postgresql_client.get_or_create_locality(session, **locality_track_request.locality.model_dump())
        track = await postgresql_client.get_or_create_track(session, locality_track_request.track.model_dump())

        await postgresql_client.link_track_to_locality(session, locality.locality_id, track.track_id)

    return {
        "message": "Track successfully added to locality.",
        "locality": locality.name,
        "track": track.name,
    }