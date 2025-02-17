from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.logger import Logger
from clients.postgresql_client import PostgreSQLClient
from clients.http_client import HTTPClient
from models.schemas.locality_track_request import TrackLocalityRequest
from models.bounds import Bounds

from sqlalchemy.exc import IntegrityError

logger = Logger()
http_client = HTTPClient()

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

localities_router = APIRouter()
postgresql_client = PostgreSQLClient()

@localities_router.get("/")
async def get_localities(bounds: Bounds = Depends()):
    query = urlencode({
        'data': f"""
            [out:json];
            (
                node["place"="city"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
                node["place"="town"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
                node["place"="village"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
                node["place"="hamlet"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
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
    logger.info(f"Raw data received from Overpass API: {len(data.get("elements", []))} entries found")

    extracted_point_features = [
        {
            "type": "Feature",
            "properties": {
                "id": element["id"],
                "name": element["tags"]["name"]
            },
            "geometry": {
                "type": "Point",
                "coordinates": [element["lon"], element["lat"]],
            }
        }
        for element in data.get("elements", [])
        if "tags" in element and "name" in element["tags"]
    ]
    logger.info(f"Extracted point features: {extracted_point_features}")

    return extracted_point_features


@localities_router.get("/{id}")
async def get_locality(id: int):
    query = urlencode({
        'data': f"""
            [out:json];
            node({id});
            out body;
        """
    })
    url = f"{OVERPASS_API_URL}?{query}"
    logger.info(f"Fetching data for specific locality with ID {id} from Overpass API: {url}")


@localities_router.put("/tracks")
async def add_track_to_locality(payload: TrackLocalityRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    try:
        async with session.begin():
            locality = await postgresql_client.get_or_create_locality(session, **payload.locality.model_dump())
            track = await postgresql_client.get_or_create_track(session, payload.track.model_dump())

            await postgresql_client.link_track_to_locality(session, locality.locality_id, track.track_id)

        return {
            "message": "Track successfully added to locality.",
            "locality": locality.name,
            "track": track.name,
        }
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Integrity error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")