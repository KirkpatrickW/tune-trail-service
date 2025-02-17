from fastapi import HTTPException
from clients.http_client import HTTPClient
from utils.http_helpers import RetryConfig, handle_retry
import asyncio
import time

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"

CLIENT_ID = "cbdfa4fd597743bf814729bfd1595f82"
CLIENT_SECRET = "0c93e6f13ff54d998cfc055ab0f0dcd9"

token = {"access_token": None, "expires_at": 0}
token_lock = asyncio.Lock()

rate_limit_event = asyncio.Event()
rate_limit_event.set()

retry_config = RetryConfig(
    rate_limit_event,
    max_retries=3,
    retry_after_fallback=30,
)

http_client = HTTPClient()

async def fetch_token():
    async with token_lock:
        if token["access_token"] and time.time() < token["expires_at"]:
            return token["access_token"]

        response = await http_client.post(
            TOKEN_URL, 
            auth=(CLIENT_ID, CLIENT_SECRET), 
            data={"grant_type": "client_credentials"}
        )

        if response.status_code == 200:
            token_data = response.json()
            token.update({
                "access_token": token_data["access_token"],
                "expires_at": time.time() + token_data["expires_in"] - 60
            })
            return token["access_token"]

        raise HTTPException(status_code=response.status_code, detail="Failed to obtain Spotify token")
        

async def search_tracks(query: str, offset: int, limit: int):
    token = await fetch_token()
    headers = { "Authorization": f"Bearer {token}" }
    params = { "q": query, "type": "track", "offset": offset, "limit": limit }

    return await handle_retry(retry_config, SEARCH_URL, params, headers)
