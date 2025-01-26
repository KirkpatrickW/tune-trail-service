import httpx
from fastapi import APIRouter, HTTPException
from models.bounds import Bounds
from urllib.parse import urlencode
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

localities_router = APIRouter()

@localities_router.get("/")
async def get_localities(bounds: Bounds):
    query = urlencode(f"""
        [out:json];
        (
            node["place"="city"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
            node["place"="town"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
            node["place"="village"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
            node["place"="hamlet"]({bounds.south}, {bounds.west}, {bounds.north}, {bounds.east});
        );
        out;
    """)
    url = f"https://overpass-api.de/api/interpreter?data={query}"
    logger.info(f"Beginning to fetch data from Overpass API: {url}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error fetching localities")
        
        data = response.json()
        logger.info(f"Raw data received from Overpass API: {data}")

        extracted_point_features = [
            {
                "type": "Feature",
                "properties": {"name": element["tags"]["name"]},
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