import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config.logger import logger, correlation_id_ctx

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_ctx.set(correlation_id)

        # The need to manually save `is_disconnected` arises due to a bug in Starlette where `request.is_disconnected()` 
        # may not update correctly during asynchronous tasks. By saving it to `request.state.is_disconnected`, we ensure 
        # its value is consistently available throughout the request lifecycle, even when the connection state changes.
        request.state.is_disconnected = request.is_disconnected

        logger.info(f"Request received: {request.method} {request.url}")
        response = await call_next(request)

        response.headers["X-Correlation-ID"] = correlation_id

        return response