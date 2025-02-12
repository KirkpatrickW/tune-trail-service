from urllib.parse import quote
from utils.http_helpers import RetryConfig, handle_retry
import asyncio

ISRC_URL = "https://api.deezer.com/track/isrc:"

rate_limit_event = asyncio.Event()
rate_limit_event.set()

def validate_rate_limit_body(response_json: dict):
    if response_json.get("error", {}).get("message") == "Quota limit exceeded" and response_json["error"].get("code") == 4:
        return True
    return False

retry_config = RetryConfig(
    rate_limit_event,
    max_retries=3,
    retry_after_fallback=5,
    validate_rate_limit_body=validate_rate_limit_body
)

async def fetch_track_by_isrc(isrc: str):
    encoded_isrc = quote(isrc)
    return await handle_retry(retry_config, f"{ISRC_URL}{encoded_isrc}")