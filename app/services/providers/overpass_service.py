import asyncio
from urllib.parse import urlencode

from clients.http_client import HTTPClient
from utils.http_helpers import RetryConfig, handle_retry

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

class OverpassService:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(OverpassService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance


    def _init(self):
        self.app_token = {"access_token": None, "expires_at": 0}

        self.app_token_lock = asyncio.Lock()
        self.rate_limit_event = asyncio.Event()
        self.rate_limit_event.set()

        self.retry_config = RetryConfig(
            self.rate_limit_event,
            max_retries=3,
            retry_after_fallback=30,
        )

        self.http_client = HTTPClient()

    
    async def get_localities_by_bounds(self, north, east, south, west):
        query = urlencode({
            'data': f"""
                [out:json];
                (
                    node["place"="city"]({south}, {west}, {north}, {east});
                    node["place"="town"]({south}, {west}, {north}, {east});
                    node["place"="village"]({south}, {west}, {north}, {east});
                    node["place"="hamlet"]({south}, {west}, {north}, {east});
                );
                out;
            """
        })

        get_localities_response = await handle_retry(
            self.retry_config,
            "GET",
            f"{OVERPASS_API_URL}?{query}"
        )

        return [
            {
                "locality_id": element["id"],
                "name": element["tags"].get("name", ""),
                "latitude": element["lat"],
                "longitude": element["lon"]
            }
            for element in get_localities_response.get("elements", [])
            if "tags" in element and "name" in element["tags"]
        ]
    

    async def get_locality_by_id(self, locality_id):
        query = urlencode({
            'data': f"""
                [out:json];
                node({locality_id});
                out;
            """
        })

        response = await handle_retry(
            self.retry_config,
            "GET",
            f"{OVERPASS_API_URL}?{query}"
        )

        elements = response.get("elements", [])
        if elements and "tags" in elements[0] and "name" in elements[0]["tags"]:
            element = elements[0]
            return {
                "locality_id": element["id"],
                "name": element["tags"].get("name", ""),
                "latitude": element["lat"],
                "longitude": element["lon"]
            }
        return None