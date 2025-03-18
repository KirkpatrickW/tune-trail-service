from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config.logger import Logger

logger = Logger()

class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(e)
            raise e