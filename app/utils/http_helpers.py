from dataclasses import dataclass
from fastapi import HTTPException
from clients.http_client import HTTPClient
from httpx import HTTPStatusError
import asyncio

http_client = HTTPClient()

METHODS = {
    'GET': http_client.get,
    'POST': http_client.post,
    'PUT': http_client.put,
    'DELETE': http_client.delete,
}

METHOD_ARGUMENTS = {
    "GET": {"params"},
    "DELETE": {"params"},
    "POST": {"params", "json", "data"},
    "PUT": {"params", "json", "data"},
    "PATCH": {"params", "json", "data"},
}

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


async def handle_retry(
    retry_config: RetryConfig,
    method: str,
    url: str,
    params: dict = None,
    headers: dict = None,
    auth: tuple = None,
    data: dict = None,
    json: dict = None
):
    method = method.upper()
    method_function = METHODS.get(method)
    if not method_function:
        raise HTTPException(status_code=400, detail="Unsupported HTTP method")

    allowed_args = METHOD_ARGUMENTS.get(method, set())
    if "data" not in allowed_args and data is not None:
        raise HTTPException(status_code=400, detail=f"{method} requests cannot have a body")
    if "json" not in allowed_args and json is not None:
        raise HTTPException(status_code=400, detail=f"{method} requests cannot have a JSON body")

    for _ in range(retry_config.max_retries):
        await retry_config.rate_limit_event.wait()

        try:
            kwargs = {"url": url, "headers": headers, "auth": auth}
            if "params" in allowed_args:
                kwargs["params"] = params
            if "json" in allowed_args and json is not None:
                kwargs["json"] = json
            elif "data" in allowed_args and data is not None:
                kwargs["data"] = data

            response = await method_function(**kwargs)
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