import logging.config
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from config.logger import LOGGING_CONFIG, logger, correlation_id_ctx
from http_client import client
from routes.localities import localities_router
from routes.tracks import tracks_router

logging.config.dictConfig(LOGGING_CONFIG)


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


origins = ["*"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(localities_router, prefix="/localities")
app.include_router(tracks_router, prefix="/tracks")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
