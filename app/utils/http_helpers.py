from dataclasses import dataclass
from fastapi import HTTPException, Request
from http_client import get_client
from httpx import HTTPStatusError
import asyncio

from config.logger import logger

@dataclass
class RetryConfig:
    rate_limit_event: asyncio.Event
    max_retries: int
    retry_after_fallback: int
    validate_rate_limit_body: callable = None


async def handle_rate_limit(rate_limit_event: asyncio.Event, retry_after: int):
    if rate_limit_event.is_set():
        rate_limit_event.clear()
        await asyncio.sleep(retry_after)
        rate_limit_event.set()


async def handle_retry(retry_config: RetryConfig, url: str, params: dict = None, headers: dict = None):
    for _ in range(retry_config.max_retries):
        await retry_config.rate_limit_event.wait()

        try:
            response = await get_client().get(url, params=params, headers=headers)
            response.raise_for_status()

            response_json = response.json()

            if retry_config.validate_rate_limit_body and retry_config.validate_rate_limit_body(response_json):
                retry_after = int(response.headers.get("Retry-After", retry_config.retry_after_fallback))
                await handle_rate_limit(retry_config.rate_limit_event, retry_after)
                continue

            return response_json
        
        except HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", retry_config.retry_after_fallback))
                await handle_rate_limit(retry_config.rate_limit_event, retry_after)
                continue
            
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    raise HTTPException(status_code=500, detail="API rate limit exceeded or unexpected error")