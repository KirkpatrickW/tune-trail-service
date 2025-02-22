import logging.config
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.supervisors.statreload import StatReload
from clients.postgresql_client import PostgreSQLClient

from config.logger import LOGGING_CONFIG
from clients.http_client import HTTPClient
from middleware.correlation_id import CorrelationIdMiddleware
from routes.localities import localities_router
from routes.tracks import tracks_router
from lifecycle.lifespan_manager import create_lifespan
from lifecycle.reload_with_flag_handler import reload_with_flag_handler
from services.postgresql_server_manager import PostgreSQLServerManager

logging.config.dictConfig(LOGGING_CONFIG)
StatReload.run = reload_with_flag_handler

def on_reload_startup():
    PostgreSQLClient().run_migrations()

def on_startup():
    PostgreSQLServerManager().start_server()
    on_reload_startup()

async def on_reload_shutdown():
    await HTTPClient().aclose()

def on_shutdown():
    on_reload_shutdown()
    PostgreSQLServerManager().stop_server()

lifespan = create_lifespan(
    on_reload_startup=on_reload_startup,
    on_startup=on_startup,
    on_reload_shutdown=on_reload_shutdown,
    on_shutdown=on_shutdown
)

app = FastAPI(lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(localities_router, prefix="/localities")
app.include_router(tracks_router, prefix="/tracks")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
