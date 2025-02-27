from urllib.parse import quote
from utils.http_helpers import RetryConfig, handle_retry
import asyncio

ISRC_URL = "https://api.deezer.com/track/isrc:"

class DeezerService:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DeezerService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.rate_limit_event = asyncio.Event()
        self.rate_limit_event.set()

        def validate_rate_limit_body(response_json: dict):
            if response_json.get("error", {}).get("message") == "Quota limit exceeded" and response_json["error"].get("code") == 4:
                return True
            return False

        self.retry_config = RetryConfig(
            self.rate_limit_event,
            max_retries=3,
            retry_after_fallback=5,
            validate_rate_limit_body=validate_rate_limit_body
        )

    async def fetch_track_by_isrc(self, isrc: str):
        return await handle_retry(
            self.retry_config, 
            "GET",
            f"{ISRC_URL}{quote(isrc)}"
        )
