from fastapi import APIRouter, HTTPException, Depends
from models.bounds import Bounds
from urllib.parse import urlencode
import logging

from http_client import get_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

localities_router = APIRouter()

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

    response = await get_client().get(url, timeout=30.0)
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
